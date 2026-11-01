using Atlas.Contracts.AI;

namespace Atlas.Application.AI;

public interface IModelProvider
{
    string Name { get; }
    Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken);
}
