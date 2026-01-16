"""LLM prompts for the Memory Reasoning Engine."""

INFERENCE_SYSTEM_PROMPT = """You are a Memory Reasoning Engine. Your task is to analyze memories \
and derive new knowledge through logical inference.

You will be given:
1. A reasoning goal (question to answer)
2. Retrieved memories (facts, events, knowledge)
3. Knowledge graph relationships (entity connections)
4. Tool execution statistics (if relevant)

Your job is to:
1. Analyze the provided information
2. Draw logical conclusions
3. Generate derived knowledge with confidence scores
4. Explain your reasoning

Rules:
- Only derive conclusions that are strongly supported by the evidence
- Assign confidence scores honestly (0.0-1.0)
- If evidence is insufficient, say so rather than guessing
- Distinguish between deduction (certain), induction (probable), and speculation (possible)
"""

INFERENCE_USER_PROMPT = """## Reasoning Goal
{goal}

## Retrieved Memories
{memories}

## Knowledge Graph Context
{graph_context}

## Tool Statistics (if relevant)
{tool_stats}

## Task
Based on the above information, derive conclusions that answer the reasoning goal.

For each conclusion, provide:
1. The derived knowledge (clear, concise statement)
2. Inference type: deduction | induction | summarization | analogy | aggregation
3. Confidence score (0.0-1.0)
4. Brief reasoning explanation
5. Source memory IDs used

Respond in this JSON format:
```json
{{
    "conclusions": [
        {{
            "content": "The derived knowledge statement",
            "inference_type": "deduction",
            "confidence": 0.85,
            "reasoning": "Brief explanation of how this was derived",
            "source_ids": ["id1", "id2"]
        }}
    ],
    "answer": "Direct answer to the reasoning goal",
    "insufficient_evidence": false,
    "missing_information": []
}}
```
"""

CONSISTENCY_CHECK_PROMPT = """You are verifying the consistency of a derived conclusion.

## Original Reasoning Goal
{goal}

## Derived Conclusion
{conclusion}

## Original Confidence
{original_confidence}

## Source Evidence
{evidence}

## Task
Independently evaluate whether this conclusion is valid based on the evidence.

Respond with:
```json
{{
    "is_consistent": true/false,
    "adjusted_confidence": 0.0-1.0,
    "issues": ["list of any issues found"],
    "reasoning": "Brief explanation"
}}
```
"""

ENTITY_RELEVANCE_PROMPT = """Given the reasoning goal, identify which entities are most relevant.

## Reasoning Goal
{goal}

## Available Entities
{entities}

## Task
Rank the entities by relevance to the goal. Return the top {limit} most relevant.

Respond with:
```json
{{
    "relevant_entities": [
        {{"name": "entity_name", "relevance_score": 0.9, "reason": "why relevant"}}
    ]
}}
```
"""

MEMORY_SCORING_PROMPT = """Score these memories by relevance to the reasoning goal.

## Reasoning Goal
{goal}

## Memories to Score
{memories}

## Task
Assign a relevance score (0.0-1.0) to each memory.

Respond with:
```json
{{
    "scores": [
        {{"id": "memory_id", "score": 0.85, "reason": "brief reason"}}
    ]
}}
```
"""


def build_inference_prompt(
    goal: str,
    memories: list[dict],
    graph_context: list[str],
    tool_stats: dict | None = None,
) -> str:
    """Build the inference prompt with all context."""
    # Format memories
    if memories:
        memories_text = "\n".join(
            f"- [{m.get('id', 'unknown')}] ({m.get('memory_type', 'unknown')}): {m.get('summary', '')}"
            for m in memories
        )
    else:
        memories_text = "No relevant memories found."

    # Format graph context
    if graph_context:
        graph_text = "\n".join(f"- {rel}" for rel in graph_context)
    else:
        graph_text = "No knowledge graph relationships found."

    # Format tool stats
    if tool_stats:
        stats_lines = []
        for tool_name, stats in tool_stats.items():
            stats_lines.append(
                f"- {tool_name}: success_rate={stats.get('success_rate', 0):.1%}, "
                f"avg_score={stats.get('avg_score', 0):.2f}, "
                f"total_calls={stats.get('total_calls', 0)}"
            )
        tool_text = "\n".join(stats_lines) if stats_lines else "No tool statistics available."
    else:
        tool_text = "No tool statistics available."

    return INFERENCE_USER_PROMPT.format(
        goal=goal,
        memories=memories_text,
        graph_context=graph_text,
        tool_stats=tool_text,
    )


def build_consistency_prompt(
    goal: str,
    conclusion: str,
    original_confidence: float,
    evidence: list[str],
) -> str:
    """Build the consistency check prompt."""
    evidence_text = "\n".join(f"- {e}" for e in evidence) if evidence else "No evidence provided."

    return CONSISTENCY_CHECK_PROMPT.format(
        goal=goal,
        conclusion=conclusion,
        original_confidence=original_confidence,
        evidence=evidence_text,
    )


__all__ = [
    "CONSISTENCY_CHECK_PROMPT",
    "ENTITY_RELEVANCE_PROMPT",
    "INFERENCE_SYSTEM_PROMPT",
    "INFERENCE_USER_PROMPT",
    "MEMORY_SCORING_PROMPT",
    "build_consistency_prompt",
    "build_inference_prompt",
]
