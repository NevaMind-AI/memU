"""
InfraGenius + MemU Integration Example

This shows how to add MemU memory tools to an existing OpenAgents project
like InfraGenius. The agent can then remember deployment history, configs,
and learn from past operations.

To integrate with InfraGenius:
1. Copy the memory tools to infra-genius/tools/memory.py
2. Add tool configs to agents/deployer.yaml
3. The agent now has persistent memory!
"""

# ============================================================================
# STEP 1: Memory Tools for InfraGenius (copy to infra-genius/tools/memory.py)
# ============================================================================

MEMORY_TOOLS_CODE = '''
"""
MemU Memory Tools for InfraGenius

Add long-term memory to your infrastructure agent.
Remembers deployments, configs, and learns from operations.
"""

import os
from memu.app.service import MemoryService
from memu.adapters.openagents import MemUOpenAgentsAdapter

# Try to import the tool decorator
try:
    from openagents.workspace.tool_decorator import tool
except ImportError:
    def tool(func=None, *, name=None, description=None, input_schema=None):
        if func is not None:
            return func
        return lambda f: f

# Initialize MemU service (lazy, on first use)
_adapter = None

def _get_adapter():
    global _adapter
    if _adapter is None:
        service = MemoryService(
            llm_profiles={
                "default": {
                    "provider": "openai",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "chat_model": "gpt-4o-mini",
                },
                "embedding": {
                    "provider": "openai",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "embed_model": "text-embedding-3-small",
                },
            },
            database_config={
                "metadata_store": {"provider": "sqlite", "path": "infra_memory.db"},
            },
        )
        _adapter = MemUOpenAgentsAdapter(service=service)
        _adapter.initialize(agent_id="infra-genius")
    return _adapter


@tool(description="Store deployment info, configs, or learnings in long-term memory")
def remember(content: str, category: str = "deployment") -> str:
    """
    Store information in memory.

    Args:
        content: What to remember (deployment details, config, error, etc.)
        category: Category - deployment, config, error, learning

    Returns:
        Confirmation message
    """
    from memu.adapters.openagents.tools import memorize, set_memu_service

    adapter = _get_adapter()
    set_memu_service(adapter.service)

    # Add category prefix for better retrieval
    tagged_content = f"[{category.upper()}] {content}"
    return memorize(content=tagged_content, modality="text")


@tool(description="Search memory for relevant past deployments, configs, or learnings")
def recall(query: str) -> str:
    """
    Search memory for relevant information.

    Args:
        query: What to search for (e.g., "postgres deployment", "error handling")

    Returns:
        Relevant memories
    """
    from memu.adapters.openagents.tools import retrieve, set_memu_service

    adapter = _get_adapter()
    set_memu_service(adapter.service)

    return retrieve(query=query, top_k=5)


@tool(description="List recent memories")
def list_memories(limit: int = 10) -> str:
    """
    List recent memories.

    Args:
        limit: Max items to show

    Returns:
        List of memories
    """
    from memu.adapters.openagents.tools import list_memories as _list, set_memu_service

    adapter = _get_adapter()
    set_memu_service(adapter.service)

    return _list(limit=limit)
'''

# ============================================================================
# STEP 2: YAML Config Addition (add to agents/deployer.yaml)
# ============================================================================

YAML_TOOLS_CONFIG = """
    # Add these tools to the existing tools section in deployer.yaml

    - name: "remember"
      description: "Store deployment info, configs, or learnings in long-term memory"
      implementation: "tools.memory.remember"
      input_schema:
        type: object
        properties:
          content:
            type: string
            description: "What to remember"
          category:
            type: string
            description: "Category: deployment, config, error, learning"
            default: "deployment"
        required: ["content"]

    - name: "recall"
      description: "Search memory for relevant past deployments, configs, or learnings"
      implementation: "tools.memory.recall"
      input_schema:
        type: object
        properties:
          query:
            type: string
            description: "What to search for"
        required: ["query"]

    - name: "list_memories"
      description: "List recent memories"
      implementation: "tools.memory.list_memories"
      input_schema:
        type: object
        properties:
          limit:
            type: integer
            description: "Max items to show"
            default: 10
        required: []
"""

# ============================================================================
# STEP 3: Updated Agent Instruction (add to deployer.yaml instruction)
# ============================================================================

INSTRUCTION_ADDITION = """
    # Add to the instruction section:

    MEMORY CAPABILITIES:
    You have long-term memory! Use it to:
    - Remember successful deployments with `remember`
    - Recall past configs and solutions with `recall`
    - Learn from errors and remember fixes

    WORKFLOW WITH MEMORY:
    1. Before deploying, use `recall` to check for similar past deployments
    2. After successful deployment, use `remember` to store the config
    3. If errors occur, remember the error and solution for next time

    Example:
    - User: "Deploy my-app to sandbox"
    - You: First recall("my-app deployment") to check history
    - Then proceed with deployment
    - After success: remember("Deployed my-app to sandbox-1, used npm build", "deployment")
"""

# ============================================================================
# Demo: Test the integration locally
# ============================================================================


def demo():
    """Demo the MemU tools that would be added to InfraGenius."""
    import os

    print("=" * 60)
    print("InfraGenius + MemU Integration Demo")
    print("=" * 60)

    if not os.environ.get("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set. Showing code only.\n")
        print("STEP 1: Create tools/memory.py with:")
        print("-" * 40)
        print(MEMORY_TOOLS_CODE[:500] + "...")
        print("\nSTEP 2: Add to agents/deployer.yaml tools section:")
        print("-" * 40)
        print(YAML_TOOLS_CONFIG)
        print("\nSTEP 3: Update agent instruction:")
        print("-" * 40)
        print(INSTRUCTION_ADDITION)
        return

    # Actually test the tools
    from memu.adapters.openagents import MemUOpenAgentsAdapter
    from memu.adapters.openagents.tools import memorize, retrieve, set_memu_service
    from memu.app.service import MemoryService

    print("\n🔧 Initializing MemU service...")
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "chat_model": "gpt-4o-mini",
            },
            "embedding": {
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={"metadata_store": {"provider": "inmemory"}},
    )

    adapter = MemUOpenAgentsAdapter(service=service)
    adapter.initialize(agent_id="infra-genius")
    set_memu_service(service)

    print("✅ MemU initialized!\n")

    # Simulate InfraGenius remembering deployments
    print("📝 Storing deployment memories...")

    result = memorize(
        content="[DEPLOYMENT] Deployed react-app to sandbox-1. "
        "Used npm install && npm run build. Server on port 8000. "
        "URL: https://8000-sandbox-1.e2b.app"
    )
    print(f"  {result}")

    result = memorize(
        content="[CONFIG] PostgreSQL connection: host=db.example.com, port=5432, user=admin. Used for backend API."
    )
    print(f"  {result}")

    result = memorize(
        content="[ERROR] Deployment failed due to missing NODE_ENV. Fix: Set NODE_ENV=production before npm run build."
    )
    print(f"  {result}")

    # Simulate recalling
    print("\n🔍 Recalling memories...")

    result = retrieve(query="How do I deploy a React app?")
    print(f"\nQuery: 'How do I deploy a React app?'\n{result}")

    result = retrieve(query="PostgreSQL database config")
    print(f"\nQuery: 'PostgreSQL database config'\n{result}")

    result = retrieve(query="deployment errors and fixes")
    print(f"\nQuery: 'deployment errors and fixes'\n{result}")

    print("\n" + "=" * 60)
    print("✅ Integration demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
