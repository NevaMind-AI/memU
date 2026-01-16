"""Tests for Knowledge Graph functionality."""

import importlib.util
import tempfile
from pathlib import Path

# Direct file import to avoid circular import issues from memu.database.__init__
spec = importlib.util.spec_from_file_location(
    "knowledge_graph", Path(__file__).parent.parent / "src" / "memu" / "database" / "knowledge_graph.py"
)
knowledge_graph_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge_graph_module)
KnowledgeGraph = knowledge_graph_module.KnowledgeGraph


class TestKnowledgeGraphBasics:
    """Test basic knowledge graph operations."""

    def test_create_empty_graph(self):
        """Test creating an empty in-memory graph."""
        graph = KnowledgeGraph()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_entity(self):
        """Test adding entities to the graph."""
        graph = KnowledgeGraph()

        name = graph.add_entity("John Smith", node_type="Person")
        assert name == "John Smith"
        assert graph.node_count == 1

        # Check entity attributes
        entities = graph.get_all_entities()
        assert len(entities) == 1
        assert entities[0]["name"] == "John Smith"
        assert entities[0]["type"] == "Person"

    def test_add_relationship(self):
        """Test adding relationships between entities."""
        graph = KnowledgeGraph()

        graph.add_relationship(
            subject="John",
            predicate="works_at",
            obj="Google",
            subject_type="Person",
            object_type="Organization",
        )

        assert graph.node_count == 2
        assert graph.edge_count == 1

        relationships = graph.get_all_relationships()
        assert len(relationships) == 1
        assert relationships[0]["subject"] == "John"
        assert relationships[0]["predicate"] == "works_at"
        assert relationships[0]["object"] == "Google"

    def test_add_multiple_relationships(self):
        """Test adding multiple relationships."""
        graph = KnowledgeGraph()

        graph.add_relationship("John", "works_at", "Google", "Person", "Organization")
        graph.add_relationship("John", "lives_in", "San Francisco", "Person", "Place")
        graph.add_relationship("John", "married_to", "Sarah", "Person", "Person")

        assert graph.node_count == 4  # John, Google, San Francisco, Sarah
        assert graph.edge_count == 3


class TestEntityDeduplication:
    """Test entity deduplication with fuzzy matching."""

    def test_exact_match_deduplication(self):
        """Test that exact matches are deduplicated."""
        graph = KnowledgeGraph()

        graph.add_entity("John Smith", node_type="Person")
        graph.add_entity("john smith", node_type="Person")  # Same, different case

        assert graph.node_count == 1

    def test_subset_match_prefers_longer_name(self):
        """Test that subset matches prefer longer names."""
        graph = KnowledgeGraph()

        # Add shorter name first
        graph.add_entity("Dr. Watson", node_type="Person")
        # Add longer name - should merge
        graph.add_entity("Dr. Emma Watson", node_type="Person")

        assert graph.node_count == 1
        entities = graph.get_all_entities()
        assert entities[0]["name"] == "Dr. Emma Watson"

    def test_different_entities_not_merged(self):
        """Test that different entities are not merged."""
        graph = KnowledgeGraph()

        graph.add_entity("John Smith", node_type="Person")
        graph.add_entity("Jane Doe", node_type="Person")

        assert graph.node_count == 2


class TestGraphTraversal:
    """Test graph traversal and context retrieval."""

    def test_get_related_entities(self):
        """Test getting related entities."""
        graph = KnowledgeGraph()

        graph.add_relationship("John", "works_at", "Google", "Person", "Organization")
        graph.add_relationship("John", "married_to", "Sarah", "Person", "Person")

        related = graph.get_related_entities("John")
        assert len(related) == 2

        names = [r["name"] for r in related]
        assert "Google" in names
        assert "Sarah" in names

    def test_get_subgraph_context(self):
        """Test getting subgraph context as text."""
        graph = KnowledgeGraph()

        graph.add_relationship("John", "works_at", "Google", "Person", "Organization")
        graph.add_relationship("Google", "located_in", "Mountain View", "Organization", "Place")

        # Depth 1 - only direct connections
        context = graph.get_subgraph_context("John", depth=1)
        assert len(context) == 1
        assert "(Person) John --[works_at]--> (Organization) Google" in context

        # Depth 2 - includes Google's connections
        context = graph.get_subgraph_context("John", depth=2)
        assert len(context) == 2

    def test_get_subgraph_context_nonexistent_entity(self):
        """Test subgraph context for non-existent entity."""
        graph = KnowledgeGraph()
        context = graph.get_subgraph_context("NonExistent")
        assert context == []


