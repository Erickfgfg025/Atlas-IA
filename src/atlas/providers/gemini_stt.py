"""Cloud speech-to-text adapter using Gemini audio understanding."""
from __future__ import annotations
import asyncio
from atlas.backend.config import Settings
from atlas.providers.gemini import MissingGeminiConfiguration

class GeminiSpeechToText:
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.gemini_api_key.strip()
        self.model = settings.gemini_model.strip()
        if not self.api_key or not self.model:
            raise MissingGeminiConfiguration("Configure GEMINI_API_KEY e GEMINI_MODEL.")

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        if not audio:
            raise ValueError("O arquivo de áudio está vazio.")
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        instruction = ("Transcreva fielmente o áudio. Preserve o idioma falado e a pontuação natural. "
                       "Retorne somente a transcrição, sem comentários.")
        response = await asyncio.to_thread(client.models.generate_content, model=self.model,
            contents=[instruction, types.Part.from_bytes(data=audio, mime_type=mime_type)])
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise RuntimeError("O modelo não retornou uma transcrição.")
        return text.strip()
