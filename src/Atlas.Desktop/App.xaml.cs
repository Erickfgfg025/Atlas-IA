using System;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Atlas.AI;
using Atlas.Application.AI;
using Atlas.Application.Memory;
using Atlas.Memory;
using Atlas.Application.Security;
using Atlas.Application.Settings;
using Atlas.Infrastructure.Security;
using Atlas.Infrastructure.Settings;
using Microsoft.UI.Xaml;

namespace Atlas.Desktop;

public partial class App : Microsoft.UI.Xaml.Application
{
    private const long MaxDiagnosticLogBytes = 1_048_576; // 1 MiB
    private const uint MessageBoxIconError = 0x10;

    private Window? _window;
    private readonly HttpClient _httpClient = new();

    public App()
    {
        // Register diagnostics before loading App.xaml resources so failures during
        // XAML initialization have a chance to be recorded.
        UnhandledException += OnUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandledException;
        try
        {
            InitializeComponent();
        }
        catch (Exception exception)
        {
            WriteStartupDiagnostic("App.InitializeComponent", exception);
            if (exception is Microsoft.UI.Xaml.Markup.XamlParseException)
                WriteStartupCanaries();
            ShowStartupFailure(exception);
        }
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        try
        {
            var settingsStore = new JsonSettingsStore();
            ISecretStore secretStore = new ProtectedDataSecretStore();
            var providers = new Dictionary<string, IModelProvider>(StringComparer.Ordinal)
            {
                ["Gemini"] = new GeminiModelProvider(_httpClient, secretStore),
                ["Ollama"] = new OllamaModelProvider(_httpClient, settingsStore),
                ["Hermes"] = new HermesAgentProvider()
            };
            var memoryStore = new MarkdownMemoryStore(MemoryVaultOptions.CreateDefault());
            IModelRouter providerRouter = new SettingsModelRouter(settingsStore, providers);
            IModelRouter modelRouter = new MemoryAwareModelRouter(settingsStore, memoryStore, providerRouter);

            _window = new MainWindow(settingsStore, modelRouter, secretStore, memoryStore);
            _window.Activate();
        }
        catch (Exception exception)
        {
            WriteStartupDiagnostic("OnLaunched", exception);
            if (exception is Microsoft.UI.Xaml.Markup.XamlParseException)
                WriteStartupCanaries();
            ShowStartupFailure(exception);
        }
    }

    private void OnUnhandledException(object sender, Microsoft.UI.Xaml.UnhandledExceptionEventArgs args)
    {
        WriteStartupDiagnostic("WinUI.UnhandledException", args.Exception);
        // Keep the default crash behavior; swallowing a partially initialized XAML
        // exception can leave the application in an invalid state.
    }

    private void OnDomainUnhandledException(object sender, System.UnhandledExceptionEventArgs args)
    {
        if (args.ExceptionObject is Exception exception)
            WriteStartupDiagnostic("AppDomain.UnhandledException", exception);
        else
            WriteStartupDiagnostic("AppDomain.UnhandledException", new Exception(
                Convert.ToString(args.ExceptionObject) ?? "Unknown unhandled exception"));
    }

    /// <summary>
    /// Presents a fatal startup failure to the user with the full exception chain
    /// (including the inner exceptions a XamlParseException carries) and the log
    /// location, then terminates instead of leaving a silent crash behind.
    /// </summary>
    [DoesNotReturn]
    private static void ShowStartupFailure(Exception exception)
    {
        var logPath = GetDiagnosticLogPath();
        var header = exception is Microsoft.UI.Xaml.Markup.XamlParseException
            ? "O Atlas não conseguiu carregar a interface (XAML).\n\n" +
              "Detalhes técnicos abaixo: envie o registro indicado ao final para " +
              "diagnóstico. Se os arquivos do Windows App SDK estiverem ausentes, " +
              "reinstale o Atlas.\n\n"
            : "O Atlas não conseguiu iniciar.\n\n";
        var message = header +
                      DescribeExceptionChain(exception) +
                      "\n\nRegistro completo:\n" + logPath;

        try
        {
            MessageBox(IntPtr.Zero, message, "Atlas — falha de inicialização", MessageBoxIconError);
        }
        finally
        {
            Environment.Exit(1);
        }
    }

