PROMPT = """
Analyze the following audio transcription and provide two outputs:

## Transcription:
<transcription>
{transcription}
</transcription>

## Task:
1. **Processed Content**: Provide a clean, well-formatted version of the transcription with proper punctuation and paragraph breaks if needed
2. **Caption**: Provide a one-sentence summary describing what the audio is about

## Output Format:
<processed_content>
[Provide the cleaned and formatted transcription here]
</processed_content>

<caption>
[Provide a one-sentence summary of what the audio is about]
</caption>
"""
