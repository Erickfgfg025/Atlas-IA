using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Text;
using Atlas.Application.Security;

namespace Atlas.Infrastructure.Security;

/// <summary>
/// Stores secrets encrypted with Windows DPAPI, scoped to the current Windows user.
/// The files are not portable to another Windows user or machine.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class ProtectedDataSecretStore : ISecretStore
{
    private static readonly byte[] ApplicationEntropy = Encoding.UTF8.GetBytes("Atlas.Desktop.SecretStore.v1");
    private readonly string _directory;
    private readonly SemaphoreSlim _gate = new(1, 1);

    public ProtectedDataSecretStore(string? directory = null)
    {
        if (!OperatingSystem.IsWindows())
            throw new PlatformNotSupportedException("O armazenamento protegido do Atlas exige Windows.");

        _directory = directory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Atlas",
            "Secrets");
    }

    public async Task SetAsync(string key, string secret, CancellationToken cancellationToken = default)
    {
        ValidateKey(key);
        ArgumentException.ThrowIfNullOrWhiteSpace(secret);

        await _gate.WaitAsync(cancellationToken);
        string? temporaryPath = null;
        byte[]? plaintext = null;
        byte[]? protectedBytes = null;
        try
        {
            Directory.CreateDirectory(_directory);
            var path = GetPath(key);
            temporaryPath = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            plaintext = Encoding.UTF8.GetBytes(secret);
            var entropy = GetEntropy(key);
            try
            {
                protectedBytes = ProtectedData.Protect(
                    plaintext, entropy, DataProtectionScope.CurrentUser);
            }
            finally
            {
                CryptographicOperations.ZeroMemory(entropy);
            }

            await using (var stream = new FileStream(
                temporaryPath, FileMode.CreateNew, FileAccess.Write, FileShare.None,
                bufferSize: 4096, FileOptions.Asynchronous | FileOptions.WriteThrough))
            {
                await stream.WriteAsync(protectedBytes, cancellationToken);
                await stream.FlushAsync(cancellationToken);
            }

            File.Move(temporaryPath, path, overwrite: true);
        }
        finally
        {
            if (plaintext is not null)
                CryptographicOperations.ZeroMemory(plaintext);
            if (protectedBytes is not null)
                CryptographicOperations.ZeroMemory(protectedBytes);

            try
            {
                if (temporaryPath is not null && File.Exists(temporaryPath))
                    File.Delete(temporaryPath);
            }
            finally
            {
                _gate.Release();
            }
        }
    }

    public async Task<string?> GetAsync(string key, CancellationToken cancellationToken = default)
    {
        ValidateKey(key);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var path = GetPath(key);
            if (!File.Exists(path))
                return null;

            var protectedBytes = await File.ReadAllBytesAsync(path, cancellationToken);
            byte[]? plaintext = null;
            var entropy = GetEntropy(key);
            try
            {
                plaintext = ProtectedData.Unprotect(
                    protectedBytes, entropy, DataProtectionScope.CurrentUser);
                return new UTF8Encoding(false, true).GetString(plaintext);
            }
            catch (CryptographicException)
            {
                throw new InvalidOperationException(
                    "Não foi possível desbloquear a credencial deste usuário do Windows.");
            }
            finally
            {
                CryptographicOperations.ZeroMemory(protectedBytes);
                CryptographicOperations.ZeroMemory(entropy);
                if (plaintext is not null)
                    CryptographicOperations.ZeroMemory(plaintext);
            }
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task<bool> DeleteAsync(string key, CancellationToken cancellationToken = default)
    {
        ValidateKey(key);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var path = GetPath(key);
            if (!File.Exists(path))
                return false;

            File.Delete(path);
            return true;
        }
        finally
        {
            _gate.Release();
        }
    }

    private string GetPath(string key)
    {
        var keyBytes = Encoding.UTF8.GetBytes(key);
        try
        {
            var hash = Convert.ToHexString(SHA256.HashData(keyBytes));
            return Path.Combine(_directory, hash + ".dpapi");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(keyBytes);
        }
    }

    private static byte[] GetEntropy(string key)
    {
        var keyBytes = Encoding.UTF8.GetBytes(key);
        try
        {
            var entropy = new byte[ApplicationEntropy.Length + keyBytes.Length];
            Buffer.BlockCopy(ApplicationEntropy, 0, entropy, 0, ApplicationEntropy.Length);
            Buffer.BlockCopy(keyBytes, 0, entropy, ApplicationEntropy.Length, keyBytes.Length);
            return entropy;
        }
        finally
        {
            CryptographicOperations.ZeroMemory(keyBytes);
        }
    }

    private static void ValidateKey(string key)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);
        if (key.Length > 128)
            throw new ArgumentOutOfRangeException(nameof(key), "A chave deve ter até 128 caracteres.");
    }
}
