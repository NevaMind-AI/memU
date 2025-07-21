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
                    "session_date": {
                        "type": "string",
                        "description": "Session date for the memory items (format: YYYY-MM-DD)"
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
        session_date: str,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Update memory category with new content based on suggestions
        
        Args:
            character_name: Name of the character
            category: Memory category to update
            suggestion: Suggestion for what content should be added
            session_date: Session date for the memory items (format: YYYY-MM-DD)
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
            
            # Load category-specific prompt template
            update_prompt = self._load_category_update_prompt(
                category, character_name, existing_content, memory_items_text, suggestion
            )

            # Call LLM to generate updated content
            updated_content = self.llm_client.simple_chat(update_prompt)
            
            if not updated_content.strip():
                return self._add_metadata({
                    "success": False,
                    "error": f"LLM returned empty content for {category}"
                })
            
            # Clean up any extra brackets around content lines
            updated_content = self._clean_extra_brackets(updated_content)
            
            # Add memory IDs with timestamp to the updated content
            content_with_ids = self._add_memory_ids_with_timestamp(updated_content, session_date)
            
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
        """Extract memory items with IDs from content, supporting both old and new timestamp formats"""
        import re
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (self._has_memory_id_with_timestamp(line) or self._has_memory_id(line)):
                # First try to extract from timestamped format (new format)
                if self._has_memory_id_with_timestamp(line):
                    # Format: [memory_id][mentioned at date] content [links]
                    pattern = r'^\[([^\]]+)\]\[mentioned at ([^\]]+)\]\s*(.*?)(?:\s*\[([^\]]*)\])?$'
                    match = re.match(pattern, line)
                    if match:
                        memory_id = match.group(1)
                        mentioned_at = match.group(2)
                        clean_content = match.group(3).strip()
                        links = match.group(4) if match.group(4) else ""
                        
                        if memory_id and clean_content:
                            items.append({
                                "memory_id": memory_id,
                                "mentioned_at": mentioned_at,
                                "content": clean_content,
                                "links": links
                            })
                else:
                    # Fallback to basic format extraction (old format)
                    memory_id, clean_content = self._extract_memory_id(line)
                    if memory_id:
                        items.append({
                            "memory_id": memory_id,
                            "content": clean_content
                        })
        
        return items
    
    def _has_memory_id_with_timestamp(self, line: str) -> bool:
        """
        Check if a line has a memory ID with timestamp
        Format: [memory_id][mentioned at date] content
        """
        import re
        pattern = r'^\[[\w\d_]+\]\[mentioned at [^\]]+\]\s+'
        return bool(re.match(pattern, line.strip()))
    
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
    
    def _add_memory_ids_with_timestamp(self, content: str, session_date: str) -> str:
        """
        Add memory IDs with timestamp and links to content lines
        Format: [memory_id][mentioned at {session_date}] {content}
        
        Args:
            content: Raw content
            session_date: Date of the session
            
        Returns:
            Content with memory IDs, timestamps and empty links added to each line
        """
        import re
        if not content.strip():
            return content
        
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Only process non-empty lines
                # Always remove existing memory ID and generate a new unique one
                if self._has_memory_id_with_timestamp(line):
                    # Extract content without memory ID and timestamp
                    clean_content = self._extract_content_from_timestamped_line(line)
                    line = clean_content
                elif self._has_memory_id(line):
                    # Extract content without basic memory ID
                    _, clean_content = self._extract_memory_id(line)
                    line = clean_content
                
                # Generate new unique memory ID for this line
                memory_id = self._generate_memory_id()
                # Format: [memory_id][mentioned at {session_date}] {content} [links]
                processed_lines.append(f"[{memory_id}][mentioned at {session_date}] {line} []")
            else:
                # Keep empty lines as is
                processed_lines.append("")
        
        return '\n'.join(processed_lines)
    
    def _extract_content_from_timestamped_line(self, line: str) -> str:
        """
        Extract content from a timestamped memory line
        Format: [memory_id][mentioned at date] content [links]
        
        Args:
            line: Line with memory ID and timestamp
            
        Returns:
            Clean content without memory ID, timestamp, or links
        """
        import re
        # Pattern to match: [memory_id][mentioned at date] content [links] (links optional)
        pattern = r'^\[([^\]]+)\]\[mentioned at ([^\]]+)\]\s*(.*?)(?:\s*\[([^\]]*)\])?$'
        match = re.match(pattern, line.strip())
        
        if match:
            return match.group(3).strip()  # Return the content part
        return line.strip()
    
    def _clean_extra_brackets(self, content: str) -> str:
        """
        Clean up any extra brackets around content lines
        
        Args:
            content: Raw content from LLM
            
        Returns:
            Cleaned content without extra brackets around individual lines
        """
        if not content.strip():
            return content
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove extra brackets that might wrap the entire line content
                # Pattern: [content] -> content
                if line.startswith('[') and line.endswith(']') and line.count('[') == 1 and line.count(']') == 1:
                    # This looks like content wrapped in brackets, remove them
                    cleaned_line = line[1:-1].strip()
                    cleaned_lines.append(cleaned_line)
                else:
                    # Keep line as is
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _load_category_update_prompt(
        self, 
        category: str, 
        character_name: str, 
        existing_content: str, 
        memory_items_text: str, 
        suggestion: str
    ) -> str:
        """
        Load category-specific prompt template from config/{category}/prompt.txt
        
        Args:
            category: Memory category (profile, event, activity, etc.)
            character_name: Name of the character
            existing_content: Existing content in the category
            memory_items_text: Source activity content to extract from
            suggestion: Suggestion for what to extract
            
        Returns:
            Formatted prompt for the specific category
        """
        from pathlib import Path
        
        # Load category-specific prompt
        config_dir = Path(__file__).parent.parent.parent / "config" / category
        prompt_file = config_dir / "prompt.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
            
        # Load and format the prompt template
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # Format the prompt with variables for update context
        update_prompt = f"""Based on the following category-specific requirements, update the {category} memory:

{prompt_template}

=== UPDATE CONTEXT ===

Existing {category} content:
{existing_content if existing_content else "No existing content"}

Source activity content to extract from:
{memory_items_text}

Suggestion for this category: {suggestion}

=== CRITICAL UPDATE REQUIREMENTS ===

**NO PRONOUNS - COMPLETE SENTENCES ONLY**
- EVERY memory item must be a complete, standalone sentence
- ALWAYS include the full subject "{character_name}"
- NEVER use pronouns that depend on context (no "she", "he", "they", "it")
- Each memory item should be understandable without reading other items

**CRITICAL: NO "NOT SPECIFIED" OR "NOT MENTIONED" CONTENT**
- NEVER create memory items saying information is "not specified", "not mentioned", "not available", or "unknown"
- ONLY extract and record information that is ACTUALLY present in the source content
- If information is missing, simply DON'T create a memory item for that topic
- Empty/missing information should result in NO memory item, not a "not specified" item

**OUTPUT FORMAT:**
1. Each line should be one complete, self-contained statement
2. NO markdown headers, bullets, or structure
3. Write in plain text only
4. Each line will automatically get a memory ID [xxx] prefix
5. ONLY include lines with actual, factual information - NO "not specified" statements

Extract relevant information according to the category requirements above and write each piece as a complete, self-contained sentence:

Updated {category} content:"""
        
        return update_prompt
