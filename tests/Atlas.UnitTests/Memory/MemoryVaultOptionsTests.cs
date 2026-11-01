using Atlas.Memory;
using Xunit;

namespace Atlas.UnitTests.Memory;

public sealed class MemoryVaultOptionsTests
{
    [Fact]
    public void CreateDefaultKeepsVaultInsideDocumentsAtlasFolder()
    {
        var options = MemoryVaultOptions.CreateDefault();

        var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        Assert.Equal(Path.Combine(documents, "Atlas", "Vault"), options.VaultPath);
        Assert.True(Path.IsPathRooted(options.VaultPath));
    }

    [Fact]
    public void CreateDefaultKeepsIndexInsideLocalAppDataAtlasFolder()
    {
        var options = MemoryVaultOptions.CreateDefault();

        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        Assert.Equal(Path.Combine(local, "Atlas", "memory-index.db"), options.DatabasePath);
        Assert.True(Path.IsPathRooted(options.DatabasePath));
    }

    [Fact]
    public void CreateDefaultNeverSharesVaultAndIndexPaths()
    {
        var options = MemoryVaultOptions.CreateDefault();

        Assert.NotEqual(options.VaultPath, options.DatabasePath);
    }
}
