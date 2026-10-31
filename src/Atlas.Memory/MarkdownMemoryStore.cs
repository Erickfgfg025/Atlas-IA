using System.Text;
using Atlas.Application.Memory;
using Microsoft.Data.Sqlite;

namespace Atlas.Memory;

/// <summary>
/// Local-first memory store. Markdown files are authoritative; SQLite is a rebuildable search index.
/// </summary>
public sealed class MarkdownMemoryStore : IMemoryStore
{
    private readonly string _vaultRoot;
    private readonly string _connectionString;
    private readonly SemaphoreSlim _gate = new(1, 1);

    public MarkdownMemoryStore(MemoryVaultOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (string.IsNullOrWhiteSpace(options.VaultPath)) throw new ArgumentException("Vault path is required.", nameof(options));
        if (string.IsNullOrWhiteSpace(options.DatabasePath)) throw new ArgumentException("Database path is required.", nameof(options));

        _vaultRoot = Path.GetFullPath(options.VaultPath);
        var databasePath = Path.GetFullPath(options.DatabasePath);
        _connectionString = new SqliteConnectionStringBuilder { DataSource = databasePath, Mode = SqliteOpenMode.ReadWriteCreate, Cache = SqliteCacheMode.Shared }.ToString();
        Directory.CreateDirectory(_vaultRoot);
        Directory.CreateDirectory(Path.GetDirectoryName(_databasePath)!);
        InitializeDatabaseAsync(CancellationToken.None).GetAwaiter().GetResult();
    }

