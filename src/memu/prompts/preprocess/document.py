PROMPT = """
Analyze the following document text and provide two outputs:

## Document:
<document>
{document_text}
</document>

## Task:
1. **Processed Content**: Provide a condensed version of the document that preserves all key information, main points, and important details while removing verbosity and redundancy
2. **Caption**: Provide a one-sentence summary describing what the document is about

## Output Format:
<processed_content>
[Provide the condensed version of the document here]
</processed_content>

<caption>
[Provide a one-sentence summary of the document]
</caption>
"""
