using Atlas.Application.AI;
using Atlas.Application.Security;
using Atlas.Application.Settings;
using Atlas.Application.Memory;
using Atlas.Desktop.Services;
using Atlas.Desktop.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace Atlas.Desktop;

public sealed partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;
    private readonly VoiceInteractionService _voice = new();
    private bool _voiceEnabled;
    private bool _processingVoice;

    public MainWindow(ISettingsStore settingsStore, IModelRouter modelRouter, ISecretStore secretStore, IMemoryStore memoryStore)
    {
        InitializeComponent();
        Title = "Atlas";
        _viewModel = new MainViewModel(settingsStore, modelRouter, secretStore, memoryStore);
        RootLayout.DataContext = _viewModel;
        RootLayout.Loaded += MainWindow_Loaded;
        Closed += MainWindow_Closed;
        _voice.Recognized += OnVoiceRecognized;
        _voice.StatusChanged += OnVoiceStatusChanged;
        _voice.PlaybackCompleted += OnSpeechPlaybackCompleted;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        RootLayout.Loaded -= MainWindow_Loaded;
        try { await _viewModel.InitializeAsync(); }
        catch (Exception) { _viewModel.StatusMessage = "Não foi possível carregar as preferências locais."; }
    }

    private async void VoiceButton_Click(object sender, RoutedEventArgs e)
    {
        if (_voiceEnabled)
        {
            _voiceEnabled = false;
            _processingVoice = false;
            try { await _voice.StopListeningAsync(); }
            catch (Exception) { /* The session may already have stopped. */ }
            _voice.InterruptSpeech();
            VoiceButton.Content = "Voz";
            _viewModel.StatusMessage = "Modo de voz pausado.";
            return;
        }

        try
        {
            _voiceEnabled = true;
            await _voice.StartListeningAsync();
            VoiceButton.Content = "Parar voz";
            _viewModel.StatusMessage = "Atlas está ouvindo. Fale em português.";
        }
        catch (UnauthorizedAccessException)
        {
            _voiceEnabled = false;
            VoiceButton.Content = "Voz";
            _viewModel.StatusMessage = "Permita o acesso ao microfone nas configurações de privacidade do Windows.";
        }
        catch (Exception exception)
        {
            _voiceEnabled = false;
            VoiceButton.Content = "Voz";
            _viewModel.StatusMessage = exception is InvalidOperationException
                ? exception.Message
                : "Não foi possível iniciar o reconhecimento. Verifique o microfone e o pacote de fala pt-BR.";
        }
    }

    private void OnVoiceRecognized(string text)
    {
        DispatcherQueue.TryEnqueue(async () =>
        {
            if (!_voiceEnabled || _processingVoice) return;
            _processingVoice = true;
            try
            {
                _viewModel.StatusMessage = "Entendi. Estou pensando...";
                await _voice.StopListeningAsync();
                await _viewModel.SubmitVoiceTextAsync(text);
                if (!_voiceEnabled) return;
                await _voice.SpeakAsync(_viewModel.AssistantResponse);
                // Listening resumes only after playback ends, avoiding TTS feedback.
            }
            catch (Exception)
            {
                _viewModel.StatusMessage = "O ciclo de voz falhou. Verifique a conexão, o provedor e o áudio.";
                _voiceEnabled = false;
                _processingVoice = false;
                VoiceButton.Content = "Voz";
                _voice.InterruptSpeech();
            }
        });
    }

    private void OnSpeechPlaybackCompleted()
    {
        DispatcherQueue.TryEnqueue(async () =>
        {
            if (!_voiceEnabled) return;
            try
            {
                _processingVoice = false;
                await _voice.StartListeningAsync();
            }
            catch (Exception)
            {
                _voiceEnabled = false;
                _processingVoice = false;
                VoiceButton.Content = "Voz";
                _viewModel.StatusMessage = "Não consegui reativar o microfone. Toque em Voz para tentar novamente.";
            }
        });
    }

    private void OnVoiceStatusChanged(string status)
    {
        DispatcherQueue.TryEnqueue(() =>
        {
            if (_voiceEnabled) _viewModel.StatusMessage = status;
        });
    }

    private async void MainWindow_Closed(object sender, WindowEventArgs args)
    {
        _voice.Recognized -= OnVoiceRecognized;
        _voice.StatusChanged -= OnVoiceStatusChanged;
        _voice.PlaybackCompleted -= OnSpeechPlaybackCompleted;
        await _voice.DisposeAsync();
    }

    private async void OpenSettings_Click(object sender, RoutedEventArgs e)
    {
        var provider = new ComboBox { MinWidth = 220 };
        provider.Items.Add("Gemini");
        provider.Items.Add("Ollama");
        provider.Items.Add("Hermes");
        provider.SelectedIndex = _viewModel.PreferredProvider switch
        {
            "Ollama" => 1,
            "Hermes" => 2,
            _ => 0
        };

        var allowCloud = new ToggleSwitch
        {
            Header = "Permitir processamento na nuvem",
            IsOn = _viewModel.EnableCloudRequests,
            IsEnabled = provider.SelectedIndex == 0
        };
        provider.SelectionChanged += (_, _) =>
        {
            allowCloud.IsEnabled = provider.SelectedIndex == 0;
            if (!allowCloud.IsEnabled) allowCloud.IsOn = false;
        };

        var useMemory = new ToggleSwitch
        {
            Header = "Usar memória local como contexto",
            IsOn = _viewModel.EnableMemoryContext
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
        content.Children.Add(new TextBlock
        {
            Text = "A chave é armazenada com proteção do Windows (DPAPI).",
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

        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;

        _viewModel.PreferredProvider = provider.SelectedItem?.ToString() ?? "Gemini";
        _viewModel.EnableCloudRequests = allowCloud.IsOn;
        _viewModel.EnableMemoryContext = useMemory.IsOn;

        if (!string.IsNullOrWhiteSpace(apiKey.Password))
        {
            try { await _viewModel.SaveGeminiApiKeyAsync(apiKey.Password); }
            catch (Exception)
            {
                _viewModel.StatusMessage = "Não foi possível armazenar a chave no Windows.";
                return;
            }
        }

        await _viewModel.SaveSettingsCommand.ExecuteAsync(null);
    }
}
