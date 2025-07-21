"""
Add Activity Memory Action

Adds new activity memory content with strict no-pronouns formatting, following the same
high-quality standards as update_memory_with_suggestions for self-contained memory items.
"""

import json
import hashlib
from typing import Dict, Any
from datetime import datetime

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class AddActivityMemoryAction(BaseAction):
    """
    Action to add new activity memory content with strict formatting requirements
    
    Ensures all memory items are complete, self-contained sentences with no pronouns,
    following the same standards as update_memory_with_suggestions.
    """
    
    @property
    def action_name(self) -> str:
        return "add_activity_memory"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "add_activity_memory",
            "description": "Add new activity memory content with strict no-pronouns formatting for complete, self-contained memory items",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character"
                    },
                    "content": {
                        "type": "string",
                        "description": "Raw content to process and add to activity memory"
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Date of the session (e.g., '2024-01-15')",
                        "default": None
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Whether to append to existing content (true) or replace it (false)",
                        "default": True
                    },
                    "generate_embeddings": {
                        "type": "boolean",
                        "description": "Whether to generate embeddings for semantic search",
                        "default": True
                    }
                },
                "required": ["character_name", "content"]
            }
        }
    
    def execute(
        self,
        character_name: str,
        content: str,
        session_date: str = None,
        append: bool = True,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Execute add activity memory operation with strict formatting
        
        Args:
            character_name: Name of the character
            content: Raw content to process and format
            session_date: Date of the session
            append: Whether to append to existing content or replace it
            generate_embeddings: Whether to generate embeddings for the content
            
        Returns:
            Dict containing operation result including formatted content and embedding info
        """
        try:
            # Use current date if not provided
            if not session_date:
                session_date = datetime.now().strftime("%Y-%m-%d")
            
            # Load existing content if appending
            existing_content = ""
            if append:
                existing_content = self._read_memory_content(character_name, "activity")
            
            # Process raw content through LLM to ensure strict formatting
            formatted_content = self._format_content_with_llm(character_name, content, session_date)
            
            if not formatted_content.strip():
                return self._add_metadata({
                    "success": False,
                    "error": "LLM returned empty formatted content"
                })
            
            # Add memory IDs to the formatted content
            content_with_ids = self._add_memory_ids_to_content(formatted_content)
            
            # Prepare final content with header
            activity_header = f"Session Date: {session_date}\n\n"
            
            # Prepare new content
            if append and existing_content:
                # Add separator and new content
                new_content = existing_content + "\n\n" + "=" * 50 + "\n\n" + activity_header + content_with_ids
            else:
                # Replace with new content
                new_content = activity_header + content_with_ids
            
            # Save content with embeddings if enabled
            embeddings_info = ""
            if generate_embeddings and self.embeddings_enabled:
                if append and existing_content:
                    # For append mode, save first, then add embedding for just the new content
                    success = self._save_memory_content(character_name, "activity", new_content)
                    if success:
                        # Add embedding for just the new content
                        embedding_result = self._add_memory_item_embedding(character_name, "activity", content_with_ids)
                        embeddings_info = f"Generated embedding for new items: {embedding_result.get('message', 'Unknown')}"
                    else:
                        embeddings_info = "Failed to save memory"
                else:
                    # For replace mode, regenerate all embeddings
                    success = self._save_memory_with_embeddings(character_name, "activity", new_content)
                    embeddings_info = "Generated embeddings for all content"
            else:
                success = self._save_memory_content(character_name, "activity", new_content)
                embeddings_info = "No embeddings generated"
            
            if success:
                # Extract memory items for response
                memory_items = self._extract_memory_items_from_content(content_with_ids)
                
                return self._add_metadata({
                    "success": True,
                    "character_name": character_name,
                    "category": "activity",
                    "session_date": session_date,
                    "operation": "append" if append else "replace",
                    "content_added": len(content_with_ids),
                    "memory_items_added": len(memory_items),
                    "memory_items": memory_items,
                    "embeddings_generated": generate_embeddings and self.embeddings_enabled,
                    "embeddings_info": embeddings_info,
                    "file_path": f"{self.memory_core.memory_dir}/{character_name}_activity.md",
                    "message": f"Successfully {'appended' if append else 'added'} {len(memory_items)} self-contained activity memory items for {character_name}"
                })
            else:
                return self._add_metadata({
                    "success": False,
                    "error": "Failed to save activity memory"
                })
                
        except Exception as e:
            return self._handle_error(e)
    
    def _format_content_with_llm(self, character_name: str, content: str, session_date: str) -> str:
        """Use LLM to format content with strict no-pronouns requirements"""
        
        # Create enhanced prompt for strict formatting
        format_prompt = f"""You are formatting activity memory content for {character_name} on {session_date}.

Raw content to format:
{content}

**CRITICAL REQUIREMENT: NO PRONOUNS - COMPLETE SENTENCES ONLY**

Transform this raw content into properly formatted activity memory items following these strict rules:

**SELF-CONTAINED MEMORY REQUIREMENTS:**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject (use "{character_name}" instead of "she/he/they")
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Each memory item should be understandable without reading other items
- Include specific names, places, dates, and full context in each item
- Never use "the book", "the place", "the friend" - always include full titles and names

**FORMAT REQUIREMENTS:**
1. Each line should be one complete, self-contained statement
2. NO markdown headers, bullets, or structure
3. NO memory ID information (will be added automatically)
4. Write in plain text only
5. Focus on factual, concise information
6. Use specific names, titles, places, and dates in every relevant item

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

Transform the raw content into properly formatted activity memory items:

Formatted activity content:"""

        # Call LLM to format content
        formatted_content = self.llm_client.simple_chat(format_prompt)
        
        return formatted_content.strip()
    
    def _extract_memory_items_from_content(self, content: str) -> list:
        """Extract memory items with IDs from content"""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and self._has_memory_id(line):
                # Extract memory ID and content
                memory_id, clean_content = self._extract_memory_id(line)
                if memory_id and clean_content:
                    items.append({
                        "memory_id": memory_id,
                        "content": clean_content
                    })
        
        return items
    
    def _save_memory_with_embeddings(self, character_name: str, category: str, content: str) -> bool:
        """Save memory content and generate embeddings"""
        try:
            # Save the main content (content already has memory IDs)
            success = self._save_memory_content(character_name, category, content)
            
            if success and self.embeddings_enabled and content.strip():
                # Generate embeddings for the content
                self._generate_memory_embeddings(character_name, category, content)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save memory with embeddings for {character_name}: {e}")
            return False
    
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
            logger.error(f"Failed to generate memory embeddings for {character_name}:{category}: {e}")
    
    def _add_memory_item_embedding(self, character_name: str, category: str, new_content: str) -> Dict[str, Any]:
        """Add embedding for new memory items"""
        try:
            if not self.embeddings_enabled or not new_content.strip():
                return {
                    "success": False,
                    "error": "Embeddings disabled or empty item"
                }
            
            # Load existing embeddings
            char_embeddings_dir = self.embeddings_dir / character_name
            char_embeddings_dir.mkdir(exist_ok=True)
            embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
            
            existing_embeddings = []
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                    existing_embeddings = embeddings_data.get("embeddings", [])
            
            # Parse new memory items
            new_items = self._parse_memory_items(new_content)
            
            # Generate embeddings for new items
            for item in new_items:
                if not item["content"].strip():
                    continue
                    
                try:
                    embedding_vector = self.embedding_client.embed(item["content"])
                    new_item_id = f"{character_name}_{category}_item_{len(existing_embeddings)}"
                    
                    new_embedding = {
                        "item_id": new_item_id,
                        "memory_id": item["memory_id"],
                        "text": item["content"],
                        "full_line": item["full_line"],
                        "embedding": embedding_vector,
                        "line_number": len(existing_embeddings) + 1,
                        "metadata": {
                            "character": character_name,
                            "category": category,
                            "length": len(item["content"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    # Add to existing embeddings
                    existing_embeddings.append(new_embedding)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for memory item {item.get('memory_id')}: {e}")
                    continue
            
            # Save updated embeddings
            embeddings_data = {
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "content_hash": hashlib.md5(new_content.encode()).hexdigest(),
                "embeddings": existing_embeddings,
                "total_embeddings": len(existing_embeddings)
            }
            
            with open(embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "embedding_count": len(existing_embeddings),
                "new_items_count": len(new_items),
                "message": f"Added embeddings for {len(new_items)} new memory items in {category}"
            }
                
        except Exception as e:
            logger.error(f"Failed to add memory item embedding: {e}")
            return {
                "success": False,
                "error": str(e)
            } 