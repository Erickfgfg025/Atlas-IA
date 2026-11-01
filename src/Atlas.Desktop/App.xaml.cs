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
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
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
}
