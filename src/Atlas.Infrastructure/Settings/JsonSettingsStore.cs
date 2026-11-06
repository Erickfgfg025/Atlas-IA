using System.Text.Json;
using Atlas.Application.Settings;

namespace Atlas.Infrastructure.Settings;

public sealed class JsonSettingsStore : ISettingsStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    private readonly string _filePath;
    private readonly SemaphoreSlim _gate = new(1, 1);

    public JsonSettingsStore(string? filePath = null)
    {
        _filePath = filePath ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Atlas",
            "settings.json");
    }

    /// <summary>
    /// Paths the unreadable file was moved to during the last load, if any. Lets the
    /// caller report that local preferences were reset instead of failing to start.
    /// </summary>
    public string? QuarantinedFilePath { get; private set; }

    public async Task<AtlasSettings> LoadAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            QuarantinedFilePath = null;
            if (!File.Exists(_filePath))
                return new AtlasSettings();

            try
            {
                await using var stream = new FileStream(
                    _filePath, FileMode.Open, FileAccess.Read, FileShare.Read,
                    bufferSize: 4096, FileOptions.Asynchronous | FileOptions.SequentialScan);

                var settings = await JsonSerializer.DeserializeAsync<AtlasSettings>(
                    stream, JsonOptions, cancellationToken);

                return (settings ?? new AtlasSettings()).Validate();
            }
            catch (Exception exception) when (exception is JsonException or ArgumentException or NotSupportedException)
            {
                // A truncated file (power loss), a hand-edited value or a file written by
                // an older build must not lock the user out of every preference: keep the
                // unusable copy for inspection and start from the defaults.
                QuarantineUnreadableSettings();
                return new AtlasSettings();
            }
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task SaveAsync(AtlasSettings settings, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(settings);
        settings = settings.Validate();

        await _gate.WaitAsync(cancellationToken);
        var temporaryPath = _filePath + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            var directory = Path.GetDirectoryName(_filePath);
            if (!string.IsNullOrWhiteSpace(directory))
                Directory.CreateDirectory(directory);

            await using (var stream = new FileStream(
                temporaryPath, FileMode.CreateNew, FileAccess.Write, FileShare.None,
                bufferSize: 4096, FileOptions.Asynchronous | FileOptions.WriteThrough))
            {
                await JsonSerializer.SerializeAsync(stream, settings, JsonOptions, cancellationToken);
                await stream.FlushAsync(cancellationToken);
            }

            File.Move(temporaryPath, _filePath, overwrite: true);
        }
        finally
        {
            try
            {
                if (File.Exists(temporaryPath))
                    File.Delete(temporaryPath);
            }
            finally
            {
                _gate.Release();
            }
        }
    }

    private void QuarantineUnreadableSettings()
    {
        try
        {
            var quarantined = _filePath + ".invalid-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmssfff");
            File.Move(_filePath, quarantined, overwrite: true);
            QuarantinedFilePath = quarantined;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // Reading may have failed for a transient reason (locked file). Leaving the
            // file in place keeps the user's data for a later attempt.
        }
    }
}
