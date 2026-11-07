using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Atlas.Application.Security;
using Atlas.Application.AI;
using Atlas.Contracts.AI;

namespace Atlas.AI;

public sealed class GeminiModelProvider(HttpClient httpClient, ISecretStore secretStore) : IModelProvider
{
    private const string Model = "gemini-2.5-flash";

    public string Name => "Gemini";

    public async Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Prompt);

        // A key pasted from a web page can carry line breaks or stray spaces; they are
        // not part of the key and would make the HTTP header invalid.
        var apiKey = new string((await secretStore.GetAsync("gemini-api-key", cancellationToken) ?? string.Empty)
            .Where(character => !char.IsWhiteSpace(character))
            .ToArray());
        if (apiKey.Length == 0)
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
            $"https://generativelanguage.googleapis.com/v1beta/models/{Model}:generateContent");
        message.Headers.Add("x-goog-api-key", apiKey);
        message.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        message.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        using var response = await httpClient.SendAsync(
            message, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
            var detail = errorBody.Length > 500 ? errorBody[..500] : errorBody;
            throw new HttpRequestException(
                $"O Gemini retornou HTTP {(int)response.StatusCode} ({response.StatusCode}). {detail}",
                null, response.StatusCode);
        }

        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
        var root = document.RootElement;

        if (!root.TryGetProperty("candidates", out var candidates) ||
            candidates.ValueKind != JsonValueKind.Array ||
            candidates.GetArrayLength() == 0)
        {
            var blockReason = root.TryGetProperty("promptFeedback", out var feedback) &&
                              feedback.TryGetProperty("blockReason", out var reason)
                ? reason.GetString()
                : null;
            throw new InvalidOperationException(
                string.IsNullOrWhiteSpace(blockReason)
                    ? "O Gemini não retornou candidatos. Verifique os limites, a segurança do conteúdo e tente novamente."
                    : $"O Gemini bloqueou a solicitação: {blockReason}.");
        }

        var text = new StringBuilder();
        foreach (var candidate in candidates.EnumerateArray())
        {
            if (!candidate.TryGetProperty("content", out var content) ||
                !content.TryGetProperty("parts", out var parts) ||
                parts.ValueKind != JsonValueKind.Array)
                continue;

            foreach (var part in parts.EnumerateArray())
            {
                if (part.TryGetProperty("text", out var value) &&
                    value.ValueKind == JsonValueKind.String)
                    text.Append(value.GetString());
            }

            if (text.Length > 0) break;
        }

        if (text.Length == 0)
            throw new InvalidOperationException("O Gemini retornou uma resposta sem texto.");

        return new ModelResponse(text.ToString(), Name, Model);
    }
}
