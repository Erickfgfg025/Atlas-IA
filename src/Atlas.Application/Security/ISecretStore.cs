namespace Atlas.Application.Security;

public interface ISecretStore
{
    Task SetAsync(string key, string secret, CancellationToken cancellationToken = default);
    Task<string?> GetAsync(string key, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(string key, CancellationToken cancellationToken = default);
}
