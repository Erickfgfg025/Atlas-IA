from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.backend.config import Settings, get_settings
from atlas.backend.voice_routes import router


def make_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_voice_synthesis_rejects_invalid_memory_backend() -> None:
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="misconfigured"))
    response = client.post("/voice/synthesize", json={"text": "Olá, Atlas"})

    assert response.status_code == 503
    assert response.json()["detail"] == "ATLAS_MEMORY_BACKEND inválido."


def test_voice_transcription_rejects_invalid_memory_backend() -> None:
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="misconfigured"))
    response = client.post(
        "/voice/transcribe",
        files={"audio": ("sample.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "ATLAS_MEMORY_BACKEND inválido."


def test_voice_synthesis_local_mode_reaches_provider_configuration_check() -> None:
    client = make_client(Settings(ATLAS_MEMORY_BACKEND="local"))
    response = client.post("/voice/synthesize", json={"text": "Olá, Atlas"})

    assert response.status_code == 503
    assert "FISH_AUDIO_API_KEY" in response.json()["detail"]
