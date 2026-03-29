"""Graph-enhanced memory storage and retrieval.

Provides GraphStore repository for managing knowledge graph nodes, edges,
and communities, plus dual-path graph recall (precise + generalized) with
Personalized PageRank scoring.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.state import DatabaseState


@dataclass
class RecallNode:
    id: str
    name: str
    type: str
    description: str
    content: str
    community_id: str | None
    pagerank: float
    ppr_score: float


@dataclass
class RecallEdge:
    from_name: str
    to_name: str
    type: str
    instruction: str


@dataclass
class RecallResult:
    nodes: list[RecallNode]
    edges: list[RecallEdge]
    path: str  # "precise" | "generalized" | "merged" | "empty"


class PostgresGraphStore(PostgresRepoBase):
    """Repository for graph nodes, edges, and communities.

    Handles CRUD + dual-path graph recall with PPR scoring.
    """

    def __init__(
        self,
        *,
        state: DatabaseState,
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool = True,
    ) -> None:
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            scope_fields=scope_fields,
            use_vector=use_vector,
        )

    # ── Node CRUD ──────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Any | None:
        from sqlmodel import select

        model = self._sqla_models.GraphNode
        with self._sessions.session() as session:
            return session.scalar(select(model).where(model.id == node_id))

    def list_nodes(self, where: Mapping[str, Any] | None = None) -> list[Any]:
        from sqlmodel import select

        model = self._sqla_models.GraphNode
        filters = self._build_filters(model, where)
        with self._sessions.session() as session:
            return list(session.scalars(select(model).where(*filters)).all())

    def create_node(self, **kwargs: Any) -> Any:
        model = self._sqla_models.GraphNode
        now = self._now()
        obj = model(created_at=now, updated_at=now, **kwargs)
        with self._sessions.session() as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def update_node(self, node_id: str, **kwargs: Any) -> Any:
        from sqlmodel import select

        model = self._sqla_models.GraphNode
        with self._sessions.session() as session:
            obj = session.scalar(select(model).where(model.id == node_id))
            if obj is None:
                msg = f"GraphNode {node_id} not found"
                raise KeyError(msg)
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.updated_at = self._now()
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def delete_node(self, node_id: str) -> None:
        from sqlmodel import delete

        node_model = self._sqla_models.GraphNode
        edge_model = self._sqla_models.GraphEdge
        with self._sessions.session() as session:
            # Cascade: remove all edges touching this node
            session.exec(
                delete(edge_model).where(
                    (edge_model.from_id == node_id) | (edge_model.to_id == node_id)
                )
            )
            session.exec(delete(node_model).where(node_model.id == node_id))
            session.commit()

    # ── Edge CRUD ──────────────────────────────────────────────────

    def create_edge(self, **kwargs: Any) -> Any:
        model = self._sqla_models.GraphEdge
        now = self._now()
        obj = model(created_at=now, **kwargs)
        with self._sessions.session() as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def list_edges(self, where: Mapping[str, Any] | None = None) -> list[Any]:
        from sqlmodel import select

        model = self._sqla_models.GraphEdge
        filters = self._build_filters(model, where)
        with self._sessions.session() as session:
            return list(session.scalars(select(model).where(*filters)).all())

    def delete_edge(self, edge_id: str) -> None:
        from sqlmodel import delete

        model = self._sqla_models.GraphEdge
        with self._sessions.session() as session:
            session.exec(delete(model).where(model.id == edge_id))
            session.commit()

    # ── Community CRUD ─────────────────────────────────────────────

    def create_community(self, **kwargs: Any) -> Any:
        model = self._sqla_models.GraphCommunity
        now = self._now()
        obj = model(created_at=now, updated_at=now, **kwargs)
        with self._sessions.session() as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def list_communities(self, where: Mapping[str, Any] | None = None) -> list[Any]:
        from sqlmodel import select

        model = self._sqla_models.GraphCommunity
        filters = self._build_filters(model, where)
        with self._sessions.session() as session:
            return list(session.scalars(select(model).where(*filters)).all())

    def clear_communities(self) -> None:
        from sqlmodel import delete

        model = self._sqla_models.GraphCommunity
        with self._sessions.session() as session:
            session.exec(delete(model))
            session.commit()

    # ── Graph loading (for PPR) ────────────────────────────────────

    def load_graph(
        self, where: Mapping[str, Any] | None = None
    ) -> tuple[set[str], dict[str, set[str]]]:
        """Load active node IDs and undirected adjacency from DB."""
        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        edge_model = self._sqla_models.GraphEdge
        scope_filters = self._build_filters(node_model, where)

        with self._sessions.session() as session:
            node_ids = {
                row
                for row in session.scalars(
                    select(node_model.id).where(
                        node_model.status == "active", *scope_filters
                    )
                ).all()
            }

            adj: dict[str, set[str]] = defaultdict(set)
            edge_scope_filters = self._build_filters(edge_model, where)
            edges = session.execute(
                select(edge_model.from_id, edge_model.to_id).where(*edge_scope_filters)
            ).all()
            for from_id, to_id in edges:
                if from_id in node_ids and to_id in node_ids:
                    adj[from_id].add(to_id)
                    adj[to_id].add(from_id)

        for nid in node_ids:
            if nid not in adj:
                adj[nid] = set()

        return node_ids, adj

    # ── Seed search ────────────────────────────────────────────────

    def vector_seed_search(
        self,
        query_vec: list[float],
        limit: int = 6,
        min_score: float = 0.35,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Find seed nodes by pgvector cosine similarity."""
        if not self._use_vector:
            return []

        node_model = self._sqla_models.GraphNode
        distance = node_model.embedding.cosine_distance(query_vec)
        score_col = (1 - distance).label("score")
        scope_filters = self._build_filters(node_model, where)

        from sqlmodel import select

        stmt = (
            select(node_model.id, score_col)
            .where(
                node_model.status == "active",
                node_model.embedding.isnot(None),
                (1 - distance) >= min_score,
                *scope_filters,
            )
            .order_by(distance)
            .limit(limit)
        )

        with self._sessions.session() as session:
            rows = session.execute(stmt).all()
        return [(rid, float(score)) for rid, score in rows]

    def fts_seed_search(
        self, query: str, limit: int = 6, where: Mapping[str, Any] | None = None
    ) -> list[str]:
        """Fallback: full-text search on node name/description/content."""
        from sqlalchemy import func, text

        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        scope_filters = self._build_filters(node_model, where)
        tsvec = func.to_tsvector(
            "simple",
            func.coalesce(node_model.name, "")
            + " "
            + func.coalesce(node_model.description, "")
            + " "
            + func.coalesce(node_model.content, ""),
        )
        tsq = func.plainto_tsquery(text("'simple'"), query)

        stmt = (
            select(node_model.id)
            .where(node_model.status == "active", tsvec.op("@@")(tsq), *scope_filters)
            .order_by(node_model.pagerank.desc())
            .limit(limit)
        )

        with self._sessions.session() as session:
            return list(session.scalars(stmt).all())

    def get_community_peers(
        self, node_id: str, limit: int = 2, where: Mapping[str, Any] | None = None
    ) -> list[str]:
        """Get peers in the same community, ordered by validated_count."""
        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        scope_filters = self._build_filters(node_model, where)

        # First get this node's community_id
        with self._sessions.session() as session:
            node = session.scalar(select(node_model).where(node_model.id == node_id))
            if not node or not node.community_id:
                return []

            stmt = (
                select(node_model.id)
                .where(
                    node_model.community_id == node.community_id,
                    node_model.id != node_id,
                    node_model.status == "active",
                    *scope_filters,
                )
                .order_by(node_model.validated_count.desc(), node_model.updated_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    # ── Graph walk ─────────────────────────────────────────────────

    def graph_walk(
        self, start_ids: set[str], depth: int = 2, where: Mapping[str, Any] | None = None
    ) -> set[str]:
        """BFS graph walk up to `depth` hops, undirected."""
        from sqlalchemy import or_

        from sqlmodel import select

        edge_model = self._sqla_models.GraphEdge
        node_model = self._sqla_models.GraphNode
        scope_filters = self._build_filters(node_model, where)

        visited = set(start_ids)
        frontier = set(start_ids)

        with self._sessions.session() as session:
            for _ in range(depth):
                if not frontier:
                    break
                frontier_list = list(frontier)
                edge_scope_filters = self._build_filters(edge_model, where)
                stmt = select(edge_model.from_id, edge_model.to_id).where(
                    or_(
                        edge_model.from_id.in_(frontier_list),
                        edge_model.to_id.in_(frontier_list),
                    ),
                    *edge_scope_filters,
                )
                rows = session.execute(stmt).all()
                neighbors: set[str] = set()
                for from_id, to_id in rows:
                    if from_id in frontier:
                        neighbors.add(to_id)
                    if to_id in frontier:
                        neighbors.add(from_id)
                new_nodes = neighbors - visited
                visited |= new_nodes
                frontier = new_nodes

            # Filter to active nodes only, respecting scope
            active = set(
                session.scalars(
                    select(node_model.id).where(
                        node_model.id.in_(list(visited)),
                        node_model.status == "active",
                        *scope_filters,
                    )
                ).all()
            )

        return active

    # ── Node/Edge loading for recall results ───────────────────────

    def load_recall_nodes(
        self, node_ids: set[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, RecallNode]:
        """Load full node data as RecallNode dataclasses."""
        if not node_ids:
            return {}

        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        scope_filters = self._build_filters(node_model, where)
        with self._sessions.session() as session:
            rows = session.scalars(
                select(node_model).where(node_model.id.in_(list(node_ids)), *scope_filters)
            ).all()
            return {
                r.id: RecallNode(
                    id=r.id,
                    name=r.name,
                    type=r.type,
                    description=r.description or "",
                    content=r.content or "",
                    community_id=r.community_id,
                    pagerank=r.pagerank or 0.0,
                    ppr_score=0.0,
                )
                for r in rows
            }

    def load_recall_edges(
        self, node_ids: set[str], where: Mapping[str, Any] | None = None
    ) -> list[RecallEdge]:
        """Load edges where both endpoints are in node_ids, with scope filtering."""
        if not node_ids:
            return []

        from sqlalchemy import alias

        from sqlmodel import select

        edge_model = self._sqla_models.GraphEdge
        node_model = self._sqla_models.GraphNode
        node_list = list(node_ids)

        # Join node table twice to resolve from/to names
        to_node = alias(node_model.__table__, name="to_node")
        from_node = alias(node_model.__table__, name="from_node")

        with self._sessions.session() as session:
            stmt = (
                select(
                    from_node.c.name.label("from_name"),
                    to_node.c.name.label("to_name"),
                    edge_model.type,
                    edge_model.instruction,
                )
                .join(from_node, edge_model.from_id == from_node.c.id)
                .join(to_node, edge_model.to_id == to_node.c.id)
                .where(
                    edge_model.from_id.in_(node_list),
                    edge_model.to_id.in_(node_list),
                    *self._build_filters(edge_model, where),
                )
            )

            rows = session.execute(stmt).all()
            return [
                RecallEdge(
                    from_name=r.from_name,
                    to_name=r.to_name,
                    type=r.type,
                    instruction=r.instruction or "",
                )
                for r in rows
            ]

    # ── PPR algorithm ──────────────────────────────────────────────

    @staticmethod
    def personalized_pagerank(
        node_ids: set[str],
        adj: dict[str, set[str]],
        seed_ids: list[str],
        candidate_ids: set[str] | None = None,
        damping: float = 0.85,
        iterations: int = 20,
    ) -> dict[str, float]:
        """Personalized PageRank from seed nodes."""
        valid_seeds = [s for s in seed_ids if s in node_ids]
        if not valid_seeds:
            return {}

        teleport_weight = 1.0 / len(valid_seeds)
        seed_set = set(valid_seeds)

        rank = {nid: (teleport_weight if nid in seed_set else 0.0) for nid in node_ids}

        for _ in range(iterations):
            new_rank = {
                nid: ((1 - damping) * teleport_weight if nid in seed_set else 0.0)
                for nid in node_ids
            }

            for nid in node_ids:
                neighbors = adj[nid]
                if not neighbors:
                    continue
                contrib = rank[nid] / len(neighbors)
                for nb in neighbors:
                    new_rank[nb] = new_rank.get(nb, 0.0) + damping * contrib

            dangling_sum = sum(rank[nid] for nid in node_ids if not adj[nid])
            if dangling_sum > 0:
                dangling_contrib = damping * dangling_sum * teleport_weight
                for sid in valid_seeds:
                    new_rank[sid] += dangling_contrib

            rank = new_rank

        if candidate_ids is not None:
            return {nid: rank.get(nid, 0.0) for nid in candidate_ids}
        return rank

    @staticmethod
    def global_pagerank(
        node_ids: set[str],
        adj: dict[str, set[str]],
        damping: float = 0.85,
        iterations: int = 20,
    ) -> dict[str, float]:
        """Global PageRank — uniform teleport."""
        n = len(node_ids)
        if n == 0:
            return {}

        teleport_base = (1 - damping) / n
        rank = {nid: 1.0 / n for nid in node_ids}

        for _ in range(iterations):
            new_rank = {nid: teleport_base for nid in node_ids}

            for nid in node_ids:
                neighbors = adj[nid]
                if not neighbors:
                    continue
                contrib = rank[nid] / len(neighbors)
                for nb in neighbors:
                    new_rank[nb] += damping * contrib

            dangling_sum = sum(rank[nid] for nid in node_ids if not adj[nid])
            if dangling_sum > 0:
                dangling_contrib = damping * dangling_sum / n
                for nid in node_ids:
                    new_rank[nid] += dangling_contrib

            rank = new_rank

        return rank

    @staticmethod
    def label_propagation(
        node_ids: set[str],
        adj: dict[str, set[str]],
        max_iter: int = 50,
        seed: int | None = None,
    ) -> dict[str, str]:
        """Label Propagation Algorithm for community detection."""
        rng = random.Random(seed)
        nodes = list(node_ids)
        label = {nid: nid for nid in nodes}

        for _ in range(max_iter):
            changed = False
            rng.shuffle(nodes)

            for nid in nodes:
                neighbors = adj.get(nid, set())
                if not neighbors:
                    continue

                freq: dict[str, int] = defaultdict(int)
                for nb in neighbors:
                    freq[label[nb]] += 1

                max_freq = max(freq.values())
                candidates = [l for l, f in freq.items() if f == max_freq]
                best_label = min(candidates)

                if label[nid] != best_label:
                    label[nid] = best_label
                    changed = True

            if not changed:
                break

        # Renumber by descending size
        communities: dict[str, list[str]] = defaultdict(list)
        for nid, lab in label.items():
            communities[lab].append(nid)

        sorted_communities = sorted(communities.items(), key=lambda x: -len(x[1]))
        rename = {old_label: f"c-{rank + 1}" for rank, (old_label, _) in enumerate(sorted_communities)}

        return {nid: rename[label[nid]] for nid in nodes}

    # ── Maintenance (PageRank + LPA) ──────────────────────────────

    def run_maintenance(self) -> dict[str, int]:
        """Run global PageRank + LPA community detection. Returns stats."""
        node_ids, adj = self.load_graph()
        if not node_ids:
            return {"nodes": 0, "communities": 0}

        # Global PageRank
        pr_scores = self.global_pagerank(node_ids, adj)
        self.write_pagerank(pr_scores)

        # Community detection
        labels = self.label_propagation(node_ids, adj, seed=42)
        self.write_communities(labels)

        return {"nodes": len(pr_scores), "communities": len(set(labels.values()))}

    def write_pagerank(self, scores: dict[str, float]) -> None:
        """Write global PageRank scores to graph nodes."""
        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        with self._sessions.session() as session:
            for nid, score in scores.items():
                node = session.scalar(select(node_model).where(node_model.id == nid))
                if node:
                    node.pagerank = score
                    session.add(node)
            session.commit()

    def write_communities(self, labels: dict[str, str]) -> None:
        """Write community labels to nodes and rebuild community table."""
        from sqlmodel import delete, select

        node_model = self._sqla_models.GraphNode
        community_model = self._sqla_models.GraphCommunity

        with self._sessions.session() as session:
            # Update node community_id
            for nid, cid in labels.items():
                node = session.scalar(select(node_model).where(node_model.id == nid))
                if node:
                    node.community_id = cid
                    session.add(node)

            # Rebuild communities
            session.exec(delete(community_model))

            community_members: dict[str, list[str]] = defaultdict(list)
            for nid, cid in labels.items():
                community_members[cid].append(nid)

            # Extract scope fields from an existing node to propagate to communities
            scope_kwargs: dict[str, Any] = {}
            if labels:
                sample_nid = next(iter(labels))
                sample_node = session.scalar(
                    select(node_model).where(node_model.id == sample_nid)
                )
                if sample_node:
                    for field in self._scope_fields:
                        val = getattr(sample_node, field, None)
                        if val is not None and hasattr(community_model, field):
                            scope_kwargs[field] = val

            now = self._now()
            for cid, members in community_members.items():
                obj = community_model(
                    id=cid, node_count=len(members),
                    created_at=now, updated_at=now,
                    **scope_kwargs,
                )
                session.add(obj)

            session.commit()

    # ── Dual-path graph recall ─────────────────────────────────────

    def recall_precise(
        self,
        query: str,
        query_vec: list[float] | None,
        node_ids: set[str],
        adj: dict[str, set[str]],
        max_nodes: int = 6,
        where: Mapping[str, Any] | None = None,
    ) -> RecallResult:
        """Precise path: vector/FTS seed → community expansion → walk → PPR."""
        seeds: list[tuple[str, float]] = []
        if query_vec:
            seeds = self.vector_seed_search(query_vec, limit=max_nodes // 2, where=where)

        seed_ids = [s[0] for s in seeds]
        if len(seed_ids) < 2:
            fts_ids = self.fts_seed_search(query, limit=max_nodes, where=where)
            seed_id_set = set(seed_ids)
            for fid in fts_ids:
                if fid not in seed_id_set:
                    seed_ids.append(fid)

        if not seed_ids:
            return RecallResult(nodes=[], edges=[], path="precise")

        # Community expansion
        expanded = set(seed_ids)
        for sid in seed_ids:
            peers = self.get_community_peers(sid, limit=2, where=where)
            expanded.update(peers)

        # Graph walk
        walked = self.graph_walk(expanded, depth=2, where=where)

        # PPR ranking
        ppr = self.personalized_pagerank(node_ids, adj, seed_ids, candidate_ids=walked)

        nodes_data = self.load_recall_nodes(walked, where=where)
        for nid, node in nodes_data.items():
            node.ppr_score = ppr.get(nid, 0.0)

        sorted_nodes = sorted(
            nodes_data.values(),
            key=lambda n: (-n.ppr_score, -n.pagerank),
        )[:max_nodes]

        result_ids = {n.id for n in sorted_nodes}
        edges = self.load_recall_edges(result_ids, where=where)

        return RecallResult(nodes=sorted_nodes, edges=edges, path="precise")

    def recall_generalized(
        self,
        query: str,
        query_vec: list[float] | None,
        node_ids: set[str],
        adj: dict[str, set[str]],
        max_nodes: int = 6,
        where: Mapping[str, Any] | None = None,
    ) -> RecallResult:
        """Generalized path: community representatives → shallow walk → PPR."""
        from sqlmodel import select

        node_model = self._sqla_models.GraphNode
        scope_filters = self._build_filters(node_model, where)

        with self._sessions.session() as session:
            # Pick top representative per community
            stmt = (
                select(node_model.id, node_model.community_id)
                .where(
                    node_model.status == "active",
                    node_model.community_id.isnot(None),
                    *scope_filters,
                )
                .order_by(
                    node_model.community_id,
                    node_model.validated_count.desc(),
                    node_model.updated_at.desc(),
                )
            )
            rows = session.execute(stmt).all()

        # Deduplicate: first per community wins (since ordered by validated_count desc)
        seen_communities: set[str] = set()
        rep_ids: list[str] = []
        for nid, cid in rows:
            if cid not in seen_communities:
                seen_communities.add(cid)
                rep_ids.append(nid)

        if not rep_ids:
            return RecallResult(nodes=[], edges=[], path="generalized")

        # Rank community representatives by query relevance (P1 #1 fix)
        if query_vec and self._use_vector:
            rep_scores = self.vector_seed_search(
                query_vec, limit=max_nodes, where=where
            )
            rep_score_map = dict(rep_scores)
            rep_set = set(rep_ids)
            # Sort reps by cosine similarity; reps not in results get score 0
            rep_ids = sorted(
                rep_ids,
                key=lambda nid: rep_score_map.get(nid, 0.0),
                reverse=True,
            )
        seed_ids = rep_ids[:max_nodes]

        # Shallow walk
        walked = self.graph_walk(set(seed_ids), depth=1, where=where)

        # PPR ranking
        ppr = self.personalized_pagerank(node_ids, adj, seed_ids, candidate_ids=walked)

        nodes_data = self.load_recall_nodes(walked, where=where)
        for nid, node in nodes_data.items():
            node.ppr_score = ppr.get(nid, 0.0)

        sorted_nodes = sorted(
            nodes_data.values(),
            key=lambda n: (-n.ppr_score, -n.pagerank),
        )[:max_nodes]

        result_ids = {n.id for n in sorted_nodes}
        edges = self.load_recall_edges(result_ids, where=where)

        return RecallResult(nodes=sorted_nodes, edges=edges, path="generalized")

    @staticmethod
    def merge_results(
        precise: RecallResult,
        generalized: RecallResult,
        max_nodes: int = 0,
    ) -> RecallResult:
        """Merge: precise wins on dedup, generalized fills gaps, cap to max_nodes."""
        seen_ids: set[str] = set()
        merged_nodes: list[RecallNode] = []

        for n in precise.nodes:
            if n.id not in seen_ids:
                merged_nodes.append(n)
                seen_ids.add(n.id)

        for n in generalized.nodes:
            if n.id not in seen_ids:
                merged_nodes.append(n)
                seen_ids.add(n.id)

        if max_nodes > 0:
            merged_nodes = merged_nodes[:max_nodes]

        result_ids = {n.id for n in merged_nodes}
        edge_set: set[tuple[str, str, str]] = set()
        merged_edges: list[RecallEdge] = []
        for e in precise.edges + generalized.edges:
            key = (e.from_name, e.to_name, e.type)
            if key not in edge_set:
                merged_edges.append(e)
                edge_set.add(key)

        return RecallResult(nodes=merged_nodes, edges=merged_edges, path="merged")

    def graph_recall(
        self,
        query: str,
        query_vec: list[float] | None = None,
        max_nodes: int = 6,
        where: Mapping[str, Any] | None = None,
    ) -> RecallResult:
        """Full dual-path graph recall."""
        node_ids, adj = self.load_graph(where=where)
        if not node_ids:
            return RecallResult(nodes=[], edges=[], path="empty")

        precise = self.recall_precise(query, query_vec, node_ids, adj, max_nodes, where=where)
        generalized = self.recall_generalized(
            query, query_vec, node_ids, adj, max_nodes, where=where
        )

        return self.merge_results(precise, generalized, max_nodes=max_nodes)


__all__ = [
    "PostgresGraphStore",
    "RecallEdge",
    "RecallNode",
    "RecallResult",
]
