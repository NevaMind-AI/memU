"""
Tests for the OpenAI client wrapper with auto-recall.
"""

from __future__ import annotations

from unittest.mock import MagicMock


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
