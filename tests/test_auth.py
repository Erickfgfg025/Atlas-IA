import asyncio

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.auth import AuthenticatedUser, require_authenticated_user, verify_supabase_access_token
from atlas.backend.config import Settings

client = TestClient(main.app)


def configured_settings() -> Settings:
    return Settings(SUPABASE_URL="https://atlas-test.supabase.co", SUPABASE_KEY="public-test-key")


def test_auth_me_requires_bearer_token():
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_returns_verified_user_id():
    main.app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
        user_id="user-123"
    )
    try:
        response = client.get("/auth/me", headers={"Authorization": "Bearer test-token"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-123"}


def test_verifier_asks_supabase_auth_and_returns_user_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/auth/v1/user"
        assert request.headers["apikey"] == "public-test-key"
        assert request.headers["authorization"] == "Bearer valid-token"
        return httpx.Response(200, json={"id": "user-123", "email": "private@example.com"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
            return await verify_supabase_access_token(
                "valid-token", configured_settings(), client=mock_client
            )

    user = asyncio.run(run())
    assert user.user_id == "user-123"


def test_verifier_rejects_invalid_or_expired_token():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"message": "invalid token"})
            )
        ) as mock_client:
            return await verify_supabase_access_token(
                "expired-token", configured_settings(), client=mock_client
            )

    with pytest.raises(HTTPException) as error:
        asyncio.run(run())

    assert error.value.status_code == 401
    assert error.value.detail == "Sessão inválida ou expirada."


def test_verifier_fails_closed_when_supabase_is_not_configured():
    settings = Settings()
    with pytest.raises(HTTPException) as error:
        asyncio.run(verify_supabase_access_token("token", settings))

    assert error.value.status_code == 503
