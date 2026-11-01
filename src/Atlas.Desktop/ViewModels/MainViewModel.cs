using Atlas.Application.AI;
using System.Collections.ObjectModel;
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

    public ObservableCollection<MemoryEntry> Memories { get; } = [];

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
    public partial string OllamaModel { get; set; } = AtlasSettings.DefaultOllamaModel;

    [ObservableProperty]
    public partial string OllamaEndpoint { get; set; } = AtlasSettings.DefaultOllamaEndpoint;

    [ObservableProperty]
    public partial string StatusMessage { get; set; } = "Configurações locais carregadas.";

    [ObservableProperty]
    public partial string ChatInput { get; set; } = string.Empty;

    [ObservableProperty]
    public partial string AssistantResponse { get; set; } = "Escolha um provedor, configure o acesso e envie sua primeira mensagem.";

    [ObservableProperty]
    public partial string MemorySearchQuery { get; set; } = string.Empty;

    [ObservableProperty]
    public partial MemoryEntry? SelectedMemory { get; set; }

    [ObservableProperty]
    public partial string SelectedMemoryTitle { get; set; } = string.Empty;

    [ObservableProperty]
    public partial string SelectedMemoryContent { get; set; } = string.Empty;

    partial void OnSelectedMemoryChanged(MemoryEntry? value)
    {
        SelectedMemoryTitle = value?.Title ?? string.Empty;
        SelectedMemoryContent = value?.Content ?? string.Empty;
    }

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
        OllamaModel = settings.OllamaModel;
        OllamaEndpoint = settings.OllamaEndpoint;
    }

    public async Task SaveGeminiApiKeyAsync(string apiKey)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(apiKey);
        await secretStore.SetAsync("gemini-api-key", apiKey.Trim());
        StatusMessage = "Chave Gemini armazenada com proteção do Windows.";
    }

    public async Task SubmitVoiceTextAsync(string recognizedText, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(recognizedText)) return;
        if (IsBusy) throw new InvalidOperationException("Aguarde a resposta atual antes de enviar outra mensagem.");
        ChatInput = recognizedText;
        await SendMessageAsync(cancellationToken);
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
            if (_history.Count > 40)
                _history.RemoveRange(0, _history.Count - 40);
            AssistantResponse = response.Content;
            StatusMessage = $"Resposta recebida de {response.Provider} · {response.Model}";
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Keep the user prompt available so a canceled request can be retried.
            ChatInput = prompt;
            AssistantResponse = "Solicitação cancelada.";
            StatusMessage = "A solicitação foi cancelada.";
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
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.SendMessage", exception);
            AssistantResponse = "Ocorreu uma falha inesperada. Consulte o registro local em %LOCALAPPDATA%\\Atlas\\Logs\\startup-crash.log.";
            StatusMessage = "Falha inesperada ao processar a solicitação.";
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
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.SaveLastExchange", exception);
            StatusMessage = "Falha inesperada ao salvar a memória.";
        }
    }

    [RelayCommand]
    private async Task RefreshMemoriesAsync(CancellationToken cancellationToken)
    {
        try
        {
            var selectedId = SelectedMemory?.Id;
            var entries = await memoryStore.SearchAsync(MemorySearchQuery, limit: 100, cancellationToken: cancellationToken);
            Memories.Clear();
            foreach (var entry in entries) Memories.Add(entry);
            SelectedMemory = selectedId is null ? null : Memories.FirstOrDefault(x => x.Id == selectedId.Value);
            StatusMessage = $"{Memories.Count} memória(s) encontrada(s).";
        }
        catch (Exception exception) when (exception is IOException or DbException or InvalidDataException)
        {
            StatusMessage = "Não foi possível carregar as memórias locais.";
        }
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.RefreshMemories", exception);
            StatusMessage = "Falha inesperada ao carregar as memórias.";
        }
    }

    [RelayCommand]
    private async Task SaveSelectedMemoryAsync(CancellationToken cancellationToken)
    {
        if (SelectedMemory is null)
        {
            StatusMessage = "Selecione uma memória para editar.";
            return;
        }

        try
        {
            var updated = await memoryStore.UpdateAsync(SelectedMemory.Id, SelectedMemoryTitle, SelectedMemoryContent, cancellationToken);
            var index = Memories.ToList().FindIndex(x => x.Id == updated.Id);
            if (index >= 0) Memories[index] = updated;
            SelectedMemory = updated;
            StatusMessage = "Memória atualizada no armazenamento local.";
        }
        catch (Exception exception) when (exception is IOException or DbException or ArgumentException or KeyNotFoundException)
        {
            StatusMessage = exception is ArgumentException
                ? "Título ou conteúdo inválido. Confira os limites e tente novamente."
                : "Não foi possível atualizar a memória local.";
        }
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.SaveSelectedMemory", exception);
            StatusMessage = "Falha inesperada ao atualizar a memória.";
        }
    }

    [RelayCommand]
    private async Task DeleteSelectedMemoryAsync(CancellationToken cancellationToken)
    {
        if (SelectedMemory is null) return;
        try
        {
            var id = SelectedMemory.Id;
            if (await memoryStore.DeleteAsync(id, cancellationToken))
            {
                var item = Memories.FirstOrDefault(x => x.Id == id);
                if (item is not null) Memories.Remove(item);
                SelectedMemory = null;
                StatusMessage = "Memória excluída do armazenamento local.";
            }
        }
        catch (Exception exception) when (exception is IOException or DbException or InvalidDataException)
        {
            StatusMessage = "Não foi possível excluir a memória local.";
        }
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.DeleteSelectedMemory", exception);
            StatusMessage = "Falha inesperada ao excluir a memória.";
        }
    }

    [RelayCommand]
    private async Task RebuildMemoryIndexAsync(CancellationToken cancellationToken)
    {
        try
        {
            var count = await memoryStore.RebuildIndexAsync(cancellationToken);
            await RefreshMemoriesAsync(cancellationToken);
            StatusMessage = $"Índice reconstruído. {count} arquivo(s) de memória indexado(s).";
        }
        catch (Exception exception) when (exception is IOException or DbException or InvalidDataException)
        {
            StatusMessage = "Não foi possível reconstruir o índice da memória.";
        }
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.RebuildMemoryIndex", exception);
            StatusMessage = "Falha inesperada ao reconstruir o índice.";
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
                PreferredProvider = PreferredProvider,
                OllamaModel = OllamaModel.Trim(),
                OllamaEndpoint = OllamaEndpoint.Trim()
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
        catch (Exception exception)
        {
            global::Atlas.Desktop.App.WriteStartupDiagnostic("MainViewModel.SaveSettings", exception);
            StatusMessage = "Falha inesperada ao salvar as preferências.";
        }
    }
}