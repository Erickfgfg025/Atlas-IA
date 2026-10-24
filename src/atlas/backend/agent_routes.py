from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from atlas.backend.auth import verify_supabase_access_token, desktop_supabase_no_login_enabled
from atlas.backend.config import Settings, get_settings
from atlas.providers.hermes_agent import HermesAgentProvider, HermesNotConfigured

router = APIRouter(prefix="/agent", tags=["agent"])
bearer = HTTPBearer(auto_error=False)


class AgentTaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=3000)
    approved: bool = False

    @field_validator("task")
    @classmethod
    def task_must_contain_non_whitespace(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A tarefa não pode estar vazia.")
        return value


class AgentTaskResponse(BaseModel):
    agent: str
    result: str


async def _check_auth(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    if settings.memory_backend == "local":
        return
    if settings.memory_backend != "supabase":
        raise HTTPException(status_code=503, detail="ATLAS_MEMORY_BACKEND inválido.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        if desktop_supabase_no_login_enabled(settings):
            return
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")
    await verify_supabase_access_token(credentials.credentials, settings)


@router.post("/tasks", response_model=AgentTaskResponse)
async def execute_agent_task(
    request: AgentTaskRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> AgentTaskResponse:
    await _check_auth(settings, credentials)
    if not request.approved:
        raise HTTPException(
            status_code=428,
            detail="Confirme a tarefa explicitamente enviando approved=true.",
        )
    try:
        provider = HermesAgentProvider(settings)
        result = await provider.run_task(request.task)
    except HermesNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Hermes Agent não conseguiu concluir a tarefa. Consulte os logs do runtime.",
        ) from exc
    return AgentTaskResponse(agent="hermes", result=result)
