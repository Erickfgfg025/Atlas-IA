using Atlas.Application.Settings;
using Atlas.Infrastructure.Settings;
using Xunit;

namespace Atlas.UnitTests.Settings;

public sealed class JsonSettingsStoreRecoveryTests
{
    [Theory]
    [InlineData("{ \"PreferredProvider\": \"Gemini\", ")]                 // truncated write
    [InlineData("not json at all")]                                       // overwritten file
    [InlineData("{ \"EnableCloudRequests\": \"maybe\" }")]                // wrong type
    public async Task LoadFallsBackToDefaultsAndQuarantinesUnreadableFile(string content)
    {
        var directory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var file = Path.Combine(directory, "settings.json");
        Directory.CreateDirectory(directory);
        try
        {
            await File.WriteAllTextAsync(file, content);
            var store = new JsonSettingsStore(file);

            var settings = await store.LoadAsync();

            // The application keeps starting with the safe defaults.
            Assert.Equal(new AtlasSettings(), settings);
            Assert.False(settings.EnableCloudRequests);

            // The unusable file is preserved for inspection instead of being deleted.
            Assert.False(File.Exists(file));
            Assert.NotNull(store.QuarantinedFilePath);
            Assert.True(File.Exists(store.QuarantinedFilePath!));
            Assert.Equal(content, await File.ReadAllTextAsync(store.QuarantinedFilePath!));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public async Task LoadFallsBackToDefaultsWhenStoredValuesBreakTheInvariants()
    {
        var directory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var file = Path.Combine(directory, "settings.json");
        Directory.CreateDirectory(directory);
        try
        {
            // Cloud requests with a local provider can only come from a hand-edited or
            // older file; it must not stop the application from loading settings.
            await File.WriteAllTextAsync(file,
                """{ "EnableCloudRequests": true, "PreferredProvider": "Ollama" }""");
            var store = new JsonSettingsStore(file);

            var settings = await store.LoadAsync();

            Assert.Equal(AtlasSettings.DefaultProvider, settings.PreferredProvider);
            Assert.False(settings.EnableCloudRequests);
            Assert.NotNull(store.QuarantinedFilePath);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public async Task LoadKeepsAValidFileAndWritesBackAfterRecovery()
    {
        var directory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var file = Path.Combine(directory, "settings.json");
        Directory.CreateDirectory(directory);
        try
        {
            await File.WriteAllTextAsync(file, "{ \"PreferredProvider\": \"Gemini\", \"KeepWindowOnTop\": true }");
            var store = new JsonSettingsStore(file);

            var settings = await store.LoadAsync();

            Assert.True(settings.KeepWindowOnTop);
            Assert.Null(store.QuarantinedFilePath);
            Assert.True(File.Exists(file));

            await store.SaveAsync(settings with { EnableMemoryContext = true });
            var reloaded = await new JsonSettingsStore(file).LoadAsync();
            Assert.True(reloaded.EnableMemoryContext);
            Assert.True(reloaded.KeepWindowOnTop);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }
}
