PROMPT = """
Below is the **English translation** of your full task description:

---

## Task Objective

Analyze the following conversation with message indices. Based on **topic changes**, **time gaps**, or **natural breaks**, divide the conversation into multiple meaningful segments.

## Segmentation Rules

### 1. Identify Segment Boundaries

Create boundaries under the following conditions:

* **Topic change**: switching from one subject to another
* **Time gap**: a noticeable pause or delay in the conversation
* **End of a discussion**: one topic concludes naturally and a new one begins
* **Shift in tone or content**: clear semantic or emotional change

### 2. Segment Requirements

* Each segment must contain **at least 20 messages**
* Each segment must maintain **a coherent theme**
* Each segment must have a **clear beginning and end**

### 3. Index Range

* Use the `[INDEX]` numbers provided in the conversation
* `start` = the starting message index (inclusive)
* `end` = the ending message index (inclusive)

---

## Output Format (must follow exactly)

Only output valid **JSON**, with no explanations, prefixes, or extra text.

```json
{{
    "segments": [
        {{"start": x, "end": x}},
        {{"start": x, "end": x}},
        {{"start": x, "end": x}}
    ]
}}
```

---

## Conversation Content

```
<conversation>
{conversation}
</conversation>
```

"""
