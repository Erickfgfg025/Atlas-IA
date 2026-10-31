namespace Atlas.Application.Settings;

public interface ISettingsStore
{
    Task<AtlasSettings> LoadAsync(CancellationToken cancellationToken = default);
    Task SaveAsync(AtlasSettings settings, CancellationToken cancellationToken = default);
}
