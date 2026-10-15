from atlas.backend.config import DEFAULT_GEMINI_MODEL, Settings


def test_default_gemini_model_is_current_flash_model(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"


def test_legacy_gemini_model_is_migrated(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    settings = Settings(_env_file=None)
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL


def test_custom_gemini_model_is_preserved(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "custom-model")
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "custom-model"
