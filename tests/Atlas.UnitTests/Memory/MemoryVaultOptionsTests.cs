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
        Assert.EndsWith(Path.Combine("Atlas", "Vault"), options.VaultPath, StringComparison.Ordinal);
    }

    [Fact]
    public void CreateDefaultKeepsIndexInsideLocalAppDataAtlasFolder()
    {
        var options = MemoryVaultOptions.CreateDefault();

        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        Assert.Equal(Path.Combine(local, "Atlas", "memory-index.db"), options.DatabasePath);
        Assert.EndsWith(Path.Combine("Atlas", "memory-index.db"), options.DatabasePath, StringComparison.Ordinal);
    }

    [Fact]
    public void CreateDefaultNeverSharesVaultAndIndexPaths()
    {
        var options = MemoryVaultOptions.CreateDefault();

        Assert.NotEqual(options.VaultPath, options.DatabasePath);
    }
}
