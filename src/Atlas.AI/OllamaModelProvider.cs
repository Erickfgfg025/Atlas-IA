using System.Net.Http.Json;
using Atlas.Application.AI;
using Atlas.Application.Settings;
using Atlas.Contracts.AI;

namespace Atlas.AI;

public sealed class OllamaModelProvider(HttpClient httpClient, ISettingsStore settingsStore) : IModelProvider
{
    public string Name => "Ollama";

    public async Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Prompt);

        var settings = (await settingsStore.LoadAsync(cancellationToken)).Validate();
        var model = settings.OllamaModel.Trim();
        if (string.IsNullOrWhiteSpace(model))
            throw new InvalidOperationException("O modelo local do Ollama não foi configurado.");

        var messages = new List<OllamaMessage>();
        if (!string.IsNullOrWhiteSpace(request.SystemInstruction))
            messages.Add(new OllamaMessage("system", request.SystemInstruction));

        messages.AddRange((request.History ?? [])
            .Where(item => !string.IsNullOrWhiteSpace(item.Content))
            .Select(item => new OllamaMessage(
                string.Equals(item.Role, "assistant", StringComparison.OrdinalIgnoreCase) ? "assistant" : "user",
                item.Content)));
        messages.Add(new OllamaMessage("user", request.Prompt));

        var baseAddress = new Uri(settings.OllamaEndpoint.EndsWith('/') ? settings.OllamaEndpoint : settings.OllamaEndpoint + '/', UriKind.Absolute);
        var endpoint = new Uri(baseAddress, "api/chat");
        using var response = await httpClient.PostAsJsonAsync(
            endpoint, new OllamaRequest(model, messages, false), cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"O Ollama retornou HTTP {(int)response.StatusCode} ({response.StatusCode}).");

        var result = await response.Content.ReadFromJsonAsync<OllamaResponse>(cancellationToken: cancellationToken);
        if (string.IsNullOrWhiteSpace(result?.Message?.Content))
            throw new InvalidOperationException("O Ollama retornou uma resposta vazia.");

        return new ModelResponse(result.Message.Content, Name, result.Model ?? model);
    }

    private sealed record OllamaRequest(string Model, IReadOnlyList<OllamaMessage> Messages, bool Stream);
    private sealed record OllamaMessage(string Role, string Content);
    private sealed record OllamaResponse(string? Model, OllamaMessage? Message);
}
