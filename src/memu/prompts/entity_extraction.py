"""LLM prompt for extracting entities and relationships from text."""

PROMPT = """You are an expert at extracting structured knowledge from text. Your task is to identify entities and their relationships.

## Input Text:
{text}

## Instructions:
1. Extract all named entities (people, organizations, places, concepts, products, events)
2. Identify relationships between entities as subject-predicate-object triples
3. Use clear, consistent relationship predicates (e.g., works_at, lives_in, married_to, created_by)

## Entity Types:
- Person: Individual people (e.g., "John Smith", "Dr. Watson")
- Organization: Companies, institutions, teams (e.g., "Google", "MIT")
- Place: Locations, cities, countries (e.g., "San Francisco", "Japan")
- Concept: Abstract ideas, topics, skills (e.g., "machine learning", "Python")
- Product: Software, tools, products (e.g., "iPhone", "TensorFlow")
- Event: Specific events, meetings, conferences (e.g., "2024 AI Summit")

## Output Format:
Return a JSON object with two arrays:

```json
{{
  "entities": [
    {{"name": "Entity Name", "type": "Person|Organization|Place|Concept|Product|Event"}}
  ],
  "relationships": [
    {{"subject": "Entity1", "predicate": "relationship_type", "object": "Entity2"}}
  ]
}}
```

## Rules:
- Only extract entities and relationships explicitly stated or strongly implied in the text
- Use lowercase_with_underscores for predicates (e.g., works_at, is_friend_of)
- Normalize entity names (e.g., "Dr. John Smith" and "John" should both be "John Smith" if referring to same person)
- Do not invent relationships not supported by the text
- Return empty arrays if no entities or relationships found

## Common Predicates:
- works_at, employed_by, founded
- lives_in, located_in, based_in
- married_to, is_friend_of, knows
- created, developed, built
- uses, prefers, likes
- is_part_of, belongs_to, member_of
- happened_at, scheduled_for
- is_a, type_of, instance_of

## Example:
Input: "John works at Google in San Francisco. He is married to Sarah who is a doctor."

Output:
```json
{{
  "entities": [
    {{"name": "John", "type": "Person"}},
    {{"name": "Google", "type": "Organization"}},
    {{"name": "San Francisco", "type": "Place"}},
    {{"name": "Sarah", "type": "Person"}}
  ],
  "relationships": [
    {{"subject": "John", "predicate": "works_at", "object": "Google"}},
    {{"subject": "Google", "predicate": "located_in", "object": "San Francisco"}},
    {{"subject": "John", "predicate": "married_to", "object": "Sarah"}},
    {{"subject": "Sarah", "predicate": "profession", "object": "doctor"}}
  ]
}}
```

Now extract entities and relationships from the input text. Return ONLY the JSON object, no other text.
"""

SYSTEM_PROMPT = """You are a knowledge extraction assistant. Extract entities and relationships from text and return them as structured JSON. Be precise and only extract what is explicitly stated or strongly implied."""

__all__ = ["PROMPT", "SYSTEM_PROMPT"]
