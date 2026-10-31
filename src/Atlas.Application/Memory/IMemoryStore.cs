namespace Atlas.Application.Memory;

public interface IMemoryStore
{
    Task<MemoryEntry> CreateAsync(MemoryCategory category, string title, string content, CancellationToken cancellationToken = default);
    Task<MemoryEntry?> GetAsync(Guid id, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, MemoryCategory? category = null, int limit = 50, CancellationToken cancellationToken = default);
    Task<MemoryEntry> UpdateAsync(Guid id, string title, string content, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(Guid id, CancellationToken cancellationToken = default);
    Task<int> RebuildIndexAsync(CancellationToken cancellationToken = default);
}
