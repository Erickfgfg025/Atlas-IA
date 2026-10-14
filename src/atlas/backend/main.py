from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from atlas.backend.auth import AuthenticatedUser, require_authenticated_user
from atlas.backend.config import get_settings
from atlas.providers.gemini import GeminiProvider, MissingGeminiConfiguration

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str


class AuthMeResponse(BaseModel):
    user_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "atlas-api", "environment": settings.environment}


@app.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthMeResponse:
    """Return the identity verified by Supabase Auth."""
    return AuthMeResponse(user_id=user.user_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        answer = await provider.generate(request.message)
    except MissingGeminiConfiguration as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="O provedor de IA falhou.") from exc
    return ChatResponse(response=answer)
