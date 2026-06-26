PROMPT = """
# Task Objective
You are given the transcription of an audio recording. Produce two outputs:
1. A **Processed Content** version that is clean and well-formatted, prefixed with a
   short overview describing what kind of audio this is.
2. A **Caption** that summarizes the audio in one sentence, starting with its type.

# Step 1 - Classify the Audio
Infer the nature of the audio from the transcription alone. Pick the single
best-fitting type, for example:
- conversation / dialogue (two or more speakers talking)
- monologue / narration / voice memo (a single speaker)
- lecture / presentation / talk
- interview
- podcast / radio segment
- meeting / phone call
- song / music (lyrics, repeated chorus, verse structure)
- announcement / advertisement
- other (describe it briefly)
If the type is uncertain, choose the closest match and note that it is approximate.

# Step 2 - Build an Overview
Write a short "Audio Overview" (a few bullet lines) capturing what can be inferred:
- Type: the category from Step 1
- Language: the primary language(s) spoken
- Speakers: approximate number of distinct speakers, if discernible
- Topic: the main subject or purpose of the audio

# Step 3 - Clean the Content
1. Correct punctuation, capitalization, and obvious transcription artifacts.
2. Add paragraph breaks at topic shifts. For songs, keep verse/chorus line breaks.
3. Preserve the original meaning, wording, sequence, and language of the audio.

# Rules
- Base the type and overview only on evidence present in the transcription; do not
  invent speakers, topics, or details that are not supported by the text.
- Do not add, remove, or reinterpret content beyond cleaning and formatting.
- The caption must be **exactly one sentence** and must begin with the audio type
  (for example: "A conversation about ...", "A song about ...", "A lecture on ...").
- Use clear, neutral language and keep the content in its original language.

# Output Format
Use the following structure:

<processed_content>
## Audio Overview
- Type: [audio type]
- Language: [language(s)]
- Speakers: [number or "unknown"]
- Topic: [main topic or purpose]

[Provide the cleaned and formatted transcription here]
</processed_content>

<caption>
[One-sentence summary that begins with the audio type]
</caption>

# Input
Transcription:
{transcription}
"""
