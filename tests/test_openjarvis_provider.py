import httpx
import pytest

from atlas.providers.openjarvis import (
    MissingOpenJarvisConfiguration,
    OpenJarvisProvider,
)


@pytest.mark.asyncio
async def test_openjarvis_requires_base_url() -> None:
    with pytest.raises(MissingOpenJarvisConfiguration):
        OpenJarvisProvider("", "default")


@pytest.mark.asyncio
async def test_openjarvis_parses_openai_compatible_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self, url, json, headers):
        assert url == "http://jarvis.local/v1/chat/completions"
        assert json["model"] == "qwen3:8b"
        assert json["messages"][0]["content"] == "Olá"
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Resposta do Jarvis"}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenJarvisProvider("http://jarvis.local/v1", "qwen3:8b")
    assert await provider.generate("Olá") == "Resposta do Jarvis"


@pytest.mark.asyncio
async def test_openjarvis_rejects_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self, url, json, headers):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  "}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenJarvisProvider("http://jarvis.local/v1", "qwen3:8b")
    with pytest.raises(RuntimeError, match="resposta vazia"):
        await provider.generate("Olá")
