from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.config import Settings, get_settings

client = TestClient(main.app)


def test_local_memory_endpoints_persist_without_remote_auth(monkeypatch, tmp_path):
    local_settings = Settings(
        ATLAS_MEMORY_BACKEND="local",
        ATLAS_LOCAL_DB_PATH=str(tmp_path / "atlas-test.db"),
    )
    main.app.dependency_overrides[get_settings] = lambda: local_settings
    try:
        created = client.post(
            "/memories",
            json={
                "kind": "semantic",
                "content": "ATLAS usa memória local",
                "source": "test",
                "scope": "project:atlas",
                "confidence": 0.9,
            },
        )
        assert created.status_code == 201
        memory = created.json()
        assert memory["content"] == "ATLAS usa memória local"

        listed = client.get("/memories")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["id"] == memory["id"]

        updated = client.put(
            f"/memories/{memory['id']}",
            json={"content": "ATLAS usa SQLite local e memória editável"},
        )
        assert updated.status_code == 200
        assert updated.json()["content"] == "ATLAS usa SQLite local e memória editável"

        deleted = client.delete(f"/memories/{memory['id']}")
        assert deleted.status_code == 204
        assert client.get("/memories").json() == []
    finally:
        main.app.dependency_overrides.clear()


def test_supabase_memory_mode_requires_bearer_token(tmp_path):
    cloud_settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        ATLAS_LOCAL_DB_PATH=str(tmp_path / "unused.db"),
    )
    main.app.dependency_overrides[get_settings] = lambda: cloud_settings
    try:
        assert client.get("/memories").status_code == 401
        response = client.post(
            "/memories",
            json={"kind": "semantic", "content": "private", "source": "test"},
        )
        assert response.status_code == 401
    finally:
        main.app.dependency_overrides.clear()

def test_explicit_remember_command_persists_memory_without_calling_gemini(tmp_path, monkeypatch):
    from atlas.backend.main import get_memory_store

    local_settings = Settings(
        ATLAS_MEMORY_BACKEND="local",
        ATLAS_LOCAL_DB_PATH=str(tmp_path / "remember-test.db"),
    )
    main.app.dependency_overrides[get_settings] = lambda: local_settings

    def unexpected_gemini(*args, **kwargs):
        raise AssertionError("Gemini must not be called for an explicit remember command")

    monkeypatch.setattr(main, "GeminiProvider", unexpected_gemini)
    try:
        response = client.post(
            "/chat",
            json={"message": "Lembre que meu projeto usa Python e SQLite."},
        )
        assert response.status_code == 200
        assert response.json()["response"] == (
            "Memória salva: meu projeto usa Python e SQLite."
        )
        memories = client.get("/memories")
        assert memories.status_code == 200
        assert memories.json()[0]["content"] == "meu projeto usa Python e SQLite."
        assert memories.json()[0]["source"] == "explicit_user_request"
    finally:
        main.app.dependency_overrides.clear()
