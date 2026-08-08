"""Example of integrating memU with a OneBot v11 (NapCat) QQ bot for long-term memory."""

import sys
import types
import asyncio
import logging
from openai import AsyncOpenAI

# Mock the core Rust module if not compiled in the environment
mock_core = types.ModuleType("memu._core")
mock_core.hello_from_bin = lambda: "Hello from mocked bin!"
sys.modules["memu._core"] = mock_core

from memu.app import MemoryService
from memu.app.settings import MemorizeConfig, CategoryConfig
from memu.integrations.onebot import OneBotAdapter, OneBotConfig

# Configure logging to match memU standards
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("memu.examples.onebot")

# ==============================================================================
# LLM Configuration
# ==============================================================================
LLM_PROFILES = {
    "default": {
        "base_url": "",  # Your LLM endpoint
        "api_key": "",  # Your LLM API key
        "chat_model": "",  # Your LLM chat model
        "client_backend": "sdk"
    },
    "embedding": {
        "base_url": "",  # Your LLM endpoint for embeddings
        "api_key": "",  # Your LLM API key for embeddings
        "embed_model": "",  # Your LLM embedding model
        "client_backend": "sdk"
    }
}

# Initialize a chat client for generating conversational responses
chat_client = AsyncOpenAI(
    base_url=LLM_PROFILES["default"]["base_url"],
    api_key=LLM_PROFILES["default"]["api_key"]
)

async def on_qq_message(event: dict, adapter: OneBotAdapter, memory_service: MemoryService):
    """Callback function triggered when a QQ message is received via OneBot."""
    user_id = str(event.get("user_id"))
    group_id = event.get("group_id")
    text = event.get("clean_text", "")
    message_type = event.get("message_type")
    
    # Ignore empty messages or messages sent by the bot itself
    if not text or user_id == str(adapter.get_self_id()):
        return
        
    logger.info(f"Received message from User [{user_id}]: {text}")
    
    try:
        current_user = {"user_id": user_id}

        # Retrieve long-term memories related to the current message
        logger.info("Retrieving related memories from memU...")
        retrieved_result = await memory_service.retrieve(
            queries=[{"role": "user", "content": text}],
            where=current_user
        )
        
        # Handle the result based on memU's return structure
        items = (
            retrieved_result.get("items", []) 
            if isinstance(retrieved_result, dict) 
            else getattr(retrieved_result, "items", [])
        )
        
        memory_context = ""
        if items:
            memory_context = "\n".join([
                f"- {m.get('summary', '')}" if isinstance(m, dict) else f"- {m.summary}" 
                for m in items
            ])
            logger.info(f"Successfully retrieved {len(items)} related memory item(s).")
        else:
            logger.info("No related long-term memory found for the current topic.")

        # Generate a response using the LLM, augmented by retrieved memories
        logger.info("Generating response using LLM with memory context...")
        system_prompt = (
            "You are an AI assistant. There is no short-term chat history between us. "
            "You MUST rely exclusively on the clues provided in the [Long-Term Memory Database] below to answer. "
            "If there is no relevant information in the memory, simply state that you don't know or don't remember. "
            "If the memory contradicts the user's current statement (e.g., they used to like apples but now say oranges), "
            "point out the change in a friendly conversational tone.\n\n"
            f"[Long-Term Memory Database]:\n{memory_context if memory_context else 'Empty'}\n"
        )
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        response = await chat_client.chat.completions.create(
            model=LLM_PROFILES["default"]["chat_model"],
            messages=messages,
            temperature=0.7
        )
        reply_text = response.choices[0].message.content
        
        # Send the generated response back to the QQ group or private chat
        if message_type == "group":
            logger.info(f"Sending reply to group [{group_id}].")
            await adapter.send_group_msg_ack(int(group_id), f"[CQ:at,qq={user_id}] {reply_text}")
        else:
            logger.info(f"Sending private reply to user [{user_id}].")
            adapter.send_private_msg(int(user_id), reply_text)

        # Persist the current message into the memory database
        logger.info("Committing current interaction to memU storage...")
        await memory_service.create_memory_item(
            memory_type="event",
            memory_content=text,
            memory_categories=["QQConversations"],
            user=current_user
        )

        logger.info("Interaction cycle completed successfully.")
        
    except Exception as e:
        logger.error(f"Error occurred during interaction cycle: {e}", exc_info=True)


async def main():
    """Main entry point for starting the OneBot memory integration example."""
    logger.info("Initializing memU MemoryService...")
    memory_service = MemoryService(
        llm_profiles=LLM_PROFILES,
        memorize_config=MemorizeConfig(
            memory_categories=[
                CategoryConfig(name="QQConversations", description="Records of chats from QQ")
            ]
        ),
    )

    async def msg_handler(event: dict, adapter: OneBotAdapter):
        await on_qq_message(event, adapter, memory_service)

    # Initialize the OneBot adapter with standard configuration
    logger.info("Initializing OneBot v11 Adapter...")
    config = OneBotConfig(
        ws_url="ws://127.0.0.1:3001", 
        access_token="" # Replace with environment variable in production
    )
    
    adapter = OneBotAdapter(config=config, on_message=msg_handler)
    
    logger.info("Starting OneBot engine and entering event loop...")
    await adapter.connect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutdown requested by user.")