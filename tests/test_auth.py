import asyncio

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from atlas.backend import main
from atlas.backend.auth import AuthenticatedUser, desktop_supabase_no_login_enabled, require_authenticated_user, verify_supabase_access_token
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



def test_passwordless_desktop_mode_requires_single_user_supabase_configuration():
    settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        ATLAS_DESKTOP_NO_LOGIN=True,
        ATLAS_OWNER_USER_ID="owner-uuid",
        ATLAS_API_HOST="127.0.0.1",
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
        SUPABASE_SERVICE_ROLE_KEY="server-only-service-role",
    )
    assert desktop_supabase_no_login_enabled(settings)


def test_passwordless_desktop_mode_rejects_non_loopback_binding():
    settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        ATLAS_DESKTOP_NO_LOGIN=True,
        ATLAS_OWNER_USER_ID="owner-uuid",
        ATLAS_API_HOST="0.0.0.0",
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
        SUPABASE_SERVICE_ROLE_KEY="server-only-service-role",
    )
    assert not desktop_supabase_no_login_enabled(settings)


def test_passwordless_desktop_mode_requires_service_role_key():
    settings = Settings(
        ATLAS_MEMORY_BACKEND="supabase",
        ATLAS_DESKTOP_NO_LOGIN=True,
        ATLAS_OWNER_USER_ID="owner-uuid",
        ATLAS_API_HOST="127.0.0.1",
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
        SUPABASE_SERVICE_ROLE_KEY="",
    )
    assert not desktop_supabase_no_login_enabled(settings)



def activation_settings(**overrides) -> Settings:
    values = {
        "ATLAS_MEMORY_BACKEND": "supabase",
        "ATLAS_OWNER_USER_ID": "owner-uuid",
        "ATLAS_ACTIVATION_CODE": "test-activation-code-123",
        "ATLAS_ACTIVATION_SECRET": "s" * 40,
        "SUPABASE_URL": "https://atlas-test.supabase.co",
        "SUPABASE_KEY": "public-test-key",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-service-role",
    }
    values.update(overrides)
    return Settings(**values)


def test_activation_token_round_trip_and_owner_scope():
    from atlas.backend.auth import issue_activation_token, verify_activation_token

    settings = activation_settings()
    token = issue_activation_token(settings)
    user = verify_activation_token(token, settings)
    assert token.startswith("atlas1.")
    assert user.user_id == "owner-uuid"


def test_activation_token_rejects_modified_signature():
    from atlas.backend.auth import issue_activation_token, verify_activation_token

    settings = activation_settings()
    token = issue_activation_token(settings)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(HTTPException) as error:
        verify_activation_token(tampered, settings)
    assert error.value.status_code == 401


def test_activation_token_rejects_different_owner():
    from atlas.backend.auth import issue_activation_token, verify_activation_token

    token = issue_activation_token(activation_settings())
    with pytest.raises(HTTPException) as error:
        verify_activation_token(token, activation_settings(ATLAS_OWNER_USER_ID="another-owner"))
    assert error.value.status_code == 401


def test_activation_token_rejects_expired_token():
    from atlas.backend.auth import issue_activation_token, verify_activation_token

    settings = activation_settings()
    token = issue_activation_token(settings, lifetime_seconds=-1)
    with pytest.raises(HTTPException) as error:
        verify_activation_token(token, settings)
    assert error.value.status_code == 401


def test_activation_mode_requires_long_secret_and_server_credentials():
    from atlas.backend.auth import activation_enabled

    assert activation_enabled(activation_settings())
    assert not activation_enabled(activation_settings(ATLAS_ACTIVATION_SECRET="too-short"))
    assert not activation_enabled(activation_settings(SUPABASE_SERVICE_ROLE_KEY=""))
