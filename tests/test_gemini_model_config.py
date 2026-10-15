from atlas.backend.config import DEFAULT_GEMINI_MODEL, Settings


def test_default_gemini_model_is_current_flash_model() -> None:
    settings = Settings(_env_file=None)
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"


def test_legacy_gemini_model_is_migrated() -> None:
    settings = Settings(_env_file=None, gemini_model="gemini-2.5-flash")
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL


def test_custom_gemini_model_is_preserved() -> None:
    settings = Settings(_env_file=None, gemini_model="custom-model")
    assert settings.gemini_model == "custom-model"
