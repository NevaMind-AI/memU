"""
Process Conversation Action

Processes conversations into memory types (activity, profile, events, etc.) and saves to markdown files.
"""

import os
from typing import Dict, List, Any
from datetime import datetime

from .base_action import BaseAction
from ...utils import get_logger

logger = get_logger(__name__)


class ProcessConversationAction(BaseAction):
    """
    Action to process conversations into structured memory types
    
    Takes a conversation and processes it into various memory categories like:
    - activity: Raw conversation summary
    - profile: Character information extracted
    - events: Important events mentioned
    - etc.
    """
    
    @property
    def action_name(self) -> str:
        return "process_conversation"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema"""
        return {
            "name": "process_conversation",
            "description": "Process a conversation into memory types (activity, profile, events, etc.) and save to markdown files",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        },
                        "description": "List of conversation messages with role and content"
                    },
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character to store memory for"
                    },
                    "session_date": {
                        "type": "string",
                        "description": "Date of the session (YYYY-MM-DD format), optional"
                    },
                    "selected_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific memory types to process, optional (defaults to all)"
                    }
                },
                "required": ["conversation", "character_name"]
            }
        }
    
    def execute(
        self,
        conversation: List[Dict],
        character_name: str,
        session_date: str = "",
        selected_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute conversation processing
        
        Args:
            conversation: List of message dicts with 'role' and 'content' fields
            character_name: Name of the character
            session_date: Date of the session
            selected_types: Specific memory types to process (None for all)
            
        Returns:
            Dict containing processing results
        """
        try:
            results = {
                "success": True,
                "character_name": character_name,
                "session_date": session_date or datetime.now().strftime("%Y-%m-%d"),
                "memory_outputs": {},
                "errors": []
            }
            
            # Validate conversation format
            validation_result = self._validate_conversation(conversation)
            if not validation_result["valid"]:
                results["success"] = False
                results["errors"].append(validation_result["error"])
                return self._add_metadata(results)
            
            logger.info(f"Processing conversation for {character_name} ({len(conversation)} messages)")
            
            # Convert conversation to text format for LLM processing
            conversation_text = self._convert_conversation_to_text(conversation)
            
            # Determine which types to process
            types_to_process = selected_types or self.processing_order
            
            # Load existing memory content
            existing_memory = self._load_existing_memory(character_name)
            
            # Process each memory type
            for memory_type in types_to_process:
                if memory_type not in self.memory_types:
                    results["errors"].append(f"Invalid memory type: {memory_type}")
                    continue
                
                try:
                    logger.debug(f"Processing {memory_type} for {character_name}")
                    
                    # Determine input content
                    if memory_type == "activity":
                        # Activity gets raw conversation converted to text format
                        input_content = conversation_text
                    else:
                        # Other types get activity summary as input if available
                        input_content = existing_memory.get("activity", conversation_text)
                    
                    # Generate memory content using LLM
                    memory_content = self._process_memory_type(
                        memory_type=memory_type,
                        character_name=character_name,
                        input_content=input_content,
                        session_date=session_date,
                        existing_memory=existing_memory
                    )
                    
                    # Save the memory content to markdown files with embeddings
                    if self._save_memory_with_embeddings(character_name, memory_type, memory_content):
                        results["memory_outputs"][memory_type] = memory_content
                        # Update existing memory for next types
                        existing_memory[memory_type] = memory_content
                        logger.debug(f"Successfully saved {memory_type} to markdown file")
                    else:
                        results["errors"].append(f"Failed to save {memory_type} for {character_name}")
                        
                except Exception as e:
                    error_msg = f"Failed to process {memory_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["success"] = False
            
            if results["errors"]:
                logger.warning(f"Completed with {len(results['errors'])} errors for {character_name}")
            else:
                logger.info(f"Successfully processed {len(results['memory_outputs'])} memory types for {character_name}")
            
            return self._add_metadata(results)
            
        except Exception as e:
            return self._handle_error(e)
    
    def _validate_conversation(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Validate conversation format"""
        if not isinstance(conversation, list):
            return {
                "valid": False,
                "error": "Conversation must be a list of message objects with 'role' and 'content' fields"
            }
        
        if not conversation:
            return {
                "valid": False,
                "error": "Empty conversation provided"
            }
        
        # Check each message has required fields
        for i, message in enumerate(conversation):
            if not isinstance(message, dict):
                return {
                    "valid": False,
                    "error": f"Message {i} is not a dictionary"
                }
            
            if "role" not in message or "content" not in message:
                return {
                    "valid": False,
                    "error": f"Message {i} missing 'role' or 'content' field"
                }
        
        return {"valid": True}
    
    def _process_memory_type(
        self,
        memory_type: str,
        character_name: str,
        input_content: str,
        session_date: str,
        existing_memory: Dict[str, str]
    ) -> str:
        """Process a specific memory type using LLM"""
        # Get the appropriate prompt template
        prompt_template = self._get_prompt_template(memory_type)
        
        # Prepare prompt variables
        prompt_vars = {
            "character_name": character_name,
            "conversation": input_content,
            "input_content": input_content,
            "session_date": session_date or datetime.now().strftime("%Y-%m-%d"),
            "current_memory": existing_memory.get(memory_type, ""),
        }
        
        # Add all existing memory as context
        prompt_vars.update(existing_memory)
        
        # Add common expected variables with fallbacks
        expected_vars = {
            "existing_profile": existing_memory.get("profile", ""),
            "existing_events": existing_memory.get("event", ""),
            "existing_reminders": existing_memory.get("reminder", ""),
            "existing_interests": existing_memory.get("interests", ""),
            "existing_study": existing_memory.get("study", ""),
            "events": existing_memory.get("event", ""),
            "profile": existing_memory.get("profile", ""),
            "activity": existing_memory.get("activity", "")
        }
        prompt_vars.update(expected_vars)
        
        # Format the prompt
        try:
            formatted_prompt = prompt_template.format(**prompt_vars)
        except KeyError as e:
            missing_var = str(e).strip("'")
            logger.warning(f"Missing variable '{missing_var}' in prompt for {memory_type}, using empty string")
            prompt_vars[missing_var] = ""
            formatted_prompt = prompt_template.format(**prompt_vars)
        
        # Generate content using LLM
        try:
            messages = [{"role": "user", "content": formatted_prompt}]
            response = self.llm_client.chat_completion(messages)
            
            if response.success:
                return response.content.strip()
            else:
                raise Exception(f"LLM call failed: {response.error}")
                
        except Exception as e:
            logger.error(f"LLM generation failed for {memory_type}: {e}")
            raise
    
    def _get_prompt_template(self, memory_type: str) -> str:
        """Get the appropriate prompt template for a memory type"""
        prompt_path = self.config_manager.get_prompt_path(memory_type)
        if not prompt_path or not os.path.exists(prompt_path):
            raise ValueError(f"Prompt file not found for memory type: {memory_type}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _save_memory_with_embeddings(self, character_name: str, memory_type: str, content: str) -> bool:
        """Save memory content and generate embeddings"""
        try:
            # Save the main content
            success = self._save_memory_content(character_name, memory_type, content)
            
            if success and self.embeddings_enabled and content.strip():
                # Generate embeddings for the content
                self._generate_memory_embeddings(character_name, memory_type, content)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save memory with embeddings for {character_name}: {e}")
            return False
    
    def _generate_memory_embeddings(self, character_name: str, memory_type: str, content: str):
        """Generate and store embeddings for memory content - one embedding per line"""
        try:
            if not content.strip() or not self.embedding_client:
                return
            
            # Split content into lines (each line is a memory item)
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            embeddings = []
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                
                try:
                    # Generate embedding for this line
                    embedding_vector = self.embedding_client.generate_embedding(line)
                    
                    embedding_item = {
                        "item_id": f"{character_name}_{memory_type}_item_{i}",
                        "text": line,
                        "embedding": embedding_vector,
                        "line_number": i + 1,
                        "metadata": {
                            "character": character_name,
                            "memory_type": memory_type,
                            "length": len(line),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    embeddings.append(embedding_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for line {i}: {e}")
                    continue
            
            if embeddings:
                # Store embeddings
                import json
                import hashlib
                
                char_embeddings_dir = self.embeddings_dir / character_name
                char_embeddings_dir.mkdir(exist_ok=True)
                
                embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
                embeddings_data = {
                    "memory_type": memory_type,
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": hashlib.md5(content.encode()).hexdigest(),
                    "embeddings": embeddings,
                    "total_embeddings": len(embeddings)
                }
                
                with open(embeddings_file, 'w', encoding='utf-8') as f:
                    json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Generated {len(embeddings)} embeddings for {memory_type} of {character_name}")
            
        except Exception as e:
            logger.error(f"Failed to generate memory embeddings for {character_name}:{memory_type}: {e}") 