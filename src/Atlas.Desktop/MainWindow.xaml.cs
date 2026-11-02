using Atlas.Application.AI;
using Atlas.Application.Security;
using Atlas.Application.Settings;
using Atlas.Application.Memory;
using Atlas.Desktop.Services;
using Atlas.Desktop.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Atlas.WindowsBridge;
using WinRT.Interop;

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
        try
        {
            await _viewModel.InitializeAsync();
            new StartupRegistration().SetEnabled(_viewModel.StartWithWindows);
            WindowZOrder.SetAlwaysOnTop(WindowNative.GetWindowHandle(this), _viewModel.KeepWindowOnTop);
        }
        catch (Exception exception)
        {
            App.WriteStartupDiagnostic("MainWindow.Loaded", exception);
            _viewModel.StatusMessage = "Não foi possível carregar ou aplicar as preferências locais. Consulte o registro local.";
        }
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
            DisableVoice("Permita o acesso ao microfone nas configurações de privacidade do Windows.");
        }
        catch (Exception exception)
        {
            DisableVoice(exception is InvalidOperationException
                ? exception.Message
                : "Não foi possível iniciar o reconhecimento. Verifique o microfone e o pacote de fala pt-BR.");
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
            }
            catch (InvalidOperationException exception)
            {
                // The chat is busy or not ready: keep voice mode enabled and listen
                // again instead of disabling it permanently for a transient conflict.
                _viewModel.StatusMessage = exception.Message;
                await ResumeListeningAfterTurnAsync();
                return;
            }
            catch (Exception)
            {
                DisableVoice("O ciclo de voz falhou. Verifique a conexão, o provedor e o áudio.");
                return;
            }

            if (!_voiceEnabled)
            {
                _processingVoice = false;
                return;
            }

            var response = _viewModel.AssistantResponse;
            if (string.IsNullOrWhiteSpace(response))
            {
                // PlaybackCompleted never fires without audio, which would leave
                // _processingVoice stuck and the microphone off forever.
                await ResumeListeningAfterTurnAsync();
                return;
            }

            try
            {
                await _voice.SpeakAsync(response);
                // Listening resumes only after playback ends, avoiding TTS feedback.
            }
            catch (InvalidOperationException exception)
            {
                DisableVoice(exception.Message);
            }
            catch (Exception)
            {
                DisableVoice("O ciclo de voz falhou. Verifique a conexão, o provedor e o áudio.");
            }
        });
    }

    private async Task ResumeListeningAfterTurnAsync()
    {
        _processingVoice = false;
        if (!_voiceEnabled) return;
        try
        {
            await _voice.StartListeningAsync();
        }
        catch (Exception)
        {
            DisableVoice("Não consegui reativar o microfone. Toque em Voz para tentar novamente.");
        }
    }

    private void DisableVoice(string status)
    {
        _voiceEnabled = false;
        _processingVoice = false;
        VoiceButton.Content = "Voz";
        _viewModel.StatusMessage = status;
        _voice.InterruptSpeech();
    }

    private void OnSpeechPlaybackCompleted()
    {
        DispatcherQueue.TryEnqueue(async () =>
        {
            if (!_voiceEnabled) return;
            await ResumeListeningAfterTurnAsync();
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
        try
        {
            await _voice.DisposeAsync();
        }
        catch (Exception exception)
        {
            // An async void handler must never crash the process while closing.
            App.WriteStartupDiagnostic("MainWindow.Closed", exception);
        }
    }


    private async void OpenMemory_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.RefreshMemoriesCommand.ExecuteAsync(null);

        var search = new TextBox
        {
            PlaceholderText = "Buscar memórias...",
            MinWidth = 320,
            Text = _viewModel.MemorySearchQuery
        };
        var list = new ListView
        {
            ItemsSource = _viewModel.Memories,
            DisplayMemberPath = nameof(MemoryEntry.Title),
            SelectionMode = ListViewSelectionMode.Single,
            Height = 150
        };
        var title = new TextBox { Header = "Título", MaxLength = 200 };
        var body = new TextBox
        {
            Header = "Conteúdo",
            AcceptsReturn = true,
            TextWrapping = TextWrapping.Wrap,
            MinHeight = 130,
            MaxHeight = 220
        };
        list.SelectionChanged += (_, _) =>
        {
            _viewModel.SelectedMemory = list.SelectedItem as MemoryEntry;
            title.Text = _viewModel.SelectedMemoryTitle;
            body.Text = _viewModel.SelectedMemoryContent;
        };

        var searchButton = new Button { Content = "Buscar", MinWidth = 82 };
        searchButton.Click += async (_, _) =>
        {
            _viewModel.MemorySearchQuery = search.Text;
            await _viewModel.RefreshMemoriesCommand.ExecuteAsync(null);
        };
        var saveButton = new Button { Content = "Salvar alterações" };
        saveButton.Click += async (_, _) =>
        {
            _viewModel.SelectedMemoryTitle = title.Text;
            _viewModel.SelectedMemoryContent = body.Text;
            await _viewModel.SaveSelectedMemoryCommand.ExecuteAsync(null);
            list.SelectedItem = _viewModel.SelectedMemory;
        };
        var confirmDelete = new CheckBox
        {
            Content = "Confirmo excluir permanentemente a memória selecionada.",
            IsEnabled = false
        };
        list.SelectionChanged += (_, _) =>
        {
            confirmDelete.IsChecked = false;
            confirmDelete.IsEnabled = list.SelectedItem is MemoryEntry;
        };
        var deleteButton = new Button { Content = "Excluir memória" };
        deleteButton.Click += async (_, _) =>
        {
            if (_viewModel.SelectedMemory is null) return;
            if (confirmDelete.IsChecked != true)
            {
                _viewModel.StatusMessage = "Marque a confirmação antes de excluir a memória.";
                return;
            }
            await _viewModel.DeleteSelectedMemoryCommand.ExecuteAsync(null);
            confirmDelete.IsChecked = false;
            confirmDelete.IsEnabled = false;
            title.Text = string.Empty;
            body.Text = string.Empty;
        };
        var rebuildButton = new Button { Content = "Reconstruir índice" };
        rebuildButton.Click += async (_, _) =>
        {
            await _viewModel.RebuildMemoryIndexCommand.ExecuteAsync(null);
        };

        var searchRow = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        searchRow.Children.Add(search);
        searchRow.Children.Add(searchButton);
        var actions = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        actions.Children.Add(saveButton);
        actions.Children.Add(deleteButton);
        actions.Children.Add(rebuildButton);
        var content = new StackPanel { Spacing = 10, MinWidth = 520 };
        content.Children.Add(searchRow);
        content.Children.Add(list);
        content.Children.Add(title);
        content.Children.Add(body);
        content.Children.Add(confirmDelete);
        content.Children.Add(actions);

        var dialog = new ContentDialog
        {
            Title = "Memória local",
            Content = content,
            CloseButtonText = "Fechar",
            XamlRoot = RootLayout.XamlRoot
        };
        try
        {
            await dialog.ShowAsync();
        }
        catch (Exception exception)
        {
            // WinUI throws when a second ContentDialog opens while another is still
            // showing; an unhandled exception from an async void handler would kill
            // the process on a rapid double-click.
            App.WriteStartupDiagnostic("MainWindow.MemoryDialog", exception);
            _viewModel.StatusMessage = "Não foi possível abrir o diálogo de memórias.";
        }
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
        var startWithWindows = new ToggleSwitch
        {
            Header = "Iniciar com o Windows",
            IsOn = _viewModel.StartWithWindows
        };
        var keepOnTop = new ToggleSwitch
        {
            Header = "Manter Atlas sempre visível",
            IsOn = _viewModel.KeepWindowOnTop
        };

        var ollamaModel = new TextBox
        {
            Header = "Modelo Ollama",
            Text = _viewModel.OllamaModel,
            PlaceholderText = "Ex.: llama3.2"
        };
        var ollamaEndpoint = new TextBox
        {
            Header = "Endereço local do Ollama",
            Text = _viewModel.OllamaEndpoint,
            PlaceholderText = "http://127.0.0.1:11434/"
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
        content.Children.Add(ollamaModel);
        content.Children.Add(ollamaEndpoint);
        content.Children.Add(useMemory);
        content.Children.Add(startWithWindows);
        content.Children.Add(keepOnTop);
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

        ContentDialogResult dialogResult;
        try
        {
            dialogResult = await dialog.ShowAsync();
        }
        catch (Exception exception)
        {
            App.WriteStartupDiagnostic("MainWindow.SettingsDialog", exception);
            _viewModel.StatusMessage = "Não foi possível abrir o diálogo de configurações.";
            return;
        }

        if (dialogResult != ContentDialogResult.Primary) return;

        _viewModel.PreferredProvider = provider.SelectedItem?.ToString() ?? "Gemini";
        _viewModel.EnableCloudRequests = allowCloud.IsOn;
        _viewModel.OllamaModel = ollamaModel.Text;
        _viewModel.OllamaEndpoint = ollamaEndpoint.Text;
        _viewModel.EnableMemoryContext = useMemory.IsOn;
        _viewModel.StartWithWindows = startWithWindows.IsOn;
        _viewModel.KeepWindowOnTop = keepOnTop.IsOn;

        try
        {
            new StartupRegistration().SetEnabled(_viewModel.StartWithWindows);
            WindowZOrder.SetAlwaysOnTop(WindowNative.GetWindowHandle(this), _viewModel.KeepWindowOnTop);
            await _viewModel.SaveSettingsCommand.ExecuteAsync(null);
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível aplicar as preferências de inicialização ou janela.";
            return;
        }

        if (string.IsNullOrWhiteSpace(apiKey.Password)) return;

        // The key is stored last so a storage failure cannot discard the other
        // preference changes the user just confirmed.
        try
        {
            await _viewModel.SaveGeminiApiKeyAsync(apiKey.Password);
        }
        catch (Exception)
        {
            _viewModel.StatusMessage = "Não foi possível armazenar a chave no Windows. " +
                                       "As demais preferências foram aplicadas nesta sessão.";
        }
    }
}
