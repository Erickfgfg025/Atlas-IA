import asyncio

import httpx
from atlas.backend.config import Settings
from atlas.memory.supabase_conversation_store import SupabaseConversationStore


def make_store(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = SupabaseConversationStore(
        Settings(
            SUPABASE_URL="https://atlas-test.supabase.co",
            SUPABASE_KEY="public-test-key",
        ),
        access_token="user-token",
        user_id="user-123",
        client=client,
    )
    return store, client


def test_create_conversation_uses_verified_user_and_user_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/rest/v1/atlas_conversations"
        assert request.headers["authorization"] == "Bearer user-token"
        assert request.headers["apikey"] == "public-test-key"
        body = request.read()
        assert b'"user_id":"user-123"' in body
        assert b'"title":"Nova conversa"' in body
        return httpx.Response(
            201,
            json=[{
                "id": "00000000-0000-0000-0000-000000000001",
                "title": "Nova conversa",
                "created_at": "2026-10-22T12:00:00Z",
                "updated_at": "2026-10-22T12:00:00Z",
            }],
        )

    async def run():
        store, client = make_store(handler)
        try:
            return await store.create_conversation(" Nova conversa ")
        finally:
            await client.aclose()

    row = asyncio.run(run())
    assert row["title"] == "Nova conversa"


def test_add_message_checks_ownership_before_insert():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/atlas_conversations"):
            assert request.url.params["user_id"] == "eq.user-123"
            return httpx.Response(200, json=[{"id": "00000000-0000-0000-0000-000000000002"}])
        if request.method == "POST" and request.url.path.endswith("/atlas_conversation_messages"):
            assert request.headers["authorization"] == "Bearer user-token"
            assert b'"user_id":"user-123"' in request.read()
            return httpx.Response(
                201,
                json=[{
                    "id": "00000000-0000-0000-0000-000000000003",
                    "conversation_id": "00000000-0000-0000-0000-000000000002",
                    "role": "user",
                    "content": "Olá Atlas",
                    "created_at": "2026-10-22T12:00:00Z",
                }],
            )
        if request.method == "PATCH" and request.url.path.endswith("/atlas_conversations"):
            assert "updated_at" in request.read().decode()
            return httpx.Response(204)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    async def run():
        store, client = make_store(handler)
        try:
            from uuid import UUID
            return await store.add_message(UUID("00000000-0000-0000-0000-000000000002"), "user", "Olá Atlas")
        finally:
            await client.aclose()

    row = asyncio.run(run())
    assert row is not None
    assert row["content"] == "Olá Atlas"
    assert [request.method for request in requests] == ["GET", "POST", "PATCH"]


def test_add_message_refuses_conversation_not_owned_by_user():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/atlas_conversations")
        return httpx.Response(200, json=[])

    async def run():
        store, client = make_store(handler)
        try:
            from uuid import UUID
            return await store.add_message(UUID("00000000-0000-0000-0000-000000000004"), "user", "Não autorizado")
        finally:
            await client.aclose()

    assert asyncio.run(run()) is None
