import asyncio


class MissingGeminiConfiguration(RuntimeError):
    """Raised when Gemini credentials are absent."""


class GeminiProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()
        if not self.api_key:
            raise MissingGeminiConfiguration(
                "Gemini não configurado. Defina GEMINI_API_KEY no ambiente do backend."
            )
        if not self.model:
            raise MissingGeminiConfiguration("GEMINI_MODEL não foi configurado.")

    async def generate(self, prompt: str) -> str:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        response = await asyncio.to_thread(
            client.models.generate_content, model=self.model, contents=prompt
        )
        answer = getattr(response, "text", None)
        if not answer or not answer.strip():
            raise RuntimeError("Gemini retornou uma resposta vazia.")
        return answer.strip()
