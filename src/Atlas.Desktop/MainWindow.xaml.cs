using Atlas.Application.AI;
using Atlas.Application.Security;
using Atlas.Application.Settings;
using Atlas.Application.Memory;
using Atlas.Desktop.ViewModels;
using Microsoft.UI.Xaml;

namespace Atlas.Desktop;

public sealed partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;

    public MainWindow(ISettingsStore settingsStore, IModelRouter modelRouter, ISecretStore secretStore, IMemoryStore memoryStore)
    {
        InitializeComponent();
        Title = "Atlas";
        _viewModel = new MainViewModel(settingsStore, modelRouter, secretStore, memoryStore);
        RootLayout.DataContext = _viewModel;
        RootLayout.Loaded += MainWindow_Loaded;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        RootLayout.Loaded -= MainWindow_Loaded;
        try
        {
            await _viewModel.InitializeAsync();
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível carregar as preferências locais.";
        }
    }

    private async void SaveGeminiKey_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await _viewModel.SaveGeminiApiKeyAsync(GeminiApiKey.Password);
            GeminiApiKey.Password = string.Empty;
        }
        catch (ArgumentException)
        {
            _viewModel.StatusMessage = "Informe uma chave Gemini válida.";
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível armazenar a chave no Windows.";
        }
    }
}
