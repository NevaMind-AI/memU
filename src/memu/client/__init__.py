"""
memU Client Wrapper for Auto-Recall Memory Injection.

This module provides optional wrappers around OpenAI/Anthropic clients
that automatically inject recalled memories into prompts.

Usage:
    from memu.client import wrap_openai
    from openai import OpenAI

    client = OpenAI()
    service = MemoryService(...)

    # Wrap the client for auto-recall
    wrapped_client = wrap_openai(client, service, user_id="user123")

    # Now all chat completions automatically include relevant memories
    response = wrapped_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "What's my favorite drink?"}]
    )
"""

from memu.client.openai_wrapper import MemuOpenAIWrapper, wrap_openai

__all__ = ["MemuOpenAIWrapper", "wrap_openai"]
