PROMPT = """
# Task Objective
Analyze the given image and produce two outputs:
1. A **Detailed Description** that thoroughly explains what is shown in the image.
2. A **Caption** that summarizes the image in a single sentence.

# Workflow
1. Examine the image carefully.
2. Identify the **main subjects and objects** present.
3. Describe any **actions or activities** taking place.
4. Analyze the **setting, background, and environment**.
5. Note any **visible text, signs, or labels**.
6. Describe **colors, lighting, composition**, and visual layout.
7. Infer the **overall mood, atmosphere, or style** of the image.
8. Write a concise **one-sentence caption** that captures the essence of the image.

# Rules
- Base the description strictly on what is visible in the image.
- Do not invent details that cannot be inferred visually.
- Be comprehensive in the detailed description but clear and structured.
- The caption must be **exactly one sentence**.
- Use neutral and objective language.

# Output Format
Use the following structure:

<detailed_description>
[Provide the comprehensive description here]
</detailed_description>

<caption>
[Provide a one-sentence summary of the image]
</caption>
"""
