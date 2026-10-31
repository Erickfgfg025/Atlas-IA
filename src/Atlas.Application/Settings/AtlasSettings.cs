namespace Atlas.Application.Settings;

public sealed record AtlasSettings
{
    public const string DefaultProvider = "Gemini";
    public const string DefaultOllamaModel = "llama3.2";
    public const string DefaultOllamaEndpoint = "http://127.0.0.1:11434/";

    public bool EnableCloudRequests { get; init; } = false;
    public bool StartWithWindows { get; init; } = false;
    public bool KeepWindowOnTop { get; init; } = false;
    public string PreferredProvider { get; init; } = DefaultProvider;
    public string OllamaModel { get; init; } = DefaultOllamaModel;
    public string OllamaEndpoint { get; init; } = DefaultOllamaEndpoint;

    public AtlasSettings Validate()
    {
        if (PreferredProvider is not ("Gemini" or "Ollama"))
            throw new ArgumentException("Provedor de IA inválido.", nameof(PreferredProvider));

        if (EnableCloudRequests && PreferredProvider != "Gemini")
            throw new ArgumentException("Solicitações em nuvem só podem usar o provedor Gemini.");

        if (string.IsNullOrWhiteSpace(OllamaModel) || OllamaModel.Length > 128)
            throw new ArgumentException("Nome de modelo Ollama inválido.", nameof(OllamaModel));

        if (!Uri.TryCreate(OllamaEndpoint, UriKind.Absolute, out var endpoint) ||
            endpoint.Scheme != Uri.UriSchemeHttp ||
            !endpoint.IsLoopback)
            throw new ArgumentException("O Ollama deve usar um endereço HTTP local (localhost ou loopback).", nameof(OllamaEndpoint));

        return this;
    }
}
