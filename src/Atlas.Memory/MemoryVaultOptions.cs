namespace Atlas.Memory;

public sealed record MemoryVaultOptions(string VaultPath, string DatabasePath)
{
    public static MemoryVaultOptions CreateDefault() => Create(
        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData));

    /// <summary>
    /// Builds the default paths from explicit roots. When the Documents folder is
    /// unavailable (folder redirection, roaming profile or a broken shell folder the
    /// shell reports as empty) the vault falls back to the local application data
    /// folder instead of resolving against the process working directory.
    /// </summary>
    public static MemoryVaultOptions Create(string? documentsRoot, string? localAppDataRoot)
    {
        var local = ResolveRoot(localAppDataRoot) ??
                    throw new InvalidOperationException(
                        "A pasta de dados locais do usuário não está disponível; a memória do Atlas não pode ser configurada.");
        var documents = ResolveRoot(documentsRoot) ?? local;

        return new MemoryVaultOptions(
            Path.Combine(documents, "Atlas", "Vault"),
            Path.Combine(local, "Atlas", "memory-index.db"));
    }

    private static string? ResolveRoot(string? value) =>
        string.IsNullOrWhiteSpace(value) || !Path.IsPathFullyQualified(value) ? null : value;
}
