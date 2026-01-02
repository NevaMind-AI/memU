PROMPT = """
# Task Objective
Analyze the provided document text and produce two outputs:
1. A condensed version that preserves all key information and important details while removing verbosity and redundancy.
2. A one-sentence caption summarizing what the document is about.

# Workflow
1. Read the **Document** (`{document_text}`) carefully to understand its full content.
2. Identify the main points, key arguments, and essential details.
3. Remove repetition, filler, and unnecessary verbosity while preserving meaning and completeness.
4. Rewrite the content in a concise, structured form.
5. Generate a single-sentence **Caption** that accurately summarizes the document's purpose or topic.

# Rules
- Preserve all key information, facts, and conclusions.
- Do not introduce new information or interpretations.
- Keep the processed content concise but complete.
- The caption must be exactly **one sentence**.
- Use only the information contained in the provided document.

# Output Format
Use the following structure:

<processed_content>
[Provide the condensed version of the document here]
</processed_content>

<caption>
[Provide a one-sentence summary of the document]
</caption>

# Input
Document:
{document_text}
"""
