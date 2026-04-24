from memu._core import hello_from_bin
from memu.app.service import MemoryService

# Public alias used in documentation examples
MemUService = MemoryService


def _rust_entry() -> str:
    return hello_from_bin()
