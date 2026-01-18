import asyncio
import os
import sys
from typing import Annotated, Any, Literal, TypedDict

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    from langchain_core.messages import BaseMessage, HumanMessage
    from langchain_core.tools import BaseTool
    from langchain_openai import ChatOpenAI
    from langgraph.graph import START, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
except ImportError:
    print("Error: LangGraph or LangChain not installed. Please install with `uv sync --extra langgraph`")
    sys.exit(1)

from memu.app.service import MemoryService
from memu.integrations.langgraph import MemULangGraphTools


# Define state
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_demo_graph(tools: list[BaseTool], llm_model: ChatOpenAI) -> Any:
    """Build the LangGraph state graph for the demo."""
    llm_with_tools = llm_model.bind_tools(tools)

    def chatbot(state: State) -> dict[str, list[BaseMessage]]:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_edge(START, "chatbot")

    # Note: END is actually "__end__", we use the literal string for the Type Hint to avoid MyPy error
    def should_continue(state: State) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    graph_builder.add_conditional_edges("chatbot", should_continue)
    graph_builder.add_edge("tools", "chatbot")

    return graph_builder.compile()


async def initialize_infrastructure() -> tuple[MemoryService | None, list[BaseTool] | None]:
    """Initialize MemoryService and MemULangGraphTools."""
    print("=== MemU LangGraph Demo ===")
    try:
        service = MemoryService()
        print("✅ MemoryService initialized.")
    except Exception as e:
        print("❌ Failed to initialize context/storage. Make sure your database is running.")
        print(f"Error: {e}")
        return None, None

    adapter = MemULangGraphTools(service)
    tools = adapter.tools()
    print(f"✅ Tools loaded: {[t.name for t in tools]}")
    return service, tools


async def process_conversation(graph: Any, user_input: str) -> None:
    """Handle the main conversation flow."""
    print(f"\nUser: {user_input}")
    events = graph.stream({"messages": [HumanMessage(content=user_input)]}, stream_mode="values")

    async for event in events:
        if "messages" in event:
            last_msg = event["messages"][-1]
            if last_msg.type == "ai":
                print(f"Agent: {last_msg.content}")
                # Check for tool_calls safely
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    print(f"   (Tool Call: {last_msg.tool_calls})")
            elif last_msg.type == "tool":
                print(f"Tool Output: {last_msg.content}")


async def process_retrieval(graph: Any, search_input: str) -> None:
    """Handle the retrieval flow."""
    print(f"\nUser: {search_input}")
    events = graph.stream({"messages": [HumanMessage(content=search_input)]}, stream_mode="values")

    async for event in events:
        if "messages" in event:
            last_msg = event["messages"][-1]
            if last_msg.type == "ai":
                print(f"Agent: {last_msg.content}")


async def run_demo() -> None:
    """Main orchestration function."""
    service_and_tools = await initialize_infrastructure()
    service, tools = service_and_tools

    if not service or not tools:
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not found. Please set it to run the agent.")
        return

    llm = ChatOpenAI(model="gpt-4o")
    graph = build_demo_graph(tools, llm)

    print("\n--- Starting Conversation ---")
    await process_conversation(graph, "Hi, my name is David. Please remember that I am a software engineer.")

    print("\n--- Testing Retrieval ---")
    # Note: In a real persistent session, we would pass the conversation history.
    # Here we perform a fresh search memory call via the agent.
    await process_retrieval(graph, "Who is David?")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_demo())
