from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.main import get_memory_store
from atlas.providers.gemini import MissingGeminiConfiguration

client = TestClient(main.app)


class EmptyMemoryStore:
    async def list_memories(self, limit: int = 50):
        return []


def use_empty_memory_store():
    main.app.dependency_overrides[get_memory_store] = lambda: EmptyMemoryStore()


def test_visual_scene_rejects_empty_prompt():
    response = client.post("/visual/scene", json={"prompt": ""})
    assert response.status_code == 422


def test_visual_scene_returns_valid_bounded_scene(monkeypatch):
    main.app.dependency_overrides.clear()
    use_empty_memory_store()

    class StubProvider:
        def __init__(self, api_key: str, model: str) -> None:
            pass

        async def generate(self, prompt: str) -> str:
            assert "motion design" in prompt
            return '{"title":"Cena de teste","elements":[' \
                '{"type":"circle","x":50,"y":50,"size":12,"color":"#FF8A24"},' \
                '{"type":"executable","text":"ignored"}]}'

    monkeypatch.setattr(main, "GeminiProvider", StubProvider)
    try:
        response = client.post("/visual/scene", json={"prompt": "um círculo pulsando"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Cena de teste"
    assert len(payload["elements"]) == 1
    assert payload["elements"][0]["type"] == "circle"


def test_visual_scene_rejects_invalid_model_json(monkeypatch):
    main.app.dependency_overrides.clear()
    use_empty_memory_store()

    class InvalidProvider:
        def __init__(self, api_key: str, model: str) -> None:
            pass

        async def generate(self, prompt: str) -> str:
            return "isto não é JSON"

    monkeypatch.setattr(main, "GeminiProvider", InvalidProvider)
    try:
        response = client.post("/visual/scene", json={"prompt": "cena abstrata"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Não foi possível gerar a cena visual."


def test_visual_scene_requires_auth_in_supabase_mode(monkeypatch):
    main.app.dependency_overrides.clear()
    from atlas.backend.config import Settings, get_settings

    cloud_settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
    )
    main.app.dependency_overrides[get_settings] = lambda: cloud_settings
    try:
        response = client.post("/visual/scene", json={"prompt": "cena"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 401
