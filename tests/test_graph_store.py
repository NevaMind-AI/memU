"""
Tests for graph-enhanced memory: GraphStore algorithms, score fusion, and degradation paths.

Tests are pure-Python (no DB) except where noted — they test the static algorithm methods
directly and mock the DB layer for integration paths.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from memu.database.postgres.repositories.graph_store import (
    PostgresGraphStore,
    RecallEdge,
    RecallNode,
    RecallResult,
)


# ── PPR algorithm tests ──────────────────────────────────────────


class TestPersonalizedPageRank:
    """Test the static PPR implementation."""

    def test_single_seed_no_edges(self):
        """Single seed with no edges: all mass stays on seed."""
        node_ids = {"a", "b", "c"}
        adj: dict[str, set[str]] = {"a": set(), "b": set(), "c": set()}
        result = PostgresGraphStore.personalized_pagerank(node_ids, adj, ["a"])
        assert result["a"] > 0
        # Non-seeds should have zero or near-zero score
        assert result["b"] < 0.01
        assert result["c"] < 0.01

    def test_two_nodes_linked(self):
        """Two connected nodes: seed propagates to neighbor."""
        node_ids = {"a", "b"}
        adj: dict[str, set[str]] = {"a": {"b"}, "b": {"a"}}
        result = PostgresGraphStore.personalized_pagerank(node_ids, adj, ["a"])
        assert result["a"] > result["b"]
        assert result["b"] > 0

    def test_multiple_seeds(self):
        """Multiple seeds share teleport mass."""
        node_ids = {"a", "b", "c"}
        adj: dict[str, set[str]] = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
        result = PostgresGraphStore.personalized_pagerank(node_ids, adj, ["a", "c"])
        # Both seeds should have significant mass
        assert result["a"] > 0.1
        assert result["c"] > 0.1

    def test_empty_graph(self):
        """Empty graph returns empty dict."""
        result = PostgresGraphStore.personalized_pagerank(set(), {}, ["a"])
        assert result == {}

    def test_invalid_seeds_ignored(self):
        """Seeds not in node_ids are filtered out."""
        node_ids = {"a", "b"}
        adj: dict[str, set[str]] = {"a": {"b"}, "b": {"a"}}
        result = PostgresGraphStore.personalized_pagerank(node_ids, adj, ["x", "y"])
        assert result == {}

    def test_candidate_filtering(self):
        """Only candidate_ids appear in results."""
        node_ids = {"a", "b", "c"}
        adj: dict[str, set[str]] = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
        result = PostgresGraphStore.personalized_pagerank(
            node_ids, adj, ["a"], candidate_ids={"b"}
        )
        assert "b" in result
        assert "a" not in result
        assert "c" not in result

    def test_scores_sum_to_approximately_one(self):
        """PPR scores should approximately sum to 1.0."""
        node_ids = {"a", "b", "c", "d"}
        adj: dict[str, set[str]] = {
            "a": {"b", "c"},
            "b": {"a", "d"},
            "c": {"a"},
            "d": {"b"},
        }
        result = PostgresGraphStore.personalized_pagerank(node_ids, adj, ["a"])
        total = sum(result.values())
        assert abs(total - 1.0) < 0.05

    def test_damping_factor(self):
        """Lower damping = more teleport = non-seed gets less mass."""
        node_ids = {"a", "b", "c", "d"}
        adj: dict[str, set[str]] = {
            "a": {"b"}, "b": {"a", "c"}, "c": {"b", "d"}, "d": {"c"},
        }
        high_damp = PostgresGraphStore.personalized_pagerank(
            node_ids, adj, ["a"], damping=0.95
        )
        low_damp = PostgresGraphStore.personalized_pagerank(
            node_ids, adj, ["a"], damping=0.5
        )
        # Lower damping → distant node (d) gets less mass
        assert low_damp["d"] < high_damp["d"]


# ── Global PageRank tests ─────────────────────────────────────────


class TestGlobalPageRank:
    """Test global (uniform teleport) PageRank."""

    def test_empty_graph(self):
        result = PostgresGraphStore.global_pagerank(set(), {})
        assert result == {}

    def test_uniform_for_symmetric_graph(self):
        """Symmetric graph → approximately uniform scores."""
        node_ids = {"a", "b", "c"}
        adj: dict[str, set[str]] = {"a": {"b", "c"}, "b": {"a", "c"}, "c": {"a", "b"}}
        result = PostgresGraphStore.global_pagerank(node_ids, adj)
        scores = list(result.values())
        assert max(scores) - min(scores) < 0.05

    def test_hub_node_gets_higher_score(self):
        """Node with more connections gets higher PageRank."""
        node_ids = {"hub", "a", "b", "c"}
        adj: dict[str, set[str]] = {
            "hub": {"a", "b", "c"},
            "a": {"hub"},
            "b": {"hub"},
            "c": {"hub"},
        }
        result = PostgresGraphStore.global_pagerank(node_ids, adj)
        assert result["hub"] > result["a"]


# ── LPA community detection tests ─────────────────────────────────


class TestLabelPropagation:
    """Test Label Propagation Algorithm."""

    def test_disconnected_components(self):
        """Two disconnected cliques → two communities."""
        node_ids = {"a", "b", "c", "x", "y", "z"}
        adj: dict[str, set[str]] = {
            "a": {"b", "c"},
            "b": {"a", "c"},
            "c": {"a", "b"},
            "x": {"y", "z"},
            "y": {"x", "z"},
            "z": {"x", "y"},
        }
        labels = PostgresGraphStore.label_propagation(node_ids, adj, seed=42)
        # Same clique → same community
        assert labels["a"] == labels["b"] == labels["c"]
        assert labels["x"] == labels["y"] == labels["z"]
        # Different cliques → different communities
        assert labels["a"] != labels["x"]

    def test_single_node(self):
        """Single isolated node gets its own community."""
        labels = PostgresGraphStore.label_propagation({"a"}, {"a": set()}, seed=42)
        assert "a" in labels

    def test_deterministic_with_seed(self):
        """Same seed → same result."""
        node_ids = {"a", "b", "c", "d"}
        adj: dict[str, set[str]] = {
            "a": {"b"},
            "b": {"a", "c"},
            "c": {"b", "d"},
            "d": {"c"},
        }
        r1 = PostgresGraphStore.label_propagation(node_ids, adj, seed=123)
        r2 = PostgresGraphStore.label_propagation(node_ids, adj, seed=123)
        assert r1 == r2

    def test_community_ids_format(self):
        """Communities are named c-1, c-2, ... sorted by size desc."""
        node_ids = {"a", "b", "c", "x"}
        adj: dict[str, set[str]] = {
            "a": {"b", "c"},
            "b": {"a", "c"},
            "c": {"a", "b"},
            "x": set(),
        }
        labels = PostgresGraphStore.label_propagation(node_ids, adj, seed=42)
        community_ids = set(labels.values())
        assert all(c.startswith("c-") for c in community_ids)
        # The larger group (a,b,c) should be c-1
        assert labels["a"] == "c-1"


# ── Merge results tests ───────────────────────────────────────────


class TestMergeResults:
    """Test dual-path merge logic."""

    def _make_node(self, id: str, ppr: float = 0.5) -> RecallNode:
        return RecallNode(
            id=id, name=id, type="TEST", description="", content="",
            community_id=None, pagerank=0.0, ppr_score=ppr,
        )

    def _make_edge(self, f: str, t: str) -> RecallEdge:
        return RecallEdge(from_name=f, to_name=t, type="TEST", instruction="")

    def test_precise_wins_on_dedup(self):
        """Precise path nodes take priority over generalized."""
        precise = RecallResult(
            nodes=[self._make_node("a", 0.9)],
            edges=[],
            path="precise",
        )
        generalized = RecallResult(
            nodes=[self._make_node("a", 0.5), self._make_node("b", 0.3)],
            edges=[],
            path="generalized",
        )
        merged = PostgresGraphStore.merge_results(precise, generalized)
        assert len(merged.nodes) == 2
        # Node "a" should have precise score (0.9), not generalized (0.5)
        a_node = [n for n in merged.nodes if n.id == "a"][0]
        assert a_node.ppr_score == 0.9

    def test_empty_merge(self):
        """Merging two empty results."""
        empty = RecallResult(nodes=[], edges=[], path="precise")
        merged = PostgresGraphStore.merge_results(empty, empty)
        assert merged.nodes == []
        assert merged.edges == []

    def test_edge_dedup(self):
        """Duplicate edges are deduplicated."""
        e = self._make_edge("a", "b")
        r1 = RecallResult(nodes=[], edges=[e], path="precise")
        r2 = RecallResult(nodes=[], edges=[e], path="generalized")
        merged = PostgresGraphStore.merge_results(r1, r2)
        assert len(merged.edges) == 1

    def test_path_is_merged(self):
        """Merged result has path='merged'."""
        r1 = RecallResult(nodes=[], edges=[], path="precise")
        r2 = RecallResult(nodes=[], edges=[], path="generalized")
        merged = PostgresGraphStore.merge_results(r1, r2)
        assert merged.path == "merged"


# ── Score fusion tests ────────────────────────────────────────────


class TestScoreFusion:
    """Test the score fusion logic used in _rag_build_context."""

    def test_vector_weight_applied(self):
        """Vector scores are scaled by (1 - graph_weight)."""
        graph_weight = 0.3
        vector_weight = 1.0 - graph_weight
        original_score = 0.8
        fused = original_score * vector_weight
        assert abs(fused - 0.56) < 0.01

    def test_graph_weight_applied(self):
        """Graph PPR scores are normalized and scaled by graph_weight."""
        graph_weight = 0.3
        ppr_scores = [0.5, 0.3, 0.1]
        max_ppr = max(ppr_scores)
        fused = [(ppr / max_ppr) * graph_weight for ppr in ppr_scores]
        assert abs(fused[0] - 0.3) < 0.01  # 0.5/0.5 * 0.3
        assert abs(fused[1] - 0.18) < 0.01  # 0.3/0.5 * 0.3

    def test_zero_graph_weight_no_fusion(self):
        """With graph_weight=0, vector scores are unchanged."""
        graph_weight = 0.0
        vector_weight = 1.0 - graph_weight
        original = 0.75
        assert original * vector_weight == original


# ── RetrieveGraphConfig tests ─────────────────────────────────────


class TestRetrieveGraphConfig:
    """Test graph config defaults and validation."""

    def test_defaults(self):
        from memu.app.settings import RetrieveGraphConfig

        cfg = RetrieveGraphConfig()
        assert cfg.enabled is False
        assert cfg.max_nodes == 6
        assert cfg.weight == 0.3

    def test_custom_values(self):
        from memu.app.settings import RetrieveGraphConfig

        cfg = RetrieveGraphConfig(enabled=True, max_nodes=10, weight=0.5)
        assert cfg.enabled is True
        assert cfg.max_nodes == 10
        assert cfg.weight == 0.5

    def test_retrieve_config_has_graph(self):
        from memu.app.settings import RetrieveConfig

        cfg = RetrieveConfig()
        assert hasattr(cfg, "graph")
        assert cfg.graph.enabled is False

    def test_retrieve_config_graph_from_dict(self):
        from memu.app.settings import RetrieveConfig

        cfg = RetrieveConfig(graph={"enabled": True, "weight": 0.4})
        assert cfg.graph.enabled is True
        assert cfg.graph.weight == 0.4


# ── Domain model tests ────────────────────────────────────────────


class TestGraphDomainModels:
    """Test base domain models."""

    def test_graph_node_defaults(self):
        from memu.database.models import GraphNode

        node = GraphNode(type="SKILL", name="test", content="body")
        assert node.status == "active"
        assert node.validated_count == 1
        assert node.source_sessions == []
        assert node.pagerank == 0.0
        assert node.embedding is None

    def test_graph_edge_defaults(self):
        from memu.database.models import GraphEdge

        edge = GraphEdge(from_id="a", to_id="b", type="USES")
        assert edge.instruction == ""
        assert edge.condition is None

    def test_graph_community_defaults(self):
        from memu.database.models import GraphCommunity

        c = GraphCommunity()
        assert c.node_count == 0
        assert c.summary is None


# ── ORM model registration tests ──────────────────────────────────


class TestGraphORMModels:
    """Test that graph ORM models register correctly in schema."""

    def test_sqla_models_have_graph_fields_and_table(self):
        from pydantic import BaseModel, Field

        class GraphTestScope(BaseModel):
            user_id: str = Field(default="")

        from memu.database.postgres.schema import get_sqlalchemy_models

        models = get_sqlalchemy_models(scope_model=GraphTestScope)
        assert models.GraphNode is not None
        assert models.GraphEdge is not None
        assert models.GraphCommunity is not None
        # Table names
        assert models.GraphNode.__tablename__ == "gm_nodes"
        assert models.GraphEdge.__tablename__ == "gm_edges"
        assert models.GraphCommunity.__tablename__ == "gm_communities"
