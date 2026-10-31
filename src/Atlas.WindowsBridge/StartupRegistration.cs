using Microsoft.Win32;

namespace Atlas.WindowsBridge;

/// <summary>Manages only the current user's Windows startup Run entry.</summary>
public sealed class StartupRegistration
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string ValueName = "Atlas";

    public void SetEnabled(bool enabled, string? executablePath = null)
    {
        using var key = Registry.CurrentUser.CreateSubKey(RunKeyPath, writable: true)
            ?? throw new InvalidOperationException("Não foi possível acessar as configurações de inicialização do usuário.");

        if (!enabled)
        {
            key.DeleteValue(ValueName, throwOnMissingValue: false);
            return;
        }

        var path = executablePath ?? Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(path) || !Path.IsPathFullyQualified(path) || !File.Exists(path))
            throw new InvalidOperationException("Não foi possível localizar o executável instalado do Atlas.");

        key.SetValue(ValueName, string.Concat('"', path, '"'));
    }
}
