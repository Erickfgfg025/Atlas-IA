from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.config import Settings, get_settings
from atlas.backend.main import get_memory_store
from atlas.providers.gemini import MissingGeminiConfiguration

client = TestClient(main.app)


class StubProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str) -> str:
        return f"Resposta simulada para: {prompt}"


class EmptyMemoryStore:
    async def list_memories(self, limit: int = 50):
        return []


def use_empty_memory_store():
    main.app.dependency_overrides[get_memory_store] = lambda: EmptyMemoryStore()


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["memory_backend"] == "local"


def test_chat_rejects_empty_message():
    main.app.dependency_overrides.clear()
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_requires_authentication_in_supabase_mode():
    main.app.dependency_overrides.clear()
    cloud_settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
    )
    main.app.dependency_overrides[get_settings] = lambda: cloud_settings
    try:
        response = client.post("/chat", json={"message": "Olá"})
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 401


def test_local_chat_uses_provider_without_remote_auth(monkeypatch):
    main.app.dependency_overrides.clear()
    use_empty_memory_store()
    monkeypatch.setattr(main, "GeminiProvider", StubProvider)
    try:
        response = client.post("/chat", json={"message": "Olá, ATLAS"})
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["response"].startswith("Resposta simulada para:")


def test_chat_includes_relevant_memory_in_gemini_prompt(monkeypatch):
    main.app.dependency_overrides.clear()
    captured = {}

    class MemoryStore:
        async def list_memories(self, limit: int = 50):
            assert limit == 100
            return [
                {
                    "kind": "project",
                    "content": "O projeto ATLAS usa Python, PySide6 e FastAPI.",
                    "scope": "project:atlas",
                    "confidence": 1.0,
                    "created_at": "2026-10-14T12:00:00Z",
                },
                {
                    "kind": "semantic",
                    "content": "O usuário gosta de receitas de bolo de cenoura.",
                    "scope": "user",
                    "confidence": 1.0,
                    "created_at": "2026-10-14T11:00:00Z",
                },
            ]

    class CapturingProvider:
        def __init__(self, api_key: str, model: str) -> None:
            pass

        async def generate(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return "A stack é Python, PySide6 e FastAPI."

    main.app.dependency_overrides[get_memory_store] = lambda: MemoryStore()
    monkeypatch.setattr(main, "GeminiProvider", CapturingProvider)
    try:
        response = client.post(
            "/chat",
            json={"message": "Qual stack do projeto ATLAS?"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Python, PySide6 e FastAPI" in captured["prompt"]
    assert "receitas de bolo de cenoura" not in captured["prompt"]
    assert "dados não confiáveis" in captured["prompt"]


def test_chat_returns_503_when_gemini_is_not_configured(monkeypatch):
    main.app.dependency_overrides.clear()
    use_empty_memory_store()

    def missing_provider(api_key: str, model: str):
        raise MissingGeminiConfiguration("Gemini não configurado.")

    monkeypatch.setattr(main, "GeminiProvider", missing_provider)
    try:
        response = client.post("/chat", json={"message": "Olá"})
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini não configurado."


def test_chat_does_not_expose_provider_exception(monkeypatch):
    main.app.dependency_overrides.clear()
    use_empty_memory_store()

    class FailingProvider:
        def __init__(self, api_key: str, model: str) -> None:
            pass

        async def generate(self, prompt: str) -> str:
            raise RuntimeError("PRIVATE-SECRET-MUST-NOT-LEAK")

    monkeypatch.setattr(main, "GeminiProvider", FailingProvider)
    try:
        response = client.post("/chat", json={"message": "Olá"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "PRIVATE-SECRET-MUST-NOT-LEAK" not in response.text
    assert response.json()["detail"] == "O provedor de IA falhou."
