"""
Sealos Support Agent Demo
-------------------------
This script demonstrates MemU's "Add Memory" and "Retrieval" workflow
for a Customer Support Agent scenario.

It MOCKS the OpenAI API, so NO API KEY is required.
"""

import asyncio
import json
import logging
import os
import re
import sys
from unittest.mock import MagicMock, patch

# Configure logging to show Agent output clearly
# Suppress MemU internal errors (like JSON parsing fallbacks) for cleaner demo
logging.basicConfig(level=logging.ERROR)
logging.getLogger("memu").setLevel(logging.CRITICAL)
logging.getLogger("root").setLevel(logging.CRITICAL)

# Add src to sys.path
# We assume this script is in examples/ and src/ is in the parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.dirname(script_dir)
src_path = os.path.join(workspace_dir, "src")
sys.path.insert(0, src_path)

from memu.app import MemoryService  # noqa: E402
from memu.llm.openai_sdk import OpenAISDKClient  # noqa: E402

# -------------------------------------------------------------------------
# MOCK LLM IMPLEMENTATION
# -------------------------------------------------------------------------


class MockChatCompletionMessage:
    def __init__(self, content):
        self.content = content


class MockChoice:
    def __init__(self, content):
        self.message = MockChatCompletionMessage(content)


class MockChatCompletion:
    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockLLM(OpenAISDKClient):
    """
    Mocks OpenAISDKClient to satisfy MemU requirements without real API calls.
    It implements simple logic to respond to MemU's internal prompts.
    """

    def __init__(self, *args, **kwargs):
        # We don't call super() because we don't want to init real AsyncOpenAI
        self.chat_model = kwargs.get("chat_model", "mock-gpt")
        self.embed_model = kwargs.get("embed_model", "mock-embed")
        self.embed_batch_size = kwargs.get("embed_batch_size", 10)

        # Mock the internal client attribute if accessed directly
        self.client = MagicMock()

    async def summarize(self, text: str, system_prompt: str | None = None, **kwargs):
        """
        Respond to prompts based on keywords.
        """
        text_lower = text.lower()

        # --- Phase 1: Ingestion & Extraction ---

        # 1. Conversation Segmentation/Summarization Prompt
        if "summarize the following conversation" in text_lower:
            return "Captain reported a 502 Bad Gateway error on port 3000.", MockChatCompletion("Summary")

        # 2. Category Summary Update Prompt
        if "summarize the following memory category" in text_lower:
            return "Customer Issues and Errors", MockChatCompletion("Cat Summary")

        # 3. Memory Extraction Prompt (looks for XML output)
        if "xml" in text_lower and ("memory" in text_lower or "extract" in text_lower):
            # Return a mock event memory
            xml_response = """
<events>
    <memory>
        <content>Captain reported a 502 Bad Gateway error on port 3000.</content>
        <categories>
            <category>technical_issues</category>
        </categories>
    </memory>
</events>
"""
            return xml_response, MockChatCompletion(xml_response)

        # --- Phase 2: Retrieval ---

        # 4. Retrieval Decision (Sufficiency Check)
        # Prompt usually asks to decide if retrieval is needed.
        if "determine if" in text_lower or "<decision>" in text_lower or "retrieve" in text_lower:
            # If the user says "Hello", the agent needs to recall context.
            # We force it to retrieve "issues" or "errors".
            return (
                "<decision>RETRIEVE</decision><rewritten_query>current technical issues 502 error</rewritten_query>",
                MockChatCompletion("RETRIEVE"),
            )

        # 5. Ranking (Category/Item/Resource)
        # Prompt asks to "Rank the following..." and expects JSON.
        if "rank" in text_lower and "json" in text_lower:
            # Extract IDs from the prompt input to "rank" them (return them as hits)
            # Input format often has "ID: <uuid>"
            ids = re.findall(r"ID: ([a-f0-9\-]{36})", text)
            if not ids:
                # Fallback for shorter/mock IDs if not UUIDs
                ids = re.findall(r"ID: (\w+)", text)

            response_data = {}
            if "categories" in text_lower:
                response_data = {"categories": ids}
            elif "items" in text_lower:
                response_data = {"items": ids}
            elif "resources" in text_lower:
                response_data = {"resources": ids}

            json_str = json.dumps(response_data)
            return json_str, MockChatCompletion(json_str)

        # Default Fallback
        return "Mock Response", MockChatCompletion("Mock Response")

    async def embed(self, inputs):
        """
        Return dummy embeddings.
        """
        # Return a fixed random vector of length 1536 (standard OpenAI size)
        # using a deterministic pattern so it's consistent if needed.
        embeddings = [[0.01] * 1536 for _ in inputs]

        # Mock response object
        Response = MagicMock()
        Response.data = [MagicMock(embedding=e) for e in embeddings]

        return embeddings, Response

    async def vision(self, *args, **kwargs):
        return "Mock image description", MockChatCompletion("Mock image description")

    async def transcribe(self, *args, **kwargs):
        return "Mock audio transcription", "Mock audio transcription"


