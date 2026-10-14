from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.auth import AuthenticatedSession, require_authenticated_session

client = TestClient(main.app)


def test_memory_endpoints_require_authentication():
    main.app.dependency_overrides.clear()
    assert client.get("/memories").status_code == 401
    response = client.post(
        "/memories",
        json={"kind": "semantic", "content": "private", "source": "test"},
    )
    assert response.status_code == 401


def test_create_memory_uses_verified_identity_not_client_user_id(monkeypatch):
    captured = {}

    class StubStore:
        def __init__(self, settings, access_token, user_id):
            captured["user_id"] = user_id
            captured["token"] = access_token

        async def create_memory(self, memory):
            captured["memory"] = memory
            return {
                "id": "00000000-0000-0000-0000-000000000004",
                "kind": memory["kind"],
                "content": memory["content"],
                "source": memory["source"],
                "scope": memory["scope"],
                "confidence": memory["confidence"],
                "created_at": "2026-10-14T12:00:00Z",
            }

    monkeypatch.setattr(main, "SupabaseMemoryStore", StubStore)
    main.app.dependency_overrides[require_authenticated_session] = lambda: AuthenticatedSession(
        user_id="verified-user",
        access_token="verified-token",
    )
    try:
        response = client.post(
            "/memories",
            json={
                "kind": "semantic",
                "content": "ATLAS prefere segurança",
                "source": "conversation",
                "user_id": "attacker-user",
            },
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert captured["user_id"] == "verified-user"
    assert captured["token"] == "verified-token"
    assert "user_id" not in captured["memory"]
    assert response.json()["content"] == "ATLAS prefere segurança"
