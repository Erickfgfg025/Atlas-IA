from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from atlas.backend.auth import AuthenticatedUser, require_authenticated_user
from atlas.backend.auth_sessions import (
    AuthSession,
    PasswordCredentials,
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
)
from atlas.backend.config import get_settings
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
    refresh_token: str | None = None
    expires_in: int | None = None
    user_id: str | None = None
    confirmation_required: bool = False


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
