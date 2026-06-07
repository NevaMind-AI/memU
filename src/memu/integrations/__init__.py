from typing import Any

from .langgraph import MemULangGraphTools

__all__ = ["MemULangGraphTools"]


def __getattr__(name: str) -> Any:
    # Defer SDK imports so listing the package never requires fastmcp/mcp.
    if name == "build_mcp_server":
        from .mcp_server import build_server as _fastmcp_build

        return _fastmcp_build
    if name == "build_mcp_server_lowlevel":
        from .mcp_server_lowlevel import build_server as _lowlevel_build

        return _lowlevel_build
    raise AttributeError(name)
