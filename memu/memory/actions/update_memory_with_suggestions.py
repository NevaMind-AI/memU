"""
Update Memory with Suggestions Action

Updates memory categories based on new memory items and suggestions, supporting different operation types:
- ADD: Add new content
- UPDATE: Modify existing content  
- DELETE: Delete specific content
- TOUCH: Use current content but don't update (mark as accessed)
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
    supporting different operation types (ADD, UPDATE, DELETE, TOUCH).
    """
    
    @property
    def action_name(self) -> str:
        return "update_memory_with_suggestions"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": self.action_name,
            "description": "Update memory categories with different operation types (ADD, UPDATE, DELETE, TOUCH)",
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
                        "description": "Suggestion for what content should be processed in this category"
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
        Update memory category with different operation types based on suggestions
        
        Args:
            character_name: Name of the character
            category: Memory category to update
            suggestion: Suggestion for what content should be processed
            session_date: Session date for the memory items (format: YYYY-MM-DD)
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            Dict containing the operations performed in structured format
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
                    "error": "No activity content found. Run add_activity_memory first."
                })
            
            # Load existing content
            existing_content = self._read_memory_content(character_name, category)
            
            # Determine operation type and execute accordingly
            operation_result = self._determine_and_execute_operation(
                character_name, category, suggestion, session_date, 
                existing_content, activity_content, generate_embeddings
            )
            
            return self._add_metadata(operation_result)
            
        except Exception as e:
            return self._handle_error(e)
    
    def _determine_and_execute_operation(
        self, 
        character_name: str, 
        category: str, 
        suggestion: str,
        session_date: str,
        existing_content: str,
        activity_content: str,
        generate_embeddings: bool
    ) -> Dict[str, Any]:
        """
        Determine what operation to perform and execute it
        
        Returns:
            Dict containing operation results
        """
        # Load operation analysis prompt
        analysis_prompt = self._create_operation_analysis_prompt(
            category, character_name, existing_content, activity_content, suggestion
        )
        
        # Call LLM to determine operation type and content
        operation_response = self.llm_client.simple_chat(analysis_prompt)
        
        if not operation_response.strip():
            return {
                "success": False,
                "error": f"LLM returned empty operation analysis for {category}"
            }
        
        # Parse operation response
        operation_info = self._parse_operation_response(operation_response)
        
        # Execute the determined operation
        if operation_info["operation"] == "ADD":
            return self._execute_add_operation(
                character_name, category, operation_info, session_date, 
                existing_content, generate_embeddings
            )
        elif operation_info["operation"] == "UPDATE":
            return self._execute_update_operation(
                character_name, category, operation_info, session_date,
                existing_content, generate_embeddings
            )
        elif operation_info["operation"] == "DELETE":
            return self._execute_delete_operation(
                character_name, category, operation_info, session_date,
                existing_content, generate_embeddings
            )
        elif operation_info["operation"] == "TOUCH":
            return self._execute_touch_operation(
                character_name, category, operation_info, session_date, existing_content
            )
        else:
            return {
                "success": False,
                "error": f"Unknown operation type: {operation_info['operation']}"
            }
    
    def _create_operation_analysis_prompt(
        self, 
        category: str, 
        character_name: str, 
        existing_content: str, 
        activity_content: str, 
        suggestion: str
    ) -> str:
        """Create prompt to analyze what operation should be performed"""
        return f"""Analyze the following memory update scenario and determine what operation should be performed.

=== SCENARIO ===
Character: {character_name}
Category: {category}
Suggestion: {suggestion}

=== EXISTING {category.upper()} CONTENT ===
{existing_content if existing_content else "No existing content"}

=== NEW ACTIVITY CONTENT TO ANALYZE ===
{activity_content}

=== OPERATION TYPES ===
1. **ADD**: Add completely new information that doesn't exist in current content
2. **UPDATE**: Modify or enhance existing information with new details
3. **DELETE**: Remove outdated, incorrect, or irrelevant information
4. **TOUCH**: Current content is sufficient, no changes needed (mark as accessed)

=== ANALYSIS REQUIREMENTS ===

**Determine the most appropriate operation type:**

- **Choose ADD if:** New activity contains information not covered in existing content
- **Choose UPDATE if:** New activity provides updated details for existing information
- **Choose DELETE if:** Existing content is outdated/incorrect based on new activity
- **Choose TOUCH if:** Existing content already covers the new activity adequately

**For non-TOUCH operations, provide specific content:**

**NO PRONOUNS - COMPLETE SENTENCES ONLY**
- EVERY memory item must include the full subject "{character_name}"
- NEVER use pronouns (no "she", "he", "they", "it")
- Each item should be a complete, standalone sentence

**CRITICAL: NO "NOT SPECIFIED" CONTENT**
- NEVER create items saying information is "not specified" or "unknown"
- ONLY process information that is ACTUALLY present in the activity content

=== OUTPUT FORMAT ===

**OPERATION:** [ADD/UPDATE/DELETE/TOUCH]

**REASON:** [One sentence explaining why this operation was chosen]

**CONTENT:** [Only if operation is ADD, UPDATE, or DELETE]
[Each line should be one complete, self-contained statement]
[NO markdown, bullets, or structure - plain text only]
[Each line will automatically get a memory ID]

**TARGET_IDS:** [Only for UPDATE/DELETE operations]
[List memory IDs from existing content that should be modified/deleted]
[Format: memory_id1, memory_id2, memory_id3]

Analyze and determine the appropriate operation:"""
    
    def _parse_operation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract operation info"""
        lines = response.strip().split('\n')
        operation_info = {
            "operation": "TOUCH",  # Default
            "reason": "",
            "content": "",
            "target_ids": []
        }
        
        current_section = None
        content_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('**OPERATION:**'):
                operation = line.replace('**OPERATION:**', '').strip()
                if operation in ['ADD', 'UPDATE', 'DELETE', 'TOUCH']:
                    operation_info["operation"] = operation
                current_section = "operation"
                
            elif line.startswith('**REASON:**'):
                reason = line.replace('**REASON:**', '').strip()
                operation_info["reason"] = reason
                current_section = "reason"
                
            elif line.startswith('**CONTENT:**'):
                current_section = "content"
                content_lines = []
                
            elif line.startswith('**TARGET_IDS:**'):
                target_ids_text = line.replace('**TARGET_IDS:**', '').strip()
                if target_ids_text:
                    operation_info["target_ids"] = [id.strip() for id in target_ids_text.split(',')]
                current_section = "target_ids"
                
            elif current_section == "content" and line:
                content_lines.append(line)
                
            elif current_section == "reason" and line and not line.startswith('**'):
                operation_info["reason"] += " " + line
        
        if content_lines:
            operation_info["content"] = '\n'.join(content_lines)
        
        return operation_info
    
    def _execute_add_operation(
        self, 
        character_name: str, 
        category: str, 
        operation_info: Dict[str, Any],
        session_date: str,
        existing_content: str,
        generate_embeddings: bool
    ) -> Dict[str, Any]:
        """Execute ADD operation"""
        new_content = operation_info.get("content", "").strip()
        
        if not new_content:
            return {
                "success": False,
                "error": "No content provided for ADD operation"
            }
        
        # Add memory IDs with timestamp to the new content
        new_content_with_ids = self._add_memory_ids_with_timestamp(new_content, session_date)
        
        # Append new content to existing content
        if existing_content:
            final_content = existing_content + "\n" + new_content_with_ids
        else:
            final_content = new_content_with_ids
        
        # Save the combined content
        success = self._save_memory_content(character_name, category, final_content)
        
        if not success:
            return {
                "success": False,
                "error": f"Failed to save updated content to {category}"
            }
        
        # Generate embeddings if enabled
        embeddings_info = self._handle_embeddings(
            character_name, category, new_content_with_ids, generate_embeddings
        )
        
        # Extract the newly added memory items
        new_memory_items = self._extract_memory_items_from_content(new_content_with_ids)
        
        modifications = []
        for item in new_memory_items:
            modifications.append({
                "operation": "ADD",
                "memory_id": item["memory_id"],
                "content": item["content"],
                "category": category
            })
        
        return {
            "success": True,
            "character_name": character_name,
            "category": category,
            "operation": "ADD",
            "reason": operation_info.get("reason", ""),
            "items_processed": len(new_memory_items),
            "modifications": modifications,
            "embeddings_generated": generate_embeddings and self.embeddings_enabled,
            "embeddings_info": embeddings_info,
            "message": f"Successfully added {len(new_memory_items)} new memory items to {category}"
        }
    
    def _execute_update_operation(
        self, 
        character_name: str, 
        category: str, 
        operation_info: Dict[str, Any],
        session_date: str,
        existing_content: str,
        generate_embeddings: bool
    ) -> Dict[str, Any]:
        """Execute UPDATE operation"""
        new_content = operation_info.get("content", "").strip()
        target_ids = operation_info.get("target_ids", [])
        
        if not new_content:
            return {
                "success": False,
                "error": "No content provided for UPDATE operation"
            }
        
        # Parse existing content into items
        existing_items = self._extract_memory_items_from_content(existing_content)
        
        # Update specified items or add new content
        updated_items = []
        modifications = []
        
        # Add new content with memory IDs
        new_content_with_ids = self._add_memory_ids_with_timestamp(new_content, session_date)
        new_items = self._extract_memory_items_from_content(new_content_with_ids)
        
        # Keep existing items that are not being updated
        for item in existing_items:
            if target_ids and item["memory_id"] not in target_ids:
                updated_items.append(item)
            else:
                # Mark as updated/replaced
                modifications.append({
                    "operation": "UPDATED",
                    "memory_id": item["memory_id"],
                    "old_content": item["content"],
                    "category": category
                })
        
        # Add new items
        updated_items.extend(new_items)
        for item in new_items:
            modifications.append({
                "operation": "ADDED",
                "memory_id": item["memory_id"],
                "content": item["content"],
                "category": category
            })
        
        # Reconstruct content
        final_content = self._reconstruct_content_from_items(updated_items)
        
        # Save updated content
        success = self._save_memory_content(character_name, category, final_content)
        
        if not success:
            return {
                "success": False,
                "error": f"Failed to save updated content to {category}"
            }
        
        # Generate embeddings for new content
        embeddings_info = self._handle_embeddings(
            character_name, category, new_content_with_ids, generate_embeddings
        )
        
        return {
            "success": True,
            "character_name": character_name,
            "category": category,
            "operation": "UPDATE",
            "reason": operation_info.get("reason", ""),
            "items_processed": len(new_items),
            "items_updated": len([m for m in modifications if m["operation"] == "UPDATED"]),
            "modifications": modifications,
            "embeddings_generated": generate_embeddings and self.embeddings_enabled,
            "embeddings_info": embeddings_info,
            "message": f"Successfully updated {category} with {len(new_items)} new items"
        }
    
    def _execute_delete_operation(
        self, 
        character_name: str, 
        category: str, 
        operation_info: Dict[str, Any],
        session_date: str,
        existing_content: str,
        generate_embeddings: bool
    ) -> Dict[str, Any]:
        """Execute DELETE operation"""
        target_ids = operation_info.get("target_ids", [])
        
        if not target_ids:
            return {
                "success": False,
                "error": "No target IDs provided for DELETE operation"
            }
        
        # Parse existing content into items
        existing_items = self._extract_memory_items_from_content(existing_content)
        
        # Filter out items to be deleted
        remaining_items = []
        deleted_items = []
        
        for item in existing_items:
            if item["memory_id"] in target_ids:
                deleted_items.append(item)
            else:
                remaining_items.append(item)
        
        # Reconstruct content without deleted items
        final_content = self._reconstruct_content_from_items(remaining_items)
        
        # Save updated content
        success = self._save_memory_content(character_name, category, final_content)
        
        if not success:
            return {
                "success": False,
                "error": f"Failed to save updated content to {category}"
            }
        
        modifications = []
        for item in deleted_items:
            modifications.append({
                "operation": "DELETE",
                "memory_id": item["memory_id"],
                "content": item["content"],
                "category": category
            })
        
        return {
            "success": True,
            "character_name": character_name,
            "category": category,
            "operation": "DELETE",
            "reason": operation_info.get("reason", ""),
            "items_deleted": len(deleted_items),
            "modifications": modifications,
            "embeddings_generated": False,
            "message": f"Successfully deleted {len(deleted_items)} items from {category}"
        }
    
    def _execute_touch_operation(
        self, 
        character_name: str, 
        category: str, 
        operation_info: Dict[str, Any],
        session_date: str,
        existing_content: str
    ) -> Dict[str, Any]:
        """Execute TOUCH operation (no changes, just mark as accessed)"""
        return {
            "success": True,
            "character_name": character_name,
            "category": category,
            "operation": "TOUCH",
            "reason": operation_info.get("reason", ""),
            "items_processed": 0,
            "modifications": [],
            "embeddings_generated": False,
            "message": f"Category {category} touched - current content is sufficient"
        }
    
    def _reconstruct_content_from_items(self, items: List[Dict[str, str]]) -> str:
        """Reconstruct content string from memory items"""
        if not items:
            return ""
        
        lines = []
        for item in items:
            if "mentioned_at" in item:
                # New format with timestamp
                links = item.get("links", "")
                line = f"[{item['memory_id']}][mentioned at {item['mentioned_at']}] {item['content']} [{links}]"
            else:
                # Old format
                line = f"[{item['memory_id']}] {item['content']}"
            lines.append(line)
        
        return '\n'.join(lines)
    
    def _handle_embeddings(
        self, 
        character_name: str, 
        category: str, 
        content: str, 
        generate_embeddings: bool
    ) -> str:
        """Handle embedding generation and return info message"""
        if generate_embeddings and self.embeddings_enabled and content.strip():
            embedding_result = self._add_memory_item_embedding(character_name, category, content)
            return f"Generated embeddings for new content: {embedding_result.get('message', 'Unknown')}"
        return "Embeddings not generated"
    
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
    
    def _load_category_extract_prompt(
        self, 
        category: str, 
        character_name: str, 
        existing_content: str, 
        memory_items_text: str, 
        suggestion: str
    ) -> str:
        """
        Load category-specific prompt template to extract NEW content only
        
        Args:
            category: Memory category (profile, event, activity, etc.)
            character_name: Name of the character
            existing_content: Existing content in the category
            memory_items_text: Source activity content to extract from
            suggestion: Suggestion for what to extract
            
        Returns:
            Formatted prompt for extracting new content only
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
            
        # Format the prompt with variables for extracting NEW content only
        extract_prompt = f"""Based on the following category-specific requirements, extract ONLY NEW information for the {category} memory:

{prompt_template}

=== EXTRACTION CONTEXT ===

EXISTING {category} content (DO NOT DUPLICATE):
{existing_content if existing_content else "No existing content"}

Source activity content to extract from:
{memory_items_text}

Suggestion for this category: {suggestion}

=== CRITICAL EXTRACTION REQUIREMENTS ===

**ONLY EXTRACT NEW INFORMATION**
- CAREFULLY review the existing {category} content above
- ONLY extract information that is NOT already present in existing content
- If information is already covered in existing content, DO NOT extract it again
- Focus on completely NEW facts, details, or updates

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
5. ONLY include lines with actual, factual NEW information
6. If no new information is found, return empty content

Extract ONLY NEW relevant information according to the category requirements above and write each piece as a complete, self-contained sentence:

NEW {category} content to append:"""
        
        return extract_prompt
