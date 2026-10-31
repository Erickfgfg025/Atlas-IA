# Atlas local memory

Atlas memory is local-first and is not automatically sent to Gemini or any other cloud provider.

## Storage

- Markdown vault: `%USERPROFILE%\Documents\Atlas\Vault`
- SQLite index: `%LOCALAPPDATA%\Atlas\memory-index.db`
- Markdown is the source of truth. SQLite stores metadata and supports filtering/search.
- If the index is lost or inconsistent, call `IMemoryStore.RebuildIndexAsync` to recreate it from valid Markdown files.

## Categories

- Personal
- Projects
- Preferences
- Episodes

Each note is stored in a category directory with a generated GUID filename. User-provided titles never become filesystem paths. The Markdown front matter contains a stable ID, category, base64-encoded title, and UTC timestamps.

## Safety and consistency

- SQLite commands are parameterized.
- File writes use a temporary file followed by an atomic move.
- Index paths are resolved and checked to remain under the configured vault root.
- Search is bounded to 1–200 results.
- Deletion removes the index row before deleting the Markdown file; an interrupted deletion can leave an orphan file that can be recovered by rebuilding the index. Review the vault before rebuilding if you manually deleted notes.
- Markdown content is treated as data. It must never be executed as a tool instruction.

## Scope

This is the storage foundation. Automatic memory extraction, semantic embeddings, UI management, encryption-at-rest for the vault, and selective cloud context injection are not included yet. Use Windows account/device protections for the Markdown vault; it is currently plain text.
