namespace Atlas.Application.Memory;

public sealed record MemoryEntry(
    Guid Id,
    MemoryCategory Category,
    string Title,
    string Content,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);
