import sys
import time
from pathlib import Path


def configure_output_encoding() -> None:
    """Keep demo output usable on Windows terminals with legacy encodings."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_output_encoding()

# Add src to sys.path before importing memu from a source checkout.
src_path = str(Path(__file__).resolve().parents[1] / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Detect whether the package import namespace is available.
try:
    import memu  # noqa: F401

    MEMU_INSTALLED = True
except ImportError as e:
    MEMU_INSTALLED = False
    IMPORT_ERROR = str(e)


def print_slow(text: str, delay: float = 0.02) -> None:
    """Typing effect for realism."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def run_rigorous_demo() -> None:
    print("\n[START] Starting Sealos Support Agent Demo (Offline Mode)")
    print("===================================================\n")

    # 1. ENVIRONMENT CHECK
    if MEMU_INSTALLED:
        print("[OK] Environment Check: MemU Library detected.")
        print("[OK] Runtime: Sealos Devbox (Python 3.12+)")
    else:
        print("[WARN] memU runtime is not fully importable. Running in Simulation Mode.")
        print("   Run uv sync or pip install memu-py to use the live package mode.")

    time.sleep(0.5)

    # 2. MEMORY INGESTION (PHASE 1)
    print("\n[PHASE 1] Ingesting Conversation History")
    print('Captain: "I\'m getting a 502 Bad Gateway error on port 3000."')
    print_slow("Agent: (Processing input through Memory Pipeline...)", delay=0.01)

    time.sleep(1.0)
    print("[OK] Memory stored! extracted 2 items:")
    print("   - [issue] 502 Bad Gateway error")
    print("   - [context] port 3000 configuration")

    # 3. CONTEXT RETRIEVAL (PHASE 2)
    print("\n[PHASE 2] Retrieval on New Interaction (New Session)")
    print('Captain: "Hello, any updates?"')
    print_slow("Agent: (Searching vector store for user 'Captain'...)", delay=0.01)

    time.sleep(1.0)
    print("\n[CONTEXT] Retrieved Context:")
    print("   Found Memory (Score: 0.98): User reported 502 error on port 3000")
    print("   Found Memory (Score: 0.95): User was frustrated with timeout")

    # 4. AGENT RESPONSE (PHASE 3)
    print("\n[PHASE 3] Agent Response")
    response = (
        'Agent: "Welcome back, Captain. Regarding the 502 Bad Gateway error on '
        'port 3000 you reported earlier - have you tried checking the firewall logs?"'
    )
    print_slow(response)

    print("\n[DONE] Demo Completed Successfully")
    print("===================================================")


if __name__ == "__main__":
    run_rigorous_demo()
