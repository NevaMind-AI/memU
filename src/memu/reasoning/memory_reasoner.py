"""Memory Reasoning Engine - Core reasoning logic."""

from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pendulum

from memu.reasoning.derived_memory import DerivedMemory, DerivedMemoryStore
from memu.reasoning.prompts import INFERENCE_SYSTEM_PROMPT, build_consistency_prompt, build_inference_prompt
from memu.reasoning.query_dsl import ReasoningQuery, ReasoningTrace

if TYPE_CHECKING:
    from memu.database.interfaces import Database
    from memu.database.knowledge_graph import KnowledgeGraph
    from memu.llm.http_client import HTTPLLMClient

logger = logging.getLogger(__name__)


class MemoryReasoner:
    """
    Memory Reasoning Engine - Inference over memory to generate derived knowledge.

    This is the core component that transforms MemU from a retrieval system
    into a reasoning system. It:
    1. Accepts structured queries over memory
    2. Retrieves and traverses relevant memories and graph relationships
    3. Scores candidates using salience, tool stats, and relevance
    4. Runs LLM-assisted inference to derive new knowledge
    5. Writes derived memories back to storage

    The reasoning loop:
    RETRIEVE → TRAVERSE → FILTER → SCORE → INFER → WRITE BACK
    """

    def __init__(
        self,
        database: Database,
        knowledge_graph: KnowledgeGraph | None = None,
        llm_client: HTTPLLMClient | None = None,
        derived_store: DerivedMemoryStore | None = None,
    ) -> None:
        """
        Initialize the Memory Reasoner.

        Args:
            database: The memory database for retrieving memories
            knowledge_graph: Optional knowledge graph for relationship traversal
            llm_client: Optional LLM client for inference (required for full reasoning)
            derived_store: Optional store for derived memories
        """
        self.database = database
        self.knowledge_graph = knowledge_graph
        self.llm_client = llm_client
        self.derived_store = derived_store or DerivedMemoryStore()

    async def reason(self, query: ReasoningQuery) -> ReasoningTrace:
        """
        Execute a reasoning query over memory.

        This is the main entry point for the reasoning engine.

        Args:
            query: The structured reasoning query

        Returns:
            ReasoningTrace with steps, answer, and derived memories
        """
        start_time = time.time()
        trace = ReasoningTrace(query=query)

        try:
            # Step 1: RETRIEVE - Get candidate memories
            memories = await self._retrieve_memories(query, trace)

            # Step 2: TRAVERSE - Get graph context
            graph_context = self._traverse_graph(query, memories, trace)

            # Step 3: FILTER - Apply constraints
            filtered_memories = self._filter_memories(query, memories, trace)

            # Step 4: SCORE - Rank by relevance
            scored_memories = self._score_memories(query, filtered_memories, graph_context, trace)

            # Step 5: INFER - Run LLM inference
            conclusions = await self._infer(query, scored_memories, graph_context, trace)

            # Step 6: WRITE BACK - Store derived memories
            if query.write_derived and conclusions:
                await self._write_derived_memories(query, conclusions, trace)

            # Build final answer
            trace.final_answer = self._build_answer(conclusions)
            trace.total_memories_considered = len(memories)

        except Exception as e:
            logger.exception("Reasoning failed for query: %s", query.goal)
            trace.add_step(
                action="infer",
                description=f"Reasoning failed: {e!s}",
                confidence=0.0,
            )
            trace.final_answer = f"Reasoning failed: {e!s}"

        trace.execution_time_ms = (time.time() - start_time) * 1000
        return trace

    async def _retrieve_memories(
        self,
        query: ReasoningQuery,
        trace: ReasoningTrace,
    ) -> list[dict[str, Any]]:
        """Retrieve candidate memories from the database."""
        memories = []

        # Get all memory items
        all_items = self.database.memory_item_repo.list_items({})

        for item in all_items:
            memory_dict = {
                "id": item.id,
                "memory_type": item.memory_type,
                "summary": item.summary,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "when_to_use": getattr(item, "when_to_use", None),
                "metadata": getattr(item, "metadata", None),
                "tool_calls": getattr(item, "tool_calls", None),
            }
            memories.append(memory_dict)

        trace.add_step(
            action="retrieve",
            description=f"Retrieved {len(memories)} candidate memories",
            output_data={"count": len(memories)},
        )

        return memories

    def _traverse_graph(
        self,
        query: ReasoningQuery,
        memories: list[dict[str, Any]],
        trace: ReasoningTrace,
    ) -> list[str]:
        """Traverse knowledge graph for relationship context."""
        if not self.knowledge_graph:
            trace.add_step(
                action="traverse",
                description="No knowledge graph available, skipping traversal",
            )
            return []

        graph_context: list[str] = []
        entities_found: set[str] = set()

        # Extract entity names from memories
        for memory in memories:
            summary = memory.get("summary", "")
            # Simple entity extraction from summary (proper nouns)
            words = summary.split()
            for word in words:
                clean_word = word.strip(".,!?\"'()[]")
                if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                    matches = self.knowledge_graph.find_matching_nodes(clean_word)
                    entities_found.update(matches[:3])  # Limit matches per word

        # Get subgraph context for each entity
        for entity in list(entities_found)[:10]:  # Limit to top 10 entities
            context = self.knowledge_graph.get_subgraph_context(entity, depth=query.reasoning_depth)
            graph_context.extend(context)

        # Deduplicate
        graph_context = list(dict.fromkeys(graph_context))

        trace.add_step(
            action="traverse",
            description=f"Traversed graph for {len(entities_found)} entities, found {len(graph_context)} relationships",
            input_data={"entities": list(entities_found)[:10]},
            output_data={"relationships": len(graph_context)},
        )

        return graph_context[:50]  # Limit context size

    def _filter_memories(
        self,
        query: ReasoningQuery,
        memories: list[dict[str, Any]],
        trace: ReasoningTrace,
    ) -> list[dict[str, Any]]:
        """Apply query constraints to filter memories."""
        filtered = memories.copy()
        constraints = query.constraints

        # Filter by memory type
        if constraints.memory_types:
            filtered = [m for m in filtered if m.get("memory_type") in constraints.memory_types]

        # Filter by time range
        if constraints.time_range_days:
            cutoff = pendulum.now("UTC") - timedelta(days=constraints.time_range_days)
            new_filtered = []
            for m in filtered:
                created_at = m.get("created_at")
                if created_at:
                    try:
                        created_dt = pendulum.parse(created_at) if isinstance(created_at, str) else created_at
                        if created_dt >= cutoff:
                            new_filtered.append(m)
                    except Exception:
                        new_filtered.append(m)  # Keep if can't parse
                else:
                    new_filtered.append(m)
            filtered = new_filtered

        # Filter tool memories by success
        if constraints.require_tool_success:
            new_filtered = []
            for m in filtered:
                if m.get("memory_type") != "tool":
                    new_filtered.append(m)
                else:
                    tool_calls = m.get("tool_calls") or []
                    if any(tc.get("success", True) for tc in tool_calls):
                        new_filtered.append(m)
            filtered = new_filtered

        trace.add_step(
            action="filter",
            description=f"Filtered from {len(memories)} to {len(filtered)} memories",
            input_data={"original_count": len(memories)},
            output_data={"filtered_count": len(filtered)},
        )

        return filtered

    def _score_memories(
        self,
        query: ReasoningQuery,
        memories: list[dict[str, Any]],
        graph_context: list[str],
        trace: ReasoningTrace,
    ) -> list[dict[str, Any]]:
        """Score and rank memories by relevance."""
        scored = []
        goal_words = set(query.goal.lower().split())

        for memory in memories:
            score = 0.0

            # Text relevance (simple word overlap)
            summary = memory.get("summary", "").lower()
            summary_words = set(summary.split())
            if goal_words and summary_words:
                overlap = len(goal_words & summary_words)
                score += overlap / len(goal_words) * 0.4

            # when_to_use relevance
            when_to_use = memory.get("when_to_use", "") or ""
            if when_to_use:
                when_words = set(when_to_use.lower().split())
                if goal_words and when_words:
                    overlap = len(goal_words & when_words)
                    score += overlap / len(goal_words) * 0.3

            # Tool success rate bonus
            if memory.get("memory_type") == "tool" and query.include_tool_stats:
                tool_calls = memory.get("tool_calls") or []
                if tool_calls:
                    success_count = sum(1 for tc in tool_calls if tc.get("success", True))
                    success_rate = success_count / len(tool_calls)
                    score += success_rate * 0.2

            # Graph connectivity bonus
            summary_upper_words = [w for w in memory.get("summary", "").split() if w and w[0].isupper()]
            for word in summary_upper_words:
                for rel in graph_context:
                    if word.lower() in rel.lower():
                        score += 0.1
                        break

            memory["_relevance_score"] = min(1.0, score)
            scored.append(memory)

        # Sort by score
        scored.sort(key=lambda m: m.get("_relevance_score", 0), reverse=True)

        # Limit results
        top_memories = scored[: query.max_results]

        trace.add_step(
            action="score",
            description=f"Scored {len(memories)} memories, top score: {top_memories[0].get('_relevance_score', 0):.2f}"
            if top_memories
            else "No memories to score",
            output_data={
                "top_scores": [{"id": m.get("id"), "score": m.get("_relevance_score", 0)} for m in top_memories[:5]]
            },
        )

        return top_memories

    async def _infer(
        self,
        query: ReasoningQuery,
        memories: list[dict[str, Any]],
        graph_context: list[str],
        trace: ReasoningTrace,
    ) -> list[dict[str, Any]]:
        """Run LLM-assisted inference to derive conclusions."""
        if not self.llm_client:
            # Fallback: simple aggregation without LLM
            trace.add_step(
                action="infer",
                description="No LLM client available, using simple aggregation",
                confidence=0.5,
            )
            return self._simple_inference(query, memories, graph_context)

        # Build tool stats if relevant
        tool_stats = {}
        for memory in memories:
            if memory.get("memory_type") == "tool":
                tool_calls = memory.get("tool_calls") or []
                if tool_calls:
                    tool_name = tool_calls[0].get("tool_name", "unknown") if tool_calls else "unknown"
                    success_count = sum(1 for tc in tool_calls if tc.get("success", True))
                    total_score = sum(tc.get("score", 0) for tc in tool_calls)
                    tool_stats[tool_name] = {
                        "success_rate": success_count / len(tool_calls) if tool_calls else 0,
                        "avg_score": total_score / len(tool_calls) if tool_calls else 0,
                        "total_calls": len(tool_calls),
                    }

        # Build inference prompt
        prompt = build_inference_prompt(
            goal=query.goal,
            memories=memories,
            graph_context=graph_context,
            tool_stats=tool_stats if tool_stats else None,
        )

        try:
            response, _ = await self.llm_client.summarize(
                text=prompt,
                system_prompt=INFERENCE_SYSTEM_PROMPT,
                max_tokens=2000,
            )

            # Parse JSON response
            conclusions = self._parse_inference_response(response)

            trace.add_step(
                action="infer",
                description=f"LLM inference produced {len(conclusions)} conclusions",
                output_data={"conclusions_count": len(conclusions)},
                confidence=0.8,
            )

            return conclusions

        except Exception as e:
            logger.warning("LLM inference failed: %s, falling back to simple inference", e)
            trace.add_step(
                action="infer",
                description=f"LLM inference failed ({e}), using simple aggregation",
                confidence=0.4,
            )
            return self._simple_inference(query, memories, graph_context)

    def _simple_inference(
        self,
        query: ReasoningQuery,
        memories: list[dict[str, Any]],
        graph_context: list[str],
    ) -> list[dict[str, Any]]:
        """Simple inference without LLM - aggregation and summarization."""
        conclusions = []

        if not memories:
            return conclusions

        # Aggregate by memory type
        by_type: dict[str, list[str]] = {}
        for memory in memories:
            mtype = memory.get("memory_type", "unknown")
            if mtype not in by_type:
                by_type[mtype] = []
            by_type[mtype].append(memory.get("summary", ""))

        # Create aggregation conclusions
        for mtype, summaries in by_type.items():
            if len(summaries) >= 2:
                conclusions.append({
                    "content": f"Found {len(summaries)} {mtype} memories relevant to: {query.goal}",
                    "inference_type": "aggregation",
                    "confidence": 0.5,
                    "reasoning": f"Aggregated {len(summaries)} memories of type {mtype}",
                    "source_ids": [m.get("id") for m in memories if m.get("memory_type") == mtype],
                })

        # If we have graph context, note the relationships
        if graph_context:
            conclusions.append({
                "content": f"Found {len(graph_context)} entity relationships relevant to the query",
                "inference_type": "summarization",
                "confidence": 0.4,
                "reasoning": "Summarized knowledge graph relationships",
                "source_ids": [],
            })

        return conclusions

    def _parse_inference_response(self, response: str) -> list[dict[str, Any]]:
        """Parse the LLM inference response."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return data.get("conclusions", [])
        except json.JSONDecodeError:
            pass

        # Fallback: return empty if can't parse
        logger.warning("Could not parse inference response as JSON")
        return []

    async def _write_derived_memories(
        self,
        query: ReasoningQuery,
        conclusions: list[dict[str, Any]],
        trace: ReasoningTrace,
    ) -> None:
        """Write derived memories back to storage."""
        created_count = 0

        for conclusion in conclusions:
            content = conclusion.get("content", "")
            if not content:
                continue

            # Check for duplicates
            existing = self.derived_store.find_similar(content)
            if existing:
                # Reinforce existing memory
                existing.reinforce()
                continue

            # Create new derived memory
            inference_type = conclusion.get("inference_type", "summarization")
            if inference_type not in ("deduction", "induction", "summarization", "analogy", "aggregation"):
                inference_type = "summarization"

            derived = DerivedMemory(
                content=content,
                inference_type=inference_type,  # type: ignore[arg-type]
                source_memory_ids=conclusion.get("source_ids", []),
                confidence_score=conclusion.get("confidence", 0.5),
                reasoning_trace=conclusion.get("reasoning", ""),
                query_goal=query.goal,
            )

            self.derived_store.add(derived)
            created_count += 1

        trace.derived_memories_created = created_count
        trace.add_step(
            action="write",
            description=f"Created {created_count} derived memories",
            output_data={"created": created_count, "total_in_store": self.derived_store.count()},
        )

    def _build_answer(self, conclusions: list[dict[str, Any]]) -> str:
        """Build the final answer from conclusions."""
        if not conclusions:
            return "No conclusions could be derived from the available memories."

        # Find the highest confidence conclusion
        best = max(conclusions, key=lambda c: c.get("confidence", 0))
        answer_parts = [best.get("content", "")]

        # Add supporting conclusions
        for conclusion in conclusions:
            if conclusion != best and conclusion.get("confidence", 0) >= 0.5:
                answer_parts.append(f"Additionally: {conclusion.get('content', '')}")

        return " ".join(answer_parts)

    async def verify_consistency(
        self,
        derived_memory: DerivedMemory,
        num_checks: int = 3,
    ) -> float:
        """
        Verify consistency of a derived memory by re-running inference.

        Args:
            derived_memory: The derived memory to verify
            num_checks: Number of verification runs

        Returns:
            Adjusted confidence score
        """
        if not self.llm_client:
            return derived_memory.confidence_score

        consistent_count = 0
        total_confidence = 0.0

        for _ in range(num_checks):
            prompt = build_consistency_prompt(
                goal=derived_memory.query_goal or "",
                conclusion=derived_memory.content,
                original_confidence=derived_memory.confidence_score,
                evidence=[f"Source: {sid}" for sid in derived_memory.source_memory_ids],
            )

            try:
                response, _ = await self.llm_client.summarize(
                    text=prompt,
                    system_prompt="You are verifying the consistency of a derived conclusion.",
                    max_tokens=500,
                )

                # Parse response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response[json_start:json_end])
                    if data.get("is_consistent", False):
                        consistent_count += 1
                    total_confidence += data.get("adjusted_confidence", derived_memory.confidence_score)

            except Exception as e:
                logger.warning("Consistency check failed: %s", e)
                total_confidence += derived_memory.confidence_score

        # Calculate final confidence
        consistency_ratio = consistent_count / num_checks
        avg_confidence = total_confidence / num_checks

        # Blend original confidence with verification results
        final_confidence = (derived_memory.confidence_score * 0.3) + (avg_confidence * 0.4) + (consistency_ratio * 0.3)

        # Update the derived memory
        if final_confidence > derived_memory.confidence_score:
            derived_memory.reinforce()
        elif final_confidence < derived_memory.confidence_score - 0.1:
            derived_memory.weaken()

        derived_memory.consistency_checks += num_checks

        return final_confidence

    def get_derived_memories(
        self,
        entity: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[DerivedMemory]:
        """Get derived memories, optionally filtered."""
        if entity:
            return [m for m in self.derived_store.get_by_entity(entity) if m.confidence_score >= min_confidence]
        return self.derived_store.list_all(min_confidence=min_confidence)

    def prune_derived_memories(
        self,
        expire: bool = True,
        low_confidence_threshold: float = 0.2,
    ) -> dict[str, int]:
        """Prune expired and low-confidence derived memories."""
        results = {"expired": 0, "low_confidence": 0}

        if expire:
            results["expired"] = self.derived_store.prune_expired()

        results["low_confidence"] = self.derived_store.prune_low_confidence(low_confidence_threshold)

        return results


__all__ = ["MemoryReasoner"]
