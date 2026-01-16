"""Knowledge Graph storage using NetworkX for entity-relationship memory."""

from __future__ import annotations

import pickle
import threading
import time
from pathlib import Path
from typing import Any

import networkx as nx


class KnowledgeGraph:
    """
    NetworkX-based knowledge graph for storing entities and relationships.

    Enables relationship-aware memory retrieval by storing:
    - Entities (people, places, organizations, concepts)
    - Relationships as triples (subject → predicate → object)
    - Graph traversal for context-aware retrieval
    """

    def __init__(self, storage_path: str | Path | None = None):
        """
        Initialize the knowledge graph.

        Args:
            storage_path: Optional path to persist the graph. If None, graph is in-memory only.
        """
        self._lock = threading.Lock()
        self._storage_path = Path(storage_path) if storage_path else None
        self._graph_file = self._storage_path / "knowledge_graph.pkl" if self._storage_path else None
        self.graph: nx.DiGraph = self._load_graph()

    def _load_graph(self) -> nx.DiGraph:
        """Load graph from disk or create new one."""
        if self._graph_file and self._graph_file.exists():
            try:
                with self._graph_file.open("rb") as f:
                    graph = pickle.load(f)  # noqa: S301
                    return graph if graph is not None else nx.DiGraph()
            except Exception:
                # Corrupted file, start fresh
                return nx.DiGraph()
        return nx.DiGraph()

    def _save_graph(self) -> None:
        """Persist graph to disk if storage path is configured."""
        if not self._graph_file:
            return
        with self._lock:
            try:
                self._graph_file.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self._graph_file.with_suffix(".pkl.tmp")
                with temp_path.open("wb") as f:
                    pickle.dump(self.graph, f)
                if self._graph_file.exists():
                    self._graph_file.unlink()
                temp_path.rename(self._graph_file)
            except Exception as e:
                print(f"Warning: Could not save knowledge graph: {e}")

    def _find_canonical_entity(self, name: str, node_type: str = "Concept", similarity_threshold: float = 0.85) -> str:
        """
        Find canonical entity name using fuzzy matching to prevent duplicates.

        Handles cases like "Dr. Watson" vs "Dr. Emma Watson" by preferring longer names.

        Args:
            name: Entity name to check
            node_type: Type of entity (Person, Organization, etc.)
            similarity_threshold: Minimum similarity for matching (0.0-1.0)

        Returns:
            Canonical entity name to use
        """
        if not name or not name.strip():
            return name

        name_lower = name.lower().strip()
        same_type_nodes = [n for n, data in self.graph.nodes(data=True) if data.get("type") == node_type]

        if not same_type_nodes:
            return name

        # Strategy 1: Exact match (case-insensitive)
        exact_match = self._find_exact_match(name_lower, same_type_nodes)
        if exact_match:
            return exact_match

        # Strategy 2: Word-based matching
        word_match = self._find_word_match(name, name_lower, same_type_nodes)
        if word_match:
            return word_match

        # Strategy 3: Jaccard similarity
        return self._find_similarity_match(name, name_lower, same_type_nodes, similarity_threshold)

    def _find_exact_match(self, name_lower: str, same_type_nodes: list[str]) -> str | None:
        """Find exact case-insensitive match."""
        for existing_node in same_type_nodes:
            if existing_node.lower() == name_lower:
                return existing_node
        return None

    def _find_word_match(self, name: str, name_lower: str, same_type_nodes: list[str]) -> str | None:
        """Find match based on word subset relationships."""
        name_words = name_lower.split()
        name_words_set = set(name_words)

        for existing_node in same_type_nodes:
            existing_words = existing_node.lower().split()
            existing_words_set = set(existing_words)

            if existing_words_set.issubset(name_words_set):
                if len(name_words) > len(existing_words):
                    self._merge_entity_nodes(existing_node, name)
                    return name
                return existing_node
            if name_words_set.issubset(existing_words_set):
                return existing_node
        return None

    def _find_similarity_match(self, name: str, name_lower: str, same_type_nodes: list[str], threshold: float) -> str:
        """Find match based on Jaccard similarity."""
        name_words_set = set(name_lower.split())
        best_match = None
        best_similarity = 0.0

        for existing_node in same_type_nodes:
            existing_words = set(existing_node.lower().split())
            intersection = len(name_words_set & existing_words)
            union = len(name_words_set | existing_words)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = existing_node

        if best_match:
            if len(name) > len(best_match):
                self._merge_entity_nodes(best_match, name)
                return name
            return best_match

        return name

    def _merge_entity_nodes(self, old_name: str, new_name: str) -> None:
        """Merge two entity nodes, consolidating all edges."""
        if not self.graph.has_node(old_name) or old_name == new_name:
            return

        old_attrs = self.graph.nodes[old_name].copy()

        if not self.graph.has_node(new_name):
            self.graph.add_node(new_name, **old_attrs)

        # Move incoming edges
        for predecessor in list(self.graph.predecessors(old_name)):
            edge_data = self.graph.get_edge_data(predecessor, old_name)
            if not self.graph.has_edge(predecessor, new_name):
                self.graph.add_edge(predecessor, new_name, **edge_data)

        # Move outgoing edges
        for successor in list(self.graph.successors(old_name)):
            edge_data = self.graph.get_edge_data(old_name, successor)
            if not self.graph.has_edge(new_name, successor):
                self.graph.add_edge(new_name, successor, **edge_data)

        self.graph.remove_node(old_name)

    def add_entity(
        self,
        name: str,
        node_type: str = "Concept",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add an entity node to the graph.

        Args:
            name: Entity name
            node_type: Type (Person, Organization, Place, Concept, etc.)
            metadata: Optional additional attributes

        Returns:
            Canonical name used (may differ due to deduplication)
        """
        if not name or not name.strip():
            return name

        canonical_name = self._find_canonical_entity(name, node_type)

        if not self.graph.has_node(canonical_name):
            base_attrs = {
                "type": node_type,
                "created_at": time.time(),
                "access_count": 0,
                "last_accessed": time.time(),
            }
            if metadata:
                base_attrs.update(metadata)
            self.graph.add_node(canonical_name, **base_attrs)
            self._save_graph()

        return canonical_name

    def add_relationship(
        self,
        subject: str,
        predicate: str,
        obj: str,
        subject_type: str = "Concept",
        object_type: str = "Concept",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a relationship (edge) between two entities.

        Args:
            subject: Source entity name
            predicate: Relationship type (e.g., "works_at", "married_to")
            obj: Target entity name
            subject_type: Type of subject entity
            object_type: Type of object entity
            metadata: Optional edge attributes
        """
        if not all([subject, predicate, obj]):
            return

        canonical_subject = self.add_entity(subject, node_type=subject_type)
        canonical_object = self.add_entity(obj, node_type=object_type)

        if not self.graph.has_edge(canonical_subject, canonical_object):
            edge_attrs = {"type": predicate, "created_at": time.time()}
            if metadata:
                edge_attrs.update(metadata)
            self.graph.add_edge(canonical_subject, canonical_object, **edge_attrs)
            self._save_graph()

    def get_related_entities(self, entity_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get entities directly connected to the given entity.

        Args:
            entity_name: Entity to find relations for
            limit: Maximum number of results

        Returns:
            List of related entities with relationship info
        """
        if not self.graph.has_node(entity_name):
            # Try fuzzy match
            matches = self.find_matching_nodes(entity_name)
            if matches:
                entity_name = matches[0]
            else:
                return []

        related = []

        # Outgoing relationships
        for successor in self.graph.successors(entity_name):
            if len(related) >= limit:
                break
            edge_data = self.graph.get_edge_data(entity_name, successor)
            node_data = self.graph.nodes[successor]
            related.append({
                "name": successor,
                "relationship": edge_data.get("type", "related_to"),
                "direction": "outgoing",
                "entity_type": node_data.get("type", "Concept"),
            })

        # Incoming relationships
        for predecessor in self.graph.predecessors(entity_name):
            if len(related) >= limit:
                break
            edge_data = self.graph.get_edge_data(predecessor, entity_name)
            node_data = self.graph.nodes[predecessor]
            related.append({
                "name": predecessor,
                "relationship": edge_data.get("type", "related_to"),
                "direction": "incoming",
                "entity_type": node_data.get("type", "Concept"),
            })

        return related[:limit]

    def get_subgraph_context(self, entity_name: str, depth: int = 2) -> list[str]:
        """
        Get textual representation of relationships around an entity.

        Traverses the graph up to `depth` hops and formats relationships
        as human-readable strings for LLM context.

        Args:
            entity_name: Starting entity
            depth: Number of hops to traverse (radius)

        Returns:
            List of relationship strings like:
            "(Person) John --[works_at]--> (Organization) Google"
        """
        if not self.graph.has_node(entity_name):
            matches = self.find_matching_nodes(entity_name)
            if matches:
                entity_name = matches[0]
            else:
                return []

        # Use ego_graph for efficient subgraph extraction
        subgraph = nx.ego_graph(self.graph, entity_name, radius=depth)

        relationships = []
        for u, v, data in subgraph.edges(data=True):
            rel_type = data.get("type", "related_to")
            u_type = self.graph.nodes[u].get("type", "Concept")
            v_type = self.graph.nodes[v].get("type", "Concept")
            relationships.append(f"({u_type}) {u} --[{rel_type}]--> ({v_type}) {v}")

        return relationships

    def find_matching_nodes(self, query_name: str, threshold: float = 0.6) -> list[str]:
        """
        Find nodes matching the query using fuzzy matching.

        Args:
            query_name: Entity name to search for
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            List of matching node names, sorted by similarity
        """
        if not query_name or not query_name.strip():
            return []

        query_lower = query_name.lower().strip()

        # Exact match first
        for node in self.graph.nodes():
            if node.lower() == query_lower:
                return [node]

        # Fuzzy matching
        matches = []
        query_words = set(query_lower.split())

        for node in self.graph.nodes():
            node_lower = node.lower()
            node_words = set(node_lower.split())

            # Substring match
            if query_lower in node_lower or node_lower in query_lower:
                matches.append((node, 1.0))
                continue

            # Jaccard similarity
            if query_words and node_words:
                intersection = len(query_words & node_words)
                union = len(query_words | node_words)
                similarity = intersection / union if union > 0 else 0.0
                if similarity >= threshold:
                    matches.append((node, similarity))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in matches]

    def track_access(self, entity_names: list[str]) -> None:
        """Update access count and timestamp for accessed entities."""
        updated = False
        with self._lock:
            for name in entity_names:
                if self.graph.has_node(name):
                    self.graph.nodes[name]["access_count"] = self.graph.nodes[name].get("access_count", 0) + 1
                    self.graph.nodes[name]["last_accessed"] = time.time()
                    updated = True
        if updated:
            self._save_graph()

    def get_all_entities(self, entity_type: str | None = None) -> list[dict[str, Any]]:
        """
        Get all entities, optionally filtered by type.

        Args:
            entity_type: Optional type filter (Person, Organization, etc.)

        Returns:
            List of entity dictionaries
        """
        entities = []
        for node, data in self.graph.nodes(data=True):
            if entity_type is None or data.get("type") == entity_type:
                entity_data = data.copy()
                entity_data["name"] = node
                entities.append(entity_data)
        return entities

    def get_all_relationships(self) -> list[dict[str, Any]]:
        """Get all relationships in the graph."""
        relationships = []
        for u, v, data in self.graph.edges(data=True):
            relationships.append({
                "subject": u,
                "predicate": data.get("type", "related_to"),
                "object": v,
                "subject_type": self.graph.nodes[u].get("type", "Concept"),
                "object_type": self.graph.nodes[v].get("type", "Concept"),
            })
        return relationships

    def delete_entity(self, entity_name: str) -> bool:
        """Delete an entity and all its relationships."""
        if self.graph.has_node(entity_name):
            self.graph.remove_node(entity_name)
            self._save_graph()
            return True
        return False

    def clear(self) -> None:
        """Clear all entities and relationships."""
        self.graph.clear()
        self._save_graph()

    @property
    def node_count(self) -> int:
        """Number of entities in the graph."""
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """Number of relationships in the graph."""
        return self.graph.number_of_edges()

    def close(self) -> None:
        """Save and cleanup."""
        self._save_graph()


__all__ = ["KnowledgeGraph"]
