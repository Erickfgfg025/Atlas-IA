using Atlas.Contracts.AI;

namespace Atlas.Application.AI;

public interface IModelRouter
{
    Task<ModelResponse> GenerateAsync(ModelRequest request, CancellationToken cancellationToken);
}
