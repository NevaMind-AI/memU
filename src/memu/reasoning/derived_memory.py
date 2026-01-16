"""Derived Memory - Machine-generated knowledge from reasoning."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

import pendulum
from pydantic import BaseModel, Field

InferenceType = Literal["deduction", "induction", "summarization", "analogy", "aggregation"]


class DerivedMemory(BaseModel):
    """
    A memory that was derived through reasoning, not direct user input.

    These are "machine thoughts" - conclusions, insights, and aggregations
    that the system inferred from existing memories.

    Examples:
        - "John is the best DB contact" (derived from skills + tool success)
        - "This tool usually fails for X tasks" (derived from tool history)
        - "Project X depends on Y and Z" (derived from relationship traversal)
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., description="The derived knowledge/insight")
    inference_type: InferenceType = Field(
        ...,
        description="How this memory was derived",
    )
    source_memory_ids: list[str] = Field(
        default_factory=list,
        description="IDs of memories used to derive this",
    )
    source_entities: list[str] = Field(
        default_factory=list,
        description="Entity names involved in the derivation",
    )
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this derived knowledge",
    )
    reasoning_trace: str | None = Field(
        default=None,
        description="Human-readable explanation of how this was derived",
    )
    query_goal: str | None = Field(
        default=None,
        description="The original reasoning goal that produced this",
    )
    consistency_checks: int = Field(
        default=1,
        ge=1,
        description="Number of times inference was verified for consistency",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration for time-sensitive derived knowledge",
    )
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    last_verified_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))

    def is_expired(self) -> bool:
        """Check if this derived memory has expired."""
        if self.expires_at is None:
            return False
        now = pendulum.now("UTC")
        return now > self.expires_at

    def reinforce(self) -> None:
        """Reinforce this derived memory (increase confidence, update verification time)."""
        self.confidence_score = min(1.0, self.confidence_score + 0.1)
        self.consistency_checks += 1
        self.last_verified_at = pendulum.now("UTC")

    def weaken(self) -> None:
        """Weaken this derived memory (decrease confidence)."""
        self.confidence_score = max(0.0, self.confidence_score - 0.15)
        self.last_verified_at = pendulum.now("UTC")

    def to_memory_summary(self) -> str:
        """Convert to a summary string suitable for storage as a MemoryItem."""
        confidence_label = (
            "high confidence"
            if self.confidence_score >= 0.8
            else "medium confidence"
            if self.confidence_score >= 0.5
            else "low confidence"
        )
        return f"[Derived - {self.inference_type}, {confidence_label}] {self.content}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "inference_type": self.inference_type,
            "source_memory_ids": self.source_memory_ids,
            "source_entities": self.source_entities,
            "confidence_score": self.confidence_score,
            "reasoning_trace": self.reasoning_trace,
            "query_goal": self.query_goal,
            "consistency_checks": self.consistency_checks,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_verified_at": self.last_verified_at.isoformat(),
        }


class DerivedMemoryStore:
    """In-memory store for derived memories with lookup capabilities."""

    def __init__(self) -> None:
        self._memories: dict[str, DerivedMemory] = {}
        self._by_entity: dict[str, set[str]] = {}  # entity_name -> memory_ids
        self._by_source: dict[str, set[str]] = {}  # source_memory_id -> derived_memory_ids

    def add(self, memory: DerivedMemory) -> None:
        """Add a derived memory to the store."""
        self._memories[memory.id] = memory

        # Index by entities
        for entity in memory.source_entities:
            if entity not in self._by_entity:
                self._by_entity[entity] = set()
            self._by_entity[entity].add(memory.id)

        # Index by source memories
        for source_id in memory.source_memory_ids:
            if source_id not in self._by_source:
                self._by_source[source_id] = set()
            self._by_source[source_id].add(memory.id)

    def get(self, memory_id: str) -> DerivedMemory | None:
        """Get a derived memory by ID."""
        return self._memories.get(memory_id)

    def get_by_entity(self, entity_name: str) -> list[DerivedMemory]:
        """Get all derived memories involving an entity."""
        memory_ids = self._by_entity.get(entity_name, set())
        return [self._memories[mid] for mid in memory_ids if mid in self._memories]

    def get_by_source(self, source_memory_id: str) -> list[DerivedMemory]:
        """Get all derived memories that used a specific source memory."""
        memory_ids = self._by_source.get(source_memory_id, set())
        return [self._memories[mid] for mid in memory_ids if mid in self._memories]

    def find_similar(self, content: str, threshold: float = 0.8) -> DerivedMemory | None:
        """Find an existing derived memory with similar content (for deduplication)."""
        content_lower = content.lower().strip()
        content_words = set(content_lower.split())

        for memory in self._memories.values():
            existing_words = set(memory.content.lower().split())
            if not content_words or not existing_words:
                continue

            # Jaccard similarity
            intersection = len(content_words & existing_words)
            union = len(content_words | existing_words)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= threshold:
                return memory

        return None

    def prune_expired(self) -> int:
        """Remove expired derived memories. Returns count of removed."""
        expired_ids = [mid for mid, m in self._memories.items() if m.is_expired()]
        for mid in expired_ids:
            self.remove(mid)
        return len(expired_ids)

    def prune_low_confidence(self, threshold: float = 0.2) -> int:
        """Remove low-confidence derived memories. Returns count of removed."""
        low_conf_ids = [mid for mid, m in self._memories.items() if m.confidence_score < threshold]
        for mid in low_conf_ids:
            self.remove(mid)
        return len(low_conf_ids)

    def remove(self, memory_id: str) -> bool:
        """Remove a derived memory from the store."""
        if memory_id not in self._memories:
            return False

        memory = self._memories[memory_id]

        # Remove from entity index
        for entity in memory.source_entities:
            if entity in self._by_entity:
                self._by_entity[entity].discard(memory_id)

        # Remove from source index
        for source_id in memory.source_memory_ids:
            if source_id in self._by_source:
                self._by_source[source_id].discard(memory_id)

        del self._memories[memory_id]
        return True

    def list_all(self, min_confidence: float = 0.0) -> list[DerivedMemory]:
        """List all derived memories, optionally filtered by confidence."""
        return [m for m in self._memories.values() if m.confidence_score >= min_confidence]

    def count(self) -> int:
        """Return total count of derived memories."""
        return len(self._memories)

    def clear(self) -> None:
        """Clear all derived memories."""
        self._memories.clear()
        self._by_entity.clear()
        self._by_source.clear()


__all__ = [
    "DerivedMemory",
    "DerivedMemoryStore",
    "InferenceType",
]
