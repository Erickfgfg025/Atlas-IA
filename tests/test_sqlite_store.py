import asyncio
from uuid import UUID

from atlas.memory.sqlite_store import SQLiteMemoryStore


def test_sqlite_store_persists_memories_between_instances(tmp_path):
    database = tmp_path / "atlas.db"
    store = SQLiteMemoryStore(database)
    created = asyncio.run(
        store.create_memory(
            {
                "kind": "project",
                "content": "ATLAS usa SQLite local",
                "source": "test",
                "scope": "project:atlas",
                "confidence": 0.95,
            }
        )
    )

    reloaded_store = SQLiteMemoryStore(database)
    rows = asyncio.run(reloaded_store.list_memories())
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]
    assert rows[0]["content"] == "ATLAS usa SQLite local"
    assert rows[0]["kind"] == "project"


def test_sqlite_store_delete_only_existing_memory(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "atlas.db")
    created = asyncio.run(
        store.create_memory(
            {"kind": "semantic", "content": "Persistente", "source": "test"}
        )
    )
    memory_id = UUID(created["id"])
    assert asyncio.run(store.delete_memory(memory_id)) is True
    assert asyncio.run(store.delete_memory(memory_id)) is False


def test_sqlite_store_updates_memory_content(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "atlas.db")
    created = asyncio.run(
        store.create_memory(
            {"kind": "semantic", "content": "Versão antiga", "source": "test"}
        )
    )

    updated = asyncio.run(
        store.update_memory(UUID(created["id"]), {"content": "Versão corrigida"})
    )

    assert updated is not None
    assert updated["content"] == "Versão corrigida"
    assert asyncio.run(store.update_memory(UUID("00000000-0000-0000-0000-000000000099"), {"content": "não existe"})) is None
