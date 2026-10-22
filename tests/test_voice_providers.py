from unittest.mock import AsyncMock, patch
import httpx
import pytest
from atlas.backend.config import Settings
from atlas.providers.fish_audio import FishAudioProvider, MissingFishAudioConfiguration

def test_fish_audio_requires_configuration():
    with pytest.raises(MissingFishAudioConfiguration):
        FishAudioProvider(Settings())

@pytest.mark.asyncio
async def test_fish_audio_returns_audio_bytes():
    provider = FishAudioProvider(Settings(FISH_AUDIO_API_KEY="test-key", FISH_AUDIO_REFERENCE_ID="voice"))
    response = httpx.Response(200, content=b"fake-mp3")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)):
        assert await provider.synthesize("Olá, Atlas.") == b"fake-mp3"

@pytest.mark.asyncio
async def test_fish_audio_rejects_empty_text():
    provider = FishAudioProvider(Settings(FISH_AUDIO_API_KEY="test-key", FISH_AUDIO_REFERENCE_ID="voice"))
    with pytest.raises(ValueError):
        await provider.synthesize(" ")
