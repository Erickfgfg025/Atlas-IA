import asyncio
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException

from atlas.backend.config import Settings
from atlas.memory.supabase_store import SupabaseMemoryStore


def make_settings() -> Settings:
    return Settings(
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
    )


def make_store(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = SupabaseMemoryStore(
        make_settings(),
        access_token="user-access-token",
        user_id="user-123",
        client=client,
    )
    return store, client


def test_list_memories_uses_user_token_and_user_scope():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/rest/v1/atlas_memories"
        assert request.headers["apikey"] == "public-test-key"
        assert request.headers["authorization"] == "Bearer user-access-token"
        assert request.url.params["user_id"] == "eq.user-123"
        assert request.url.params["limit"] == "7"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "kind": "semantic",
                    "content": "Prefere respostas objetivas",
                    "source": "user-confirmed",
                    "scope": "user",
                    "confidence": 1.0,
                    "created_at": "2026-10-14T12:00:00Z",
                }
            ],
        )

    async def run():
        store, client = make_store(handler)
        try:
            return await store.list_memories(limit=7)
        finally:
            await client.aclose()

    rows = asyncio.run(run())
    assert len(rows) == 1
    assert rows[0]["kind"] == "semantic"


def test_create_memory_overwrites_client_user_id_with_verified_user():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["authorization"] == "Bearer user-access-token"
        payload = request.read()
        assert b'"user_id":"user-123"' in payload
        assert b'"user_id":"attacker-id"' not in payload
        assert request.headers["prefer"] == "return=representation"
        return httpx.Response(
            201,
            json=[
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "kind": "project",
                    "content": "ATLAS AI usa PySide6",
                    "source": "conversation",
                    "scope": "project:atlas",
                    "confidence": 0.9,
                    "created_at": "2026-10-14T12:00:00Z",
                }
            ],
        )

    async def run():
        store, client = make_store(handler)
        try:
            return await store.create_memory(
                {
                    "kind": "project",
                    "content": "ATLAS AI usa PySide6",
                    "source": "conversation",
                    "scope": "project:atlas",
                    "confidence": 0.9,
                    "user_id": "attacker-id",
                }
            )
        finally:
            await client.aclose()

    row = asyncio.run(run())
    assert row["kind"] == "project"


def test_delete_memory_filters_by_memory_and_user_id():
    memory_id = UUID("00000000-0000-0000-0000-000000000003")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.params["id"] == f"eq.{memory_id}"
        assert request.url.params["user_id"] == "eq.user-123"
        return httpx.Response(200, json=[{"id": str(memory_id)}])

    async def run():
        store, client = make_store(handler)
        try:
            return await store.delete_memory(memory_id)
        finally:
            await client.aclose()

    assert asyncio.run(run()) is True


def test_memory_store_fails_closed_when_supabase_is_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "row-level security denied"})

    async def run():
        store, client = make_store(handler)
        try:
            return await store.list_memories()
        finally:
            await client.aclose()

    with pytest.raises(HTTPException) as error:
        asyncio.run(run())
    assert error.value.status_code == 403
    assert "row-level security denied" not in error.value.detail

def test_update_memory_filters_by_memory_and_verified_user():
    memory_id = UUID("00000000-0000-0000-0000-000000000004")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.params["id"] == f"eq.{memory_id}"
        assert request.url.params["user_id"] == "eq.user-123"
        assert request.headers["authorization"] == "Bearer user-access-token"
        assert b'"content":"Texto corrigido"' in request.read()
        return httpx.Response(
            200,
            json=[
                {
                    "id": str(memory_id),
                    "kind": "semantic",
                    "content": "Texto corrigido",
                    "source": "test",
                    "scope": "user",
                    "confidence": 1.0,
                    "created_at": "2026-10-14T12:00:00Z",
                }
            ],
        )

    async def run():
        store, client = make_store(handler)
        try:
            return await store.update_memory(memory_id, {"content": "Texto corrigido"})
        finally:
            await client.aclose()

    row = asyncio.run(run())
    assert row is not None
    assert row["content"] == "Texto corrigido"
