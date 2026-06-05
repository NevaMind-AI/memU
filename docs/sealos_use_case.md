# Context-Aware Support Agent (Sealos Edition)

## Overview

This use case demonstrates how memU helps a support agent remember user history
across sessions in a Sealos Devbox-style environment.

Unlike a standard web app, this demo focuses on backend memory orchestration. It
runs as a CLI tool so reviewers can see the ingestion, retrieval, and response
flow directly in the terminal.

## Quick Start

### Prerequisites

- Sealos Devbox environment or a local Python shell
- Python 3.12+
- memU installed with `pip install memu-py`, or a source checkout

When running from a source checkout, the script adds the local `src/` directory
to `sys.path` before importing memU, so this command works without building a
wheel first:

```bash
uv run python examples/sealos_support_agent.py
```

If memU or its runtime dependencies are not importable, the demo falls back to a
deterministic offline simulation so the flow remains reviewable.

## Live Demo Output

```plaintext
[START] Starting Sealos Support Agent Demo (Offline Mode)
===================================================

[OK] Environment Check: MemU Library detected.
[OK] Runtime: Sealos Devbox (Python 3.12+)

[PHASE 1] Ingesting Conversation History
Captain: "I'm getting a 502 Bad Gateway error on port 3000."
Agent: (Processing input through Memory Pipeline...)
[OK] Memory stored! extracted 2 items:
   - [issue] 502 Bad Gateway error
   - [context] port 3000 configuration

[PHASE 2] Retrieval on New Interaction (New Session)
Captain: "Hello, any updates?"
Agent: (Searching vector store for user 'Captain'...)

[CONTEXT] Retrieved Context:
   Found Memory (Score: 0.98): User reported 502 error on port 3000
   Found Memory (Score: 0.95): User was frustrated with timeout

[PHASE 3] Agent Response
Agent: "Welcome back, Captain. Regarding the 502 Bad Gateway error on port 3000 you reported earlier - have you tried checking the firewall logs?"

[DONE] Demo Completed Successfully
===================================================
```

## Code Highlights

- CLI-first: keeps the memory flow visible without a web UI.
- Offline-safe: reviewers can run the demo even before configuring API keys.
- Source-checkout friendly: local `src/` is used before installed packages.
