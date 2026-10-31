using Atlas.Application.AI;
using Atlas.Application.Security;
using Atlas.Application.Settings;
using Atlas.Application.Memory;
using Atlas.Desktop.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

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
            await _viewModel.RefreshMemoriesCommand.ExecuteAsync();
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível carregar as preferências locais.";
        }
    }

    private async void DeleteMemory_Click(object sender, RoutedEventArgs e)
    {
        if (_viewModel.SelectedMemory is null) return;

        var dialog = new ContentDialog
        {
            Title = "Excluir memória?",
            Content = $"A memória \"{_viewModel.SelectedMemory.Title}\" será removida do Atlas e do arquivo Markdown local. Esta ação não pode ser desfeita.",
            PrimaryButtonText = "Excluir",
            CloseButtonText = "Cancelar",
            DefaultButton = ContentDialogButton.Close,
            XamlRoot = RootLayout.XamlRoot
        };

        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
            await _viewModel.DeleteSelectedMemoryCommand.ExecuteAsync();
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
