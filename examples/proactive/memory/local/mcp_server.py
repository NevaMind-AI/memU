import asyncio
from memu.integrations.mcp import create_mcp_server
from .common import get_memory_service


def main():
    """Main entry point for the standard MemU MCP server example."""
    print("Starting MemU Standard MCP Server...")

    # 1. Initialize the memory service
    # Note: Make sure OPENAI_API_KEY is set in your environment
    try:
        service = get_memory_service()
    except ValueError as e:
        print(f"Error initializing MemoryService: {e}")
        return

    # 2. Create the MCP server using the standardized integration
    # This automatically registers:
    # - get_memory
    # - search_memory
    # - search_items
    # - memorize
    # - list_categories
    # - create_memory_item
    # - update_memory_item
    # - delete_memory_item
    server = create_mcp_server(service, name="memu-local")

    # 3. Run the server
    # This will use the default MCP transport (stdin/stdout)
    # which is ideal for use with Claude Desktop or other MCP clients.
    print("Server initialized with all memory tools.")
    server.run()


if __name__ == "__main__":
    main()
