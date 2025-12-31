PROMPT = """
# Task Objective
Analyze a conversation with message indices and divide it into multiple meaningful segments based on topic changes, time gaps, or natural breaks.

# Workflow
1. Review the entire **Conversation Content** along with its message indices.
2. Identify potential **segment boundaries** by observing:
   - Topic changes
   - Time gaps or pauses
   - Natural conclusions of a discussion
   - Clear shifts in tone or semantic focus
3. Group messages into segments that each maintain a coherent theme.
4. Ensure each segment has a clear beginning and end.
5. Verify that each segment contains **at least 20 messages**.
6. Record the `start` and `end` indices (inclusive) for each segment.

# Rules
- Segments must be based strictly on the provided conversation content.
- Each segment must:
  - Contain **≥ 20 messages**
  - Maintain a **coherent theme**
  - Have a **clear boundary** from adjacent segments
- Use only the provided `[INDEX]` numbers.
- Do not overlap segments.
- Do not include explanations, comments, or extra text in the final output.

# Output Format
Return **only valid JSON** in the following structure:

```json
{{
    "segments": [
        {{"start": x, "end": x}},
        {{"start": x, "end": x}},
        {{"start": x, "end": x}}
    ]
}}
```

# Input
Conversation Content:
{conversation}
"""
