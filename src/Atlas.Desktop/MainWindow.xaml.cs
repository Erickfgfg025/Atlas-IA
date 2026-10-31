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
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível carregar as preferências locais.";
        }
    }

    private async void OpenSettings_Click(object sender, RoutedEventArgs e)
    {
        var provider = new ComboBox { MinWidth = 220, SelectedIndex = _viewModel.PreferredProvider == "Ollama" ? 1 : 0 };
        provider.Items.Add("Gemini");
        provider.Items.Add("Ollama");

        var allowCloud = new ToggleSwitch
        {
            Header = "Permitir processamento na nuvem",
            IsOn = _viewModel.EnableCloudRequests
        };
        var useMemory = new ToggleSwitch
        {
            Header = "Usar memória local como contexto",
            IsOn = _viewModel.EnableMemoryContext
        };
        var keepOnTop = new ToggleSwitch
        {
            Header = "Manter janela sempre visível",
            IsOn = _viewModel.KeepWindowOnTop
        };
        var apiKey = new PasswordBox
        {
            PlaceholderText = "Nova chave Gemini (opcional)",
            PasswordRevealMode = PasswordRevealMode.Peek
        };

        var content = new StackPanel { Spacing = 14 };
        content.Children.Add(new TextBlock { Text = "Provedor de IA" });
        content.Children.Add(provider);
        content.Children.Add(allowCloud);
        content.Children.Add(useMemory);
        content.Children.Add(keepOnTop);
        content.Children.Add(new TextBlock
        {
            Text = "A chave é armazenada usando a proteção do Windows.",
            TextWrapping = TextWrapping.Wrap,
            FontSize = 12
        });
        content.Children.Add(apiKey);

        var dialog = new ContentDialog
        {
            Title = "Configurações",
            Content = content,
            PrimaryButtonText = "Salvar",
            CloseButtonText = "Cancelar",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = RootLayout.XamlRoot
        };

        if (await dialog.ShowAsync() != ContentDialogResult.Primary)
            return;

        _viewModel.PreferredProvider = provider.SelectedItem?.ToString() ?? "Gemini";
        _viewModel.EnableCloudRequests = allowCloud.IsOn;
        _viewModel.EnableMemoryContext = useMemory.IsOn;
        _viewModel.KeepWindowOnTop = keepOnTop.IsOn;

        if (!string.IsNullOrWhiteSpace(apiKey.Password))
        {
            try
            {
                await _viewModel.SaveGeminiApiKeyAsync(apiKey.Password);
            }
            catch (ArgumentException)
            {
                _viewModel.StatusMessage = "A chave Gemini informada é inválida.";
                return;
            }
            catch (Exception)
            {
                _viewModel.StatusMessage = "Não foi possível armazenar a chave no Windows.";
                return;
            }
        }

        await _viewModel.SaveSettingsCommand.ExecuteAsync();
    }
}
