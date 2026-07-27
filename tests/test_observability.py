"""In-process validation of memU's OpenTelemetry instrumentation.

These tests wire the SDK with in-memory exporters/readers so every assertion is
made against *actual emitted signals* — the same spans, metrics, and log records
that would land in a collector — and checks them against memory-semconv v0.1.0.
No collector or network is involved.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from memu.app import MemoryService
from memu.observability import instruments, semconv, shutdown_telemetry
from memu.observability.telemetry import init_telemetry
from tests.test_agentic import FakeEmbeddingClient


class UsageEmbeddingClient(FakeEmbeddingClient):
    """Fake client whose raw response carries OpenAI-shaped token ``usage``."""

    def __init__(self, embed_model: str = "fake-embed") -> None:
        self.embed_model = embed_model

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], Any]:
        vectors, _ = await super().embed(inputs)
        usage = type("Usage", (), {"prompt_tokens": len(inputs), "total_tokens": len(inputs) * 3})()
        raw = type("Resp", (), {"usage": usage})()
        return vectors, raw


class Telemetry:
    """Bundle of the in-memory exporters plus a forced flush of metrics."""

    def __init__(
        self,
        spans: InMemorySpanExporter,
        reader: InMemoryMetricReader,
        logs: InMemoryLogRecordExporter,
    ) -> None:
        self.spans = spans
        self.reader = reader
        self.logs = logs

    def finished_spans(self) -> list[Any]:
        return list(self.spans.get_finished_spans())

    def span(self, name: str) -> Any:
        matches = [s for s in self.finished_spans() if s.name == name]
        assert matches, f"no span named {name!r}; saw {[s.name for s in self.finished_spans()]}"
        return matches[-1]

    def metric_points(self, name: str) -> list[Any]:
        data = self.reader.get_metrics_data()
        assert data is not None
        points: list[Any] = []
        for rm in data.resource_metrics:
            for sm in rm.scope_metrics:
                for metric in sm.metrics:
                    if metric.name == name:
                        points.extend(metric.data.data_points)
        return points

    def resource_attributes(self) -> dict[str, Any]:
        spans = self.finished_spans()
        assert spans, "no spans captured"
        return dict(spans[0].resource.attributes)

    def log_records(self) -> list[Any]:
        return [record.log_record for record in self.logs.get_finished_logs()]


@pytest.fixture
def telemetry() -> Iterator[Telemetry]:
    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    log_exporter = InMemoryLogRecordExporter()
    # set_global=False keeps every test on its own memU-owned providers (OTel
    # only allows the process globals to be set once); the instrumentation reads
    # them from memu.observability.providers regardless.
    handle = init_telemetry(
        metric_reader=metric_reader,
        log_processor=SimpleLogRecordProcessor(log_exporter),
        store_backend="inmemory",
        set_global=False,
        force=True,
    )
    # Attach a synchronous span processor so finished spans are exported inline.
    handle.tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    instruments.reset_instruments()
    yield Telemetry(span_exporter, metric_reader, log_exporter)
    handle.shutdown()


def make_service() -> MemoryService:
    service = MemoryService(database_config={"metadata_store": {"provider": "inmemory"}})
    client = UsageEmbeddingClient()
    service._embedding_pool._cache["default"] = client
    service._embedding_pool._cache["embedding"] = client
    return service


async def _seed(service: MemoryService) -> None:
    await service.commit_results(
        recall_files=[
            {"name": "Profile", "track": "memory", "description": "who the user is", "content": "# P\nlikes coffee"},
        ],
        resource=[{"path": "/workspace/notes.md", "description": "meeting notes"}],
    )


# --------------------------------------------------------------------------- #
# Resource / identity
# --------------------------------------------------------------------------- #
async def test_resource_carries_sut_identity(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    attrs = telemetry.resource_attributes()
    assert attrs[semconv.ATTR_SUT_NAME] == semconv.SUT_NAME
    assert attrs[semconv.ATTR_SUT_ARCHITECTURE] == semconv.SUT_ARCHITECTURE
    assert attrs[semconv.ATTR_SUT_STORE_BACKEND] == "inmemory"
    assert semconv.ATTR_SUT_VERSION in attrs


# --------------------------------------------------------------------------- #
# Write (commit_results)
# --------------------------------------------------------------------------- #
async def test_commit_emits_write_span_with_required_and_volume_attrs(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    span = telemetry.span(semconv.SPAN_MEMORY_WRITE)
    attrs = dict(span.attributes)
    # Required attributes (semconv §2.3).
    assert attrs[semconv.ATTR_OPERATION] == semconv.OP_WRITE
    assert attrs[semconv.ATTR_STORE_KIND] == "inmemory"
    # Data-managed surface: input size + per-tier utilization.
    assert attrs[semconv.ATTR_INPUT_SIZE_BYTES] > 0
    assert attrs[semconv.ATTR_ITEMS_FILES] == 1
    assert attrs[semconv.ATTR_ITEMS_RESOURCES] == 1
    assert attrs[semconv.ATTR_ITEMS_SEGMENTS] >= 1
    assert attrs[semconv.ATTR_EXTRACTED_FACTS_COUNT] == 2


async def test_commit_nests_embed_child_spans(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    write = telemetry.span(semconv.SPAN_MEMORY_WRITE)
    embeds = [s for s in telemetry.finished_spans() if s.name == semconv.SPAN_MEMORY_EMBED]
    assert embeds, "expected memory.embed child spans on a write"
    # Children hang off the write span (same trace, parent = write span id).
    assert any(s.parent is not None and s.parent.span_id == write.context.span_id for s in embeds)
    assert all(s.attributes[semconv.ATTR_EMBEDDER_MODEL] == "fake-embed" for s in embeds)


# --------------------------------------------------------------------------- #
# Read (progressive_retrieve) + query efficiency
# --------------------------------------------------------------------------- #
async def test_search_span_records_query_efficiency(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    telemetry.spans.clear()
    await service.progressive_retrieve("coffee")
    span = telemetry.span(semconv.SPAN_MEMORY_READ)
    attrs = dict(span.attributes)
    assert attrs[semconv.ATTR_OPERATION] == semconv.OP_SEARCH
    assert attrs[semconv.ATTR_QUERY_K] == 5
    assert attrs[semconv.ATTR_RESULTS_COUNT] >= 1
    assert 0.0 <= attrs[semconv.ATTR_TOP_SIMILARITY] <= 1.0
    # PII-safe: length present, raw text absent by default.
    assert attrs[semconv.ATTR_QUERY_LENGTH] == len("coffee")
    assert semconv.ATTR_QUERY_TEXT not in attrs


async def test_query_text_captured_only_when_opted_in(telemetry: Telemetry, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_OTEL_CAPTURE_QUERY_TEXT", "1")
    service = make_service()
    await _seed(service)
    telemetry.spans.clear()
    await service.progressive_retrieve("espresso")
    span = telemetry.span(semconv.SPAN_MEMORY_READ)
    assert span.attributes[semconv.ATTR_QUERY_TEXT] == "espresso"


# --------------------------------------------------------------------------- #
# List (list_all_recall_files)
# --------------------------------------------------------------------------- #
async def test_list_emits_read_span_with_list_operation(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    telemetry.spans.clear()
    await service.list_all_recall_files()
    span = telemetry.span(semconv.SPAN_MEMORY_READ)
    assert span.attributes[semconv.ATTR_OPERATION] == semconv.OP_LIST
    assert span.attributes[semconv.ATTR_RESULTS_COUNT] == 1


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
async def test_operation_duration_metric_labels_stay_in_budget(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    await service.progressive_retrieve("coffee")
    points = telemetry.metric_points(semconv.METRIC_OPERATION_DURATION)
    assert points, "expected duration histogram points"
    seen_ops = set()
    for point in points:
        labels = set(point.attributes)
        assert labels <= semconv.ALLOWED_METRIC_LABELS, f"out-of-budget labels: {labels}"
        assert point.attributes[semconv.METRIC_LABEL_SUT_NAME] == semconv.SUT_NAME
        seen_ops.add(point.attributes[semconv.METRIC_LABEL_OPERATION])
    assert {semconv.OP_WRITE, semconv.OP_SEARCH} <= seen_ops


async def test_recall_results_and_embed_token_metrics(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    await service.progressive_retrieve("coffee")
    recall = telemetry.metric_points(semconv.METRIC_RECALL_RESULTS_COUNT)
    assert recall and recall[-1].count >= 1
    tokens = telemetry.metric_points(semconv.METRIC_EMBED_TOKEN_TOTAL)
    assert tokens, "expected embed token counter"
    assert tokens[-1].value > 0
    assert tokens[-1].attributes[semconv.METRIC_LABEL_EMBEDDER_MODEL] == "fake-embed"


async def test_volume_gauges_report_items_and_bytes(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    items = telemetry.metric_points(semconv.METRIC_ITEMS_TOTAL)
    byte_points = telemetry.metric_points(semconv.METRIC_BYTES_TOTAL)
    assert items and items[-1].value == 2  # 1 file + 1 resource
    assert byte_points and byte_points[-1].value > 0
    for point in items + byte_points:
        assert set(point.attributes) <= semconv.ALLOWED_METRIC_LABELS
        assert point.attributes[semconv.METRIC_LABEL_STORE_KIND] == "inmemory"


# --------------------------------------------------------------------------- #
# Logs
# --------------------------------------------------------------------------- #
async def test_each_operation_emits_correlated_log(telemetry: Telemetry) -> None:
    service = make_service()
    await _seed(service)
    telemetry.spans.clear()
    telemetry.logs.clear()
    await service.progressive_retrieve("coffee")
    records = telemetry.log_records()
    assert records, "expected an OTel log record for the search op"
    search_logs = [r for r in records if r.attributes.get(semconv.ATTR_OPERATION) == semconv.OP_SEARCH]
    assert search_logs
    record = search_logs[-1]
    # Log is correlated to the read span's trace.
    assert record.trace_id not in (0, None)
    assert record.attributes[semconv.ATTR_SUT_NAME] == semconv.SUT_NAME


# --------------------------------------------------------------------------- #
# Error path
# --------------------------------------------------------------------------- #
async def test_failed_operation_marks_span_error_and_still_times(telemetry: Telemetry) -> None:
    service = make_service()
    with pytest.raises(ValueError, match="Unknown filter field"):
        await service.list_all_recall_files(where={"nope": "x"})
    span = telemetry.span(semconv.SPAN_MEMORY_READ)
    assert span.status.status_code.name == "ERROR"
    assert span.events, "expected a recorded exception event"
    # The failed op is still counted in the duration histogram.
    points = telemetry.metric_points(semconv.METRIC_OPERATION_DURATION)
    assert any(p.attributes[semconv.METRIC_LABEL_OPERATION] == semconv.OP_LIST for p in points)


# --------------------------------------------------------------------------- #
# Cardinality-budget guard
# --------------------------------------------------------------------------- #
def test_recording_rejects_out_of_budget_label() -> None:
    with pytest.raises(ValueError, match="disallowed metric label"):
        instruments._reject_bad_labels({"memory_user_id": "u1"})


def test_no_op_without_sdk_does_not_raise() -> None:
    """With no global handle the API is a no-op; recording helpers must be safe."""
    shutdown_telemetry()
    instruments.reset_instruments()
    # These would raise if they assumed an SDK/meter was present.
    instruments.record_operation_duration(semconv.OP_WRITE, "inmemory", 0.01)
    instruments.record_recall_results("inmemory", 3)
    instruments.record_embed_tokens("fake-embed", 5)
    logging.getLogger("memu.observability").info("noop check")


# --------------------------------------------------------------------------- #
# Config knobs
# --------------------------------------------------------------------------- #
def test_otel_enabled_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.observability import config

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv(config.ENV_ENABLED, "yes")
    assert config.otel_enabled() is True
    monkeypatch.setenv(config.ENV_ENABLED, "off")
    assert config.otel_enabled() is False
    # With the flag unset, presence of an OTLP endpoint enables it.
    monkeypatch.delenv(config.ENV_ENABLED, raising=False)
    assert config.otel_enabled() is False
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
    assert config.otel_enabled() is True


def test_store_backend_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.observability import config

    monkeypatch.delenv(config.ENV_STORE_BACKEND, raising=False)
    assert config.store_backend_override() is None
    monkeypatch.setenv(config.ENV_STORE_BACKEND, "pgvector")
    assert config.store_backend_override() == "pgvector"


# --------------------------------------------------------------------------- #
# Telemetry bootstrap: resource + OTLP wiring + global lifecycle
# --------------------------------------------------------------------------- #
def test_build_resource_carries_identity_and_backend() -> None:
    from memu.observability.telemetry import build_resource

    resource = build_resource({"deployment.environment": "test"}, "sqlite")
    attrs = dict(resource.attributes)
    assert attrs[semconv.ATTR_SUT_NAME] == semconv.SUT_NAME
    assert attrs[semconv.ATTR_SUT_STORE_BACKEND] == "sqlite"
    assert attrs["deployment.environment"] == "test"


def test_otlp_exporters_built_when_endpoint_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.observability import telemetry

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
    monkeypatch.delenv("MEMU_OTEL_ENABLED", raising=False)
    # Construction only — no export/connection happens here.
    assert telemetry._otlp_span_exporter() is not None
    assert telemetry._otlp_metric_reader() is not None
    assert telemetry._otlp_log_processor() is not None


def test_otlp_builders_return_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.observability import telemetry

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("MEMU_OTEL_ENABLED", "0")
    assert telemetry._otlp_span_exporter() is None
    assert telemetry._otlp_metric_reader() is None
    assert telemetry._otlp_log_processor() is None


def test_global_init_and_shutdown_lifecycle() -> None:
    from memu.observability import telemetry
    from memu.observability.telemetry import get_telemetry_handle, init_telemetry

    metric_reader = InMemoryMetricReader()
    handle = init_telemetry(
        metric_reader=metric_reader,
        log_processor=SimpleLogRecordProcessor(InMemoryLogRecordExporter()),
        set_global=True,
        force=True,
    )
    assert get_telemetry_handle() is handle
    # A second call without force returns the same handle (idempotent).
    assert init_telemetry(set_global=True) is handle
    shutdown_telemetry()
    assert get_telemetry_handle() is None
    assert telemetry is not None


# --------------------------------------------------------------------------- #
# Token extraction across provider response shapes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 0),
        (type("R", (), {"usage": type("U", (), {"total_tokens": 12, "prompt_tokens": 4})()})(), 12),
        (type("R", (), {"usage": type("U", (), {"total_tokens": 0, "prompt_tokens": 4})()})(), 4),
        ({"usage": {"total_tokens": 9}}, 9),
        ({"usage": {"prompt_tokens": 7}}, 7),
        ({"nothing": True}, 0),
    ],
)
def test_extract_tokens_handles_provider_shapes(raw: Any, expected: int) -> None:
    from memu.observability.operation import _extract_tokens

    assert _extract_tokens(raw) == expected
