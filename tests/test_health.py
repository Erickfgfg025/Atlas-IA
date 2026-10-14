from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.auth import AuthenticatedUser, require_authenticated_user
from atlas.providers.gemini import MissingGeminiConfiguration

client = TestClient(main.app)


class StubProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str) -> str:
        return f"Resposta simulada para: {prompt}"


def authorize_test_user():
    main.app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
        user_id="user-test"
    )


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_rejects_empty_message():
    authorize_test_user()
    try:
        response = client.post("/chat", json={"message": ""})
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 422


def test_chat_requires_authentication():
    main.app.dependency_overrides.clear()
    response = client.post("/chat", json={"message": "Olá"})
    assert response.status_code == 401


def test_chat_uses_provider_and_returns_response(monkeypatch):
    authorize_test_user()
    monkeypatch.setattr(main, "GeminiProvider", StubProvider)
    try:
        response = client.post("/chat", json={"message": "Olá, ATLAS"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"response": "Resposta simulada para: Olá, ATLAS"}


def test_chat_returns_503_when_gemini_is_not_configured(monkeypatch):
    authorize_test_user()

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
    authorize_test_user()

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
