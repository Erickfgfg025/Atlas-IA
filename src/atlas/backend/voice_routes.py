from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from atlas.backend.auth import verify_supabase_access_token, desktop_supabase_no_login_enabled
from atlas.backend.config import Settings, get_settings
from atlas.providers.fish_audio import FishAudioProvider, MissingFishAudioConfiguration
from atlas.providers.gemini import MissingGeminiConfiguration
from atlas.providers.gemini_stt import GeminiSpeechToText

router = APIRouter(prefix="/voice", tags=["voice"])
bearer = HTTPBearer(auto_error=False)

class VoiceSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

async def _check_auth(settings: Settings, credentials: HTTPAuthorizationCredentials | None) -> None:
    if settings.memory_backend == "local":
        return
    if settings.memory_backend != "supabase":
        raise HTTPException(status_code=503, detail="ATLAS_MEMORY_BACKEND inválido.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        if desktop_supabase_no_login_enabled(settings):
            return
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")
    await verify_supabase_access_token(credentials.credentials, settings)

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> dict[str, str]:
    await _check_auth(settings, credentials)
    allowed = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/mp4", "audio/aac", "audio/flac", "audio/3gpp"}
    mime = (audio.content_type or "").split(";")[0].strip().lower()
    if mime not in allowed:
        await audio.close()
        raise HTTPException(status_code=415, detail="Formato de áudio não suportado.")
    limit = settings.max_audio_upload_mb * 1024 * 1024
    data = await audio.read(limit + 1)
    await audio.close()
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="Arquivo de áudio excede o limite permitido.")
    try:
        return {"text": await GeminiSpeechToText(settings).transcribe(data, mime)}
    except MissingGeminiConfiguration as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Não foi possível transcrever o áudio.") from exc

@router.post("/synthesize")
async def synthesize_speech(
    request: VoiceSynthesisRequest,
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> Response:
    await _check_auth(settings, credentials)
    try:
        audio_bytes = await FishAudioProvider(settings).synthesize(request.text)
    except MissingFishAudioConfiguration as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Não foi possível gerar a voz.") from exc
    return Response(content=audio_bytes, media_type="audio/mpeg", headers={"Content-Disposition": 'inline; filename="atlas-response.mp3"', "Cache-Control": "no-store"})
