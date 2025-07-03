#!/usr/bin/env python3
"""
Memory Update Pipeline Demo (Step-by-Step)

This example illustrates how PersonaLab's `MemoryUpdatePipeline` works internally.
It feeds a sample conversation to the pipeline and prints the result of each stage:

1. Modification stage – extract possible profile/event updates from the conversation.
2. Update stage – merge the suggested updates into the existing memory.
3. Theory-of-Mind stage – generate psychological insights.

To keep the demo fully offline and runnable without API keys, we use `CustomLLMClient`
with a very small mock function that returns deterministic answers depending on the
prompt it receives.  If you want to see real LLM outputs instead, replace the
`mock_llm_function` with `OpenAIClient.from_env()` (requires an OpenAI API key in
`OPENAI_API_KEY`).
"""

from __future__ import annotations

from typing import Dict, List

from personalab.llm import OpenAIClient
from personalab.memory import EventMemory, Memory, MemoryUpdatePipeline, ProfileMemory

# ---------------------------------------------------------------------------
# 1. Initialize OpenAI client (requires OPENAI_API_KEY environment variable)
# ---------------------------------------------------------------------------

openai_client = OpenAIClient.from_env()

# ---------------------------------------------------------------------------
# 2. Prepare initial memory and sample conversation
# ---------------------------------------------------------------------------

# Existing memory for the user
initial_profile = "Name: Alice\n- Likes: Reading"
initial_events = [
    "Alice finished reading 'Pride and Prejudice' last week.",
]

memory = Memory(agent_id="demo_agent", user_id="alice")
memory.profile_memory = ProfileMemory(initial_profile)
memory.event_memory = EventMemory(events=initial_events)

# ----- Define multiple sessions (each session is a list of messages) -----

sessions: List[List[Dict[str, str]]] = [
    # Session 1 – hiking & spring
    [
        {
            "role": "user",
            "content": "I can't wait for spring! I'm already planning a hiking trip to the Alps.",
        },
        {
            "role": "assistant",
            "content": "That sounds exciting! The Alps are beautiful during spring.",
        },
    ],
    # Session 2 – new hobby: guitar
    [
        {
            "role": "user",
            "content": "Guess what—I just bought a guitar and started taking lessons!",
        },
        {
            "role": "assistant",
            "content": "Nice! Learning guitar can be really fun and rewarding.",
        },
    ],
    # Session 3 – favourite foods discussion
    [
        {
            "role": "user",
            "content": "My favorite food has to be sushi. I could eat it every day!",
        },
        {
            "role": "assistant",
            "content": "Sushi is delicious—do you prefer nigiri or rolls?",
        },
    ],
]

# ---------------------------------------------------------------------------
# 3. Run the pipeline for each session and display results
# ---------------------------------------------------------------------------

pipeline = MemoryUpdatePipeline(llm_client=openai_client)

for idx, conversation in enumerate(sessions, start=1):
    print("\n" + "=" * 80)
    print(f"Session {idx}: processing {len(conversation)} messages")
    print("-" * 80)

    updated_memory, pipeline_result = pipeline.update_with_pipeline(
        memory, conversation
    )

    # Stage outputs
    print("\n--- Modification Stage Output ---")
    print(pipeline_result.modification_result.strip())

    print("\n--- Update Stage Output ---")
    print(pipeline_result.update_result.raw_llm_response.strip())

    print("\n--- Theory-of-Mind Stage Output ---")
    print(pipeline_result.mind_result.insights.strip())

    print("\n--- Memory Snapshot After Session ---")
    print(updated_memory.to_prompt())

    # Use the updated memory for the next session
    memory = updated_memory

print("\n" + "=" * 80)
print("All sessions processed.")
print("Final memory:\n")
print(memory.to_prompt())
