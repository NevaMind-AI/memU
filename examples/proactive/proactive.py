import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)
from memory.local.memorize import memorize
from memory.local.tools import _get_todos, memu_server

# Set your Anthropic API key here if it's not set in the environment variables
# os.environ["ANTHROPIC_API_KEY"] = ""

N_MESSAGES_MEMORIZE = 2


async def trigger_memorize(messages: list[dict[str, any]]) -> bool:
    """Background task to memorize conversation messages."""
    try:
        await memorize(messages)
        print("\n[Background] Memorization submitted.")
        return True
    except Exception as e:
        print(f"\n[Background] Memorization failed: {e!r}")
        return False


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"memu": memu_server},
        allowed_tools=[
            # "mcp__memu__memu_memory",
            "mcp__memu__memu_todos",
        ],
    )

    conversation_messages: list[dict[str, any]] = []
    pending_tasks: list[asyncio.Task] = []

    print("Claude Autorun")
    print("Type 'quit' or 'exit' to end the session.")
    print("-" * 40)

    round = 0
    async with ClaudeSDKClient(options=options) as client:
        while True:
            want_user_input = False

            if round == 0:
                want_user_input = True
            else:
                todos = await _get_todos()
                if todos:
                    user_input = f"Please continue with the following todos:\n{todos}"
                else:
                    want_user_input = True

            if want_user_input:
                try:
                    user_input = input("\nYou: ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("quit", "exit"):
                    break

            # Record user message
            conversation_messages.append({"role": "user", "content": user_input})

            # Send query to Claude
            await client.query(user_input)

            # Collect assistant response
            assistant_text_parts: list[str] = []

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"Claude: {block.text}")
                            assistant_text_parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    print(f"Result: {message.result}")

            # Record assistant message
            if assistant_text_parts:
                conversation_messages.append({"role": "assistant", "content": "\n".join(assistant_text_parts)})

            # Check if we should trigger memorization
            if len(conversation_messages) >= N_MESSAGES_MEMORIZE:
                print(f"\n[Info] Reached {N_MESSAGES_MEMORIZE} messages, triggering memorization...")
                success = await trigger_memorize(conversation_messages.copy())
                if success:
                    conversation_messages.clear()

            round += 1

    # User quit - memorize remaining messages if any
    if conversation_messages:
        print("\n[Info] Session ended, memorizing remaining messages...")
        success = await trigger_memorize(conversation_messages.copy())

    # Wait for all pending memorization tasks to complete
    if pending_tasks:
        print("[Info] Waiting for memorization tasks to complete...")
        await asyncio.gather(*pending_tasks, return_exceptions=True)

    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
