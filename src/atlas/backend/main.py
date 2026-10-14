from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from atlas.backend.auth import (
    AuthenticatedSession,
    AuthenticatedUser,
    require_authenticated_session,
    require_authenticated_user,
)
from atlas.backend.auth_sessions import (
    PasswordCredentials,
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
)
from atlas.backend.config import get_settings
from atlas.memory.contracts import MemoryKind
from atlas.memory.supabase_store import SupabaseMemoryStore
from atlas.providers.gemini import GeminiProvider, MissingGeminiConfiguration

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
_bearer = HTTPBearer(auto_error=False)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str


class AuthMeResponse(BaseModel):
    user_id: str


class AuthSessionResponse(BaseModel):
    access_token: str | None = None
    expires_in: int | None = None
    user_id: str | None = None
    confirmation_required: bool = False


class MemoryCreateRequest(BaseModel):
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=200)
    scope: str = Field(default="user", min_length=1, max_length=200)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    id: UUID
    kind: MemoryKind
    content: str
    source: str
    scope: str
    confidence: float
    created_at: datetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "atlas-api", "environment": settings.environment}


@app.post("/auth/signup", response_model=AuthSessionResponse)
async def auth_signup(credentials: PasswordCredentials) -> AuthSessionResponse:
    session = await sign_up_with_password(
        credentials.email, credentials.password, settings
    )
    return AuthSessionResponse(**session.model_dump())


@app.post("/auth/login", response_model=AuthSessionResponse)
async def auth_login(credentials: PasswordCredentials) -> AuthSessionResponse:
    session = await sign_in_with_password(
        credentials.email, credentials.password, settings
    )
    return AuthSessionResponse(**session.model_dump())


@app.post("/auth/logout", status_code=204)
async def auth_logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
) -> Response:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Envie um token de acesso para encerrar a sessão.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await sign_out(credentials.credentials, settings)
    return Response(status_code=204)


@app.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthMeResponse:
    """Return the identity verified by Supabase Auth."""
    return AuthMeResponse(user_id=user.user_id)


@app.get("/memories", response_model=list[MemoryResponse])
async def list_memories(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    session: AuthenticatedSession = Depends(require_authenticated_session),
) -> list[MemoryResponse]:
    store = SupabaseMemoryStore(settings, session.access_token, session.user_id)
    rows = await store.list_memories(limit=limit)
    return [MemoryResponse.model_validate(row) for row in rows]


@app.post("/memories", response_model=MemoryResponse, status_code=201)
async def create_memory(
    memory: MemoryCreateRequest,
    session: AuthenticatedSession = Depends(require_authenticated_session),
) -> MemoryResponse:
    store = SupabaseMemoryStore(settings, session.access_token, session.user_id)
    row = await store.create_memory(memory.model_dump(mode="json"))
    return MemoryResponse.model_validate(row)


@app.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    session: AuthenticatedSession = Depends(require_authenticated_session),
) -> Response:
    store = SupabaseMemoryStore(settings, session.access_token, session.user_id)
    deleted = await store.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memória não encontrada.")
    return Response(status_code=204)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ChatResponse:
    try:
        provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        answer = await provider.generate(request.message)
    except MissingGeminiConfiguration as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="O provedor de IA falhou.") from exc
    return ChatResponse(response=answer)
