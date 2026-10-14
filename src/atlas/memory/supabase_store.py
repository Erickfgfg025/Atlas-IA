"""User-scoped Supabase memory access through PostgREST and the user's bearer token."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from atlas.backend.config import Settings


class SupabaseMemoryStore:
    """Use the verified user's token so PostgreSQL RLS remains the access boundary."""

    def __init__(
        self,
        settings: Settings,
        access_token: str,
        user_id: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.access_token = access_token
        self.user_id = user_id
        self.client = client

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        if not self.settings.supabase_url.strip() or not self.settings.supabase_key.strip():
            raise HTTPException(
                status_code=503,
                detail="Memória Supabase não configurada no backend.",
            )
        headers = {
            "apikey": self.settings.supabase_key.strip(),
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def _request(
        self,
        method: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        url = f"{self.settings.supabase_url.rstrip('/')}/rest/v1/atlas_memories"
        headers = self._headers(prefer=prefer)

        async def send(client: httpx.AsyncClient) -> httpx.Response:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise HTTPException(
                    status_code=503,
                    detail="O serviço de memória demorou demais para responder.",
                ) from exc
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível acessar o serviço de memória.",
                ) from exc

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Sessão inválida ou expirada.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Acesso à memória não autorizado pelas políticas do banco.",
                )
            if response.status_code not in (200, 201, 204):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Memória indisponível. Confirme se a migração foi aplicada "
                        "e se a tabela está exposta à Data API."
                    ),
                )
            return response

        if self.client is not None:
            return await send(self.client)
        async with httpx.AsyncClient(timeout=8.0) as client:
            return await send(client)

    async def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            params={
                "select": "id,kind,content,source,scope,confidence,created_at",
                "user_id": f"eq.{self.user_id}",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        try:
            rows = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="Resposta inválida do serviço de memória.") from exc
        if not isinstance(rows, list):
            raise HTTPException(status_code=503, detail="Resposta inválida do serviço de memória.")
        return [row for row in rows if isinstance(row, dict)]

    async def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **memory,
            "user_id": self.user_id,
        }
        response = await self._request(
            "POST",
            params={"select": "id,kind,content,source,scope,confidence,created_at"},
            payload=payload,
            prefer="return=representation",
        )
        try:
            rows = response.json()
            row = rows[0] if isinstance(rows, list) and rows else None
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="Resposta inválida do serviço de memória.") from exc
        if not isinstance(row, dict):
            raise HTTPException(status_code=503, detail="O banco não retornou a memória criada.")
        return row

    async def delete_memory(self, memory_id: UUID) -> bool:
        response = await self._request(
            "DELETE",
            params={
                "id": f"eq.{memory_id}",
                "user_id": f"eq.{self.user_id}",
                "select": "id",
            },
            prefer="return=representation",
        )
        try:
            rows = response.json()
        except ValueError:
            rows = []
        return isinstance(rows, list) and bool(rows)
