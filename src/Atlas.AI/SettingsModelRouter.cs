using Atlas.Application.AI;
using Atlas.Application.Settings;
using Atlas.Contracts.AI;

namespace Atlas.AI;

public sealed class SettingsModelRouter(
    ISettingsStore settingsStore,
    IReadOnlyDictionary<string, IModelProvider> providers) : IModelRouter
{
    public async Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Prompt);

        var settings = (await settingsStore.LoadAsync(cancellationToken)).Validate();
        if (settings.PreferredProvider == "Gemini" && !settings.EnableCloudRequests)
            throw new InvalidOperationException("Solicitações à nuvem estão desativadas. Ative a permissão nas preferências para usar o Gemini.");

        if (!providers.TryGetValue(settings.PreferredProvider, out var provider))
            throw new InvalidOperationException($"O provedor {settings.PreferredProvider} não está disponível.");

        return await provider.GenerateAsync(request, cancellationToken);
    }
}
