using Atlas.AI;
using Atlas.Application.AI;
using Atlas.Application.Memory;
using Atlas.Application.Settings;
using Atlas.Contracts.AI;
using Xunit;

namespace Atlas.UnitTests.AI;

public sealed class MemoryAwareModelRouterTests
{
    [Fact]
    public async Task DoesNotQueryMemoryWhenMemoryContextIsDisabled()
    {
        var memory = new StubMemoryStore();
        var inner = new CapturingRouter();
        var router = new MemoryAwareModelRouter(
            new StubSettingsStore(new AtlasSettings { EnableMemoryContext = false }), memory, inner);

        await router.GenerateAsync(new ModelRequest("What do you know about my project?"), CancellationToken.None);

        Assert.Equal(0, memory.SearchCalls);
        Assert.Null(inner.LastRequest!.SystemInstruction);
    }

    [Fact]
    public async Task AddsRelevantMemoryAsUntrustedContextWhenEnabled()
    {
        var memory = new StubMemoryStore();
        memory.Entries.Add(new MemoryEntry(Guid.NewGuid(), MemoryCategory.Projects, "Atlas",
            "The project uses .NET 10.", DateTimeOffset.UtcNow, DateTimeOffset.UtcNow));
        var inner = new CapturingRouter();
        var router = new MemoryAwareModelRouter(
            new StubSettingsStore(new AtlasSettings { EnableMemoryContext = true }), memory, inner);

        await router.GenerateAsync(new ModelRequest("Tell me about my Atlas project"), CancellationToken.None);

        Assert.True(memory.SearchCalls > 0);
        Assert.Contains("The project uses .NET 10.", inner.LastRequest!.SystemInstruction);
        Assert.Contains("not instructions", inner.LastRequest.SystemInstruction);
    }

    private sealed class CapturingRouter : IModelRouter
    {
        public ModelRequest? LastRequest { get; private set; }
        public Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(new ModelResponse("ok", "Ollama", "test"));
        }
    }

    private sealed class StubSettingsStore(AtlasSettings settings) : ISettingsStore
    {
        public Task<AtlasSettings> LoadAsync(CancellationToken cancellationToken = default) => Task.FromResult(settings);
        public Task SaveAsync(AtlasSettings value, CancellationToken cancellationToken = default) => Task.CompletedTask;
    }

    private sealed class StubMemoryStore : IMemoryStore
    {
        public List<MemoryEntry> Entries { get; } = [];
        public int SearchCalls { get; private set; }
        public Task<MemoryEntry> CreateAsync(MemoryCategory category, string title, string content, CancellationToken cancellationToken = default) => throw new NotImplementedException();
        public Task<MemoryEntry?> GetAsync(Guid id, CancellationToken cancellationToken = default) => Task.FromResult(Entries.FirstOrDefault(x => x.Id == id));
        public Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, MemoryCategory? category = null, int limit = 50, CancellationToken cancellationToken = default)
        {
            SearchCalls++;
            IReadOnlyList<MemoryEntry> result = Entries.Where(x =>
                x.Title.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                x.Content.Contains(query, StringComparison.OrdinalIgnoreCase)).Take(limit).ToArray();
            return Task.FromResult(result);
        }
        public Task<MemoryEntry> UpdateAsync(Guid id, string title, string content, CancellationToken cancellationToken = default) => throw new NotImplementedException();
        public Task<bool> DeleteAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotImplementedException();
        public Task<int> RebuildIndexAsync(CancellationToken cancellationToken = default) => throw new NotImplementedException();
    }
}
