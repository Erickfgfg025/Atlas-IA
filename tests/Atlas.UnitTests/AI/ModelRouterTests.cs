using Atlas.AI;
using Atlas.Application.AI;
using Atlas.Application.Settings;
using Atlas.Contracts.AI;
using Xunit;

namespace Atlas.UnitTests.AI;

public sealed class ModelRouterTests
{
    [Fact]
    public async Task RejectsGeminiWhenCloudConsentIsDisabled()
    {
        var router = new SettingsModelRouter(
            new StubSettingsStore(new AtlasSettings { EnableCloudRequests = false }),
            new Dictionary<string, IModelProvider> { ["Gemini"] = new StubProvider("Gemini") });

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            router.GenerateAsync(new ModelRequest("hello"), CancellationToken.None));
    }

    [Fact]
    public async Task RoutesToSelectedLocalProvider()
    {
        var router = new SettingsModelRouter(
            new StubSettingsStore(new AtlasSettings { PreferredProvider = "Ollama" }),
            new Dictionary<string, IModelProvider> { ["Ollama"] = new StubProvider("Ollama") });

        var result = await router.GenerateAsync(new ModelRequest("hello"), CancellationToken.None);

        Assert.Equal("Ollama", result.Provider);
    }

    private sealed class StubProvider(string name) : IModelProvider
    {
        public string Name => name;
        public Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken) =>
            Task.FromResult(new ModelResponse("ok", name, "test-model"));
    }

    private sealed class StubSettingsStore(AtlasSettings settings) : ISettingsStore
    {
        public Task<AtlasSettings> LoadAsync(CancellationToken cancellationToken = default) => Task.FromResult(settings);
        public Task SaveAsync(AtlasSettings value, CancellationToken cancellationToken = default) => Task.CompletedTask;
    }
}
