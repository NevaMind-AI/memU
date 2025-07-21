"""
Update Memory with Suggestions Action

Updates memory categories based on new memory items and suggestions, returning structured results.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class UpdateMemoryWithSuggestionsAction(BaseAction):
    """
    Update memory categories based on new memory items and suggestions,
    returning the modifications in structured format.
    """
    
    @property
    def action_name(self) -> str:
        return "update_memory_with_suggestions"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Update memory categories based on new memory items and suggestions, returning modifications in structured format",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "category": {
                        "type": "string",
                        "description": "Memory category to update"
                    },

                    "suggestion": {
                        "type": "string",
                        "description": "Suggestion for what content should be added to this category"
                    },
                    "generate_embeddings": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to generate embeddings for the new content"
                    }
                },
                "required": ["character_name", "category", "suggestion"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        category: str,
        suggestion: str,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Update memory category with new content based on suggestions
        
        Args:
            character_name: Name of the character
            category: Memory category to update
            suggestion: Suggestion for what content should be added
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            Dict containing the modifications in structured format
        """
        try:
            # Validate category
            if category not in self.memory_types:
                return self._add_metadata({
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                })
            
            # Read memory items from activity category (stored in step 2 of workflow)
            activity_content = self._read_memory_content(character_name, "activity")
            if not activity_content:
                return self._add_metadata({
                    "success": False,
                    "error": "No activity content found. Run summarize_conversation and add_activity_memory first."
                })
            
            # Use activity content as the source of memory items for LLM processing
            memory_items_text = f"Activity content:\n{activity_content}"
            
            # Load existing content
            existing_content = self._read_memory_content(character_name, category)
            
            # Create enhanced prompt for LLM to generate self-contained content
            update_prompt = f"""You are updating the {category} memory for {character_name}. 

Existing {category} content:
{existing_content if existing_content else "No existing content"}

Source activity content to extract from:
{memory_items_text}

Suggestion for this category: {suggestion}

**CRITICAL REQUIREMENT: NO PRONOUNS - COMPLETE SENTENCES ONLY**

Based on the suggestion, extract and organize relevant information from the activity content to update the {category} category. 

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Each memory item should be understandable without reading other items
- Include specific names, places, dates, and full context in each item
- Never use "the book", "the place", "the friend" - always include full titles and names

**FORMAT REQUIREMENTS:**
1. Each line should be one complete, self-contained statement
2. NO markdown headers, bullets, or structure
3. NO duplicate memory ID information 
4. Write in plain text only
5. Each line will automatically get a memory ID [xxx] prefix
6. Focus on factual, concise information
7. Use specific names, titles, places, and dates in every relevant item

**COMPLETE SENTENCE EXAMPLES:**
✅ GOOD: "{character_name} works as a product manager at TechFlow Solutions"
❌ BAD: "Works as a product manager" (missing subject)
✅ GOOD: "{character_name} went hiking with Sarah Johnson in Blue Ridge Mountains"
❌ BAD: "Went hiking with Sarah" (missing location and full name context)
✅ GOOD: "{character_name} read 'The Midnight Library' by Matt Haig and found it inspiring"
❌ BAD: "Found the book inspiring" (missing book title and author)

**QUALITY STANDARDS:**
- Never use "he", "she", "they", "it" - always use the person's actual name
- Never use "the book", "the place", "the friend" - always include full titles and names
- Each sentence must be complete and understandable independently
- Include sufficient detail so each item makes sense on its own

Extract relevant information and write each piece as a complete, self-contained sentence:

Updated {category} content:"""

            # Call LLM to generate updated content
            updated_content = self.llm_client.simple_chat(update_prompt)
            
            if not updated_content.strip():
                return self._add_metadata({
                    "success": False,
                    "error": f"LLM returned empty content for {category}"
                })
            
            # Add memory IDs to the updated content
            content_with_ids = self._add_memory_ids_to_content(updated_content)
            
            # Save the updated content
            success = self._save_memory_content(character_name, category, content_with_ids)
            
            if not success:
                return self._add_metadata({
                    "success": False,
                    "error": f"Failed to save updated content to {category}"
                })
            
            # Generate embeddings if enabled
            embeddings_info = ""
            if generate_embeddings and self.embeddings_enabled:
                self._generate_memory_embeddings(character_name, category, content_with_ids)
                embeddings_info = "Generated embeddings for updated content"
            
            # Extract the newly added memory items for JSON response
            new_memory_items_added = self._extract_memory_items_from_content(content_with_ids)
            
            # Prepare JSON response with the modifications
            modifications = []
            for item in new_memory_items_added:
                # Add all extracted items as modifications
                modifications.append({
                    "memory_id": item["memory_id"],
                    "content": item["content"],
                    "category": category
                })
            
            return self._add_metadata({
                "success": True,
                "character_name": character_name,
                "category": category,
                "modifications": modifications,
                "content_length": len(content_with_ids),
                "embeddings_generated": generate_embeddings and self.embeddings_enabled,
                "embeddings_info": embeddings_info,
                "file_path": f"{self.memory_core.memory_dir}/{character_name}_{category}.md",
                "message": f"Successfully updated {category} for {character_name} with {len(modifications)} self-contained modifications"
            })
            
        except Exception as e:
            return self._handle_error(e)
    
    def _extract_memory_items_from_content(self, content: str) -> List[Dict[str, str]]:
        """Extract memory items with IDs from content"""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and self._has_memory_id(line):
                # Extract memory ID and content
                memory_id, clean_content = self._extract_memory_id(line)
                if memory_id:
                    items.append({
                        "memory_id": memory_id,
                        "content": clean_content
                    })
        
        return items
    
    def _generate_memory_embeddings(self, character_name: str, category: str, content: str):
        """Generate and store embeddings for memory content - one embedding per line"""
        try:
            if not content.strip() or not self.embedding_client:
                return
            
            # Parse memory items with IDs
            memory_items = self._parse_memory_items(content)
            
            embeddings = []
            for i, item in enumerate(memory_items):
                if not item["content"].strip():
                    continue
                
                try:
                    # Generate embedding for the clean content (without memory ID)
                    embedding_vector = self.embedding_client.embed(item["content"])
                    
                    embedding_item = {
                        "item_id": f"{character_name}_{category}_item_{i}",
                        "memory_id": item["memory_id"],  # Store the original memory ID
                        "text": item["content"],  # Store clean content
                        "full_line": item["full_line"],  # Store full line with memory ID
                        "embedding": embedding_vector,
                        "line_number": item["line_number"],
                        "metadata": {
                            "character": character_name,
                            "category": category,
                            "length": len(item["content"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    embeddings.append(embedding_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for memory item {item.get('memory_id', i)}: {e}")
                    continue
            
            if embeddings:
                # Store embeddings
                char_embeddings_dir = self.embeddings_dir / character_name
                char_embeddings_dir.mkdir(exist_ok=True)
                
                embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
                embeddings_data = {
                    "category": category,
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": hashlib.md5(content.encode()).hexdigest(),
                    "embeddings": embeddings,
                    "total_embeddings": len(embeddings)
                }
                
                with open(embeddings_file, 'w', encoding='utf-8') as f:
                    json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Generated {len(embeddings)} embeddings for {category} of {character_name}")
                
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {category}: {e}") 