    public async Task<MemoryEntry> CreateAsync(MemoryCategory category, string title, string content, CancellationToken cancellationToken = default)
    {
        Validate(category, title, content);
        var now = DateTimeOffset.UtcNow;
        var entry = new MemoryEntry(Guid.NewGuid(), category, title.Trim(), content.Trim(), now, now);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var path = GetPath(entry);
            await WriteMarkdownAsync(path, entry, cancellationToken);
            try
            {
                await using var connection = await OpenConnectionAsync(cancellationToken);
                await using var command = connection.CreateCommand();
                command.CommandText = """
                    INSERT INTO memories (id, category, title, content, relative_path, created_utc, updated_utc)
                    VALUES ($id, $category, $title, $content, $path, $created, $updated);
                    """;
                AddParameters(command, entry, GetRelativePath(path));
                await command.ExecuteNonQueryAsync(cancellationToken);
            }
            catch
            {
                TryDelete(path);
                throw;
            }
            return entry;
        }
        finally { _gate.Release(); }
    }

    public async Task<MemoryEntry?> GetAsync(Guid id, CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var metadata = await FindMetadataAsync(id, cancellationToken);
            if (metadata is null) return null;
            var path = ResolveRelativePath(metadata.Value.Path);
            if (!File.Exists(path)) return null;
            var content = await ReadBodyAsync(path, cancellationToken);
            return new MemoryEntry(id, metadata.Value.Category, metadata.Value.Title, content, metadata.Value.Created, metadata.Value.Updated);
        }
        finally { _gate.Release(); }
    }

    public async Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, MemoryCategory? category = null, int limit = 50, CancellationToken cancellationToken = default)
    {
        if (limit is < 1 or > 200) throw new ArgumentOutOfRangeException(nameof(limit), "Limit must be between 1 and 200.");
        await _gate.WaitAsync(cancellationToken);
        try
        {
            await using var connection = await OpenConnectionAsync(cancellationToken);
            await using var command = connection.CreateCommand();
            command.CommandText = """
                SELECT id, category, title, relative_path, created_utc, updated_utc
                FROM memories
                WHERE ($query = '' OR title LIKE $pattern ESCAPE '\' OR content LIKE $pattern ESCAPE '\')
                  AND ($category IS NULL OR category = $category)
                ORDER BY updated_utc DESC LIMIT $limit;
                """;
            command.Parameters.AddWithValue("$query", query?.Trim() ?? string.Empty);
            command.Parameters.AddWithValue("$pattern", "%" + EscapeLike(query?.Trim() ?? string.Empty) + "%");
            command.Parameters.AddWithValue("$category", category?.ToString());
            command.Parameters.AddWithValue("$limit", limit);

            var results = new List<MemoryEntry>();
            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var id = Guid.Parse(reader.GetString(0));
                var itemCategory = Enum.Parse<MemoryCategory>(reader.GetString(1));
                var title = reader.GetString(2);
                var path = ResolveRelativePath(reader.GetString(3));
                if (!File.Exists(path)) continue;
                var content = await ReadBodyAsync(path, cancellationToken);
                results.Add(new MemoryEntry(id, itemCategory, title, content,
                    DateTimeOffset.Parse(reader.GetString(4)), DateTimeOffset.Parse(reader.GetString(5))));
            }
            return results;
        }
        finally { _gate.Release(); }
    }

    public async Task<MemoryEntry> UpdateAsync(Guid id, string title, string content, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(title)) throw new ArgumentException("Title is required.", nameof(title));
        if (string.IsNullOrWhiteSpace(content)) throw new ArgumentException("Content is required.", nameof(content));
        if (title.Length > 200) throw new ArgumentException("Title cannot exceed 200 characters.", nameof(title));

        await _gate.WaitAsync(cancellationToken);
        try
        {
            var metadata = await FindMetadataAsync(id, cancellationToken) ?? throw new KeyNotFoundException($"Memory '{id}' was not found.");
            var oldPath = ResolveRelativePath(metadata.Value.Path);
            var updated = new MemoryEntry(id, metadata.Value.Category, title.Trim(), content.Trim(), metadata.Value.Created, DateTimeOffset.UtcNow);
            var newPath = GetPath(updated);
            await WriteMarkdownAsync(newPath, updated, cancellationToken);
            try
            {
                await using var connection = await OpenConnectionAsync(cancellationToken);
                await using var command = connection.CreateCommand();
                command.CommandText = "UPDATE memories SET title=$title, content=$content, relative_path=$path, updated_utc=$updated WHERE id=$id;";
                command.Parameters.AddWithValue("$title", updated.Title);
                command.Parameters.AddWithValue("$content", updated.Content);
                command.Parameters.AddWithValue("$path", GetRelativePath(newPath));
                command.Parameters.AddWithValue("$updated", updated.UpdatedAt.ToString("O"));
                command.Parameters.AddWithValue("$id", id.ToString("D"));
                await command.ExecuteNonQueryAsync(cancellationToken);
            }
            catch
            {
                if (!string.Equals(oldPath, newPath, StringComparison.OrdinalIgnoreCase)) TryDelete(newPath);
                throw;
            }
            if (!string.Equals(oldPath, newPath, StringComparison.OrdinalIgnoreCase)) TryDelete(oldPath);
            return updated;
        }
        finally { _gate.Release(); }
    }

    public async Task<bool> DeleteAsync(Guid id, CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var metadata = await FindMetadataAsync(id, cancellationToken);
            if (metadata is null) return false;
            await using var connection = await OpenConnectionAsync(cancellationToken);
            await using var transaction = await connection.BeginTransactionAsync(cancellationToken);
            await using (var command = connection.CreateCommand())
            {
                command.Transaction = (SqliteTransaction)transaction;
                command.CommandText = "DELETE FROM memories WHERE id=$id;";
                command.Parameters.AddWithValue("$id", id.ToString("D"));
                await command.ExecuteNonQueryAsync(cancellationToken);
            }
            await transaction.CommitAsync(cancellationToken);
            TryDelete(ResolveRelativePath(metadata.Value.Path));
            return true;
        }
        finally { _gate.Release(); }
    }

    public async Task<int> RebuildIndexAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var recovered = new List<(MemoryEntry Entry, string Path)>();
            foreach (var file in Directory.EnumerateFiles(_vaultRoot, "*.md", SearchOption.AllDirectories))
            {
                cancellationToken.ThrowIfCancellationRequested();
                var parsed = await ReadMarkdownAsync(file, cancellationToken);
                if (parsed is not null) recovered.Add((parsed, GetRelativePath(file)));
            }

            await using var connection = await OpenConnectionAsync(cancellationToken);
            await using var transaction = await connection.BeginTransactionAsync(cancellationToken);
            await using (var clear = connection.CreateCommand())
            {
                clear.Transaction = (SqliteTransaction)transaction;
                clear.CommandText = "DELETE FROM memories;";
                await clear.ExecuteNonQueryAsync(cancellationToken);
            }
            foreach (var item in recovered)
            {
                await using var insert = connection.CreateCommand();
                insert.Transaction = (SqliteTransaction)transaction;
                insert.CommandText = """
                    INSERT OR REPLACE INTO memories (id, category, title, content, relative_path, created_utc, updated_utc)
                    VALUES ($id, $category, $title, $content, $path, $created, $updated);
                    """;
                AddParameters(insert, item.Entry, item.Path);
                await insert.ExecuteNonQueryAsync(cancellationToken);
            }
            await transaction.CommitAsync(cancellationToken);
            return recovered.Count;
        }
        finally { _gate.Release(); }
    }

    private async Task InitializeDatabaseAsync(CancellationToken cancellationToken)
    {
        await using var connection = await OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                relative_path TEXT NOT NULL UNIQUE,
                created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_memories_category_updated ON memories(category, updated_utc DESC);
            """;
        await command.ExecuteNonQueryAsync(cancellationToken);

        // Migrate indexes created by earlier Atlas builds.
        await using var columnsCommand = connection.CreateCommand();
        columnsCommand.CommandText = "PRAGMA table_info(memories);";
        await using var reader = await columnsCommand.ExecuteReaderAsync(cancellationToken);
        var hasContentColumn = false;
        while (await reader.ReadAsync(cancellationToken))
        {
            if (string.Equals(reader.GetString(1), "content", StringComparison.OrdinalIgnoreCase))
            {
                hasContentColumn = true;
                break;
            }
        }
        await reader.DisposeAsync();
        if (!hasContentColumn)
        {
            await using var migration = connection.CreateCommand();
            migration.CommandText = "ALTER TABLE memories ADD COLUMN content TEXT NOT NULL DEFAULT '';";
            await migration.ExecuteNonQueryAsync(cancellationToken);
        }
    }

    private async Task<SqliteConnection> OpenConnectionAsync(CancellationToken cancellationToken)
    {
        var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        return connection;
    }

    private async Task<(MemoryCategory Category, string Title, string Path, DateTimeOffset Created, DateTimeOffset Updated)?> FindMetadataAsync(Guid id, CancellationToken cancellationToken)
    {
        await using var connection = await OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT category,title,relative_path,created_utc,updated_utc FROM memories WHERE id=$id;";
        command.Parameters.AddWithValue("$id", id.ToString("D"));
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken)) return null;
        return (Enum.Parse<MemoryCategory>(reader.GetString(0)), reader.GetString(1), reader.GetString(2),
            DateTimeOffset.Parse(reader.GetString(3)), DateTimeOffset.Parse(reader.GetString(4)));
    }

    private string GetPath(MemoryEntry entry) => Path.Combine(_vaultRoot, entry.Category.ToString().ToLowerInvariant(), entry.Id.ToString("N") + ".md");
    private string GetRelativePath(string path) => Path.GetRelativePath(_vaultRoot, path);
    private string ResolveRelativePath(string relative)
    {
        var full = Path.GetFullPath(Path.Combine(_vaultRoot, relative));
        var prefix = _vaultRoot.EndsWith(Path.DirectorySeparatorChar) ? _vaultRoot : _vaultRoot + Path.DirectorySeparatorChar;
        if (!full.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Memory index contains a path outside the vault.");
        return full;
    }

    private static async Task WriteMarkdownAsync(string path, MemoryEntry entry, CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var title = Convert.ToBase64String(Encoding.UTF8.GetBytes(entry.Title));
        var markdown = $"---\natlas_id: {entry.Id:D}\ncategory: {entry.Category}\ntitle_base64: {title}\ncreated_utc: {entry.CreatedAt:O}\nupdated_utc: {entry.UpdatedAt:O}\n---\n\n# {entry.Title}\n\n{entry.Content}\n";
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            await File.WriteAllTextAsync(temp, markdown, new UTF8Encoding(false), cancellationToken);
            File.Move(temp, path, true);
        }
        finally { TryDelete(temp); }
    }

    private static async Task<string> ReadBodyAsync(string path, CancellationToken cancellationToken)
    {
        var text = await File.ReadAllTextAsync(path, cancellationToken);
        var end = text.IndexOf("\n---\n", StringComparison.Ordinal);
        if (!text.StartsWith("---\n", StringComparison.Ordinal) || end < 0) return text;
        return ExtractBody(text, end + 5);
    }

    private static async Task<MemoryEntry?> ReadMarkdownAsync(string path, CancellationToken cancellationToken)
    {
        try
        {
            var text = await File.ReadAllTextAsync(path, cancellationToken);
            if (!text.StartsWith("---\n", StringComparison.Ordinal)) return null;
            var end = text.IndexOf("\n---\n", StringComparison.Ordinal);
            if (end < 0) return null;
            var header = text[4..end].Split('\n');
            string? Value(string key) => header.FirstOrDefault(x => x.StartsWith(key + ": ", StringComparison.Ordinal))?[(key.Length + 2)..];
            if (!Guid.TryParse(Value("atlas_id"), out var id) ||
                !Enum.TryParse<MemoryCategory>(Value("category"), out var category) ||
                Value("title_base64") is not { } encoded ||
                Value("created_utc") is not { } created ||
                Value("updated_utc") is not { } updated) return null;
            var title = Encoding.UTF8.GetString(Convert.FromBase64String(encoded));
            var body = ExtractBody(text, end + 5);
            return new MemoryEntry(id, category, title, body, DateTimeOffset.Parse(created), DateTimeOffset.Parse(updated));
        }
        catch (Exception ex) when (ex is IOException or FormatException or ArgumentException) { return null; }
    }

    private static string ExtractBody(string text, int bodyStart)
    {
        while (bodyStart < text.Length && text[bodyStart] == '\n') bodyStart++;
        var headingEnd = text.IndexOf('\n', bodyStart);
        if (headingEnd >= 0 && text[bodyStart..headingEnd].StartsWith("# ", StringComparison.Ordinal))
        {
            bodyStart = headingEnd + 1;
            if (bodyStart < text.Length && text[bodyStart] == '\n') bodyStart++;
        }
        return text[bodyStart..].Trim();
    }

    private static void AddParameters(SqliteCommand command, MemoryEntry entry, string relativePath)
    {
        command.Parameters.AddWithValue("$id", entry.Id.ToString("D"));
        command.Parameters.AddWithValue("$category", entry.Category.ToString());
        command.Parameters.AddWithValue("$title", entry.Title);
        command.Parameters.AddWithValue("$content", entry.Content);
        command.Parameters.AddWithValue("$path", relativePath);
        command.Parameters.AddWithValue("$created", entry.CreatedAt.ToString("O"));
        command.Parameters.AddWithValue("$updated", entry.UpdatedAt.ToString("O"));
    }

    private static void Validate(MemoryCategory category, string title, string content)
    {
        if (!Enum.IsDefined(category)) throw new ArgumentOutOfRangeException(nameof(category));
        if (string.IsNullOrWhiteSpace(title)) throw new ArgumentException("Title is required.", nameof(title));
        if (title.Length > 200) throw new ArgumentException("Title cannot exceed 200 characters.", nameof(title));
        if (string.IsNullOrWhiteSpace(content)) throw new ArgumentException("Content is required.", nameof(content));
        if (content.Length > 100_000) throw new ArgumentException("Memory content cannot exceed 100,000 characters.", nameof(content));
    }

    private static string EscapeLike(string value) => value.Replace("\\", "\\\\").Replace("%", "\\%").Replace("_", "\\_");
    private static void TryDelete(string path) { try { if (File.Exists(path)) File.Delete(path); } catch (IOException) { } catch (UnauthorizedAccessException) { } }
}
