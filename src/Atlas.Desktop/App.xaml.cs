using System;
using System.IO;
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
    private Window? _window;
    private readonly HttpClient _httpClient = new();

    public App()
    {
        // Register diagnostics before loading App.xaml resources so failures during
        // XAML initialization have a chance to be recorded.
        UnhandledException += OnUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandledException;
        InitializeComponent();
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
            throw;
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

    internal static void WriteStartupDiagnostic(string source, Exception exception)
    {
        try
        {
            var directory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Atlas", "Logs");
            Directory.CreateDirectory(directory);
            var path = Path.Combine(directory, "startup-crash.log");
            var entry = $"""
                [{DateTimeOffset.Now:O}] {source}
                OS: {Environment.OSVersion}
                Framework: {System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription}
                Process: {Environment.ProcessPath}
                Architecture: {System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture}
                {exception}
                
                """;
            File.AppendAllText(path, entry + Environment.NewLine);
        }
        catch
        {
            // Diagnostics must never become a second source of startup failure.
        }
    }
}
