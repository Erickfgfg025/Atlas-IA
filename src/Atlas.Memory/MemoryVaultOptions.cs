namespace Atlas.Memory;

public sealed record MemoryVaultOptions(string VaultPath, string DatabasePath)
{
    public static MemoryVaultOptions CreateDefault()
    {
        var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        var root = Path.Combine(documents, "Atlas", "Vault");
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        return new MemoryVaultOptions(root, Path.Combine(local, "Atlas", "memory-index.db"));
    }
}
