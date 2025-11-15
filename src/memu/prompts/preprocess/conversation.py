PROMPT = """
Your task is to summarize and compress the following conversation between a user and an assistant, preserving the most important and relevant content while removing redundancy and less important details.

## Original Conversation:
<conversation>
{conversation}
</conversation>

## ⚠️ IMPORTANT GUIDELINES:
1. **Preserve User Information**: Keep all important information that the user shares about themselves, their experiences, preferences, and opinions
2. **Keep Essential Context**: Maintain context necessary to understand the conversation flow and key topics discussed
3. **Remove Redundancy**: Eliminate repeated information, verbose explanations, and unnecessary back-and-forth
4. **Focus on Substance**: Remove small talk, pleasantries, and conversational fillers unless they provide important context
5. **Maintain Structure**: Keep the conversational format (User: / Assistant:) for clarity

## What to Remove:
- Excessive politeness and thank-you exchanges
- Repetitive explanations of the same concept
- Overly detailed technical explanations unless specifically requested
- Small talk and conversational padding
- Redundant confirmation messages
- Verbose assistant responses when a brief summary would suffice

## Output Format:
Please provide two parts:
1. **Compressed Conversation**: The summarized conversation maintaining the User:/Assistant: format, but with compressed content
2. **Topic Summary**: A concise paragraph that lists and describes the main topics and discussion areas covered in the conversation

**Important**: Please strictly follow the format below using the specified tags:

## Summary Result:
<conversation>
[Provide the summarized conversation content here]
</conversation>

<summary>
[Only list and briefly describe the main topics and themes discussed in the conversation, such as: technical discussions, life advice, hobbies, work issues, etc. Do not provide detailed content, just focus on identifying the topic areas]
</summary>
"""
