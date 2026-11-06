using Atlas.Memory;
using Xunit;

namespace Atlas.UnitTests.Memory;

public sealed class MemoryVaultOptionsTests
{
    [Fact]
    public void CreateDefaultKeepsVaultInsideDocumentsAtlasFolder()
    {
        var options = MemoryVaultOptions.CreateDefault();

        // The vault must always be an absolute path: a relative one would silently
        // write memories next to whatever the process working directory happens to be.
        Assert.True(Path.IsPathFullyQualified(options.VaultPath));
        Assert.EndsWith(Path.Combine("Atlas", "Vault"), options.VaultPath, StringComparison.Ordinal);

        var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        if (Path.IsPathFullyQualified(documents))
            Assert.Equal(Path.Combine(documents, "Atlas", "Vault"), options.VaultPath);
    }

    [Fact]
    public void CreateDefaultKeepsIndexInsideLocalAppDataAtlasFolder()
    {
        var options = MemoryVaultOptions.CreateDefault();

        Assert.True(Path.IsPathFullyQualified(options.DatabasePath));
        Assert.EndsWith(Path.Combine("Atlas", "memory-index.db"), options.DatabasePath, StringComparison.Ordinal);

        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if (Path.IsPathFullyQualified(local))
            Assert.Equal(Path.Combine(local, "Atlas", "memory-index.db"), options.DatabasePath);
    }

    [Fact]
    public void CreateDefaultNeverSharesVaultAndIndexPaths()
    {
        var options = MemoryVaultOptions.CreateDefault();

        Assert.NotEqual(options.VaultPath, options.DatabasePath);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("relative/Documents")]
    public void CreateFallsBackToLocalAppDataInsteadOfAWorkingDirectoryPath(string documentsRoot)
    {
        // A redirected or broken Documents folder used to produce a relative vault
        // path, silently writing memories next to the process working directory.
        var local = Path.Combine(Path.GetTempPath(), "atlas-local-appdata");

        var options = MemoryVaultOptions.Create(documentsRoot, local);

        Assert.True(Path.IsPathFullyQualified(options.VaultPath));
        Assert.Equal(Path.Combine(local, "Atlas", "Vault"), options.VaultPath);
        Assert.Equal(Path.Combine(local, "Atlas", "memory-index.db"), options.DatabasePath);
    }

    [Fact]
    public void CreateUsesDocumentsWhenItIsAValidAbsolutePath()
    {
        var documents = Path.Combine(Path.GetTempPath(), "atlas-documents");
        var local = Path.Combine(Path.GetTempPath(), "atlas-local-appdata");

        var options = MemoryVaultOptions.Create(documents, local);

        Assert.Equal(Path.Combine(documents, "Atlas", "Vault"), options.VaultPath);
        Assert.Equal(Path.Combine(local, "Atlas", "memory-index.db"), options.DatabasePath);
    }

    [Fact]
    public void CreateFailsFastWhenNoLocalAppDataRootIsUsable()
    {
        Assert.Throws<InvalidOperationException>(() => MemoryVaultOptions.Create(null, string.Empty));
    }
}
