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
        var bodyResults = await _store.SearchAsync("local memory", MemoryCategory.Projects);

        Assert.NotNull(loaded);
        Assert.Equal("Implement local memory.", loaded.Content);
        Assert.Single(results);
        Assert.Single(bodyResults);
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
        Assert.Equal("New content", (await _store.GetAsync(created.Id))!.Content);
        Assert.Equal(1, await _store.RebuildIndexAsync());
        Assert.Equal("New content", (await _store.GetAsync(created.Id))!.Content);
        Assert.True(await _store.DeleteAsync(created.Id));
        Assert.Null(await _store.GetAsync(created.Id));
    }


    [Fact]
    public async Task ConstructorMigratesLegacyIndexWithoutContentColumn()
    {
        var migrationRoot = Path.Combine(_root, "legacy");
        var vault = Path.Combine(migrationRoot, "vault");
        var database = Path.Combine(migrationRoot, "index.db");
        Directory.CreateDirectory(migrationRoot);
        await using (var connection = new Microsoft.Data.Sqlite.SqliteConnection(
            new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder { DataSource = database }.ToString()))
        {
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = """
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    relative_path TEXT NOT NULL UNIQUE,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                """;
            await command.ExecuteNonQueryAsync();
        }

        var migrated = new MarkdownMemoryStore(new MemoryVaultOptions(vault, database));
        var entry = await migrated.CreateAsync(MemoryCategory.Projects, "Migration", "Legacy index migrated.");
        Assert.Equal("Legacy index migrated.", (await migrated.GetAsync(entry.Id))!.Content);
        Assert.Single(await migrated.SearchAsync("Legacy index"));
    }

    [Fact]
    public async Task UpdateRejectsContentOverLimit_WithoutChangingStoredMemory()
    {
        var created = await _store.CreateAsync(MemoryCategory.Projects, "Stable title", "Stable content");

        await Assert.ThrowsAsync<ArgumentException>(() =>
            _store.UpdateAsync(created.Id, "Changed title", new string('x', 100_001)));

        var loaded = await _store.GetAsync(created.Id);
        Assert.NotNull(loaded);
        Assert.Equal("Stable title", loaded.Title);
        Assert.Equal("Stable content", loaded.Content);
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_root)) Directory.Delete(_root, true); } catch (IOException) { }
    }
}
