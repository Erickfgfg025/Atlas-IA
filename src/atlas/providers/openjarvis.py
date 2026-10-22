from __future__ import annotations

import httpx


class MissingOpenJarvisConfiguration(RuntimeError):
    """Raised when the OpenJarvis endpoint is not configured."""


class OpenJarvisProvider:
    """Client for an OpenJarvis server exposing its OpenAI-compatible API."""

    def __init__(self, base_url: str, model: str, api_key: str = "") -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        if not self.base_url:
            raise MissingOpenJarvisConfiguration(
                "OPENJARVIS_BASE_URL não foi configurada."
            )
        if not self.model:
            raise MissingOpenJarvisConfiguration("OPENJARVIS_MODEL não foi configurado.")

    async def generate(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=8.0)) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
        if response.status_code in (401, 403):
            raise RuntimeError("OpenJarvis recusou a autenticação configurada.")
        if response.status_code == 429:
            raise RuntimeError("OpenJarvis atingiu o limite de requisições.")
        response.raise_for_status()
        data = response.json()
        try:
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenJarvis retornou uma resposta em formato inválido.") from exc
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("OpenJarvis retornou uma resposta vazia.")
        return answer.strip()
