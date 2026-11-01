using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using Atlas.AI;
using Atlas.Application.Security;
using Atlas.Contracts.AI;
using Xunit;

namespace Atlas.UnitTests.AI;

public sealed class GeminiModelProviderTests
{
    [Fact]
    public async Task MapsAssistantHistoryToModelRoleAndAppendsPromptOnce()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore("key"));
        var history = new[]
        {
            new ModelMessage("user", "Pergunta anterior"),
            new ModelMessage("assistant", "Resposta anterior")
        };

        await provider.GenerateAsync(
            new ModelRequest("Pergunta atual", History: history), CancellationToken.None);

        // Gemini expects "model" (never "assistant") and a single trailing user turn.
        Assert.Equal(2, Regex.Matches(handler.LastRequestBody, "\"role\":\"user\"").Count);
        Assert.Equal(1, Regex.Matches(handler.LastRequestBody, "\"role\":\"model\"").Count);
        Assert.Contains("\"text\":\"Resposta anterior\"", handler.LastRequestBody);
        Assert.Equal(1, Regex.Matches(handler.LastRequestBody, "Pergunta atual").Count);
    }

    [Fact]
    public async Task IncludesSystemInstructionWhenProvided()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore("key"));

        await provider.GenerateAsync(
            new ModelRequest("Oi", SystemInstruction: "Você é o Atlas."), CancellationToken.None);

        Assert.Contains("\"systemInstruction\"", handler.LastRequestBody);
        Assert.Contains("Você é o Atlas.", handler.LastRequestBody);
    }

    [Fact]
    public async Task ThrowsActionableErrorWhenApiKeyIsMissing()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK));
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore(null));

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(() =>
            provider.GenerateAsync(new ModelRequest("Oi"), CancellationToken.None));

        Assert.Contains("chave", exception.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Empty(handler.LastRequestUri);
    }

    [Fact]
    public async Task PropagatesHttpStatusCodeWhenGeminiFails()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.TooManyRequests)
        {
            Content = new StringContent(
                """{"error":{"code":429,"message":"quota"}}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore("key"));

        var exception = await Assert.ThrowsAsync<HttpRequestException>(() =>
            provider.GenerateAsync(new ModelRequest("Oi"), CancellationToken.None));

        Assert.Equal(HttpStatusCode.TooManyRequests, exception.StatusCode);
        Assert.Contains("429", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task SurfacesContentBlockReasonWhenNoCandidatesReturned()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"promptFeedback":{"blockReason":"SAFETY"}}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore("key"));

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(() =>
            provider.GenerateAsync(new ModelRequest("Oi"), CancellationToken.None));

        Assert.Contains("SAFETY", exception.Message, StringComparison.Ordinal);
    }

    private sealed class StubSecretStore(string? secret) : ISecretStore
    {
        public Task SetAsync(string key, string value, CancellationToken cancellationToken = default) => Task.CompletedTask;
        public Task<string?> GetAsync(string key, CancellationToken cancellationToken = default) => Task.FromResult(secret);
        public Task<bool> DeleteAsync(string key, CancellationToken cancellationToken = default) => Task.FromResult(false);
    }

    private sealed class RecordingHandler(Func<HttpRequestMessage, HttpResponseMessage> responseFactory) : HttpMessageHandler
    {
        public string LastRequestUri { get; private set; } = string.Empty;
        public string LastRequestBody { get; private set; } = string.Empty;

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequestUri = request.RequestUri?.ToString() ?? string.Empty;
            if (request.Content is not null)
                LastRequestBody = await request.Content.ReadAsStringAsync(cancellationToken);
            return responseFactory(request);
        }
    }
}
