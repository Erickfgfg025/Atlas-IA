"""Supabase password sign-in, sign-up, and sign-out helpers."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from atlas.backend.config import Settings


class AuthSession(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    user_id: str | None = None
    confirmation_required: bool = False


class PasswordCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


def _auth_headers(settings: Settings) -> dict[str, str]:
    if not settings.supabase_url.strip() or not settings.supabase_key.strip():
        raise HTTPException(
            status_code=503,
            detail="Autenticação Supabase não configurada no backend.",
        )
    return {
        "apikey": settings.supabase_key.strip(),
        "Content-Type": "application/json",
    }


async def _post_auth(
    path: str,
    settings: Settings,
    payload: dict[str, Any],
    *,
    client: httpx.AsyncClient | None = None,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = _auth_headers(settings)
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/{path.lstrip('/')}"

    async def send(http_client: httpx.AsyncClient) -> dict[str, Any]:
        try:
            response = await http_client.post(url, headers=headers, json=payload, params=query_params)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação temporariamente indisponível.",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail="Não foi possível conectar ao serviço de autenticação.",
            ) from exc

        if response.status_code in (400, 401, 422):
            try:
                error_data = response.json()
            except ValueError:
                error_data = {}
            error_text = " ".join(
                str(error_data.get(key, ""))
                for key in ("msg", "message", "error_description", "error")
            ).lower() if isinstance(error_data, dict) else ""
            if "email not confirmed" in error_text or "email_not_confirmed" in error_text:
                raise HTTPException(
                    status_code=403,
                    detail="E-mail ainda não confirmado. Abra o link recebido e depois tente entrar novamente.",
                )
            if path.startswith("signup") and ("already registered" in error_text or "user already registered" in error_text):
                raise HTTPException(
                    status_code=409,
                    detail="Este e-mail já possui cadastro. Confirme a mensagem recebida ou entre na sua conta.",
                )
            if path.startswith("token"):
                raise HTTPException(
                    status_code=401,
                    detail="E-mail ou senha incorretos. Se acabou de criar a conta, confirme o e-mail primeiro.",
                )
            raise HTTPException(
                status_code=400,
                detail="O Supabase recusou a solicitação. Verifique o e-mail, a senha e as configurações de autenticação.",
            )
        if response.status_code not in (200, 201):
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação temporariamente indisponível.",
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=503,
                detail="Resposta inválida do serviço de autenticação.",
            ) from exc
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=503,
                detail="Resposta inválida do serviço de autenticação.",
            )
        return data

    if client is not None:
        return await send(client)
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        return await send(http_client)


async def sign_in_with_password(
    email: str,
    password: str,
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> AuthSession:
    data = await _post_auth(
        "token?grant_type=password",
        settings,
        {"email": email.strip(), "password": password},
        client=client,
    )
    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=401, detail="A autenticação não retornou uma sessão válida.")
    user_id = user.get("id")
    return AuthSession(
        access_token=access_token,
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        user_id=user_id if isinstance(user_id, str) else None,
    )


async def sign_up_with_password(
    email: str,
    password: str,
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> AuthSession:
    data = await _post_auth(
        "signup",
        settings,
        {"email": email.strip(), "password": password},
        client=client,
        query_params={
            "redirect_to": settings.auth_email_redirect_url.strip()
        } if settings.auth_email_redirect_url.strip() else None,
    )
    user = data.get("user") if isinstance(data.get("user"), dict) else data
    access_token = data.get("access_token")
    user_id = user.get("id") if isinstance(user, dict) else None
    return AuthSession(
        access_token=access_token if isinstance(access_token, str) and access_token else None,
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        user_id=user_id if isinstance(user_id, str) else None,
        confirmation_required=not (isinstance(access_token, str) and bool(access_token)),
    )


async def sign_out(
    access_token: str,
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> None:
    headers = _auth_headers(settings)
    headers["Authorization"] = f"Bearer {access_token}"
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/logout"

    async def send(http_client: httpx.AsyncClient) -> None:
        try:
            response = await http_client.post(url, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail="Não foi possível encerrar a sessão no serviço de autenticação.",
            ) from exc
        if response.status_code not in (200, 204):
            raise HTTPException(
                status_code=503,
                detail="Não foi possível encerrar a sessão no serviço de autenticação.",
            )

    if client is not None:
        await send(client)
        return
    async with httpx.AsyncClient(timeout=5.0) as http_client:
        await send(http_client)
