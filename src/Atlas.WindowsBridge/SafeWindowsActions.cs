using System.ComponentModel;
using System.Diagnostics;

namespace Atlas.WindowsBridge;

/// <summary>
/// Narrow, consent-gated Windows integration surface. It deliberately does not
/// expose arbitrary command execution, PowerShell, cmd.exe, or shell arguments.
/// </summary>
public sealed class SafeWindowsActions
{
    public Uri ValidateExternalUri(string value, bool userConfirmed)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(value);
        if (!userConfirmed)
            throw new UnauthorizedAccessException("Esta ação exige confirmação explícita do usuário.");

        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp) ||
            string.IsNullOrWhiteSpace(uri.Host) ||
            !string.IsNullOrEmpty(uri.UserInfo))
            throw new ArgumentException("Somente endereços HTTP ou HTTPS válidos são permitidos.", nameof(value));

        return uri;
    }

    public void OpenExternalUri(string value, bool userConfirmed)
    {
        var uri = ValidateExternalUri(value, userConfirmed);
        try
        {
            Process.Start(new ProcessStartInfo(uri.AbsoluteUri) { UseShellExecute = true });
        }
        catch (Win32Exception exception)
        {
            throw new InvalidOperationException("O Windows não conseguiu abrir o endereço no navegador padrão.", exception);
        }
    }
}
