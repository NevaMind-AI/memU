# ADR 0005: Extract Embedding into a Dedicated Package, Fully Decoupled from Chat Clients

- Status: Accepted
- Date: 2026-06-24

## Context

Embedding (vectorization) was coupled into the text/chat LLM clients: `embed()`
lived on `OpenAIClient`, `HTTPLLMClient` (which carried its own inline
`_EmbeddingBackend` classes), `AnthropicClient` (raising), and `LazyLLMClient`.
The service routed vectorization through an LLM profile (`_get_step_embedding_client`
returned a chat client), and some retrieval paths reused a single client for both
chat and `embed()`.

This had several problems:

- embedding providers were limited to whatever the chat client happened to
  support, so embedding-only providers (Jina, Voyage) had no clean home;
- embedding payload/parse logic was duplicated (an orphaned `memu.embedding`
  module plus the inline backends inside `HTTPLLMClient`);
- the `vision` capability already had a clean sibling package (`memu.vlm`, see the
  LLM/VLM gateway refactor), so embedding was the odd one out;
- mixing chat and embedding on one client blurred capability boundaries and made
  per-capability provider/transport selection impossible.

ADR 0004 deliberately deferred this as an isolated, independently revertable step
("Decouple embedding").

## Decision

Make embedding a first-class capability in its own package, `memu.embedding`,
structured identically to `memu.llm` and `memu.vlm`, and remove embedding from the
chat clients entirely.

Package layout (`memu.embedding`):

- `backends/`: per-provider request/response shapes — `openai`, `jina`, `voyage`,
  `doubao` (incl. multimodal), `openrouter`; the HTTP client falls back to an
  OpenAI-compatible backend for any other provider.
- `http_client` / `openai_sdk`: transport clients; `embed()` returns
  `(vectors, raw_response)` so usage metadata is preserved.
- `gateway.build_embedding_client(cfg)`: dispatch on `client_backend`
  (`sdk` / `httpx` / `lazyllm_backend`; `anthropic` raises — Claude has no
  embeddings API).
- `defaults`: per-provider default models and embedding-only endpoints.

Configuration and wiring:

- New `EmbeddingConfig` / `EmbeddingProfilesConfig`, sibling to `LLMConfig` /
  `VLMConfig`. `MemoryService` accepts an optional `embedding_profiles`; when
  omitted, profiles are derived from the LLM profiles via
  `embedding_config_from_llm`, so existing configs keep working.
- `MemoryService` builds/caches embedding clients per profile and wraps them with
  the same `LLMClientWrapper`, so interceptors and usage tracking are identical to
  chat/vision.
- All vectorization call sites (query embedding, category/item embedding, RAG
  ranking) go through `_get_step_embedding_client` / `_get_embedding_client`.

Decoupling the chat clients:

- `OpenAIClient`, `HTTPLLMClient`, and `AnthropicClient` no longer expose
  `embed()`; `HTTPLLMClient` no longer carries inline embedding backends.
- `LazyLLMClient` keeps `embed()` because it is a multi-capability framework
  adapter and serves as the embedding transport for `lazyllm_backend`.
- `LLMConfig.embed_model` / `embed_batch_size` are retained **only** as a
  backward-compat bridge consumed by `embedding_config_from_llm`; they no longer
  affect chat clients. New configs should set `embedding_profiles` directly.

## Consequences

Positive:

- clear capability boundaries: `memu.llm` (text), `memu.vlm` (vision),
  `memu.embedding` (vectors) are isomorphic and independent;
- embedding-only providers (Jina, Voyage) are first-class; new providers are a
  single backend module plus a registry entry;
- no duplicated embedding logic; one source of truth;
- per-capability provider/transport selection (e.g. chat via OpenAI, embed via
  Voyage) with zero-config derivation as the default.

Negative:

- `LLMConfig` still carries `embed_model` / `embed_batch_size` as a bridge, so the
  decoupling is not yet "pure" at the config layer (kept for backward
  compatibility);
- an explicit `embedding_profiles` is required to use an embedding provider that
  differs from the chat provider;
- one more package/gateway to maintain in parity with `llm`/`vlm`.
