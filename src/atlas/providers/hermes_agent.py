from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

from atlas.backend.config import Settings


class HermesNotConfigured(RuntimeError):
    """Raised when the optional Hermes runtime is unavailable."""


class HermesAgentProvider:
    """Narrow bridge to Hermes AIAgent with only the web toolset enabled."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.hermes_agent_enabled:
            raise HermesNotConfigured(
                "Hermes Agent está desativado. Configure HERMES_AGENT_ENABLED=true após preparar o runtime."
            )
        if not settings.hermes_agent_model.strip():
            raise HermesNotConfigured("Configure HERMES_AGENT_MODEL no ambiente do backend.")
        root = settings.hermes_agent_path.strip()
        if not root:
            raise HermesNotConfigured("Configure HERMES_AGENT_PATH para o checkout preparado do Hermes.")
        path = Path(root).expanduser().resolve()
        if not path.is_dir() or not (path / "run_agent.py").is_file():
            raise HermesNotConfigured(
                "HERMES_AGENT_PATH deve apontar para um checkout Hermes com run_agent.py."
            )
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
        try:
            module = importlib.import_module("run_agent")
            self._agent_class = getattr(module, "AIAgent")
        except (ImportError, AttributeError) as exc:
            raise HermesNotConfigured(
                "Não foi possível importar AIAgent. Prepare as dependências do checkout Hermes."
            ) from exc

    def _run_sync(self, task: str) -> str:
        agent = self._agent_class(
            model=self.settings.hermes_agent_model.strip(),
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
        result = agent.chat(
            "Execute esta tarefa usando somente ferramentas de pesquisa web disponíveis. "
            "Não afirme ter alterado arquivos, sistemas ou contas. Se a tarefa exigir "
            "ações fora da pesquisa web, explique essa limitação.\n\n"
            f"Tarefa solicitada pelo usuário:\n{task}"
        )
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Hermes Agent retornou uma resposta vazia.")
        return result.strip()[:20000]

    async def run_task(self, task: str) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._run_sync, task),
                timeout=self.settings.hermes_agent_task_timeout_seconds,
            )
        except TimeoutError as exc:
            raise TimeoutError(
                "O tempo de espera do Hermes terminou. A thread subjacente pode continuar ativa; "
                "por isso, o runtime deve ser executado em worker isolado para produção."
            ) from exc
