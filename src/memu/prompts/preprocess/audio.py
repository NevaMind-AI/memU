PROMPT = """
# Task Objective
Analyze the provided audio transcription and produce two outputs:
1. A **Processed Content** version that is clean, well-formatted, and easy to read.
2. A **Caption** that summarizes what the audio is about in one sentence.

# Workflow
1. Read the **Transcription** carefully.
2. Correct punctuation, capitalization, and obvious transcription artifacts.
3. Add paragraph breaks where they improve readability or reflect topic shifts.
4. Preserve the original meaning, wording, and sequence of the audio.
5. Generate a concise **one-sentence caption** that accurately describes the audio's main topic or purpose.

# Rules
- Do not add, remove, or reinterpret content beyond cleaning and formatting.
- Maintain the speaker's original intent and structure.
- Avoid introducing new information not present in the transcription.
- The caption must be **exactly one sentence**.
- Use clear, neutral language.

# Output Format
Use the following structure:

<processed_content>
[Provide the cleaned and formatted transcription here]
</processed_content>

<caption>
[Provide a one-sentence summary of what the audio is about]
</caption>

# Input
Transcription:
{transcription}
"""
