"""Supabase Auth token verification for backend-only endpoints."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from atlas.backend.config import Settings, get_settings


def activation_enabled(settings: Settings) -> bool:
    return bool(settings.activation_code.strip() and len(settings.activation_secret.strip()) >= 32 and settings.atlas_owner_user_id.strip() and settings.memory_backend == "supabase" and settings.supabase_url.strip() and settings.supabase_key.strip() and settings.supabase_service_role_key.strip())


def is_activation_token(token: str) -> bool:
    return token.startswith("atlas1.")


def issue_activation_token(settings: Settings, lifetime_seconds: int = 15552000) -> str:
    payload = {"typ": "atlas_activation", "sub": settings.atlas_owner_user_id.strip(), "exp": int(time.time()) + lifetime_seconds}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).rstrip(b"=").decode()
    signature = hmac.new(settings.activation_secret.strip().encode(), encoded.encode("ascii"), hashlib.sha256).digest()
    return "atlas1." + encoded + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


def verify_activation_token(token: str, settings: Settings) -> AuthenticatedUser:
    if not activation_enabled(settings):
        raise HTTPException(status_code=503, detail="Ativação por código não está configurada.")
    try:
        prefix, encoded, supplied = token.split(".", 2)
        expected = base64.urlsafe_b64encode(hmac.new(settings.activation_secret.strip().encode(), encoded.encode("ascii"), hashlib.sha256).digest()).rstrip(b"=").decode()
        if prefix != "atlas1" or not hmac.compare_digest(supplied, expected):
            raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode((encoded + "=" * (-len(encoded) % 4)).encode("ascii")))
        owner = settings.atlas_owner_user_id.strip()
        if payload.get("typ") != "atlas_activation" or payload.get("sub") != owner or not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
            raise ValueError("claims")
        return AuthenticatedUser(user_id=owner)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeError) as exc:
        raise HTTPException(status_code=401, detail="Código de ativação inválido ou sessão expirada.", headers={"WWW-Authenticate": "Bearer"}) from exc


def desktop_supabase_no_login_enabled(settings: Settings) -> bool:
    """Permit passwordless access only for a loopback-bound single-user backend."""
    return bool(
        settings.desktop_no_login
        and settings.memory_backend == "supabase"
        and settings.supabase_url.strip()
        and settings.supabase_key.strip()
        and settings.supabase_service_role_key.strip()
        and settings.atlas_owner_user_id.strip()
        and settings.api_host.strip().lower() in {"127.0.0.1", "localhost", "::1"}
    )

_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Minimal identity derived from Supabase Auth, never from client-supplied IDs."""

    user_id: str


class AuthenticatedSession(AuthenticatedUser):
    """Verified user identity plus the bearer token for RLS-enforced data access."""

    access_token: str


async def verify_supabase_access_token(
    token: str,
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> AuthenticatedUser:
    """Ask Supabase Auth to validate a JWT; do not decode it without verification."""
    if not settings.supabase_url.strip() or not settings.supabase_key.strip():
        raise HTTPException(
            status_code=503,
            detail="Autenticação Supabase não configurada no backend.",
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": settings.supabase_key.strip(),
        "Authorization": f"Bearer {token}",
    }

    async def request_user(http_client: httpx.AsyncClient) -> AuthenticatedUser:
        try:
            response = await http_client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação temporariamente indisponível.",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail="Não foi possível validar a sessão de autenticação.",
            ) from exc

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail="Sessão inválida ou expirada.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação temporariamente indisponível.",
            )

        try:
            payload = response.json()
            user_id = payload["id"]
            if not isinstance(user_id, str) or not user_id.strip():
                raise ValueError("Missing user id")
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Resposta inválida do serviço de autenticação.",
            ) from exc

        return AuthenticatedUser(user_id=user_id)

    if client is not None:
        return await request_user(client)

    async with httpx.AsyncClient(timeout=5.0) as http_client:
        return await request_user(http_client)


async def require_authenticated_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Envie um token de acesso no cabeçalho Authorization: Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if is_activation_token(credentials.credentials):
        return verify_activation_token(credentials.credentials, settings)
    return await verify_supabase_access_token(credentials.credentials, settings)


async def require_authenticated_session(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Envie um token de acesso no cabeçalho Authorization: Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = verify_activation_token(credentials.credentials, settings) if is_activation_token(credentials.credentials) else await verify_supabase_access_token(credentials.credentials, settings)
    return AuthenticatedSession(user_id=user.user_id, access_token=credentials.credentials)