# -------------------------------------------------------------------------
# MAIN SCENARIO
# -------------------------------------------------------------------------


async def run_demo():
    print("\n🚀 Starting Sealos Support Agent Demo (Offline Mode)\n")

    # 1. Setup Memory Service with Mock LLM
    # We patch the class where it is defined, so any import will see the mock
    with patch("memu.llm.openai_sdk.OpenAISDKClient", MockLLM):
        service = MemoryService(
            llm_profiles={
                "default": {
                    "api_key": "mock-key",  # value doesn't matter
                    "chat_model": "gpt-4o",
                    "client_backend": "sdk",
                }
            },
            database_config={
                "type": "sqlite",  # or in-memory default if supported, but let's use default
                "url": "sqlite:///:memory:",  # Force in-memory DB for clean run
            },
        )

        # ----------------------------------------------------------------
        # PHASE 1: History (Ingest/Add Memory)
        # ----------------------------------------------------------------
        print("📝 --- Phase 1: Ingesting Conversation History ---")

        # Simulate a conversation file content
        conversation_text = """
        [Captain]: I'm getting a 502 Bad Gateway error on port 3000.
        [Agent]: I'm checking the logs.
        """

        # Create a temporary file for the conversation
        temp_dir = os.path.join(workspace_dir, "examples", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        conv_file = os.path.join(temp_dir, "conversation_log.txt")
        # Ensure absolute path for MemU
        conv_file = os.path.abspath(conv_file)

        with open(conv_file, "w") as f:
            f.write(conversation_text)

        print('👤 Captain: "I\'m getting a 502 Bad Gateway error on port 3000."')
        print("🤖 Agent: (Memorizing this interaction...)")

        # Call memorize
        try:
            result = await service.memorize(resource_url=conv_file, modality="conversation")
            items = result.get("items", [])
            print(f"✅ Memory stored! extracted {len(items)} items.")
            for item in items:
                print(f"   - [{item['memory_type']}] {item['summary']}")
        except Exception as e:
            print(f"❌ meaningful error during memorize: {e}")
            import traceback

            traceback.print_exc()

        # ----------------------------------------------------------------
        # PHASE 2: Retrieval (Search Memory)
        # ----------------------------------------------------------------
        print("\n🔍 --- Phase 2: Retrieval on New Interaction ---")

        user_query = "Hello"
        print(f'👤 Captain: "{user_query}"')
        print("🤖 Agent: (Searching memory for context...)")

        # Simulate retrieval workflow
        # We construct a query context
        queries = [{"role": "user", "content": user_query}]

        try:
            # We assume the agent strategy is to check for 'current issues' or 'open tickets'
            # The MockLLM is programmed to rewrite "Hello" -> "current technical issues"
            search_result = await service.retrieve(queries=queries)

            # ----------------------------------------------------------------
            # PHASE 3: Response
            # ----------------------------------------------------------------
            categories = search_result.get("categories", [])
            items = search_result.get("items", [])

            print("\n💡 Retrieved Context:")
            if not items and not categories:
                print("   (No relevant memories found)")

            for item in items:
                print(f"   Found Memory: {item['summary']}")

            print("\n💬 --- Phase 3: Agent Response ---")

            if items:
                # Determine response based on retrieved items
                issue_found = any("502" in i["summary"] or "error" in i["summary"] for i in items)
                if issue_found:
                    print(
                        '🤖 Agent: "Welcome back, Captain. I see you had a 502 error on port 3000 recently. Is that resolved?"'
                    )
                else:
                    print('🤖 Agent: "Hello Captain, how can I help you today?"')
            else:
                print('🤖 Agent: "Hello Captain, how can I help you today?"')

        except Exception as e:
            print(f"❌ Error during retrieval: {e}")
            import traceback

            traceback.print_exc()

    print("\n✨ Demo Completed Successfully")


if __name__ == "__main__":
    asyncio.run(run_demo())
