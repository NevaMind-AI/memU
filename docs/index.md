# memU Documentation

memU is a Python library for AI memory and conversation management.
It centers on `MemoryService`, workflow-based ingestion and retrieval, pluggable
storage backends, and profile-based LLM routing.

## Start here

- [Getting Started](tutorials/getting_started.md): install `memu-py` and run the
  first memory workflow.
- [Architecture](architecture.md): understand `MemoryService`, workflows,
  storage backends, LLM profiles, and the self-evolve review gate.
- [Folder Memory Compiler](folder_memory_compiler.md): compile raw files into a
  Markdown memory repository with reviewed evolution instructions.
- [SQLite Storage](sqlite.md): configure local persistent storage.

## Integrations

- [LangGraph](langgraph_integration.md): expose memU memory as LangGraph tools.
- [Grok](providers/grok.md): configure Grok provider defaults.
- [Sealos Devbox](sealos-devbox-guide.md): deploy the support-agent example.

## Design records

The [Architecture Decision Records](adr/README.md) explain why the project uses
workflow pipelines, pluggable storage, first-class user scope, Markdown-backed
context harnesses, and reviewed self-evolution patches.
