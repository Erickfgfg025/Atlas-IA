"""Supabase Auth token verification for backend-only endpoints."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from atlas.backend.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Minimal identity derived from Supabase Auth, never from client-supplied IDs."""

    user_id: str


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
    return await verify_supabase_access_token(credentials.credentials, settings)
