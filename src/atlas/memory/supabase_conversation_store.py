"""Supabase-backed conversation history scoped to the authenticated user."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException

from atlas.backend.config import Settings


class SupabaseConversationStore:
    """Persist conversation history in Supabase with the user's JWT and RLS."""

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
            raise HTTPException(status_code=503, detail="Supabase não está configurado no backend.")
        headers = {
            "apikey": self.settings.supabase_key.strip(),
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        if table not in {"atlas_conversations", "atlas_conversation_messages"}:
            raise ValueError("Unsupported table")
        url = f"{self.settings.supabase_url.rstrip('/')}/rest/v1/{table}"
        headers = self._headers(prefer=prefer)

        async def send(client: httpx.AsyncClient) -> httpx.Response:
            try:
                response = await client.request(
                    method, url, headers=headers, params=params, json=payload
                )
            except httpx.TimeoutException as exc:
                raise HTTPException(status_code=503, detail="O histórico demorou para responder.") from exc
            except httpx.RequestError as exc:
                raise HTTPException(status_code=503, detail="Não foi possível acessar o histórico.") from exc
            if response.status_code in (401, 403):
                raise HTTPException(status_code=401 if response.status_code == 401 else 403,
                                    detail="Sessão inválida ou acesso ao histórico não autorizado.")
            if response.status_code not in (200, 201, 204):
                raise HTTPException(status_code=503, detail="Histórico Supabase indisponível; confira as migrações.")
            return response

        if self.client is not None:
            return await send(self.client)
        async with httpx.AsyncClient(timeout=8.0) as client:
            return await send(client)

    @staticmethod
    def _rows(response: httpx.Response) -> list[dict[str, Any]]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="Resposta inválida do histórico.") from exc
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise HTTPException(status_code=503, detail="Resposta inválida do histórico.")
        return payload

    async def create_conversation(self, title: str = "Nova conversa") -> dict[str, Any]:
        clean_title = title.strip()[:160] or "Nova conversa"
        response = await self._request(
            "POST", "atlas_conversations",
            params={"select": "id,title,created_at,updated_at"},
            payload={"id": str(uuid4()), "user_id": self.user_id, "title": clean_title},
            prefer="return=representation",
        )
        rows = self._rows(response)
        if not rows:
            raise HTTPException(status_code=503, detail="O banco não retornou a conversa criada.")
        return rows[0]

    async def list_conversations(self, limit: int = 30) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        response = await self._request(
            "GET", "atlas_conversations",
            params={
                "select": "id,title,created_at,updated_at",
                "user_id": f"eq.{self.user_id}",
                "order": "updated_at.desc",
                "limit": str(safe_limit),
            },
        )
        conversations = self._rows(response)
        # Bounded N+1 is acceptable for the first cloud implementation; optimize with a view later.
        for conversation in conversations:
            latest = await self._request(
                "GET", "atlas_conversation_messages",
                params={
                    "select": "content",
                    "conversation_id": f"eq.{conversation['id']}",
                    "user_id": f"eq.{self.user_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            messages = self._rows(latest)
            conversation["last_message"] = messages[0]["content"] if messages else None
        return conversations

    async def list_messages(self, conversation_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        # The user_id filter plus RLS prevents reading another user's conversation.
        response = await self._request(
            "GET", "atlas_conversation_messages",
            params={
                "select": "id,conversation_id,role,content,created_at",
                "conversation_id": f"eq.{conversation_id}",
                "user_id": f"eq.{self.user_id}",
                "order": "created_at.desc",
                "limit": str(safe_limit),
            },
        )
        return list(reversed(self._rows(response)))

    async def add_message(self, conversation_id: UUID, role: str, content: str) -> dict[str, Any] | None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        clean_content = content.strip()
        if not clean_content or len(clean_content) > 20000:
            raise ValueError("content must contain between 1 and 20000 characters")
        # Verify ownership before inserting a message.
        owned = await self._request(
            "GET", "atlas_conversations",
            params={
                "select": "id",
                "id": f"eq.{conversation_id}",
                "user_id": f"eq.{self.user_id}",
                "limit": "1",
            },
        )
        if not self._rows(owned):
            return None
        response = await self._request(
            "POST", "atlas_conversation_messages",
            params={"select": "id,conversation_id,role,content,created_at"},
            payload={
                "id": str(uuid4()),
                "conversation_id": str(conversation_id),
                "user_id": self.user_id,
                "role": role,
                "content": clean_content,
            },
            prefer="return=representation",
        )
        rows = self._rows(response)
        if not rows:
            raise HTTPException(status_code=503, detail="O banco não retornou a mensagem criada.")
        await self._request(
            "PATCH", "atlas_conversations",
            params={"id": f"eq.{conversation_id}", "user_id": f"eq.{self.user_id}"},
            payload={"updated_at": "now()"},
            prefer="return=minimal",
        )
        return rows[0]

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        response = await self._request(
            "DELETE", "atlas_conversations",
            params={
                "id": f"eq.{conversation_id}",
                "user_id": f"eq.{self.user_id}",
                "select": "id",
            },
            prefer="return=representation",
        )
        return bool(self._rows(response))
