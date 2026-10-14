"""SQLite-backed conversation history, kept separate from durable user memories."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from atlas.memory.sqlite_store import default_database_path


class SQLiteConversationStore:
    """Persist conversations and their messages in the local ATLAS database."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = (
            Path(database_path).expanduser() if database_path else default_database_path()
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS atlas_conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 160),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS atlas_conversation_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL
                        REFERENCES atlas_conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 20000),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_atlas_conversations_updated "
                "ON atlas_conversations(updated_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_atlas_messages_conversation "
                "ON atlas_conversation_messages(conversation_id, created_at)"
            )
            connection.commit()

    async def create_conversation(self, title: str = "Nova conversa") -> dict[str, Any]:
        clean_title = title.strip()[:160] or "Nova conversa"
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(uuid4()),
            "title": clean_title,
            "created_at": now,
            "updated_at": now,
        }
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO atlas_conversations (id, title, created_at, updated_at)
                VALUES (:id, :title, :created_at, :updated_at)
                """,
                row,
            )
            connection.commit()
        return row

    async def list_conversations(self, limit: int = 30) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT m.content FROM atlas_conversation_messages AS m
                        WHERE m.conversation_id = c.id
                        ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1) AS last_message
                FROM atlas_conversations AS c
                ORDER BY c.updated_at DESC, c.rowid DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def list_messages(
        self, conversation_id: UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with closing(self._connect()) as connection:
            exists = connection.execute(
                "SELECT 1 FROM atlas_conversations WHERE id = ?",
                (str(conversation_id),),
            ).fetchone()
            if exists is None:
                return []
            rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM atlas_conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (str(conversation_id), safe_limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    async def add_message(
        self, conversation_id: UUID, role: str, content: str
    ) -> dict[str, Any] | None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        clean_content = content.strip()
        if not clean_content or len(clean_content) > 20000:
            raise ValueError("content must contain between 1 and 20000 characters")
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(uuid4()),
            "conversation_id": str(conversation_id),
            "role": role,
            "content": clean_content,
            "created_at": now,
        }
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            exists = connection.execute(
                "SELECT 1 FROM atlas_conversations WHERE id = ?",
                (str(conversation_id),),
            ).fetchone()
            if exists is None:
                return None
            connection.execute(
                """
                INSERT INTO atlas_conversation_messages
                    (id, conversation_id, role, content, created_at)
                VALUES (:id, :conversation_id, :role, :content, :created_at)
                """,
                row,
            )
            connection.execute(
                "UPDATE atlas_conversations SET updated_at = ? WHERE id = ?",
                (now, str(conversation_id)),
            )
            connection.commit()
        return row

    async def update_title(
        self, conversation_id: UUID, title: str
    ) -> dict[str, Any] | None:
        clean_title = title.strip()
        if not clean_title or len(clean_title) > 160:
            raise ValueError("title must contain between 1 and 160 characters")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE atlas_conversations SET title = ?, updated_at = ? WHERE id = ?",
                (clean_title, now, str(conversation_id)),
            )
            if cursor.rowcount == 0:
                connection.commit()
                return None
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM atlas_conversations WHERE id = ?",
                (str(conversation_id),),
            ).fetchone()
            connection.commit()
        return dict(row) if row is not None else None

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                "DELETE FROM atlas_conversations WHERE id = ?",
                (str(conversation_id),),
            )
            connection.commit()
        return cursor.rowcount > 0
