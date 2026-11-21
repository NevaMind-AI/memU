"""Compare resource planning and complete SQLite commits against a Git revision.

Run from the checkout with ``uv run python benchmarks/benchmark_resource_planning.py``.
Use ``--baseline-ref <commit> --batch-sizes 1 10 50 1000`` for a different baseline
or bulk workload. Standard memorize resource discovery defaults to a 50-resource cap.

All records are synthetic, SQLite files live in a temporary directory, and
embeddings are deterministic local substitutes. Timings exclude setup and two
warm-up rounds, and report six measured rounds by default. The planning
measurement excludes database I/O; complete commits include SQLite I/O, both
planning passes, and writes, but no real embedding service or network latency.
The selected baseline's planner is executed as trusted local benchmark code.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import statistics
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType
from typing import Any, cast

from sqlalchemy import insert

from memu.app import MemoryService, agentic
from memu.app.agentic import _EmbeddingBatch, _ResourcePlan
from memu.database.sqlite.sqlite import SQLiteStore

Planner = Callable[..., list[_ResourcePlan]]
SCOPE = {"user_id": "synthetic-user", "agent_id": "synthetic-agent"}
SEED_TIME = datetime(2020, 1, 1, tzinfo=UTC)


class LocalEmbedding:
    async def embed(self, texts: list[str]) -> tuple[list[list[float]], None]:
        return [[float(len(text)), 1.0] for text in texts], None


def baseline_planner(revision: str) -> Planner:
    repository = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(  # noqa: S603
        ["git", "show", f"{revision}:src/memu/app/agentic.py"],  # noqa: S607
        cwd=repository,
        text=True,
    )
    mixin = next(
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == "AgenticMixin"
    )
    method = next(node for node in mixin.body if isinstance(node, ast.FunctionDef) and node.name == "_plan_resources")
    namespace = dict(vars(agentic))
    # Only the requested historical planner is loaded; imports and module code do not run.
    exec(  # noqa: S102
        compile(ast.Module(body=[method], type_ignores=[]), str(repository / "src/memu/app/agentic.py"), "exec"),
        namespace,
    )
    return cast(Planner, namespace[method.name])


def seed_records(count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"resource-{index:06d}",
            "url": f"/synthetic/file-{index}.md",
            "local_path": f"/synthetic/file-{index}.md",
            "caption": "seed caption",
            "embedding": [1.0, 1.0],
            "track": "workspace",
            "created_at": SEED_TIME,
            "updated_at": SEED_TIME,
            **SCOPE,
        }
        for index in range(count)
    ]


def make_service(records: list[dict[str, Any]], path: Path | None = None) -> MemoryService:
    metadata: dict[str, Any] = {"provider": "inmemory"}
    if path is not None:
        metadata = {"provider": "sqlite", "dsn": f"sqlite:///{path}"}
    service = MemoryService(database_config={"metadata_store": metadata})
    service._embedding_pool._cache["embedding"] = LocalEmbedding()
    store = service.database
    if isinstance(store, SQLiteStore):
        with store._sessions.engine.begin() as connection:
            connection.execute(insert(store._sqla_models.Resource), records)
    else:
        model = store.resource_repo.resource_model  # type: ignore[attr-defined]
        store.resources.update({record["id"]: model(**record) for record in records})
    return service


def payload(count: int, round_index: int) -> list[dict[str, Any]]:
    return [
        {"path": f"/synthetic/file-{index}.md", "description": f"caption {round_index % 2}"} for index in range(count)
    ]


def resource_state(service: MemoryService) -> dict[str, dict[str, Any]]:
    return {
        resource_id: resource.model_dump(exclude={"updated_at"})
        for resource_id, resource in service.database.resource_repo.list_resources(SCOPE).items()
    }


async def measure(records: list[dict[str, Any]], count: int, baseline: Planner, trials: int) -> dict[str, Any]:
    planners: dict[str, Planner] = {"baseline": baseline, "current": agentic.AgenticMixin._plan_resources}
    planning: dict[str, list[float]] = {mode: [] for mode in planners}
    commits: dict[str, list[float]] = {mode: [] for mode in planners}
    planning_service = make_service(records)
    with tempfile.TemporaryDirectory(prefix="memu-resource-benchmark-") as directory:
        services = {mode: make_service(records, Path(directory) / f"{mode}.sqlite3") for mode in planners}
        for mode, service in services.items():
            service.__dict__["_plan_resources"] = MethodType(planners[mode], service)
        try:
            for round_index in range(trials + 2):
                items = payload(count, round_index)
                modes = list(planners) if round_index % 2 == 0 else list(reversed(planners))
                plans: dict[str, tuple[list[_ResourcePlan], list[str]]] = {}
                responses: dict[str, list[dict[str, Any]]] = {}
                for mode in modes:
                    batch = _EmbeddingBatch()
                    started = time.perf_counter()
                    result = planners[mode](
                        planning_service, items, store=planning_service.database, user_scope=SCOPE, batch=batch
                    )
                    planning_ms = (time.perf_counter() - started) * 1000
                    plans[mode] = result, batch._texts
                    started = time.perf_counter()
                    committed = await services[mode].commit_results(resource=items, user=SCOPE)
                    commit_ms = (time.perf_counter() - started) * 1000
                    responses[mode] = [
                        {key: value for key, value in resource.items() if key != "updated_at"}
                        for resource in committed["resources"]
                    ]
                    if round_index >= 2:
                        planning[mode].append(planning_ms)
                        commits[mode].append(commit_ms)
                if plans["baseline"] != plans["current"] or responses["baseline"] != responses["current"]:
                    message = "Baseline and current plans, embedding requests, or commit results differ"
                    raise RuntimeError(message)
            if resource_state(services["baseline"]) != resource_state(services["current"]):
                message = "Baseline and current final resource states differ"
                raise RuntimeError(message)
        finally:
            planning_service.database.close()
            for service in services.values():
                service.database.close()
    return {
        "existing_resources": len(records),
        "submitted_urls": count,
        "measured_rounds": trials,
        "planning_median_ms": {mode: round(statistics.median(samples), 3) for mode, samples in planning.items()},
        "sqlite_commit_median_ms": {mode: round(statistics.median(samples), 3) for mode, samples in commits.items()},
        "equivalent_plans_embedding_requests_results_and_final_state": True,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-ref", default="d3c61df", help="Trusted Git revision containing the baseline planner"
    )
    parser.add_argument("--existing", type=int, default=5000)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 10, 50])
    parser.add_argument("--trials", type=int, default=6)
    args = parser.parse_args()
    if args.existing < 1 or args.trials < 1 or any(size < 1 or size > args.existing for size in args.batch_sizes):
        parser.error("existing/trials must be positive; each batch size must be between 1 and existing")
    with tempfile.TemporaryDirectory(prefix="memu-offline-config-") as directory:
        os.environ.update(
            MEMU_CONFIG_ENV=str(Path(directory) / "unused.env"), MEMU_EVENTS_BASE_URL="", MEMU_TEMPLATE_BASE_URL=""
        )
        baseline = baseline_planner(args.baseline_ref)
        records = seed_records(args.existing)
        print(json.dumps({"baseline_ref": args.baseline_ref, "synthetic_data": True, "real_embedding_network": False}))
        for count in args.batch_sizes:
            print(json.dumps(await measure(records, count, baseline, args.trials)), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
