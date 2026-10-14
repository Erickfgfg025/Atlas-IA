from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from atlas.backend.auth import (
    AuthenticatedUser,
    require_authenticated_user,
    verify_supabase_access_token,
)
from atlas.backend.auth_sessions import (
    PasswordCredentials,
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
)
from atlas.backend.config import Settings, get_settings
from atlas.memory.contracts import MemoryKind
from atlas.memory.retrieval import build_memory_augmented_prompt, select_relevant_memories
from atlas.memory.sqlite_store import SQLiteMemoryStore
from atlas.memory.supabase_store import SupabaseMemoryStore
from atlas.providers.gemini import GeminiProvider, MissingGeminiConfiguration

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
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


async def get_memory_store(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> Any:
    """Select local SQLite or user-scoped Supabase storage from configuration."""
    if app_settings.memory_backend == "local":
        return SQLiteMemoryStore(app_settings.local_db_path or None)
    if app_settings.memory_backend != "supabase":
        raise HTTPException(status_code=503, detail="ATLAS_MEMORY_BACKEND inválido.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Envie um token de acesso no cabeçalho Authorization: Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = await verify_supabase_access_token(credentials.credentials, app_settings)
    return SupabaseMemoryStore(
        app_settings,
        credentials.credentials,
        session.user_id,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "atlas-api",
        "environment": settings.environment,
        "memory_backend": settings.memory_backend,
        "auth_mode": "local" if settings.memory_backend == "local" else "supabase",
    }


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
    store: Any = Depends(get_memory_store),
) -> list[MemoryResponse]:
    rows = await store.list_memories(limit=limit)
    return [MemoryResponse.model_validate(row) for row in rows]


@app.post("/memories", response_model=MemoryResponse, status_code=201)
async def create_memory(
    memory: MemoryCreateRequest,
    store: Any = Depends(get_memory_store),
) -> MemoryResponse:
    row = await store.create_memory(memory.model_dump(mode="json"))
    return MemoryResponse.model_validate(row)


@app.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    store: Any = Depends(get_memory_store),
) -> Response:
    deleted = await store.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memória não encontrada.")
    return Response(status_code=204)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: Any = Depends(get_memory_store),
) -> ChatResponse:
    try:
        try:
            stored_memories = await store.list_memories(limit=100)
        except HTTPException as exc:
            if exc.status_code < 500:
                raise
            stored_memories = []

        relevant_memories = select_relevant_memories(
            request.message,
            stored_memories,
            limit=5,
        )
        prompt = build_memory_augmented_prompt(request.message, relevant_memories)
        provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        answer = await provider.generate(prompt)
    except MissingGeminiConfiguration as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="O provedor de IA falhou.") from exc
    return ChatResponse(response=answer)
