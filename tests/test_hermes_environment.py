from pathlib import Path

from atlas.backend.config import Settings
from atlas.providers.hermes_agent import HermesAgentProvider


def test_hermes_worker_environment_excludes_backend_secrets(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / "run_agent.py").write_text("# prepared Hermes entry point\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/tmp/home")
    monkeypatch.setenv("SUPABASE_KEY", "must-not-be-forwarded")
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "must-not-be-forwarded")
    monkeypatch.setenv("GEMINI_API_KEY", "allowed-provider-key")

    provider = HermesAgentProvider(
        Settings(
            hermes_agent_enabled=True,
            hermes_agent_path=str(tmp_path),
            hermes_agent_model="gemini-test",
        )
    )

    child_env = provider._worker_environment()

    assert child_env["PATH"] == "/usr/bin"
    assert child_env["GEMINI_API_KEY"] == "allowed-provider-key"
    assert "SUPABASE_KEY" not in child_env
    assert "FISH_AUDIO_API_KEY" not in child_env
    assert "ATLAS_MEMORY_BACKEND" not in child_env
