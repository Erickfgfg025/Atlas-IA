using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Atlas.Application.Security;
using Atlas.Application.AI;
using Atlas.Contracts.AI;

namespace Atlas.AI;

public sealed class GeminiModelProvider(HttpClient httpClient, ISecretStore secretStore) : IModelProvider
{
    public string Name => "Gemini";

    public async Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Prompt);
        var apiKey = await secretStore.GetAsync("gemini-api-key", cancellationToken);
        if (string.IsNullOrWhiteSpace(apiKey))
            throw new InvalidOperationException("Configure a chave da API Gemini nas configurações seguras do Atlas.");

        var contents = (request.History ?? [])
            .Where(message => !string.IsNullOrWhiteSpace(message.Content))
            .Select(message => new
            {
                role = string.Equals(message.Role, "assistant", StringComparison.OrdinalIgnoreCase) ? "model" : "user",
                parts = new[] { new { text = message.Content } }
            })
            .ToList();
        contents.Add(new { role = "user", parts = new[] { new { text = request.Prompt } } });

        var payload = new Dictionary<string, object> { ["contents"] = contents };
        if (!string.IsNullOrWhiteSpace(request.SystemInstruction))
            payload["systemInstruction"] = new { parts = new[] { new { text = request.SystemInstruction } } };

        using var message = new HttpRequestMessage(
            HttpMethod.Post,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent");
        message.Headers.Add("x-goog-api-key", apiKey);
        message.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        message.Content = new StringContent(
            JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        using var response = await httpClient.SendAsync(message, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"O Gemini retornou HTTP {(int)response.StatusCode} ({response.StatusCode}).");

        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
        var text = document.RootElement
            .GetProperty("candidates")[0]
            .GetProperty("content")
            .GetProperty("parts")
            .EnumerateArray()
            .Select(part => part.TryGetProperty("text", out var value) ? value.GetString() : null)
            .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));

        if (string.IsNullOrWhiteSpace(text))
            throw new InvalidOperationException("O Gemini retornou uma resposta vazia.");

        return new ModelResponse(text, Name, "gemini-2.5-flash");
    }
}
