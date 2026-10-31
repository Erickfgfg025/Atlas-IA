using Atlas.Application.Settings;
using Atlas.Infrastructure.Settings;
using Xunit;

namespace Atlas.UnitTests.Settings;

public sealed class AtlasSettingsTests
{
    [Fact]
    public void DefaultsKeepCloudRequestsDisabled()
    {
        var settings = new AtlasSettings();

        Assert.False(settings.EnableCloudRequests);
        Assert.False(settings.StartWithWindows);
        Assert.Equal("Gemini", settings.PreferredProvider);
    }

    [Fact]
    public void RejectsCloudRequestsWithLocalProvider()
    {
        var settings = new AtlasSettings
        {
            EnableCloudRequests = true,
            PreferredProvider = "Ollama"
        };

        Assert.Throws<ArgumentException>(() => settings.Validate());
    }

    [Fact]
    public async Task SettingsPersistBetweenStoreInstances()
    {
        var file = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"), "settings.json");
        try
        {
            var firstStore = new JsonSettingsStore(file);
            var expected = new AtlasSettings
            {
                EnableCloudRequests = true,
                PreferredProvider = "Gemini",
                KeepWindowOnTop = true
            };

            await firstStore.SaveAsync(expected);
            var loaded = await new JsonSettingsStore(file).LoadAsync();

            Assert.Equal(expected, loaded);
        }
        finally
        {
            var directory = Path.GetDirectoryName(file);
            if (directory is not null && Directory.Exists(directory))
                Directory.Delete(directory, recursive: true);
        }
    }
}
