![MemU Banner](assets/banner.png)

<div align="center">

# MemU

### A Future-Oriented Agentic Memory System

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

</div>

---

MemU is an agentic memory framework for LLM and AI agent backends. It receives **multimodal inputs** (conversations, documents, images), extracts them into structured memory, and organizes them into a **hierarchical file system** that supports both **embedding-based (RAG)** and **non-embedding (LLM)** retrieval.

---

MemU is collaborating with four open-source projects to launch the 2026 New Year Challenge. 🎉Between January 8–18, contributors can submit PRs to memU and earn cash rewards, community recognition, and platform credits. 🎁Join the community here: https://discord.gg/KaWy6SBAsx

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🗂️ **Hierarchical File System** | Three-layer architecture: Resource → Item → Category with full traceability |
| 🔍 **Dual Retrieval Methods** | RAG (embedding-based) for speed, LLM (non-embedding) for deep semantic understanding |
| 🎨 **Multimodal Support** | Process conversations, documents, images, audio, and video |
| 🔄 **Self-Evolving Memory** | Memory structure adapts and improves based on usage patterns |

---

## 🗂️ Hierarchical File System

MemU organizes memory using a **three-layer architecture** inspired by hierarchical storage systems:

<img width="100%" alt="structure" src="assets/structure.png" />

| Layer | Description | Examples |
|-------|-------------|----------|
| **Resource** | Raw multimodal data warehouse | JSON conversations, text documents, images, videos |
| **Item** | Discrete extracted memory units | Individual preferences, skills, opinions, habits |
| **Category** | Aggregated textual memory with summaries | `preferences.md`, `work_life.md`, `relationships.md` |

**Key Benefits:**
- **Full Traceability**: Track from raw data → items → categories and back
- **Progressive Summarization**: Each layer provides increasingly abstracted views
- **Flexible Organization**: Categories evolve based on content patterns

---

## 🎨 Multimodal Support

MemU processes diverse content types into unified memory:

| Modality | Input | Processing |
|----------|-------|------------|
| `conversation` | JSON chat logs | Extract preferences, opinions, habits, relationships |
| `document` | Text files (.txt, .md) | Extract knowledge, skills, facts |
| `image` | PNG, JPG, etc. | Vision model extracts visual concepts and descriptions |
| `video` | Video files | Frame extraction + vision analysis |
| `audio` | Audio files | Transcription + text processing |

All modalities are unified into the same three-layer hierarchy, enabling cross-modal retrieval.

---

## 🚀 Quick Start

### Option 1: Cloud Version

Try MemU instantly without any setup:

👉 **[memu.so](https://memu.so)** - Hosted cloud service with full API access

For enterprise deployment and custom solutions, contact **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer YOUR_API_KEY` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Register a memorization task |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Get task status |
| `POST` | `/api/v3/memory/categories` | List memory categories |
| `POST` | `/api/v3/memory/retrieve` | Retrieve memories (semantic search) |

📚 **[Full API Documentation](https://memu.pro/docs#cloud-version)**

---

### Option 2: Self-Hosted
