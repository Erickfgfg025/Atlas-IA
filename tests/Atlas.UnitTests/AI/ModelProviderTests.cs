using System.Net;
using System.Text;
using Atlas.AI;
using Atlas.Application.Security;
using Atlas.Contracts.AI;
using Xunit;

namespace Atlas.UnitTests.AI;

public sealed class ModelProviderTests
{
    [Fact]
    public async Task GeminiSendsApiKeyInHeaderAndParsesCandidateText()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"candidates":[{"content":{"parts":[{"text":"Olá do Gemini"}]}}]}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new GeminiModelProvider(new HttpClient(handler), new StubSecretStore("secret-test"));

        var result = await provider.GenerateAsync(new ModelRequest("Oi"), CancellationToken.None);

        Assert.Equal("Olá do Gemini", result.Content);
        Assert.Equal("Gemini", result.Provider);
        Assert.Equal("secret-test", handler.LastRequestHeaders["x-goog-api-key"]);
        Assert.DoesNotContain("secret-test", handler.LastRequestUri);
    }

    [Fact]
    public async Task OllamaPostsChatToLoopbackEndpoint()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"model":"llama3.2","message":{"role":"assistant","content":"Resposta local"}}""",
                Encoding.UTF8, "application/json")
        });
        var provider = new OllamaModelProvider(
            new HttpClient(handler), new Uri("http://127.0.0.1:11434/"));

        var result = await provider.GenerateAsync(new ModelRequest("Oi"), CancellationToken.None);

        Assert.Equal("Resposta local", result.Content);
        Assert.Equal("Ollama", result.Provider);
        Assert.EndsWith("/api/chat", handler.LastRequestUri);
    }

    private sealed class StubSecretStore(string? secret) : ISecretStore
    {
        public Task SetAsync(string key, string value, CancellationToken cancellationToken = default) => Task.CompletedTask;
        public Task<string?> GetAsync(string key, CancellationToken cancellationToken = default) => Task.FromResult(secret);
        public Task<bool> DeleteAsync(string key, CancellationToken cancellationToken = default) => Task.FromResult(false);
    }

    private sealed class RecordingHandler(Func<HttpRequestMessage, HttpResponseMessage> responseFactory) : HttpMessageHandler
    {
        public Dictionary<string, string> LastRequestHeaders { get; } = new(StringComparer.OrdinalIgnoreCase);
        public string LastRequestUri { get; private set; } = string.Empty;

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequestUri = request.RequestUri?.ToString() ?? string.Empty;
            foreach (var header in request.Headers)
                LastRequestHeaders[header.Key] = string.Join(",", header.Value);
            return Task.FromResult(responseFactory(request));
        }
    }
}
