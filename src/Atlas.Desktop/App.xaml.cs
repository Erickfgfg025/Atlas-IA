using Atlas.AI;
using Atlas.Application.AI;
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
            ["Ollama"] = new OllamaModelProvider(
                _httpClient, new Uri(AtlasSettings.DefaultOllamaEndpoint), AtlasSettings.DefaultOllamaModel)
        };
        IModelRouter modelRouter = new SettingsModelRouter(settingsStore, providers);

        _window = new MainWindow(settingsStore, modelRouter, secretStore);
        _window.Activate();
    }
}
