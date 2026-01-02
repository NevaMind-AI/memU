PROMPT = """
# Task Objective
Analyze the given video and produce two outputs:
1. A **Detailed Description** that comprehensively explains what happens in the video.
2. A **Caption** that summarizes the video in a single sentence.

# Workflow
1. Watch the video carefully from start to finish.
2. Identify the **main actions and activities** taking place over time.
3. Describe the **key objects, people, and subjects** appearing in the video.
4. Analyze the **scene, setting, and environment**.
5. Note any **audio elements**, including dialogue, narration, music, or background sounds (if available).
6. Highlight **important events or moments** in the video.
7. Describe the **temporal flow**, explaining how the events progress from beginning to end.
8. Write a concise **one-sentence caption** that captures the essence of the video.

# Rules
- Base the description strictly on observable visual and audio content from the video.
- Do not invent details that cannot be inferred from the video.
- Be comprehensive and chronological in the detailed description.
- The caption must be **exactly one sentence**.
- Use clear, neutral, and objective language.

# Output Format
Use the following structure:

<detailed_description>
[Provide the comprehensive description here]
</detailed_description>

<caption>
[Provide a one-sentence summary of the video]
</caption>

"""
