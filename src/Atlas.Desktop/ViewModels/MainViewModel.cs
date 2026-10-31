using Atlas.Application.AI;
using Atlas.Application.Security;
using Atlas.Application.Memory;
using System.Data.Common;
using Atlas.Application.Settings;
using Atlas.Contracts.AI;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Atlas.Desktop.ViewModels;

public partial class MainViewModel(
    ISettingsStore settingsStore,
    IModelRouter modelRouter,
    ISecretStore secretStore,
    IMemoryStore memoryStore) : ObservableObject
{
    private readonly List<ModelMessage> _history = [];

    [ObservableProperty]
    public partial bool EnableCloudRequests { get; set; }

    [ObservableProperty]
    public partial bool EnableMemoryContext { get; set; }

    [ObservableProperty]
    public partial bool StartWithWindows { get; set; }

    [ObservableProperty]
    public partial bool KeepWindowOnTop { get; set; }

    [ObservableProperty]
    public partial string PreferredProvider { get; set; } = AtlasSettings.DefaultProvider;

    [ObservableProperty]
    public partial string StatusMessage { get; set; } = "Configurações locais carregadas.";

    [ObservableProperty]
    public partial string ChatInput { get; set; } = string.Empty;

    [ObservableProperty]
    public partial string AssistantResponse { get; set; } = "Escolha um provedor, configure o acesso e envie sua primeira mensagem.";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(SendMessageCommand))]
    public partial bool IsBusy { get; set; }

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        var settings = await settingsStore.LoadAsync(cancellationToken);
        EnableCloudRequests = settings.EnableCloudRequests;
        EnableMemoryContext = settings.EnableMemoryContext;
        KeepWindowOnTop = settings.KeepWindowOnTop;
        PreferredProvider = settings.PreferredProvider;
        StartWithWindows = settings.StartWithWindows;
    }

    public async Task SaveGeminiApiKeyAsync(string apiKey)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(apiKey);
        await secretStore.SetAsync("gemini-api-key", apiKey.Trim());
        StatusMessage = "Chave Gemini armazenada com proteção do Windows.";
    }

    [RelayCommand]
    private async Task SendMessageAsync(CancellationToken cancellationToken)
    {
        var prompt = ChatInput.Trim();
        if (string.IsNullOrWhiteSpace(prompt) || IsBusy)
            return;

        IsBusy = true;
        ChatInput = string.Empty;
        AssistantResponse = "Processando sua solicitação...";
        try
        {
            var response = await modelRouter.GenerateAsync(
                new ModelRequest(prompt, History: _history.ToArray()), cancellationToken);
            _history.Add(new ModelMessage("user", prompt));
            _history.Add(new ModelMessage("assistant", response.Content));
            AssistantResponse = response.Content;
            StatusMessage = $"Resposta recebida de {response.Provider} · {response.Model}";
        }
        catch (InvalidOperationException exception)
        {
            AssistantResponse = exception.Message;
            StatusMessage = "A solicitação não pôde ser iniciada.";
        }
        catch (HttpRequestException)
        {
            AssistantResponse = PreferredProvider == "Ollama"
                ? "Não consegui conectar ao Ollama local. Confirme se ele está instalado, aberto e com o modelo baixado."
                : "Não consegui conectar ao Gemini. Verifique sua conexão, a chave e o acesso à API.";
            StatusMessage = "Falha de comunicação com o provedor.";
        }
        catch (Exception exception) when (exception is DbException or IOException)
        {
            AssistantResponse = "Não consegui consultar a memória local. Verifique a pasta de dados ou desative o contexto de memória nas preferências.";
            StatusMessage = "Falha ao acessar a memória local.";
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            AssistantResponse = "O provedor demorou demais para responder. Tente novamente.";
            StatusMessage = "Tempo limite da solicitação.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand]
    private async Task SaveLastExchangeAsync(CancellationToken cancellationToken)
    {
        if (_history.Count < 2 || _history[^2].Role != "user" || _history[^1].Role != "assistant")
        {
            StatusMessage = "Envie uma mensagem antes de salvar uma memória.";
            return;
        }

        var title = $"Conversa · {DateTime.Now:yyyy-MM-dd HH:mm}";
        var content = $"Usuário: {_history[^2].Content}\n\nAtlas: {_history[^1].Content}";
        if (content.Length > 100_000) content = content[..100_000];
        try
        {
            await memoryStore.CreateAsync(MemoryCategory.Episodes, title, content, cancellationToken);
            StatusMessage = "Conversa salva na memória local.";
        }
        catch (Exception exception) when (exception is IOException or InvalidOperationException or ArgumentException or DbException)
        {
            StatusMessage = "Não foi possível salvar a memória local.";
        }
    }

    [RelayCommand]
    private async Task SaveSettingsAsync(CancellationToken cancellationToken)
    {
        try
        {
            var settings = new AtlasSettings
            {
                EnableCloudRequests = EnableCloudRequests,
                EnableMemoryContext = EnableMemoryContext,
                StartWithWindows = StartWithWindows,
                KeepWindowOnTop = KeepWindowOnTop,
                PreferredProvider = PreferredProvider
            }.Validate();

            await settingsStore.SaveAsync(settings, cancellationToken);
            StatusMessage = "Preferências salvas neste computador.";
        }
        catch (ArgumentException exception)
        {
            StatusMessage = exception.Message;
        }
        catch (IOException)
        {
            StatusMessage = "Não foi possível salvar as preferências. Verifique o acesso à pasta de dados.";
        }
    }
}
