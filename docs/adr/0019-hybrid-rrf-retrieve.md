# ADR 0019: Hybrid retrieve on the current path — BM25 + cosine via RRF

- Status: Accepted
- Date: 2026-09-04
- Builds on: ADR 0007 (hybrid retrieval sketch), ADR 0002 (backend-specific vector search)
- Scope: local `progressive_retrieve` ranking for L2 segments and workspace
  resources. Does not change memorize, file roll-up, the wiki-graph kernel, or
  cloud retrieve.

## Context

ADR 0007 specified a single-pass hybrid: min-max-normalize cosine and BM25,
fuse, search L2, roll up to L1. The kernel in that ADR is still Proposed.
Meanwhile `progressive_retrieve` embeds the query once and ranks by cosine
only — `RecallFileSegment.text` and `Resource.caption` are stored and then
ignored at search time.

Exact tokens (error codes, hostnames, CJK terms, paths) miss when they are
not in cosine `top_k`. Inject runs this every turn.

## Decision

Fuse BM25 with cosine on the **current** retrieve path, using Reciprocal Rank
Fusion rather than ADR 0007’s unspecified min-max linear blend.

- Tokenizer: lowercase latin/digit runs; CJK/kana/hangul unigrams + bigrams.
- Fusion: `score = Σ 1/(60 + rank_i)` over the cosine ranking and the BM25
  ranking. No α.
- sqlite / inmemory / postgres resources: the scoped pool is already scanned
  in Python; BM25 scores that whole pool (they have no keyword index).
- postgres segments: pgvector still ranks cosine. Hybrid takes
  `candidate_k = max(50, 5 * top_k)` cosine hits, BM25 over scoped texts,
  unions via RRF, then cuts to `top_k`.
- File layer stays a roll-up (`max` of segment scores).
- Default on. Cosine-only via `ProgressiveRetrieveConfig.hybrid=False` or
  `MEMU_RETRIEVE_HYBRID=0`.
- Ranking stays in the repo. `vector_search_segments` /
  `vector_search_resources` take optional `query_text`.

When hybrid is on, hit `score` is the RRF value, not cosine similarity.

This **does not accept** ADR 0007’s kernel. The min-max linear sketch there
remains the formula for that future path if it lands; this ADR is the
algorithm the current code actually runs.

## Consequences

Positive:

- Exact-term recall without an LLM or a new column.
- Each backend keeps its vector strategy (Python scan vs pgvector).
- Kill switch restores the previous ranking.

Negative:

- Default-on changes inject ranking and the numeric `score` field.
- Postgres hybrid BM25 still reads scoped texts (no `tsvector` yet).
- CJK n-grams are a coarse substitute for a real word segmenter.
