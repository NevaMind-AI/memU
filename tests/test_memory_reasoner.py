"""Tests for the Memory Reasoning Engine."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pendulum
import pytest

from memu.reasoning.derived_memory import DerivedMemory, DerivedMemoryStore
from memu.reasoning.memory_reasoner import MemoryReasoner
from memu.reasoning.query_dsl import ReasoningConstraints, ReasoningQuery, ReasoningTrace

# Configure pytest-asyncio
pytestmark = pytest.mark.anyio


# ============================================================================
# DerivedMemory Tests
# ============================================================================


class TestDerivedMemory:
    """Tests for DerivedMemory model."""

    def test_create_derived_memory(self) -> None:
        """Test creating a derived memory."""
        dm = DerivedMemory(
            content="John is the best database expert",
            inference_type="deduction",
            source_memory_ids=["mem1", "mem2"],
            confidence_score=0.85,
        )

        assert dm.content == "John is the best database expert"
        assert dm.inference_type == "deduction"
        assert dm.source_memory_ids == ["mem1", "mem2"]
        assert dm.confidence_score == 0.85
        assert dm.id is not None
        assert dm.created_at is not None

    def test_derived_memory_reinforce(self) -> None:
        """Test reinforcing a derived memory."""
        dm = DerivedMemory(
            content="Test content",
            inference_type="induction",
            confidence_score=0.5,
        )
        original_confidence = dm.confidence_score
        original_checks = dm.consistency_checks

        dm.reinforce()

        assert dm.confidence_score > original_confidence
        assert dm.consistency_checks == original_checks + 1

    def test_derived_memory_weaken(self) -> None:
        """Test weakening a derived memory."""
        dm = DerivedMemory(
            content="Test content",
            inference_type="induction",
            confidence_score=0.5,
        )
        original_confidence = dm.confidence_score

        dm.weaken()

        assert dm.confidence_score < original_confidence

    def test_derived_memory_expiration(self) -> None:
        """Test derived memory expiration."""
        # Not expired
        dm1 = DerivedMemory(
            content="Test",
            inference_type="summarization",
            expires_at=pendulum.now("UTC") + timedelta(days=1),
        )
        assert not dm1.is_expired()

        # Expired
        dm2 = DerivedMemory(
            content="Test",
            inference_type="summarization",
            expires_at=pendulum.now("UTC") - timedelta(days=1),
        )
        assert dm2.is_expired()

        # No expiration
        dm3 = DerivedMemory(
            content="Test",
            inference_type="summarization",
        )
        assert not dm3.is_expired()

    def test_to_memory_summary(self) -> None:
        """Test converting to memory summary string."""
        dm = DerivedMemory(
            content="Important insight",
            inference_type="deduction",
            confidence_score=0.9,
        )

        summary = dm.to_memory_summary()

        assert "Derived" in summary
        assert "deduction" in summary
        assert "high confidence" in summary
        assert "Important insight" in summary

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        dm = DerivedMemory(
            content="Test content",
            inference_type="analogy",
            source_memory_ids=["id1"],
            confidence_score=0.7,
        )

        d = dm.to_dict()

        assert d["content"] == "Test content"
        assert d["inference_type"] == "analogy"
        assert d["source_memory_ids"] == ["id1"]
        assert d["confidence_score"] == 0.7


# ============================================================================
# DerivedMemoryStore Tests
# ============================================================================


class TestDerivedMemoryStore:
    """Tests for DerivedMemoryStore."""

    def test_add_and_get(self) -> None:
        """Test adding and retrieving derived memories."""
        store = DerivedMemoryStore()
        dm = DerivedMemory(
            content="Test",
            inference_type="deduction",
        )

        store.add(dm)
        retrieved = store.get(dm.id)

        assert retrieved is not None
        assert retrieved.content == "Test"

    def test_get_by_entity(self) -> None:
        """Test retrieving by entity."""
        store = DerivedMemoryStore()
        dm = DerivedMemory(
            content="John is an expert",
            inference_type="deduction",
            source_entities=["John", "Google"],
        )
        store.add(dm)

        results = store.get_by_entity("John")
        assert len(results) == 1
        assert results[0].content == "John is an expert"

        results = store.get_by_entity("Unknown")
        assert len(results) == 0

    def test_get_by_source(self) -> None:
        """Test retrieving by source memory ID."""
        store = DerivedMemoryStore()
        dm = DerivedMemory(
            content="Derived from mem1",
            inference_type="induction",
            source_memory_ids=["mem1", "mem2"],
        )
        store.add(dm)

        results = store.get_by_source("mem1")
        assert len(results) == 1

        results = store.get_by_source("mem3")
        assert len(results) == 0

    def test_find_similar(self) -> None:
        """Test finding similar derived memories."""
        store = DerivedMemoryStore()
        dm = DerivedMemory(
            content="John is the best database expert at Google",
            inference_type="deduction",
        )
        store.add(dm)

        # Very similar content (high overlap)
        similar = store.find_similar("John is the best database expert at Google company", threshold=0.7)
        assert similar is not None

        # Different content
        different = store.find_similar("Sarah works in marketing department")
        assert different is None

    def test_prune_expired(self) -> None:
        """Test pruning expired memories."""
        store = DerivedMemoryStore()

        # Add expired memory
        dm1 = DerivedMemory(
            content="Expired",
            inference_type="summarization",
            expires_at=pendulum.now("UTC") - timedelta(days=1),
        )
        store.add(dm1)

        # Add valid memory
        dm2 = DerivedMemory(
            content="Valid",
            inference_type="summarization",
        )
        store.add(dm2)

        pruned = store.prune_expired()

        assert pruned == 1
        assert store.count() == 1
        assert store.get(dm2.id) is not None

    def test_prune_low_confidence(self) -> None:
        """Test pruning low confidence memories."""
        store = DerivedMemoryStore()

        dm1 = DerivedMemory(
            content="Low confidence",
            inference_type="induction",
            confidence_score=0.1,
        )
        store.add(dm1)

        dm2 = DerivedMemory(
            content="High confidence",
            inference_type="deduction",
            confidence_score=0.9,
        )
        store.add(dm2)

        pruned = store.prune_low_confidence(threshold=0.3)

        assert pruned == 1
        assert store.count() == 1
        assert store.get(dm2.id) is not None

    def test_remove(self) -> None:
        """Test removing a derived memory."""
        store = DerivedMemoryStore()
        dm = DerivedMemory(
            content="Test",
            inference_type="deduction",
            source_entities=["Entity1"],
        )
        store.add(dm)

        assert store.remove(dm.id)
        assert store.get(dm.id) is None
        assert len(store.get_by_entity("Entity1")) == 0

    def test_list_all(self) -> None:
        """Test listing all memories with confidence filter."""
        store = DerivedMemoryStore()

        for i, conf in enumerate([0.2, 0.5, 0.8]):
            dm = DerivedMemory(
                content=f"Memory {i}",
                inference_type="summarization",
                confidence_score=conf,
            )
            store.add(dm)

        all_memories = store.list_all()
        assert len(all_memories) == 3

        high_conf = store.list_all(min_confidence=0.6)
        assert len(high_conf) == 1


# ============================================================================
# ReasoningQuery Tests
# ============================================================================


class TestReasoningQuery:
    """Tests for ReasoningQuery DSL."""

    def test_create_query(self) -> None:
        """Test creating a reasoning query."""
        query = ReasoningQuery(
            goal="Who can help with database optimization?",
            constraints=ReasoningConstraints(
                entity_types=["Person"],
                memory_types=["knowledge", "tool"],
            ),
            reasoning_depth=2,
        )

        assert query.goal == "Who can help with database optimization?"
        assert query.constraints.entity_types == ["Person"]
        assert query.reasoning_depth == 2

    def test_query_defaults(self) -> None:
        """Test query default values."""
        query = ReasoningQuery(goal="Test goal")

        assert query.reasoning_depth == 2
        assert query.max_results == 10
        assert query.include_tool_stats is True
        assert query.write_derived is True

    def test_to_prompt_context(self) -> None:
        """Test converting query to prompt context."""
        query = ReasoningQuery(
            goal="Find experts",
            constraints=ReasoningConstraints(
                entity_types=["Person"],
                memory_types=["knowledge"],
            ),
        )

        context = query.to_prompt_context()

        assert "Find experts" in context
        assert "Person" in context
        assert "knowledge" in context


class TestReasoningTrace:
    """Tests for ReasoningTrace."""

    def test_add_step(self) -> None:
        """Test adding steps to trace."""
        query = ReasoningQuery(goal="Test")
        trace = ReasoningTrace(query=query)

        trace.add_step(
            action="retrieve",
            description="Retrieved 10 memories",
            output_data={"count": 10},
        )

        assert len(trace.steps) == 1
        assert trace.steps[0].action == "retrieve"
        assert trace.steps[0].step_number == 1

    def test_trace_metadata(self) -> None:
        """Test trace metadata tracking."""
        query = ReasoningQuery(goal="Test")
        trace = ReasoningTrace(query=query)

        trace.derived_memories_created = 3
        trace.total_memories_considered = 50
        trace.execution_time_ms = 1234.5

        assert trace.derived_memories_created == 3
        assert trace.total_memories_considered == 50
        assert trace.execution_time_ms == 1234.5


# ============================================================================
# MemoryReasoner Tests
# ============================================================================


class TestMemoryReasoner:
    """Tests for MemoryReasoner."""

    @pytest.fixture
    def mock_database(self) -> MagicMock:
        """Create a mock database."""
        db = MagicMock()
        db.memory_item_repo = MagicMock()
        db.memory_item_repo.list_items = MagicMock(return_value=[])
        return db

    @pytest.fixture
    def mock_knowledge_graph(self) -> MagicMock:
        """Create a mock knowledge graph."""
        kg = MagicMock()
        kg.find_matching_nodes = MagicMock(return_value=[])
        kg.get_subgraph_context = MagicMock(return_value=[])
        return kg

    @pytest.fixture
    def reasoner(self, mock_database: MagicMock, mock_knowledge_graph: MagicMock) -> MemoryReasoner:
        """Create a reasoner instance."""
        return MemoryReasoner(
            database=mock_database,
            knowledge_graph=mock_knowledge_graph,
        )

    def test_reasoner_init(self, mock_database: MagicMock) -> None:
        """Test reasoner initialization."""
        reasoner = MemoryReasoner(database=mock_database)

        assert reasoner.database is mock_database
        assert reasoner.derived_store is not None

    async def test_reason_empty_memories(self, reasoner: MemoryReasoner) -> None:
        """Test reasoning with no memories."""
        query = ReasoningQuery(goal="Find experts")

        trace = await reasoner.reason(query)

        assert trace.final_answer is not None
        assert "No conclusions" in trace.final_answer or len(trace.steps) > 0

    async def test_reason_with_memories(
        self,
        mock_database: MagicMock,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Test reasoning with memories."""
        # Setup mock memories
        mock_memory = MagicMock()
        mock_memory.id = "mem1"
        mock_memory.memory_type = "knowledge"
        mock_memory.summary = "John is a database expert at Google"
        mock_memory.created_at = pendulum.now("UTC")
        mock_memory.when_to_use = "database questions"
        mock_memory.metadata = None
        mock_memory.tool_calls = None

        mock_database.memory_item_repo.list_items.return_value = [mock_memory]

        # Setup mock graph
        mock_knowledge_graph.find_matching_nodes.return_value = ["John", "Google"]
        mock_knowledge_graph.get_subgraph_context.return_value = ["(Person) John --[works_at]--> (Organization) Google"]

        reasoner = MemoryReasoner(
            database=mock_database,
            knowledge_graph=mock_knowledge_graph,
        )

        query = ReasoningQuery(
            goal="Who can help with database optimization?",
            constraints=ReasoningConstraints(memory_types=["knowledge"]),
        )

        trace = await reasoner.reason(query)

        assert trace.total_memories_considered >= 1
        assert len(trace.steps) >= 1

    async def test_filter_by_memory_type(
        self,
        mock_database: MagicMock,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Test filtering memories by type."""
        # Create memories of different types
        mem1 = MagicMock()
        mem1.id = "mem1"
        mem1.memory_type = "knowledge"
        mem1.summary = "Knowledge memory"
        mem1.created_at = pendulum.now("UTC")
        mem1.when_to_use = None
        mem1.metadata = None
        mem1.tool_calls = None

        mem2 = MagicMock()
        mem2.id = "mem2"
        mem2.memory_type = "event"
        mem2.summary = "Event memory"
        mem2.created_at = pendulum.now("UTC")
        mem2.when_to_use = None
        mem2.metadata = None
        mem2.tool_calls = None

        mock_database.memory_item_repo.list_items.return_value = [mem1, mem2]

        reasoner = MemoryReasoner(
            database=mock_database,
            knowledge_graph=mock_knowledge_graph,
        )

        query = ReasoningQuery(
            goal="Test",
            constraints=ReasoningConstraints(memory_types=["knowledge"]),
        )

        trace = await reasoner.reason(query)

        # Check that filter step was executed
        filter_steps = [s for s in trace.steps if s.action == "filter"]
        assert len(filter_steps) == 1

    async def test_filter_by_time_range(
        self,
        mock_database: MagicMock,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Test filtering memories by time range."""
        # Recent memory
        mem1 = MagicMock()
        mem1.id = "mem1"
        mem1.memory_type = "knowledge"
        mem1.summary = "Recent memory"
        mem1.created_at = pendulum.now("UTC")
        mem1.when_to_use = None
        mem1.metadata = None
        mem1.tool_calls = None

        # Old memory
        mem2 = MagicMock()
        mem2.id = "mem2"
        mem2.memory_type = "knowledge"
        mem2.summary = "Old memory"
        mem2.created_at = pendulum.now("UTC") - timedelta(days=100)
        mem2.when_to_use = None
        mem2.metadata = None
        mem2.tool_calls = None

        mock_database.memory_item_repo.list_items.return_value = [mem1, mem2]

        reasoner = MemoryReasoner(
            database=mock_database,
            knowledge_graph=mock_knowledge_graph,
        )

        query = ReasoningQuery(
            goal="Test",
            constraints=ReasoningConstraints(time_range_days=30),
        )

        trace = await reasoner.reason(query)

        # Filter should have reduced count
        filter_steps = [s for s in trace.steps if s.action == "filter"]
        assert len(filter_steps) == 1

    async def test_tool_memory_scoring(
        self,
        mock_database: MagicMock,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Test scoring of tool memories."""
        # Tool memory with high success rate
        tool_mem = MagicMock()
        tool_mem.id = "tool1"
        tool_mem.memory_type = "tool"
        tool_mem.summary = "Database query tool"
        tool_mem.created_at = pendulum.now("UTC")
        tool_mem.when_to_use = "database queries"
        tool_mem.metadata = None
        tool_mem.tool_calls = [
            {"tool_name": "db_query", "success": True, "score": 0.9},
            {"tool_name": "db_query", "success": True, "score": 0.8},
            {"tool_name": "db_query", "success": False, "score": 0.2},
        ]

        mock_database.memory_item_repo.list_items.return_value = [tool_mem]

        reasoner = MemoryReasoner(
            database=mock_database,
            knowledge_graph=mock_knowledge_graph,
        )

        query = ReasoningQuery(
            goal="database query",
            include_tool_stats=True,
        )

        trace = await reasoner.reason(query)

        # Score step should have been executed
        score_steps = [s for s in trace.steps if s.action == "score"]
        assert len(score_steps) == 1

    def test_get_derived_memories(self, reasoner: MemoryReasoner) -> None:
        """Test retrieving derived memories."""
        # Add some derived memories
        dm1 = DerivedMemory(
            content="Test 1",
            inference_type="deduction",
            source_entities=["Entity1"],
            confidence_score=0.8,
        )
        dm2 = DerivedMemory(
            content="Test 2",
            inference_type="induction",
            source_entities=["Entity2"],
            confidence_score=0.3,
        )

        reasoner.derived_store.add(dm1)
        reasoner.derived_store.add(dm2)

        # Get all
        all_memories = reasoner.get_derived_memories()
        assert len(all_memories) == 2

        # Get by entity
        entity_memories = reasoner.get_derived_memories(entity="Entity1")
        assert len(entity_memories) == 1

        # Get with confidence filter
        high_conf = reasoner.get_derived_memories(min_confidence=0.5)
        assert len(high_conf) == 1

    def test_prune_derived_memories(self, reasoner: MemoryReasoner) -> None:
        """Test pruning derived memories."""
        # Add expired memory
        dm1 = DerivedMemory(
            content="Expired",
            inference_type="summarization",
            expires_at=pendulum.now("UTC") - timedelta(days=1),
        )
        reasoner.derived_store.add(dm1)

        # Add low confidence memory
        dm2 = DerivedMemory(
            content="Low conf",
            inference_type="induction",
            confidence_score=0.1,
        )
        reasoner.derived_store.add(dm2)

        # Add valid memory
        dm3 = DerivedMemory(
            content="Valid",
            inference_type="deduction",
            confidence_score=0.9,
        )
        reasoner.derived_store.add(dm3)

        results = reasoner.prune_derived_memories(expire=True, low_confidence_threshold=0.2)

        assert results["expired"] == 1
        assert results["low_confidence"] == 1
        assert reasoner.derived_store.count() == 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestReasonerIntegration:
    """Integration tests for the reasoning engine."""

    async def test_full_reasoning_flow(self) -> None:
        """Test complete reasoning flow without LLM."""
        # Create mock database with realistic data
        mock_db = MagicMock()

        memories = []
        for i in range(5):
            mem = MagicMock()
            mem.id = f"mem{i}"
            mem.memory_type = "knowledge"
            mem.summary = f"John is an expert in database optimization technique {i}"
            mem.created_at = pendulum.now("UTC")
            mem.when_to_use = "database questions"
            mem.metadata = None
            mem.tool_calls = None
            memories.append(mem)

        mock_db.memory_item_repo = MagicMock()
        mock_db.memory_item_repo.list_items = MagicMock(return_value=memories)

        # Create mock knowledge graph
        mock_kg = MagicMock()
        mock_kg.find_matching_nodes = MagicMock(return_value=["John"])
        mock_kg.get_subgraph_context = MagicMock(
            return_value=[
                "(Person) John --[expert_in]--> (Skill) Database",
                "(Person) John --[works_at]--> (Organization) TechCorp",
            ]
        )

        reasoner = MemoryReasoner(
            database=mock_db,
            knowledge_graph=mock_kg,
        )

        query = ReasoningQuery(
            goal="Who can help with database optimization?",
            reasoning_depth=2,
            max_results=5,
        )

        trace = await reasoner.reason(query)

        # Verify trace
        assert trace.final_answer is not None
        assert trace.total_memories_considered == 5
        assert trace.execution_time_ms > 0

        # Verify steps were executed
        actions = [s.action for s in trace.steps]
        assert "retrieve" in actions
        assert "traverse" in actions
        assert "filter" in actions
        assert "score" in actions

    async def test_reasoning_with_llm_mock(self) -> None:
        """Test reasoning with mocked LLM client."""
        mock_db = MagicMock()
        mem = MagicMock()
        mem.id = "mem1"
        mem.memory_type = "knowledge"
        mem.summary = "John is a database expert"
        mem.created_at = pendulum.now("UTC")
        mem.when_to_use = None
        mem.metadata = None
        mem.tool_calls = None
        mock_db.memory_item_repo = MagicMock()
        mock_db.memory_item_repo.list_items = MagicMock(return_value=[mem])

        mock_kg = MagicMock()
        mock_kg.find_matching_nodes = MagicMock(return_value=[])
        mock_kg.get_subgraph_context = MagicMock(return_value=[])

        # Mock LLM client
        mock_llm = AsyncMock()
        llm_response = (
            '{"conclusions": [{"content": "John is the best expert", '
            '"inference_type": "deduction", "confidence": 0.9, '
            '"reasoning": "Based on evidence", "source_ids": ["mem1"]}], '
            '"answer": "John"}'
        )
        mock_llm.summarize = AsyncMock(return_value=(llm_response, {}))

        reasoner = MemoryReasoner(
            database=mock_db,
            knowledge_graph=mock_kg,
            llm_client=mock_llm,
        )

        query = ReasoningQuery(goal="Who is the expert?")

        trace = await reasoner.reason(query)

        assert trace.final_answer is not None
        assert "John" in trace.final_answer or trace.derived_memories_created > 0


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
