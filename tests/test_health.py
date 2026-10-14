from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.config import Settings, get_settings
from atlas.providers.gemini import MissingGeminiConfiguration

client = TestClient(main.app)


class StubProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str) -> str:
        return f"Resposta simulada para: {prompt}"


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
    monkeypatch.setattr(main, "GeminiProvider", StubProvider)
    response = client.post("/chat", json={"message": "Olá, ATLAS"})
    assert response.status_code == 200
    assert response.json() == {"response": "Resposta simulada para: Olá, ATLAS"}


def test_chat_returns_503_when_gemini_is_not_configured(monkeypatch):
    main.app.dependency_overrides.clear()

    def missing_provider(api_key: str, model: str):
        raise MissingGeminiConfiguration("Gemini não configurado.")

    monkeypatch.setattr(main, "GeminiProvider", missing_provider)
    response = client.post("/chat", json={"message": "Olá"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini não configurado."


def test_chat_does_not_expose_provider_exception(monkeypatch):
    main.app.dependency_overrides.clear()

    class FailingProvider:
        def __init__(self, api_key: str, model: str) -> None:
            pass

        async def generate(self, prompt: str) -> str:
            raise RuntimeError("PRIVATE-SECRET-MUST-NOT-LEAK")

    monkeypatch.setattr(main, "GeminiProvider", FailingProvider)
    response = client.post("/chat", json={"message": "Olá"})

    assert response.status_code == 502
    assert "PRIVATE-SECRET-MUST-NOT-LEAK" not in response.text
    assert response.json()["detail"] == "O provedor de IA falhou."
