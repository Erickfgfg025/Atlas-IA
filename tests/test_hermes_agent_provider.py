from __future__ import annotations

import os
from pathlib import Path

import pytest

from atlas.backend.config import Settings
from atlas.providers.hermes_agent import HermesAgentProvider, HermesNotConfigured


def make_settings(path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "memory_backend": "local",
        "hermes_agent_enabled": True,
        "hermes_agent_path": str(path),
        "hermes_agent_model": "test-model",
        "hermes_agent_task_timeout_seconds": 10,
    }
    values.update(overrides)
    return Settings(**values)


def test_provider_requires_prepared_checkout(tmp_path: Path) -> None:
    with pytest.raises(HermesNotConfigured, match="run_agent.py"):
        HermesAgentProvider(make_settings(tmp_path))


def test_provider_runs_in_child_process_with_restricted_toolsets(tmp_path: Path) -> None:
    (tmp_path / "run_agent.py").write_text(
        """
class AIAgent:
    def __init__(self, **kwargs):
        assert kwargs["enabled_toolsets"] == ["web"]
        assert "terminal" in kwargs["disabled_toolsets"]
        assert kwargs["skip_memory"] is True

    def chat(self, prompt):
        assert "Tarefa de teste" in prompt
        print("mensagem interna do agente")
        return "Resultado de teste do Hermes"
""",
        encoding="utf-8",
    )
    provider = HermesAgentProvider(make_settings(tmp_path))
    assert provider._run_process("Tarefa de teste") == "Resultado de teste do Hermes"


def test_worker_environment_does_not_forward_unrelated_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "run_agent.py").write_text("class AIAgent: pass\n", encoding="utf-8")
    monkeypatch.setenv("SUPABASE_KEY", "must-not-leak")
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "must-not-leak")
    monkeypatch.setenv("GEMINI_API_KEY", "allowed-model-key")
    env = HermesAgentProvider(make_settings(tmp_path))._worker_environment()
    assert env.get("GEMINI_API_KEY") == "allowed-model-key"
    assert "SUPABASE_KEY" not in env
    assert "FISH_AUDIO_API_KEY" not in env
