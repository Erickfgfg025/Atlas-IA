from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from atlas.backend.config import Settings


class HermesNotConfigured(RuntimeError):
    """Raised when the optional Hermes runtime is unavailable."""


_WORKER_SCRIPT = r"""
import contextlib
import json
import sys
import traceback

payload = json.load(sys.stdin)
sys.path.insert(0, payload["hermes_path"])

try:
    from run_agent import AIAgent

    agent = AIAgent(
        model=payload["model"],
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        enabled_toolsets=["web"],
        disabled_toolsets=[
            "terminal",
            "file",
            "computer",
            "code_execution",
            "browser",
        ],
    )
    task_prompt = (
        "Execute esta tarefa usando somente ferramentas de pesquisa web disponíveis. "
        "Não afirme ter alterado arquivos, sistemas ou contas. Se a tarefa exigir "
        "ações fora da pesquisa web, explique essa limitação.\n\n"
        "Tarefa solicitada pelo usuário:\n" + payload["task"]
    )
    with contextlib.redirect_stdout(sys.stderr):
        result = agent.chat(task_prompt)
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Hermes Agent retornou uma resposta vazia.")
    json.dump({"result": result.strip()[:20000]}, sys.stdout, ensure_ascii=False)
except Exception as exc:
    json.dump({"error": str(exc)[:1000]}, sys.stdout, ensure_ascii=False)
    sys.exit(1)
"""


class HermesAgentProvider:
    """Run the restricted Hermes bridge in a separate, timeout-terminable process."""

    _PROVIDER_ENV_KEYS = (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "TOGETHER_API_KEY",
        "FIREWORKS_API_KEY",
        "MISTRAL_API_KEY",
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.hermes_agent_enabled:
            raise HermesNotConfigured(
                "Hermes Agent está desativado. Configure HERMES_AGENT_ENABLED=true "
                "após preparar o runtime."
            )
        if not settings.hermes_agent_model.strip():
            raise HermesNotConfigured("Configure HERMES_AGENT_MODEL no ambiente do backend.")
        root = settings.hermes_agent_path.strip()
        if not root:
            raise HermesNotConfigured(
                "Configure HERMES_AGENT_PATH para o checkout preparado do Hermes."
            )
        path = Path(root).expanduser().resolve()
        if not path.is_dir() or not (path / "run_agent.py").is_file():
            raise HermesNotConfigured(
                "HERMES_AGENT_PATH deve apontar para um checkout Hermes com run_agent.py."
            )
        self.hermes_path = path

    def _worker_environment(self) -> dict[str, str]:
        """Pass only runtime essentials and explicitly allowlisted model credentials."""
        allowed = ("PATH", "HOME", "USERPROFILE", "TMP", "TEMP", "SYSTEMROOT")
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        for key in self._PROVIDER_ENV_KEYS:
            if key in os.environ:
                env[key] = os.environ[key]
        return env

    def _run_process(self, task: str) -> str:
        payload = json.dumps(
            {
                "hermes_path": str(self.hermes_path),
                "model": self.settings.hermes_agent_model.strip(),
                "task": task,
            },
            ensure_ascii=False,
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", _WORKER_SCRIPT],
                input=payload,
                text=True,
                capture_output=True,
                timeout=self.settings.hermes_agent_task_timeout_seconds,
                check=False,
                cwd=str(self.hermes_path),
                env=self._worker_environment(),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Hermes excedeu o limite de tempo. O processo filho foi encerrado."
            ) from exc
        if completed.returncode != 0:
            try:
                detail = json.loads(completed.stdout).get("error", "")
            except (json.JSONDecodeError, AttributeError):
                detail = ""
            raise RuntimeError(
                "Hermes Agent falhou no processo isolado."
                + (f" Detalhe: {detail}" if detail else "")
            )
        try:
            result = json.loads(completed.stdout).get("result", "")
        except (json.JSONDecodeError, AttributeError) as exc:
            raise RuntimeError("Hermes retornou uma resposta inválida.") from exc
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Hermes Agent retornou uma resposta vazia.")
        return result.strip()[:20000]

    async def run_task(self, task: str) -> str:
        return await asyncio.to_thread(self._run_process, task)