class TestFuzzyMatching:
    """Test fuzzy matching for entity lookup."""

    def test_find_exact_match(self):
        """Test finding exact match."""
        graph = KnowledgeGraph()
        graph.add_entity("John Smith", node_type="Person")

        matches = graph.find_matching_nodes("John Smith")
        assert len(matches) == 1
        assert matches[0] == "John Smith"

    def test_find_case_insensitive_match(self):
        """Test case-insensitive matching."""
        graph = KnowledgeGraph()
        graph.add_entity("John Smith", node_type="Person")

        matches = graph.find_matching_nodes("john smith")
        assert len(matches) == 1
        assert matches[0] == "John Smith"

    def test_find_partial_match(self):
        """Test partial/substring matching."""
        graph = KnowledgeGraph()
        graph.add_entity("John Smith", node_type="Person")

        matches = graph.find_matching_nodes("John")
        assert len(matches) == 1
        assert matches[0] == "John Smith"

    def test_find_no_match(self):
        """Test when no match is found."""
        graph = KnowledgeGraph()
        graph.add_entity("John Smith", node_type="Person")

        matches = graph.find_matching_nodes("Jane Doe")
        assert len(matches) == 0


class TestAccessTracking:
    """Test access count tracking."""

    def test_track_access(self):
        """Test that access tracking updates counts."""
        graph = KnowledgeGraph()
        graph.add_entity("John", node_type="Person")

        # Initial access count should be 0
        entities = graph.get_all_entities()
        assert entities[0]["access_count"] == 0

        # Track access
        graph.track_access(["John"])

        entities = graph.get_all_entities()
        assert entities[0]["access_count"] == 1

    def test_track_multiple_accesses(self):
        """Test tracking multiple accesses."""
        graph = KnowledgeGraph()
        graph.add_entity("John", node_type="Person")

        graph.track_access(["John"])
        graph.track_access(["John"])
        graph.track_access(["John"])

        entities = graph.get_all_entities()
        assert entities[0]["access_count"] == 3


class TestPersistence:
    """Test graph persistence to disk."""

    def test_save_and_load(self):
        """Test saving and loading graph from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate graph
            graph1 = KnowledgeGraph(storage_path=tmpdir)
            graph1.add_relationship("John", "works_at", "Google", "Person", "Organization")
            graph1.close()

            # Load graph from disk
            graph2 = KnowledgeGraph(storage_path=tmpdir)
            assert graph2.node_count == 2
            assert graph2.edge_count == 1

            relationships = graph2.get_all_relationships()
            assert relationships[0]["subject"] == "John"
            assert relationships[0]["object"] == "Google"


class TestDeleteOperations:
    """Test delete operations."""

    def test_delete_entity(self):
        """Test deleting an entity."""
        graph = KnowledgeGraph()
        graph.add_entity("John", node_type="Person")
        assert graph.node_count == 1

        result = graph.delete_entity("John")
        assert result is True
        assert graph.node_count == 0

    def test_delete_nonexistent_entity(self):
        """Test deleting non-existent entity."""
        graph = KnowledgeGraph()
        result = graph.delete_entity("NonExistent")
        assert result is False

    def test_clear_graph(self):
        """Test clearing the entire graph."""
        graph = KnowledgeGraph()
        graph.add_relationship("John", "works_at", "Google", "Person", "Organization")
        graph.add_relationship("Sarah", "lives_in", "NYC", "Person", "Place")

        assert graph.node_count == 4
        assert graph.edge_count == 2

        graph.clear()

        assert graph.node_count == 0
        assert graph.edge_count == 0


class TestEntityTypeFiltering:
    """Test filtering entities by type."""

    def test_get_entities_by_type(self):
        """Test getting entities filtered by type."""
        graph = KnowledgeGraph()

        graph.add_entity("John", node_type="Person")
        graph.add_entity("Sarah", node_type="Person")
        graph.add_entity("Google", node_type="Organization")
        graph.add_entity("NYC", node_type="Place")

        people = graph.get_all_entities(entity_type="Person")
        assert len(people) == 2

        orgs = graph.get_all_entities(entity_type="Organization")
        assert len(orgs) == 1
        assert orgs[0]["name"] == "Google"

    def test_get_all_entities_no_filter(self):
        """Test getting all entities without filter."""
        graph = KnowledgeGraph()

        graph.add_entity("John", node_type="Person")
        graph.add_entity("Google", node_type="Organization")

        all_entities = graph.get_all_entities()
        assert len(all_entities) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_entity_name(self):
        """Test adding entity with empty name."""
        graph = KnowledgeGraph()
        result = graph.add_entity("", node_type="Person")
        assert result == ""
        assert graph.node_count == 0

    def test_empty_relationship(self):
        """Test adding relationship with empty values."""
        graph = KnowledgeGraph()
        graph.add_relationship("", "works_at", "Google")
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_whitespace_only_entity(self):
        """Test adding entity with whitespace-only name."""
        graph = KnowledgeGraph()
        graph.add_entity("   ", node_type="Person")
        assert graph.node_count == 0

    def test_duplicate_relationship(self):
        """Test that duplicate relationships are not added."""
        graph = KnowledgeGraph()

        graph.add_relationship("John", "works_at", "Google")
        graph.add_relationship("John", "works_at", "Google")  # Duplicate

        assert graph.edge_count == 1