    private static string DescribeExceptionChain(Exception exception)
    {
        var builder = new StringBuilder();
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            builder.Append(current.GetType().FullName)
                   .Append(" (0x").Append(current.HResult.ToString("X8")).AppendLine(")")
                   .AppendLine(current.Message);
            foreach (System.Collections.DictionaryEntry entry in current.Data)
            {
                builder.Append("  Data[").Append(entry.Key).Append("] = ")
                       .AppendLine(Convert.ToString(entry.Value) ?? "(null)");
            }
        }
        return builder.ToString().TrimEnd();
    }

    /// <summary>
    /// Isolates the cause of a XamlParseException that carries no inner exception:
    /// verifies payload files next to the executable, that the application brushes
    /// resolve, that a parse-time StaticResource lookup succeeds, and that the
    /// custom sound-wave control can be activated. Never throws; results are
    /// appended to the diagnostic log.
    /// </summary>
    private static void WriteStartupCanaries()
    {
        try
        {
            var report = new StringBuilder();
            foreach (var fileName in new[]
                     {
                         "resources.pri", "Microsoft.ui.xaml.dll", "Microsoft.WindowsAppRuntime.dll"
                     })
            {
                var path = Path.Combine(AppContext.BaseDirectory, fileName);
                report.Append(fileName).Append(": ");
                report.AppendLine(File.Exists(path)
                    ? new FileInfo(path).Length + " bytes"
                    : "MISSING");
            }

            try
            {
                var dictionary = Application.Current?.Resources;
                if (dictionary is null)
                {
                    report.AppendLine("App resources: Application.Current.Resources is null");
                }
                else
                {
                    var brush = dictionary["AtlasBackgroundBrush"];
                    report.Append("App resource AtlasBackgroundBrush: ")
                          .AppendLine(brush is null ? "NOT FOUND" : brush.GetType().FullName ?? "unknown");
                }
            }
            catch (Exception exception)
            {
                report.Append("App resource AtlasBackgroundBrush: FAILED ")
                      .Append(exception.GetType().Name)
                      .Append(" (0x").Append(exception.HResult.ToString("X8")).Append(") ")
                      .AppendLine(exception.Message);
            }

            try
            {
                Microsoft.UI.Xaml.Markup.XamlReader.Load(
                    "<Border xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\" " +
                    "Background=\"{StaticResource AtlasBackgroundBrush}\"/>");
                report.AppendLine("Parse-time StaticResource probe: OK");
            }
            catch (Exception exception)
            {
                report.Append("Parse-time StaticResource probe: FAILED ")
                      .Append(exception.GetType().FullName)
                      .Append(" (0x").Append(exception.HResult.ToString("X8")).Append(") ")
                      .AppendLine(exception.Message);
            }

            try
            {
                _ = new Atlas.Desktop.Controls.OrganicOrb();
                report.AppendLine("OrganicOrb activation probe: OK");
            }
            catch (Exception exception)
            {
                report.Append("OrganicOrb activation probe: FAILED ")
                      .Append(exception.GetType().FullName)
                      .Append(" (0x").Append(exception.HResult.ToString("X8")).Append(") ")
                      .AppendLine(exception.Message);
            }

            WriteStartupDiagnostic("StartupCanary", new Exception(report.ToString().TrimEnd()));
        }
        catch
        {
            // Canary diagnostics must never mask the original failure.
        }
    }

    private static string GetDiagnosticLogPath() => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Atlas", "Logs", "startup-crash.log");

    internal static void WriteStartupDiagnostic(string source, Exception exception)
    {
        try
        {
            var path = GetDiagnosticLogPath();
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            RotateDiagnosticLog(path);
            var entry = $"""
                [{DateTimeOffset.Now:O}] {source}
                OS: {Environment.OSVersion}
                Framework: {RuntimeInformation.FrameworkDescription}
                Process: {Environment.ProcessPath}
                Architecture: {RuntimeInformation.ProcessArchitecture}
                {exception}

                """;
            File.AppendAllText(path, entry + Environment.NewLine);
        }
        catch
        {
            // Diagnostics must never become a second source of startup failure.
        }
    }

    private static void RotateDiagnosticLog(string path)
    {
        try
        {
            var info = new FileInfo(path);
            if (info.Exists && info.Length > MaxDiagnosticLogBytes)
                File.Move(path, path + ".old", overwrite: true);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // Keep writing to the current log when rotation is not possible.
        }
    }

    // Resolves to MessageBoxW under CharSet.Unicode; used only for fatal startup failures.
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBox(IntPtr hWnd, string text, string caption, uint type);
}
