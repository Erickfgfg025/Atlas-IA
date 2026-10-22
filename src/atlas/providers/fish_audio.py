"""Fish Audio text-to-speech adapter. Credentials remain server-side."""
from __future__ import annotations
import httpx
from atlas.backend.config import Settings

class MissingFishAudioConfiguration(RuntimeError):
    """Fish Audio is not configured on the backend."""

class FishAudioProvider:
    API_URL = "https://api.fish.audio/v1/tts"
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.fish_audio_api_key.strip()
        self.reference_id = settings.fish_audio_reference_id.strip()
        self.model = settings.fish_audio_model.strip() or "s1"
        if not self.api_key or not self.reference_id:
            raise MissingFishAudioConfiguration("Configure FISH_AUDIO_API_KEY e FISH_AUDIO_REFERENCE_ID no backend.")

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("O texto para sintetizar não pode estar vazio.")
        payload = {"text": text, "reference_id": self.reference_id, "format": "mp3", "mp3_bitrate": 128, "latency": "normal", "normalize": True}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "model": self.model}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=8.0)) as client:
                response = await client.post(self.API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise RuntimeError("Fish Audio demorou demais para gerar o áudio.") from exc
        except httpx.RequestError as exc:
            raise RuntimeError("Não foi possível conectar ao Fish Audio.") from exc
        if response.status_code in (401, 403):
            raise RuntimeError("Fish Audio recusou a chave configurada.")
        if response.status_code == 429:
            raise RuntimeError("Limite de requisições do Fish Audio atingido.")
        if not response.is_success:
            raise RuntimeError(f"Fish Audio retornou HTTP {response.status_code}.")
        if not response.content:
            raise RuntimeError("Fish Audio retornou áudio vazio.")
        return response.content
