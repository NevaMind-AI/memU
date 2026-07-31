from importlib.metadata import PackageNotFoundError, version

from memu.app.service import MemoryService

# Public alias used in documentation examples
MemUService = MemoryService

try:
    __version__ = version("memu-cli")
except PackageNotFoundError:  # pragma: no cover - a source checkout with no installed dist
    # Guarded on purpose (ADR 0016): this value exists to fill one telemetry
    # field, and a telemetry field must never be able to break `import memu`.
    __version__ = "0+unknown"

__all__ = ["MemUService", "MemoryService", "__version__"]
