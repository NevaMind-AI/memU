"""
Tests for the OpenAI client wrapper with auto-recall.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock


class FakeMemoryService:
    def __init__(self) -> None:
        self.retrieve_calls = []

    async def retrieve(self, queries, where=None, ranking=None):
        self.retrieve_calls.append({"queries": queries, "where": where, "ranking": ranking})
        return {
            "items": [
                {"summary": "one"},
                {"summary": "two"},
                {"summary": "three"},
            ]
        }


class AsyncCreateCompletions:
    def __init__(self) -> None:
        self.kwargs = {}

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return {"ok": True, "method": "create"}


class AsyncAcreateCompletions:
    def __init__(self) -> None:
        self.kwargs = {}

    async def acreate(self, **kwargs):
        self.kwargs = kwargs
        return {"ok": True, "method": "acreate"}

    def create(self, **kwargs):
        raise AssertionError("acreate should be preferred when present")


class TestMemuOpenAIWrapper:
    """Tests for OpenAI client wrapper."""

    def test_extract_user_query_simple(self):
        """Should extract user query from messages."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What's my favorite drink?"},
        ]

        query = completions._extract_user_query(messages)
        assert query == "What's my favorite drink?"

    def test_extract_user_query_multiple_turns(self):
        """Should extract most recent user query."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What's my name?"},
        ]

        query = completions._extract_user_query(messages)
        assert query == "What's my name?"

    def test_extract_user_query_from_multiple_text_parts(self):
        """Should concatenate text parts from multimodal user content."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Remember that I like coffee."},
                    {"type": "image_url", "image_url": {"url": "https://example.test/photo.png"}},
                    {"type": "text", "text": "What should I order today?"},
                    {"type": "text", "text": 123},
                ],
            },
        ]

        query = completions._extract_user_query(messages)
        assert query == "Remember that I like coffee.\nWhat should I order today?"

    def test_inject_memories_into_existing_system(self):
        """Should append memories to existing system message."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]

        memories = [
            {"summary": "User loves coffee"},
            {"summary": "User is named Alex"},
        ]

        result = completions._inject_memories(messages, memories)

        assert len(result) == 2
        assert "<memu_context>" in result[0]["content"]
        assert "User loves coffee" in result[0]["content"]
        assert "User is named Alex" in result[0]["content"]
        assert result[0]["content"].startswith("You are helpful.")

    def test_inject_memories_does_not_mutate_original_messages(self):
        """Should leave caller-owned message dictionaries untouched."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]

        result = completions._inject_memories(messages, [{"summary": "User loves coffee"}])

        assert messages == [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        assert result is not messages
        assert result[0] is not messages[0]

    def test_inject_memories_appends_to_system_content_parts(self):
        """Should support system messages whose content is a list of text parts."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)
        original_part = {"type": "text", "text": "You are helpful."}
        messages = [
            {"role": "system", "content": [original_part]},
            {"role": "user", "content": "Hi"},
        ]

        result = completions._inject_memories(messages, [{"summary": "User loves coffee"}])

        assert messages[0]["content"] == [original_part]
        assert result[0]["content"] is not messages[0]["content"]
        assert result[0]["content"][0] == original_part
        assert result[0]["content"][0] is not original_part
        assert result[0]["content"][1]["type"] == "text"
        assert "<memu_context>" in result[0]["content"][1]["text"]
        assert "User loves coffee" in result[0]["content"][1]["text"]

    def test_inject_memories_creates_system_message(self):
        """Should create system message if none exists."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [
            {"role": "user", "content": "Hi"},
        ]

        memories = [{"summary": "User loves tea"}]

        result = completions._inject_memories(messages, memories)

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert "<memu_context>" in result[0]["content"]
        assert "User loves tea" in result[0]["content"]

    def test_inject_memories_empty_list(self):
        """Should return original messages if no memories."""
        from memu.client.openai_wrapper import MemuChatCompletions

        completions = MemuChatCompletions(MagicMock(), MagicMock(), {}, "salience", 5)

        messages = [{"role": "user", "content": "Hi"}]
        result = completions._inject_memories(messages, [])

        assert result == messages

    def test_wrap_openai_convenience_function(self):
        """Should create wrapper with convenience function."""
        from memu.client import wrap_openai

        mock_client = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_service = MagicMock()

        wrapped = wrap_openai(
            mock_client,
            mock_service,
            user_id="user123",
            agent_id="bot1",
            ranking="salience",
            top_k=3,
        )

        assert wrapped._user_data == {"user_id": "user123", "agent_id": "bot1"}
        assert wrapped._ranking == "salience"
        assert wrapped._top_k == 3

    def test_wrap_openai_does_not_mutate_user_data(self):
        """Should not mutate caller-owned user_data dictionaries."""
        from memu.client import wrap_openai

        mock_client = MagicMock()
        mock_client.chat.completions = MagicMock()
        user_data = {"user_id": "original", "team_id": "team1"}

        wrapped = wrap_openai(
            mock_client,
            MagicMock(),
            user_data=user_data,
            user_id="override",
            agent_id="agent1",
        )

        assert user_data == {"user_id": "original", "team_id": "team1"}
        assert wrapped._user_data == {
            "user_id": "override",
            "team_id": "team1",
            "agent_id": "agent1",
        }

    def test_wrapper_scope_is_stable_after_external_user_data_mutation(self):
        """Should keep the wrapper's retrieve scope stable after construction."""
        from memu.client import wrap_openai

        mock_client = MagicMock()
        mock_client.chat.completions = MagicMock()
        service = FakeMemoryService()
        user_data = {"user_id": "u1"}
        wrapped = wrap_openai(mock_client, service, user_data=user_data)
        user_data["user_id"] = "u2"

        asyncio.run(wrapped.chat.completions._retrieve_memories("what do I like?"))

        assert service.retrieve_calls[0]["where"] == {"user_id": "u1"}

    def test_retrieve_memories_respects_top_k_limit(self):
        """Should inject at most top_k retrieved memories."""
        from memu.client.openai_wrapper import MemuChatCompletions

        service = FakeMemoryService()
        completions = MemuChatCompletions(MagicMock(), service, {}, "salience", 2)

        memories = asyncio.run(completions._retrieve_memories("what do I like?"))

        assert [memory["summary"] for memory in memories] == ["one", "two"]
        assert service.retrieve_calls[0]["ranking"] == "salience"

    def test_acreate_awaits_async_create_result(self):
        """Should await AsyncOpenAI-style create() coroutine results."""
        from memu.client.openai_wrapper import MemuChatCompletions

        original = AsyncCreateCompletions()
        completions = MemuChatCompletions(original, FakeMemoryService(), {}, "salience", 1)

        result = asyncio.run(completions.acreate(messages=[{"role": "user", "content": "What do I like?"}]))

        assert result == {"ok": True, "method": "create"}
        assert "<memu_context>" in original.kwargs["messages"][0]["content"]
        assert "one" in original.kwargs["messages"][0]["content"]

    def test_acreate_prefers_legacy_acreate_when_present(self):
        """Should keep compatibility with clients exposing acreate()."""
        from memu.client.openai_wrapper import MemuChatCompletions

        original = AsyncAcreateCompletions()
        completions = MemuChatCompletions(original, FakeMemoryService(), {}, "salience", 1)

        result = asyncio.run(completions.acreate(messages=[{"role": "user", "content": "What do I like?"}]))

        assert result == {"ok": True, "method": "acreate"}
        assert "<memu_context>" in original.kwargs["messages"][0]["content"]

    def test_wrapper_rejects_unknown_ranking(self):
        """Should reject invalid ranking at the integration boundary."""
        from memu.client import wrap_openai

        mock_client = MagicMock()
        mock_client.chat.completions = MagicMock()

        try:
            wrap_openai(mock_client, MagicMock(), ranking="random")
        except ValueError as exc:
            assert "retrieve ranking must be 'similarity' or 'salience'" in str(exc)
        else:
            raise AssertionError("wrap_openai should reject unknown ranking")

    def test_wrapper_rejects_non_positive_top_k(self):
        """Should reject invalid top_k at the integration boundary."""
        from memu.client import wrap_openai

        mock_client = MagicMock()
        mock_client.chat.completions = MagicMock()

        try:
            wrap_openai(mock_client, MagicMock(), top_k=0)
        except ValueError as exc:
            assert "top_k must be a positive integer" in str(exc)
        else:
            raise AssertionError("wrap_openai should reject non-positive top_k")

    def test_wrapper_proxies_other_attributes(self):
        """Should proxy non-chat attributes to original client."""
        from memu.client import MemuOpenAIWrapper

        mock_client = MagicMock()
        mock_client.models = MagicMock()
        mock_client.models.list = MagicMock(return_value=["gpt-4"])
        mock_client.chat.completions = MagicMock()

        wrapped = MemuOpenAIWrapper(mock_client, MagicMock(), {})

        # Should proxy to original
        result = wrapped.models.list()
        assert result == ["gpt-4"]
