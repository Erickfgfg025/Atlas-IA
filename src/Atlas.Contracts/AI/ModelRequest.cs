namespace Atlas.Contracts.AI;

public sealed record ModelRequest(
    string Prompt,
    string? SystemInstruction = null,
    IReadOnlyList<ModelMessage>? History = null);

public sealed record ModelMessage(string Role, string Content);

public sealed record ModelResponse(string Content, string Provider, string Model);
