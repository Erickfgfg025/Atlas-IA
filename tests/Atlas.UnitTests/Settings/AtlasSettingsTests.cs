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
        Assert.Equal("http://127.0.0.1:11434/", settings.OllamaEndpoint);
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
    public void RejectsNonLoopbackOllamaEndpoint()
    {
        var settings = new AtlasSettings
        {
            PreferredProvider = "Ollama",
            OllamaEndpoint = "http://example.com:11434/"
        };

        Assert.Throws<ArgumentException>(() => settings.Validate());
    }

    [Fact]
    public void RejectsBlankOllamaModelWhenOllamaIsSelected()
    {
        var settings = new AtlasSettings
        {
            PreferredProvider = "Ollama",
            OllamaModel = "  "
        };

        Assert.Throws<ArgumentException>(() => settings.Validate());
    }

    [Fact]
    public void ReplacesUnusedOllamaFieldsWithDefaultsInsteadOfFailing()
    {
        // A stale Ollama endpoint must not block saving or loading every other
        // preference while Gemini or Hermes is the selected provider.
        var settings = new AtlasSettings
        {
            PreferredProvider = "Hermes",
            EnableMemoryContext = true,
            OllamaModel = string.Empty,
            OllamaEndpoint = "http://example.com:11434/"
        };

        var validated = settings.Validate();

        Assert.Equal(AtlasSettings.DefaultOllamaModel, validated.OllamaModel);
        Assert.Equal(AtlasSettings.DefaultOllamaEndpoint, validated.OllamaEndpoint);
        Assert.True(validated.EnableMemoryContext);
    }

    [Fact]
    public void KeepsOllamaFieldsUntouchedWhenTheyAreAlreadyValid()
    {
        var settings = new AtlasSettings
        {
            PreferredProvider = "Ollama",
            OllamaModel = "qwen2.5:3b",
            OllamaEndpoint = "http://localhost:11434/"
        };

        var validated = settings.Validate();

        Assert.Equal("qwen2.5:3b", validated.OllamaModel);
        Assert.Equal("http://localhost:11434/", validated.OllamaEndpoint);
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
