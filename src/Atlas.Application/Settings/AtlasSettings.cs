namespace Atlas.Application.Settings;

public sealed record AtlasSettings
{
    public const string DefaultProvider = "Gemini";

    public bool EnableCloudRequests { get; init; } = false;
    public bool StartWithWindows { get; init; } = false;
    public bool KeepWindowOnTop { get; init; } = false;
    public string PreferredProvider { get; init; } = DefaultProvider;

    public AtlasSettings Validate()
    {
        if (PreferredProvider is not ("Gemini" or "Ollama"))
            throw new ArgumentException("Provedor de IA inválido.", nameof(PreferredProvider));

        if (EnableCloudRequests && PreferredProvider != "Gemini")
            throw new ArgumentException("Solicitações em nuvem só podem usar o provedor Gemini.");

        return this;
    }
}
