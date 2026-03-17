from typing import Any


def __getattr__(name: str) -> Any:
    if name == "MemULangGraphTools":
        from .langgraph import MemULangGraphTools

        return MemULangGraphTools
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["MemULangGraphTools"]
