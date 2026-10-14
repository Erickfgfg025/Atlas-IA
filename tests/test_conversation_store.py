from uuid import UUID

import pytest

from atlas.memory.conversation_store import SQLiteConversationStore


@pytest.mark.asyncio
async def test_conversation_and_messages_persist(tmp_path):
    store = SQLiteConversationStore(tmp_path / "atlas.db")
    conversation = await store.create_conversation(" Planejamento ATLAS ")
    conversation_id = UUID(conversation["id"])

    user_message = await store.add_message(conversation_id, "user", "  Olá, ATLAS  ")
    assistant_message = await store.add_message(
        conversation_id, "assistant", "Olá! Como posso ajudar?"
    )

    assert user_message is not None
    assert user_message["content"] == "Olá, ATLAS"
    assert assistant_message is not None
    messages = await store.list_messages(conversation_id)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [message["content"] for message in messages] == [
        "Olá, ATLAS",
        "Olá! Como posso ajudar?",
    ]

    reopened = SQLiteConversationStore(tmp_path / "atlas.db")
    restored = await reopened.list_messages(conversation_id)
    assert len(restored) == 2
    assert restored[0]["content"] == "Olá, ATLAS"


@pytest.mark.asyncio
async def test_conversation_list_is_recent_first_and_limited(tmp_path):
    store = SQLiteConversationStore(tmp_path / "atlas.db")
    older = await store.create_conversation("Antiga")
    newer = await store.create_conversation("Nova")

    await store.add_message(UUID(older["id"]), "user", "mensagem antiga")
    await store.add_message(UUID(newer["id"]), "user", "mensagem nova")

    rows = await store.list_conversations(limit=1)
    assert len(rows) == 1
    assert rows[0]["id"] == newer["id"]
    assert rows[0]["last_message"] == "mensagem nova"


@pytest.mark.asyncio
async def test_invalid_roles_and_empty_messages_are_rejected(tmp_path):
    store = SQLiteConversationStore(tmp_path / "atlas.db")
    conversation = await store.create_conversation()
    conversation_id = UUID(conversation["id"])

    with pytest.raises(ValueError):
        await store.add_message(conversation_id, "system", "texto")
    with pytest.raises(ValueError):
        await store.add_message(conversation_id, "user", "   ")


@pytest.mark.asyncio
async def test_delete_conversation_deletes_its_messages(tmp_path):
    store = SQLiteConversationStore(tmp_path / "atlas.db")
    conversation = await store.create_conversation()
    conversation_id = UUID(conversation["id"])
    await store.add_message(conversation_id, "user", "apagar")

    assert await store.delete_conversation(conversation_id) is True
    assert await store.list_messages(conversation_id) == []
    assert await store.delete_conversation(conversation_id) is False
