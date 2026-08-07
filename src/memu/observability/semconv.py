"""memory-semconv v0.1.0 — the naming contract for memU's OpenTelemetry signals.

Every span name, attribute key, and metric name memU emits lives here so the
convention is defined in exactly one place. The values track the ``memory.*``
namespace defined in the benchmark program's *OTel Contribution Roadmap* §2
(ISI-1068), published as ``memory-semconv v0.1.0``.

Two rules from the spec are baked into these names and enforced by their use:

* **Metric names use ``_`` (Prometheus-native); span attribute keys use ``.``
  (OTel convention).** The two families never mix.
* **Cardinality discipline.** The only labels allowed on metrics are
  :data:`METRIC_LABEL_OPERATION`, :data:`METRIC_LABEL_STORE_KIND`,
  :data:`METRIC_LABEL_SUT_NAME`, and :data:`METRIC_LABEL_EMBEDDER_MODEL`.
  High-cardinality context (tenant, query text) is a span attribute only —
  see :data:`ATTR_QUERY_TEXT` and its opt-in gate.
"""

from __future__ import annotations

from typing import Final

SEMCONV_VERSION: Final = "0.1.0"
"""The memory-semconv version these names implement."""

# --- Solution-under-test identity (memU) ------------------------------------
# Resource attributes, set once per process by ``init_telemetry`` — never on a
# per-span basis (§2.3 "Resource attributes").
SUT_NAME: Final = "memu"
SUT_ARCHITECTURE: Final = "vector"

ATTR_SUT_NAME: Final = "memory.sut.name"
ATTR_SUT_VERSION: Final = "memory.sut.version"
ATTR_SUT_ARCHITECTURE: Final = "memory.sut.architecture"
ATTR_SUT_STORE_BACKEND: Final = "memory.sut.store_backend"

# --- Span names (one per memory operation, §2.3) ----------------------------
SPAN_MEMORY_WRITE: Final = "memory.write"
SPAN_MEMORY_READ: Final = "memory.read"
SPAN_MEMORY_EMBED: Final = "memory.embed"

# --- ``memory.operation`` values (low-cardinality; also the metric label) ---
# memU's public surface is add/search/update/delete/list. ``commit_results``
# folds add/update/delete into one write path (distinguished by the write.*
# span attributes below); ``progressive_retrieve`` is a search; and
# ``list_all_recall_files`` is a list.
OP_WRITE: Final = "write"
OP_SEARCH: Final = "search"
OP_LIST: Final = "list"
OP_EMBED: Final = "embed"

# --- Span attribute keys ----------------------------------------------------
ATTR_OPERATION: Final = "memory.operation"
ATTR_STORE_KIND: Final = "memory.store.kind"
ATTR_QUERY_K: Final = "memory.query.k"
ATTR_TENANT: Final = "memory.tenant"
ATTR_RESULTS_COUNT: Final = "memory.results.count"
ATTR_TOP_SIMILARITY: Final = "memory.top_similarity"
ATTR_INPUT_SIZE_BYTES: Final = "memory.input.size_bytes"
ATTR_EXTRACTED_FACTS_COUNT: Final = "memory.extracted.facts_count"
ATTR_EMBEDDER_MODEL: Final = "memory.embedder.model"
ATTR_EMBED_TOKEN_COUNT: Final = "memory.embed.token_count"

# Query introspection. §2.4 forbids ``memory.query.text`` anywhere by default
# (PII risk), so we emit a PII-safe length proxy always and gate the raw text
# behind an explicit opt-in (see ``observability.config``). The text lands only
# when a benchmark operator turns it on *and* accepts collector-side scrubbing.
ATTR_QUERY_LENGTH: Final = "memory.query.length"
ATTR_QUERY_TEXT: Final = "memory.query.text"

# memU-specific per-tier detail. Kept as span attributes (not metric labels) so
# the aggregate volume gauges stay within the spec's label budget while traces
# still expose per-tier utilization (files / segments-as-vectors / resources).
ATTR_ITEMS_FILES: Final = "memory.items.files"
ATTR_ITEMS_SEGMENTS: Final = "memory.items.segments"
ATTR_ITEMS_RESOURCES: Final = "memory.items.resources"
# ``commit_results`` create-or-update bookkeeping — how a write decomposed into
# add vs update vs delete, per the issue's "distinguish via span attributes".
ATTR_WRITE_FILES_CREATED: Final = "memory.write.files_created"
ATTR_WRITE_FILES_UPDATED: Final = "memory.write.files_updated"
ATTR_WRITE_RESOURCES_CREATED: Final = "memory.write.resources_created"
ATTR_WRITE_RESOURCES_DELETED: Final = "memory.write.resources_deleted"

# --- Metric names (Prometheus-native ``_``) ---------------------------------
METRIC_OPERATION_DURATION: Final = "memory_operation_duration_seconds"
METRIC_RECALL_RESULTS_COUNT: Final = "memory_recall_results_count"
METRIC_ITEMS_TOTAL: Final = "memory_items_total"
METRIC_BYTES_TOTAL: Final = "memory_bytes_total"
METRIC_EMBED_TOKEN_TOTAL: Final = "memory_embed_token_total"

# --- Metric label keys (the entire allowed set, §2.1 rule 4) ----------------
METRIC_LABEL_OPERATION: Final = "memory_operation"
METRIC_LABEL_STORE_KIND: Final = "memory_store_kind"
METRIC_LABEL_SUT_NAME: Final = "memory_sut_name"
METRIC_LABEL_EMBEDDER_MODEL: Final = "memory_embedder_model"

# The only labels a metric is ever allowed to carry. Used by tests and by the
# recording helpers to fail loudly if an out-of-budget label sneaks in.
ALLOWED_METRIC_LABELS: Final = frozenset({
    METRIC_LABEL_OPERATION,
    METRIC_LABEL_STORE_KIND,
    METRIC_LABEL_SUT_NAME,
    METRIC_LABEL_EMBEDDER_MODEL,
})

__all__ = [name for name in dir() if name.isupper()]
