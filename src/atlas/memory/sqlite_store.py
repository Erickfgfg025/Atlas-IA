"""SQLite-backed local memory store for a single-user ATLAS installation."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


def default_database_path() -> Path:
    """Return a per-user writable database path without requiring configuration."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ATLAS AI" / "atlas.db"
    return Path.home() / ".local" / "share" / "atlas-ai" / "atlas.db"


class SQLiteMemoryStore:
    """Persist memory on this computer; intended for the local, single-user mode."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path).expanduser() if database_path else default_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS atlas_memories (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK (
                        kind IN ('session', 'episodic', 'semantic', 'project', 'operational')
                    ),
                    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 12000),
                    source TEXT NOT NULL CHECK (length(source) BETWEEN 1 AND 200),
                    scope TEXT NOT NULL CHECK (length(scope) BETWEEN 1 AND 200),
                    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_atlas_memories_created "
                "ON atlas_memories(created_at DESC)"
            )
            connection.commit()

    async def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, kind, content, source, scope, confidence, created_at "
                "FROM atlas_memories ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid4()),
            "kind": memory["kind"],
            "content": memory["content"],
            "source": memory["source"],
            "scope": memory.get("scope", "user"),
            "confidence": memory.get("confidence", 1.0),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO atlas_memories
                    (id, kind, content, source, scope, confidence, created_at)
                VALUES
                    (:id, :kind, :content, :source, :scope, :confidence, :created_at)
                """,
                row,
            )
            connection.commit()
        return row

    async def delete_memory(self, memory_id: UUID) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM atlas_memories WHERE id = ?", (str(memory_id),)
            )
            connection.commit()
        return cursor.rowcount > 0
