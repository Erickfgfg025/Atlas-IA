from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.backend.agent_routes import router
from atlas.backend.config import Settings, get_settings


def make_app(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_hermes_task_requires_explicit_approval() -> None:
    client = make_app(Settings(ATLAS_MEMORY_BACKEND="local", HERMES_AGENT_ENABLED=False))
    response = client.post("/agent/tasks", json={"task": "Pesquise novidades do Python"})
    assert response.status_code == 428
    assert "approved=true" in response.json()["detail"]


def test_hermes_disabled_returns_service_unavailable() -> None:
    client = make_app(Settings(memory_backend="local", hermes_agent_enabled=False))
    response = client.post(
        "/agent/tasks",
        json={"task": "Pesquise novidades do Python", "approved": True},
    )
    assert response.status_code == 503
    assert "desativado" in response.json()["detail"]


def test_hermes_rejects_whitespace_only_task() -> None:
    client = make_app(Settings(memory_backend="local", hermes_agent_enabled=False))
    response = client.post(
        "/agent/tasks",
        json={"task": "   ", "approved": True},
    )
    assert response.status_code == 422


def test_hermes_rejects_invalid_memory_backend() -> None:
    client = make_app(Settings(memory_backend="misconfigured", hermes_agent_enabled=False))
    response = client.post(
        "/agent/tasks",
        json={"task": "Pesquise novidades do Python", "approved": True},
    )
    assert response.status_code == 503
    assert "inválido" in response.json()["detail"]
