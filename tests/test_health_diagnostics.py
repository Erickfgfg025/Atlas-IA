from fastapi.testclient import TestClient

import atlas.backend.main as main
from atlas.backend.config import Settings


def test_health_reports_provider_configuration_without_secrets(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            ATLAS_MEMORY_BACKEND="local",
            GEMINI_API_KEY="test-secret-value",
            FISH_AUDIO_API_KEY="fish-secret-value",
            FISH_AUDIO_REFERENCE_ID="test-voice",
            HERMES_AGENT_ENABLED=False,
        ),
    )
    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["providers"]["chat"] == {"selected": "gemini", "configured": True}
    assert data["providers"]["voice_stt"]["configured"] is True
    assert data["providers"]["voice_tts"]["configured"] is True
    assert data["providers"]["hermes"]["enabled"] is False
    assert "test-secret-value" not in response.text
    assert "fish-secret-value" not in response.text
    assert "not tested" in data["diagnostics_note"]


def test_health_marks_unknown_chat_provider_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(ATLAS_CHAT_PROVIDER="unknown", ATLAS_MEMORY_BACKEND="local"),
    )
    data = TestClient(main.app).get("/health").json()

    assert data["providers"]["chat"] == {"selected": "unknown", "configured": False}



def test_health_does_not_assume_openjarvis_is_running(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(ATLAS_CHAT_PROVIDER="openjarvis", ATLAS_MEMORY_BACKEND="local"),
    )
    data = TestClient(main.app).get("/health").json()

    assert data["providers"]["chat"] == {
        "selected": "openjarvis",
        "configured": False,
    }


def test_health_does_not_report_invalid_memory_backend_as_supabase(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(ATLAS_MEMORY_BACKEND="typo"),
    )
    data = TestClient(main.app).get("/health").json()

    assert data["auth_mode"] == "invalid"
