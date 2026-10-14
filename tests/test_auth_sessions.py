import asyncio

import httpx
import pytest
from fastapi import HTTPException

from atlas.backend.auth_sessions import (
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
)
from atlas.backend.config import Settings


def settings() -> Settings:
    return Settings(
        SUPABASE_URL="https://atlas-test.supabase.co",
        SUPABASE_KEY="public-test-key",
    )


def test_sign_in_posts_credentials_to_supabase_and_returns_session():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/token"
        assert request.url.query == b"grant_type=password"
        assert request.headers["apikey"] == "public-test-key"
        assert request.read() == b'{"email":"user@example.com","password":"long-password"}'
        return httpx.Response(
            200,
            json={
                "access_token": "access-test",
                "refresh_token": "refresh-test",
                "expires_in": 3600,
                "user": {"id": "user-123"},
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await sign_in_with_password(
                " user@example.com ", "long-password", settings(), client=client
            )

    session = asyncio.run(run())
    assert session.access_token == "access-test"
    assert session.refresh_token == "refresh-test"
    assert session.user_id == "user-123"
    assert session.confirmation_required is False


def test_sign_in_hides_upstream_credentials_error():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(400, json={"msg": "sensitive upstream detail"})
            )
        ) as client:
            return await sign_in_with_password("bad@example.com", "wrong-password", settings(), client=client)

    with pytest.raises(HTTPException) as error:
        asyncio.run(run())
    assert error.value.status_code == 401
    assert "sensitive upstream detail" not in error.value.detail


def test_signup_reports_email_confirmation_when_no_session_returned():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/signup"
        return httpx.Response(200, json={"id": "user-123", "email": "user@example.com"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await sign_up_with_password(
                "user@example.com", "long-password", settings(), client=client
            )

    session = asyncio.run(run())
    assert session.user_id == "user-123"
    assert session.access_token is None
    assert session.confirmation_required is True


def test_sign_out_sends_access_token_to_supabase():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/logout"
        assert request.headers["authorization"] == "Bearer access-test"
        return httpx.Response(204)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await sign_out("access-test", settings(), client=client)

    asyncio.run(run())
