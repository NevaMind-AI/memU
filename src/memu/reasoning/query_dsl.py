"""Memory Query DSL - Structured queries over memory for reasoning."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReasoningConstraints(BaseModel):
    """Constraints for filtering memories during reasoning."""

    entity_types: list[str] | None = Field(
        default=None,
        description="Filter by entity types (Person, Organization, Place, Concept)",
    )
    memory_types: list[str] | None = Field(
        default=None,
        description="Filter by memory types (profile, event, knowledge, behavior, skill, tool)",
    )
    relationships: list[str] | None = Field(
        default=None,
        description="Filter by relationship types (works_at, married_to, knows, etc.)",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for memories",
    )
    time_range_days: int | None = Field(
        default=None,
        description="Only consider memories from the last N days",
    )
    require_tool_success: bool = Field(
        default=False,
        description="For tool memories, only consider successful executions",
    )
    min_tool_success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum success rate for tool memories",
    )


class ReasoningQuery(BaseModel):
    """
    Structured query for memory reasoning.

    Example:
        {
            "goal": "Who can help with database optimization?",
            "constraints": {
                "entity_types": ["Person"],
                "relationships": ["works_on", "expert_in"],
                "memory_types": ["knowledge", "tool"]
            },
            "reasoning_depth": 2,
            "max_results": 10
        }
    """

    goal: str = Field(..., description="The reasoning goal or question to answer")
    constraints: ReasoningConstraints = Field(
        default_factory=ReasoningConstraints,
        description="Constraints for filtering memories",
    )
    reasoning_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="How many hops to traverse in the knowledge graph",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    include_tool_stats: bool = Field(
        default=True,
        description="Include tool execution statistics in scoring",
    )
    write_derived: bool = Field(
        default=True,
        description="Whether to write derived memories back to storage",
    )

    def to_prompt_context(self) -> str:
        """Convert query to a context string for LLM prompts."""
        parts = [f"Goal: {self.goal}"]

        if self.constraints.entity_types:
            parts.append(f"Entity types: {', '.join(self.constraints.entity_types)}")
        if self.constraints.memory_types:
            parts.append(f"Memory types: {', '.join(self.constraints.memory_types)}")
        if self.constraints.relationships:
            parts.append(f"Relationships: {', '.join(self.constraints.relationships)}")
        if self.constraints.min_confidence > 0:
            parts.append(f"Min confidence: {self.constraints.min_confidence}")

        return "\n".join(parts)


InferenceStrategy = Literal["deduction", "induction", "abduction", "analogy"]


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain."""

    step_number: int
    action: Literal["retrieve", "traverse", "filter", "score", "infer", "write"]
    description: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ReasoningTrace(BaseModel):
    """Complete trace of a reasoning execution."""

    query: ReasoningQuery
    steps: list[ReasoningStep] = Field(default_factory=list)
    final_answer: str | None = None
    derived_memories_created: int = 0
    total_memories_considered: int = 0
    execution_time_ms: float = 0.0

    def add_step(
        self,
        action: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Add a step to the reasoning trace."""
        step = ReasoningStep(
            step_number=len(self.steps) + 1,
            action=action,  # type: ignore[arg-type]
            description=description,
            input_data=input_data or {},
            output_data=output_data or {},
            confidence=confidence,
        )
        self.steps.append(step)


__all__ = [
    "InferenceStrategy",
    "ReasoningConstraints",
    "ReasoningQuery",
    "ReasoningStep",
    "ReasoningTrace",
]
