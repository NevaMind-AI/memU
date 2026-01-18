"""Demo script for MemU LangGraph Integration."""

import asyncio
import logging
import os
import sys

# Try imports and fail proactively if missing
try:
    import langgraph  # noqa: F401
    from langchain_core.tools import BaseTool

    from memu.app.service import MemoryService
    from memu.integrations.langgraph import MemULangGraphTools
except ImportError:
    print("Missing dependencies. Please run: uv sync --extra langgraph")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langgraph_demo")


async def initialize_infrastructure() -> MemULangGraphTools:
    """Initialize the MemoryService and the LangGraph adapter."""
    # Ensure OPENAI_API_KEY is present
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables.")

    # In a real scenario, you might load config from file or env
    service = MemoryService()
    return MemULangGraphTools(service)


async def process_conversation(tools: list[BaseTool], user_id: str) -> None:
    """Simulate a conversation where memory is saved."""
    save_tool = next(t for t in tools if t.name == "save_memory")

    logger.info("--- Simulating Save Memory ---")
    inputs = {
        "content": "The user prefers dark mode and likes Python programming.",
        "user_id": user_id,
        "metadata": {"source": "demo_script"},
    }
    # Invoke the tool (async execution)
    result = await save_tool.ainvoke(inputs)
    logger.info("Save Result: %s", result)


async def process_retrieval(tools: list[BaseTool], user_id: str) -> None:
    """Simulate retrieving memory."""
    search_tool = next(t for t in tools if t.name == "search_memory")

    logger.info("--- Simulating Search Memory ---")
    inputs = {"query": "What are the user's preferences?", "user_id": user_id, "limit": 3}
    result = await search_tool.ainvoke(inputs)
    logger.info("Search Result:\n%s", result)


async def main() -> None:
    """Main entry point."""
    logger.info("Starting LangGraph Demo...")

    adapter = await initialize_infrastructure()
    tools = adapter.tools()

    user_id = "demo_user_123"

    await process_conversation(tools, user_id)
    await process_retrieval(tools, user_id)

    logger.info("Demo completed.")


if __name__ == "__main__":
    asyncio.run(main())
