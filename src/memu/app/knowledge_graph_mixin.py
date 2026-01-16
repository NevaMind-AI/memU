"""Mixin for knowledge graph operations in MemU service."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from memu.database.knowledge_graph import KnowledgeGraph
from memu.prompts.entity_extraction import PROMPT as ENTITY_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class KnowledgeGraphMixin:
    """Mixin providing knowledge graph functionality for MemU service."""

    if TYPE_CHECKING:
        _get_llm_client: Callable[..., Any]
        _extract_json_blob: Callable[[str], str]

    _knowledge_graph: KnowledgeGraph | None = None

    def _get_knowledge_graph(self, storage_path: str | None = None) -> KnowledgeGraph:
        """Get or create the knowledge graph instance."""
        if self._knowledge_graph is None:
            self._knowledge_graph = KnowledgeGraph(storage_path)
        return self._knowledge_graph

    async def extract_entities_and_relationships(
        self,
        text: str,
        llm_client: Any | None = None,
    ) -> dict[str, list[dict[str, str]]]:
        """
        Extract entities and relationships from text using LLM.

        Args:
            text: Text to extract from
            llm_client: Optional LLM client override

        Returns:
            Dict with 'entities' and 'relationships' lists
        """
        if not text or not text.strip():
            return {"entities": [], "relationships": []}

        client = llm_client or self._get_llm_client()
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            response = await client.summarize(prompt)
            json_str = self._extract_json_blob(response)
            result = json.loads(json_str)

            # Validate structure
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])

            # Filter valid entities
            valid_entities = [
                e for e in entities
                if isinstance(e, dict) and e.get("name") and e.get("type")
            ]

            # Filter valid relationships
            valid_relationships = [
                r for r in relationships
                if isinstance(r, dict)
                and r.get("subject")
                and r.get("predicate")
                and r.get("object")
            ]

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse entity extraction response: {e}")
            return {"entities": [], "relationships": []}
        else:
            return {"entities": valid_entities, "relationships": valid_relationships}

    def populate_knowledge_graph(
        self,
        extraction_result: dict[str, list[dict[str, str]]],
        knowledge_graph: KnowledgeGraph | None = None,
    ) -> tuple[int, int]:
        """
        Populate knowledge graph with extracted entities and relationships.

        Args:
            extraction_result: Result from extract_entities_and_relationships
            knowledge_graph: Optional graph instance override

        Returns:
            Tuple of (entities_added, relationships_added)
        """
        graph = knowledge_graph or self._get_knowledge_graph()
        entities_added = 0
        relationships_added = 0

        # Build entity type lookup
        entity_types: dict[str, str] = {}
        for entity in extraction_result.get("entities", []):
            name = entity.get("name", "").strip()
            entity_type = entity.get("type", "Concept")
            if name:
                entity_types[name.lower()] = entity_type
                graph.add_entity(name, node_type=entity_type)
                entities_added += 1

        # Add relationships
        for rel in extraction_result.get("relationships", []):
            subject = rel.get("subject", "").strip()
            predicate = rel.get("predicate", "").strip()
            obj = rel.get("object", "").strip()

            if subject and predicate and obj:
                # Get types from lookup or default to Concept
                subject_type = entity_types.get(subject.lower(), "Concept")
                object_type = entity_types.get(obj.lower(), "Concept")

                graph.add_relationship(
                    subject=subject,
                    predicate=predicate,
                    obj=obj,
                    subject_type=subject_type,
                    object_type=object_type,
                )
                relationships_added += 1

        return entities_added, relationships_added

    def query_knowledge_graph(
        self,
        query: str,
        depth: int = 2,
        knowledge_graph: KnowledgeGraph | None = None,
    ) -> list[str]:
        """
        Query knowledge graph for context related to a query.

        Extracts entity names from query and retrieves their subgraph context.

        Args:
            query: User query text
            depth: Graph traversal depth
            knowledge_graph: Optional graph instance override

        Returns:
            List of relationship strings for context
        """
        graph = knowledge_graph or self._get_knowledge_graph()
        context_lines: list[str] = []

        # Extract potential entity names from query
        # Look for capitalized words/phrases
        potential_entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query)

        # Also try the whole query as entity search
        all_candidates = list({*potential_entities, query})

        seen_relationships: set[str] = set()
        matched_entities: list[str] = []

        for candidate in all_candidates:
            matches = graph.find_matching_nodes(candidate, threshold=0.5)
            for match in matches[:2]:  # Limit matches per candidate
                if match not in matched_entities:
                    matched_entities.append(match)
                    subgraph_context = graph.get_subgraph_context(match, depth=depth)
                    for line in subgraph_context:
                        if line not in seen_relationships:
                            seen_relationships.add(line)
                            context_lines.append(line)

        # Track access for matched entities
        if matched_entities:
            graph.track_access(matched_entities)

        return context_lines

    def get_graph_stats(
        self, knowledge_graph: KnowledgeGraph | None = None
    ) -> dict[str, int]:
        """Get knowledge graph statistics."""
        graph = knowledge_graph or self._get_knowledge_graph()
        return {
            "entity_count": graph.node_count,
            "relationship_count": graph.edge_count,
        }


__all__ = ["KnowledgeGraphMixin"]
