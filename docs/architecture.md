# memU Architecture Overview

memU is designed as a memory infrastructure layer for AI agents and workflows.
It focuses on how memory is structured, stored, and retrieved across agent interactions.

## Scope of This Repository

This repository focuses on:
- Agent memory abstractions
- Memory lifecycle and retrieval concepts
- Workflow and orchestration logic

It intentionally does NOT include server-side implementations.

## Server-side Components

Server-side APIs and backend services are handled in a separate repository
(memU-server), which is under active development.

## How Components Fit Together

- memU: Core memory and agent infrastructure
- memU-server: Backend services and APIs
- Client / Agents: Consume memory via defined abstractions
