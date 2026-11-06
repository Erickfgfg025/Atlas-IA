namespace Atlas.Application.Settings;

public sealed record AtlasSettings
{
    public const string DefaultProvider = "Gemini";
    public const string DefaultOllamaModel = "llama3.2";
    public const string DefaultOllamaEndpoint = "http://127.0.0.1:11434/";

    public bool EnableCloudRequests { get; init; } = false;
    public bool EnableMemoryContext { get; init; } = false;
    public bool StartWithWindows { get; init; } = false;
    public bool KeepWindowOnTop { get; init; } = false;
    public string PreferredProvider { get; init; } = DefaultProvider;
    public string OllamaModel { get; init; } = DefaultOllamaModel;
    public string OllamaEndpoint { get; init; } = DefaultOllamaEndpoint;

    /// <summary>
    /// Validates the settings and returns the value that should be persisted.
    /// The Ollama model and endpoint are only enforced when Ollama is the selected
    /// provider; with any other provider a stale or blank value falls back to its
    /// default instead of rejecting the whole configuration.
    /// </summary>
    public AtlasSettings Validate()
    {
        if (PreferredProvider is not ("Gemini" or "Ollama" or "Hermes"))
            throw new ArgumentException("Provedor de IA inválido.", nameof(PreferredProvider));

        if (EnableCloudRequests && PreferredProvider != "Gemini")
            throw new ArgumentException("Solicitações em nuvem só podem usar o provedor Gemini.");

        var usesOllama = PreferredProvider == "Ollama";
        var model = usesOllama ? RequireOllamaModel(OllamaModel) : NormalizeOllamaModel(OllamaModel);
        var endpoint = usesOllama ? RequireLoopbackEndpoint(OllamaEndpoint) : NormalizeOllamaEndpoint(OllamaEndpoint);

        if (string.Equals(model, OllamaModel, StringComparison.Ordinal) &&
            string.Equals(endpoint, OllamaEndpoint, StringComparison.Ordinal))
            return this;

        return this with { OllamaModel = model, OllamaEndpoint = endpoint };
    }

    private static string RequireOllamaModel(string? value)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length > 128)
            throw new ArgumentException("Nome de modelo Ollama inválido.", nameof(OllamaModel));

        return value;
    }

    private static string RequireLoopbackEndpoint(string? value)
    {
        if (!IsLoopbackHttpEndpoint(value))
            throw new ArgumentException(
                "O Ollama deve usar um endereço HTTP local (localhost ou loopback).", nameof(OllamaEndpoint));

        return value!;
    }

    private static string NormalizeOllamaModel(string? value) =>
        string.IsNullOrWhiteSpace(value) || value.Length > 128 ? DefaultOllamaModel : value;

    private static string NormalizeOllamaEndpoint(string? value) =>
        IsLoopbackHttpEndpoint(value) ? value! : DefaultOllamaEndpoint;

    private static bool IsLoopbackHttpEndpoint(string? value) =>
        Uri.TryCreate(value, UriKind.Absolute, out var endpoint) &&
        endpoint.Scheme == Uri.UriSchemeHttp &&
        endpoint.IsLoopback;
}
