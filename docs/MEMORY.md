# Atlas local memory

Atlas memory is local-first. Memory context is **disabled by default** and must be enabled separately in preferences.

## Storage

- Markdown vault: `%USERPROFILE%\Documents\Atlas\Vault`
- SQLite index: `%LOCALAPPDATA%\Atlas\memory-index.db`
- Markdown is the source of truth. SQLite stores metadata and a searchable content index.
- Existing indexes are migrated when the content column is missing.
- If the index is lost or inconsistent, call `IMemoryStore.RebuildIndexAsync` to recreate it from valid Markdown files.

## Categories

- Personal
- Projects
- Preferences
- Episodes

Each note is stored in a category directory with a generated GUID filename. User-provided titles never become filesystem paths. The Markdown front matter contains a stable ID, category, base64-encoded title, and UTC timestamps.

## User control and privacy

- The user must explicitly click **Salvar última conversa na memória local** to save the latest successful exchange.
- The user must separately enable **Usar memórias locais como contexto** before the agent retrieves memories for a response.
- With Ollama, retrieved memory remains on the local machine.
- With Gemini, retrieved memory is included in the prompt sent to Google's API only when both memory context and cloud requests are enabled. These are independent consent settings.
- Disabling memory context stops retrieval for future requests; it does not delete previously saved notes.
- The memory context is labelled as untrusted reference data. Instructions found inside notes must never be treated as executable commands or policy overrides.

## Safety and consistency

- SQLite commands are parameterized.
- File writes use a temporary file followed by an atomic move.
- Updates write a separate versioned file before switching the SQLite reference, preserving the previous file if the database update fails.
- Index paths are resolved and checked to remain under the configured vault root.
- Search is bounded to 1–200 results.
- SQLite's native dependency is pinned to a patched version to avoid the known high-severity SQLitePCLRaw 2.1.11 advisory.
- Deletion removes the index row before deleting the Markdown file. If deletion is interrupted after the database commit, a leftover Markdown file may be recovered by rebuilding the index; review the vault before rebuilding after a partial deletion.
- Markdown content is plain text and is not encrypted by Atlas yet. Protect the Windows account and device.

## Scope

This is the first integrated memory version. Automatic memory extraction, semantic embeddings, full memory-management UI, vault encryption-at-rest, and selective memory deletion from the UI are not included yet.
