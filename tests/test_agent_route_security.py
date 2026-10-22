from fastapi import FastAPI
from fastapi.testclient import TestClient

import atlas.backend.agent_routes as agent_routes
from atlas.backend.config import Settings, get_settings


def make_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(agent_routes.router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_agent_requires_explicit_approval_before_starting_runtime(monkeypatch) -> None:
    def unexpected_provider(*args, **kwargs):
        raise AssertionError("runtime must not start without explicit approval")

    monkeypatch.setattr(agent_routes, "HermesAgentProvider", unexpected_provider)
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="local"))

    response = client.post("/agent/tasks", json={"task": "Pesquise preços"})

    assert response.status_code == 428
    assert "approved=true" in response.json()["detail"]


def test_agent_fails_closed_for_invalid_memory_backend() -> None:
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="invalid"))

    response = client.post(
        "/agent/tasks",
        json={"task": "Pesquise preços", "approved": True},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "ATLAS_MEMORY_BACKEND inválido."


def test_agent_requires_bearer_token_in_supabase_mode() -> None:
    client = make_client(
        Settings(
            ATLAS_MEMORY_BACKEND="supabase",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_KEY="test-key",
        )
    )

    response = client.post(
        "/agent/tasks",
        json={"task": "Pesquise preços", "approved": True},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Autenticação obrigatória."


def test_agent_rejects_blank_task() -> None:
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="local"))

    response = client.post(
        "/agent/tasks",
        json={"task": "   ", "approved": True},
    )

    assert response.status_code == 422
