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
RUNNING_MEMORIZATION: asyncio.Task | None = None


async def trigger_memorize(messages: list[dict[str, any]]) -> bool:
    """Create a background task to memorize conversation messages.

    Returns True if the task was successfully created and registered.
    """
    global RUNNING_MEMORIZATION
    try:
        memorize_awaitable = memorize(messages)
        RUNNING_MEMORIZATION = asyncio.create_task(memorize_awaitable)
    except Exception as e:
        print(f"\n[Memory] Memorization initialization failed: {e!r}")
        return False
    else:
        print("\n[Memory] Memorization task submitted.")
        return True


async def get_next_input(iteration: int) -> tuple[str | None, bool]:
    """
    Get the next input for the conversation.

    Returns:
        tuple of (input_text, should_break)
        - input_text: The user input or todo-based input, None if should continue
        - should_break: True if the loop should break
    """
    if iteration == 0:
        return await get_user_input()

    todos = await _get_todos()

    print(f">>> Todos:\n{todos}\n")
    print("-" * 40)

    if todos and "[todo]" in todos.lower():
        return f"Please continue with the following todos:\n{todos}", False

    return await get_user_input()


async def get_user_input() -> tuple[str | None, bool]:
    """
    Get input from the user.

    Returns:
        tuple of (input_text, should_break)
    """
    try:
        user_input = input("\nYou: ").strip()
    except EOFError:
        return None, True

    if not user_input:
        return None, False

    if user_input.lower() in ("quit", "exit"):
        return None, True

    return user_input, False


async def process_response(client: ClaudeSDKClient) -> list[str]:
    """Process the assistant response and return collected text parts."""
    assistant_text_parts: list[str] = []

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
                    assistant_text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            print(f"Result: {message.result}")

    return assistant_text_parts


async def check_and_memorize(conversation_messages: list[dict[str, any]]) -> None:
    """Check if memorization threshold is reached and trigger if needed.

    Skips triggering if a previous memorization task is still running.
    """
    global RUNNING_MEMORIZATION

    if len(conversation_messages) < N_MESSAGES_MEMORIZE:
        return

    # Check if there's a running memorization task
    if RUNNING_MEMORIZATION is not None:
        if not RUNNING_MEMORIZATION.done():
            print("\n[Info] Have running memorization, skipping...")
            return
        # Previous task completed, check for exceptions
        try:
            RUNNING_MEMORIZATION.result()
        except Exception as e:
            print(f"\n[Memory] Memorization failed: {e!r}")
        RUNNING_MEMORIZATION = None

    print(f"\n[Info] Reached {N_MESSAGES_MEMORIZE} messages, triggering memorization...")
    success = await trigger_memorize(conversation_messages.copy())
    if success:
        conversation_messages.clear()


async def run_conversation_loop(client: ClaudeSDKClient) -> list[dict[str, any]]:
    """Run the main conversation loop."""
    conversation_messages: list[dict[str, any]] = []
    iteration = 0

    while True:
        user_input, should_break = await get_next_input(iteration)

        if should_break:
            break
        if user_input is None:
            continue

        conversation_messages.append({"role": "user", "content": user_input})
        await client.query(user_input)

        assistant_text_parts = await process_response(client)

        if assistant_text_parts:
            conversation_messages.append({
                "role": "assistant",
                "content": "\n".join(assistant_text_parts),
            })

        await check_and_memorize(conversation_messages)
        iteration += 1

    return conversation_messages


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"memu": memu_server},
        allowed_tools=[
            # "mcp__memu__memu_memory",
            "mcp__memu__memu_todos",
        ],
    )

    print("Claude Autorun")
    print("Type 'quit' or 'exit' to end the session.")
    print("-" * 40)

    async with ClaudeSDKClient(options=options) as client:
        remaining_messages = await run_conversation_loop(client)

    # Wait for any running memorization task to complete
    global RUNNING_MEMORIZATION
    if RUNNING_MEMORIZATION is not None and not RUNNING_MEMORIZATION.done():
        print("\n[Info] Waiting for running memorization task to complete...")
        try:
            await RUNNING_MEMORIZATION
            print("\n[Memory] Running memorization completed successfully.")
        except Exception as e:
            print(f"\n[Memory] Running memorization failed: {e!r}")
        RUNNING_MEMORIZATION = None

    # Memorize remaining messages and wait for completion
    if remaining_messages:
        print("\n[Info] Session ended, memorizing remaining messages...")
        success = await trigger_memorize(remaining_messages.copy())
        if success and RUNNING_MEMORIZATION is not None:
            print("\n[Info] Waiting for final memorization to complete...")
            try:
                await RUNNING_MEMORIZATION
                print("\n[Memory] Final memorization completed successfully.")
            except Exception as e:
                print(f"\n[Memory] Final memorization failed: {e!r}")

    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
