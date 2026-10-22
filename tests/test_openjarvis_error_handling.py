import asyncio

import httpx
import pytest

from atlas.providers.openjarvis import MissingOpenJarvisConfiguration, OpenJarvisProvider


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (401, "recusou a autenticação"),
        (403, "recusou a autenticação"),
        (429, "limite de requisições"),
    ],
)
def test_openjarvis_maps_common_http_errors(
    monkeypatch: pytest.MonkeyPatch, status_code: int, message: str
) -> None:
    async def fake_post(self, url, json, headers):
        request = httpx.Request("POST", url)
        return httpx.Response(status_code, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenJarvisProvider("http://jarvis.local/v1", "qwen3:8b")
    with pytest.raises(RuntimeError, match=message):
        asyncio.run(provider.generate("Olá"))


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
def test_openjarvis_rejects_malformed_response(
    monkeypatch: pytest.MonkeyPatch, payload: dict
) -> None:
    async def fake_post(self, url, json, headers):
        request = httpx.Request("POST", url)
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenJarvisProvider("http://jarvis.local/v1", "qwen3:8b")
    with pytest.raises(RuntimeError):
        asyncio.run(provider.generate("Olá"))


def test_openjarvis_requires_model() -> None:
    with pytest.raises(MissingOpenJarvisConfiguration, match="OPENJARVIS_MODEL"):
        OpenJarvisProvider("http://jarvis.local/v1", " ")
