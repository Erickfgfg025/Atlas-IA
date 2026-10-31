using Xunit;
using Atlas.Application.Memory;
using Atlas.Memory;

namespace Atlas.UnitTests.Memory;

public sealed class MarkdownMemoryStoreTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "atlas-memory-tests", Guid.NewGuid().ToString("N"));
    private readonly MarkdownMemoryStore _store;

    public MarkdownMemoryStoreTests()
    {
        _store = new MarkdownMemoryStore(new MemoryVaultOptions(Path.Combine(_root, "vault"), Path.Combine(_root, "index.db")));
    }

    [Fact]
    public async Task CreateGetAndSearch_PersistMarkdownAndIndex()
    {
        var created = await _store.CreateAsync(MemoryCategory.Projects, "Atlas roadmap", "Implement local memory.");
        var loaded = await _store.GetAsync(created.Id);
        var results = await _store.SearchAsync("roadmap", MemoryCategory.Projects);

        Assert.NotNull(loaded);
        Assert.Equal("Implement local memory.", loaded.Content);
        Assert.Single(results);
        Assert.True(Directory.GetFiles(Path.Combine(_root, "vault"), "*.md", SearchOption.AllDirectories).Length == 1);
    }

    [Fact]
    public async Task RebuildIndex_RestoresDeletedIndexRows()
    {
        var created = await _store.CreateAsync(MemoryCategory.Personal, "Profile", "Local-only data.");
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection(new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder { DataSource = Path.Combine(_root, "index.db") }.ToString()))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = "DELETE FROM memories;";
            await command.ExecuteNonQueryAsync();
        }

        Assert.Equal(1, await _store.RebuildIndexAsync());
        Assert.NotNull(await _store.GetAsync(created.Id));
    }

    [Fact]
    public async Task UpdateAndDelete_ChangeStoredMemory()
    {
        var created = await _store.CreateAsync(MemoryCategory.Preferences, "Old title", "Old content");
        var updated = await _store.UpdateAsync(created.Id, "New title", "New content");
        Assert.Equal("New title", updated.Title);
        Assert.True(await _store.DeleteAsync(created.Id));
        Assert.Null(await _store.GetAsync(created.Id));
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_root)) Directory.Delete(_root, true); } catch (IOException) { }
    }
}
