using System.Runtime.Versioning;
using Atlas.Infrastructure.Security;
using Xunit;

namespace Atlas.UnitTests.Security;

[SupportedOSPlatform("windows")]
public sealed class ProtectedDataSecretStoreTests
{
    [Fact]
    public async Task SecretCanBeStoredAndReadByTheSameWindowsUser()
    {
        var directory = Path.Combine(Path.GetTempPath(), "AtlasSecretTests", Guid.NewGuid().ToString("N"));
        try
        {
            var store = new ProtectedDataSecretStore(directory);
            await store.SetAsync("gemini-api-key", "test-secret-value");

            Assert.Equal("test-secret-value", await store.GetAsync("gemini-api-key"));
        }
        finally
        {
            if (Directory.Exists(directory))
                Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public async Task SecretKeysAreIsolatedAndDeleteIsIdempotent()
    {
        var directory = Path.Combine(Path.GetTempPath(), "AtlasSecretTests", Guid.NewGuid().ToString("N"));
        try
        {
            var store = new ProtectedDataSecretStore(directory);
            await store.SetAsync("provider-a", "secret-a");

            Assert.Null(await store.GetAsync("provider-b"));
            Assert.True(await store.DeleteAsync("provider-a"));
            Assert.False(await store.DeleteAsync("provider-a"));
            Assert.Null(await store.GetAsync("provider-a"));
        }
        finally
        {
            if (Directory.Exists(directory))
                Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public async Task RejectsEmptyKeyAndSecret()
    {
        var store = new ProtectedDataSecretStore(Path.GetTempPath());
        await Assert.ThrowsAsync<ArgumentException>(() => store.SetAsync("", "secret"));
        await Assert.ThrowsAsync<ArgumentException>(() => store.SetAsync("api-key", " "));
    }
}
