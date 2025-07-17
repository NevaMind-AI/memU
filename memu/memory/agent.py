"""
Memory Agent - File-based Memory Management with LLM Tools

This agent handles memory management operations through function tools:
- Reading and writing character profiles and events
- Analyzing conversations for memory updates
- Searching through memory content
- Managing memory files
"""

import json
import os
import sys
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
import re
from difflib import SequenceMatcher
from collections import defaultdict

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .db_manager import MemoryDatabaseManager
from .embeddings import get_default_embedding_client
from ..prompts.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


class MemoryAgent:
    """
    Memory Agent for file-based memory management operations.
    
    Provides memory management capabilities through callable functions:
    - read_character_profile: Read complete character profile
    - read_character_events: Read character event records  
    - update_character_memory: Update memory files from conversation
    - search_relevant_events: Search for events relevant to a query
    - analyze_session_for_events: Extract events from conversations
    - analyze_session_for_profile: Update profile from conversations
    - clear_character_memory: Clear memory files for characters
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient = None,
        memory_dir: str = "memory",
        use_database: bool = True,
        embedding_client=None,
        **db_kwargs
    ):
        """
        Initialize Memory Agent
        
        Args:
            llm_client: LLM client for processing conversations
            memory_dir: Directory to store memory files (when use_database=False)
            use_database: Whether to use database storage (True) or file storage (False)
            embedding_client: Embedding client for vector generation
            **db_kwargs: Database connection parameters
        """
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self.use_database = use_database
        
        # Initialize thread lock for file operations
        self._file_lock = threading.Lock()
        
        # Initialize storage manager
        if use_database:
            self.storage_manager = MemoryDatabaseManager(**db_kwargs)
            
            # Setup embedding client
            if embedding_client:
                self.storage_manager.set_embedding_client(embedding_client)
            else:
                # Try to get default embedding client
                default_embedding = get_default_embedding_client()
                if default_embedding:
                    self.storage_manager.set_embedding_client(default_embedding)
                    logger.info("Using default embedding client for vector generation")
                else:
                    logger.warning("No embedding client configured - vectors will not be generated")
        else:
            self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize prompt loader
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.prompt_loader = get_prompt_loader(str(prompts_dir))
        
        storage_type = "database" if use_database else "file"
        logger.info(f"Memory Agent initialized with {storage_type} storage")
        logger.info(f"Prompts directory: {prompts_dir}")
    
    def _safe_json_parse(self, json_string: str) -> Dict[str, Any]:
        """Safely parse JSON string with error handling and fixing"""
        if not json_string or not isinstance(json_string, str):
            logger.warning(f"Invalid JSON input: {type(json_string)}")
            return {}
        
        # Try direct parsing first
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            
            # Try to fix common JSON issues
            try:
                # Remove potential trailing commas
                fixed_json = json_string.strip()
                
                # Fix unterminated strings by finding the last complete JSON structure
                if "Unterminated string" in str(e):
                    # Find the last valid opening brace
                    last_brace = fixed_json.rfind('{')
                    if last_brace != -1:
                        # Try to find a matching closing brace or add one
                        brace_count = 0
                        valid_end = len(fixed_json)
                        
                        for i in range(last_brace, len(fixed_json)):
                            if fixed_json[i] == '{':
                                brace_count += 1
                            elif fixed_json[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    valid_end = i + 1
                                    break
                        
                        if brace_count > 0:
                            # Add missing closing braces
                            fixed_json = fixed_json[:valid_end] + '}' * brace_count
                
                # Try parsing the fixed JSON
                return json.loads(fixed_json)
                
            except Exception as fix_error:
                logger.error(f"Failed to fix JSON: {fix_error}")
                
                # Last resort: try to extract key-value pairs manually
                try:
                    return self._extract_json_manually(json_string)
                except Exception as manual_error:
                    logger.error(f"Manual JSON extraction failed: {manual_error}")
                    return {}

    def _extract_json_manually(self, json_string: str) -> Dict[str, Any]:
        """Manually extract key-value pairs from malformed JSON"""
        result = {}
        
        # Look for common patterns like "key": "value"
        import re
        
        # Pattern for string values
        string_pattern = r'"(\w+)"\s*:\s*"([^"]*)"'
        matches = re.findall(string_pattern, json_string)
        for key, value in matches:
            result[key] = value
        
        # Pattern for array values
        array_pattern = r'"(\w+)"\s*:\s*\[(.*?)\]'
        array_matches = re.findall(array_pattern, json_string)
        for key, array_content in array_matches:
            try:
                # Try to parse the array content
                array_value = json.loads(f'[{array_content}]')
                result[key] = array_value
            except:
                # Split by comma as fallback
                items = [item.strip().strip('"') for item in array_content.split(',')]
                result[key] = items
        
        # Pattern for number values
        number_pattern = r'"(\w+)"\s*:\s*(\d+)'
        number_matches = re.findall(number_pattern, json_string)
        for key, value in number_matches:
            result[key] = int(value)
        
        logger.info(f"Manually extracted JSON: {result}")
        return result
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available memory tools"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_character_profile",
                    "description": "Read the complete profile information for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read profile for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_character_events", 
                    "description": "Read all event records for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read events for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_character_reminders",
                    "description": "Read all reminders and todo items for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read reminders for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_character_important_events",
                    "description": "Read important life events and milestones for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read important events for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_character_interests",
                    "description": "Read interests, hobbies, and preferences for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read interests for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_character_study",
                    "description": "Read study information, learning goals, and educational content for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to read study information for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_memory_file",
                    "description": "Read any memory file type for a character (profile, event, reminder, important_event, interests, study)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character"
                            },
                            "memory_type": {
                                "type": "string",
                                "description": "Type of memory file to read",
                                "enum": ["profile", "event", "reminder", "important_event", "interests", "study"]
                            }
                        },
                        "required": ["character_name", "memory_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_character_memory",
                    "description": "Update character memory files from conversation session",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to update memory for"
                            },
                            "conversation": {
                                "type": "string",
                                "description": "The conversation text to analyze and update from"
                            },
                            "session_date": {
                                "type": "string", 
                                "description": "Date of the conversation session",
                                "default": ""
                            }
                        },
                        "required": ["character_name", "conversation"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_memory_file",
                    "description": "Update a specific memory file type for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character"
                            },
                            "memory_type": {
                                "type": "string",
                                "description": "Type of memory file to update",
                                "enum": ["profile", "event", "reminder", "important_event", "interests", "study"]
                            },
                            "content": {
                                "type": "string",
                                "description": "New content to write to the file"
                            },
                            "append": {
                                "type": "boolean",
                                "description": "Whether to append to existing content (true) or replace it (false)",
                                "default": False
                            }
                        },
                        "required": ["character_name", "memory_type", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_relevant_events",
                    "description": "Search for events relevant to a specific query across characters",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find relevant events"
                            },
                            "characters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of character names to search in (optional, searches all if empty)",
                                "default": []
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of top results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_available_characters",
                    "description": "List all available characters in memory",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_character_memory",
                    "description": "Clear all memory files for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to clear memory for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_character_info",
                    "description": "Get information about a character's memory files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to get info for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            }
        ]

        # Add database-specific tools if using database storage
        if self.use_database:
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_similar_content",
                    "description": "Search for similar content using vector similarity (database storage only)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "content_type": {
                                "type": "string",
                                "description": "Type of content to search (optional)",
                                "enum": ["profile", "event", "reminder", "important_event", "interests", "study"]
                            },
                            "character_name": {
                                "type": "string",
                                "description": "Character name to limit search to (optional)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        return tools
    
    # Tool implementations
    
    def read_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character profile information"""
        try:
            profile_content = self.storage_manager.read_profile(character_name)
            return {
                "success": True,
                "character_name": character_name,
                "profile_content": profile_content,
                "has_profile": bool(profile_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def read_character_events(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character event records"""
        try:
            events_content = self.storage_manager.read_events(character_name)
            return {
                "success": True,
                "character_name": character_name,
                "events_content": events_content,
                "has_events": bool(events_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }

    def read_character_reminders(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character reminders and todo items"""
        try:
            if hasattr(self.storage_manager, 'read_reminders'):
                reminders_content = self.storage_manager.read_reminders(character_name)
            else:
                # Fallback for database storage
                reminders_content = self.storage_manager.read_memory_file(character_name, "reminder")
            return {
                "success": True,
                "character_name": character_name,
                "reminders_content": reminders_content,
                "has_reminders": bool(reminders_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }

    def read_character_important_events(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character important events and milestones"""
        try:
            if hasattr(self.storage_manager, 'read_important_events'):
                important_events_content = self.storage_manager.read_important_events(character_name)
            else:
                # Fallback for database storage
                important_events_content = self.storage_manager.read_memory_file(character_name, "important_event")
            return {
                "success": True,
                "character_name": character_name,
                "important_events_content": important_events_content,
                "has_important_events": bool(important_events_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }

    def read_character_interests(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character interests, hobbies, and preferences"""
        try:
            if hasattr(self.storage_manager, 'read_interests'):
                interests_content = self.storage_manager.read_interests(character_name)
            else:
                # Fallback for database storage
                interests_content = self.storage_manager.read_memory_file(character_name, "interests")
            return {
                "success": True,
                "character_name": character_name,
                "interests_content": interests_content,
                "has_interests": bool(interests_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }

    def read_character_study(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character study information, learning goals, and educational content"""
        try:
            if hasattr(self.storage_manager, 'read_study'):
                study_content = self.storage_manager.read_study(character_name)
            else:
                # Fallback for database storage
                study_content = self.storage_manager.read_memory_file(character_name, "study")
            return {
                "success": True,
                "character_name": character_name,
                "study_content": study_content,
                "has_study": bool(study_content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }

    def read_memory_file(self, character_name: str, memory_type: str) -> Dict[str, Any]:
        """Tool: Read any memory file type for a character"""
        try:
            if hasattr(self.storage_manager, 'read_memory_file'):
                content = self.storage_manager.read_memory_file(character_name, memory_type)
            else:
                # Fallback to specific methods based on memory type
                if memory_type == "profile":
                    content = self.storage_manager.read_profile(character_name)
                elif memory_type == "event":
                    content = self.storage_manager.read_events(character_name)
                else:
                    return {
                        "success": False,
                        "error": f"Memory type '{memory_type}' not supported by storage manager",
                        "character_name": character_name,
                        "memory_type": memory_type
                    }
            
            return {
                "success": True,
                "character_name": character_name,
                "memory_type": memory_type,
                "content": content,
                "has_content": bool(content.strip())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "memory_type": memory_type
            }

    def update_character_memory(self, character_name: str, conversation: str, session_date: str = "") -> Dict[str, Any]:
        """Tool: Update character memory from conversation"""
        try:
            if not self.llm_client:
                return {
                    "success": False,
                    "error": "No LLM client provided for memory analysis",
                    "character_name": character_name
                }
            
            # Read existing memory for all file types
            existing_profile = self.storage_manager.read_profile(character_name)
            existing_events = self.storage_manager.read_events(character_name)
            
            # Read existing memory for new file types (with fallback for compatibility)
            existing_reminders = ""
            existing_important_events = ""
            existing_interests = ""
            existing_study = ""
            
            if hasattr(self.storage_manager, 'read_reminders'):
                existing_reminders = self.storage_manager.read_reminders(character_name)
                existing_important_events = self.storage_manager.read_important_events(character_name)
                existing_interests = self.storage_manager.read_interests(character_name)
                existing_study = self.storage_manager.read_study(character_name)
            elif hasattr(self.storage_manager, 'read_memory_file'):
                existing_reminders = self.storage_manager.read_memory_file(character_name, "reminder")
                existing_important_events = self.storage_manager.read_memory_file(character_name, "important_event")
                existing_interests = self.storage_manager.read_memory_file(character_name, "interests")
                existing_study = self.storage_manager.read_memory_file(character_name, "study")
            
            # Analyze conversation for all memory types
            new_events = self._analyze_session_for_events(
                character_name, conversation, session_date, existing_events
            )
            
            new_reminders = self._analyze_session_for_reminders(
                character_name, conversation, session_date, existing_reminders
            )
            
            new_important_events = self._analyze_session_for_important_events(
                character_name, conversation, session_date, existing_important_events
            )
            
            new_interests = self._analyze_session_for_interests(
                character_name, conversation, session_date, existing_interests
            )
            
            new_study = self._analyze_session_for_study(
                character_name, conversation, session_date, existing_study
            )
            
            # Update profile based on conversation and new information
            updated_profile = self._analyze_session_for_profile(
                character_name, conversation, existing_profile, new_events
            )
            
            # Update all memory files
            success_results = {}
            
            # Update events
            success_events = True
            if new_events.strip():
                success_events = self.storage_manager.append_events(character_name, new_events)
            success_results["events"] = success_events
                
            # Update profile
            success_profile = True
            if updated_profile.strip() and updated_profile != existing_profile:
                success_profile = self.storage_manager.write_profile(character_name, updated_profile)
            success_results["profile"] = success_profile
            
            # Update new memory types if storage manager supports them
            if hasattr(self.storage_manager, 'append_reminders') or hasattr(self.storage_manager, 'append_memory_file'):
                # Update reminders
                success_reminders = True
                if new_reminders.strip():
                    if hasattr(self.storage_manager, 'append_reminders'):
                        success_reminders = self.storage_manager.append_reminders(character_name, new_reminders)
                    else:
                        success_reminders = self.storage_manager.append_memory_file(character_name, "reminder", new_reminders)
                success_results["reminders"] = success_reminders
                
                # Update important events
                success_important_events = True
                if new_important_events.strip():
                    if hasattr(self.storage_manager, 'append_important_events'):
                        success_important_events = self.storage_manager.append_important_events(character_name, new_important_events)
                    else:
                        success_important_events = self.storage_manager.append_memory_file(character_name, "important_event", new_important_events)
                success_results["important_events"] = success_important_events
                
                # Update interests
                success_interests = True
                if new_interests.strip():
                    if hasattr(self.storage_manager, 'append_interests'):
                        success_interests = self.storage_manager.append_interests(character_name, new_interests)
                    else:
                        success_interests = self.storage_manager.append_memory_file(character_name, "interests", new_interests)
                success_results["interests"] = success_interests
                
                # Update study information
                success_study = True
                if new_study.strip():
                    if hasattr(self.storage_manager, 'append_study'):
                        success_study = self.storage_manager.append_study(character_name, new_study)
                    else:
                        success_study = self.storage_manager.append_memory_file(character_name, "study", new_study)
                success_results["study"] = success_study
            
            # Calculate overall success
            overall_success = all(success_results.values())
            
            return {
                "success": overall_success,
                "character_name": character_name,
                "session_date": session_date,
                "update_results": success_results,
                "profile_updated": success_profile and updated_profile != existing_profile,
                "events_updated": success_events and bool(new_events.strip()),
                "reminders_updated": success_results.get("reminders", False) and bool(new_reminders.strip()),
                "important_events_updated": success_results.get("important_events", False) and bool(new_important_events.strip()),
                "interests_updated": success_results.get("interests", False) and bool(new_interests.strip()),
                "study_updated": success_results.get("study", False) and bool(new_study.strip()),
                "new_content": {
                    "events": new_events,
                    "reminders": new_reminders,
                    "important_events": new_important_events,
                    "interests": new_interests,
                    "study": new_study,
                    "updated_profile": updated_profile if updated_profile != existing_profile else ""
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def update_memory_file(self, character_name: str, memory_type: str, content: str, append: bool = False) -> Dict[str, Any]:
        """Tool: Update a specific memory file type for a character"""
        try:
            if hasattr(self.storage_manager, 'write_memory_file') and hasattr(self.storage_manager, 'append_memory_file'):
                # Use generic methods if available
                if append:
                    success = self.storage_manager.append_memory_file(character_name, memory_type, content)
                else:
                    success = self.storage_manager.write_memory_file(character_name, memory_type, content)
            else:
                # Fallback to specific methods based on memory type
                if memory_type == "profile":
                    success = self.storage_manager.write_profile(character_name, content)
                elif memory_type == "event":
                    if append:
                        success = self.storage_manager.append_events(character_name, content)
                    else:
                        success = self.storage_manager.write_events(character_name, content)
                else:
                    return {
                        "success": False,
                        "error": f"Memory type '{memory_type}' not supported by storage manager",
                        "character_name": character_name,
                        "memory_type": memory_type
                    }

            return {
                "success": success,
                "character_name": character_name,
                "memory_type": memory_type,
                "content_length": len(content),
                "operation": "append" if append else "write"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "memory_type": memory_type
            }
    
    def search_relevant_events(self, query: str, characters: List[str] = None, top_k: int = 10) -> Dict[str, Any]:
        """Tool: Search for events relevant to query"""
        try:
            # Use all characters if none specified
            if not characters:
                characters = self.storage_manager.list_characters()
            
            all_chunks = []
            
            # Prepare event chunks from all characters
            for character in characters:
                events = self.storage_manager.read_events(character)
                if not events.strip():
                    continue
                
                lines = events.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    chunk = {
                        'text': line,
                        'character': character,
                        'original_line': line
                    }
                    all_chunks.append(chunk)
            
            if not all_chunks:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "total_found": 0
                }
            
            # BM25 search
            tokenized_corpus = [chunk['text'].lower().split() for chunk in all_chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            
            # Get top results
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            
            for idx in top_indices:
                if idx < len(all_chunks) and scores[idx] > 0.1:
                    chunk = all_chunks[idx]
                    results.append({
                        "character": chunk['character'],
                        "text": chunk['text'],
                        "relevance_score": float(scores[idx])
                    })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def list_available_characters(self) -> Dict[str, Any]:
        """Tool: List characters with memory files"""
        try:
            characters = self.storage_manager.list_characters()
            return {
                "success": True,
                "characters": characters,
                "total_characters": len(characters)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_character_memory(self, character_name: str) -> Dict[str, Any]:
        """Tool: Clear memory files for a character"""
        try:
            results = self.storage_manager.clear_character_memory(character_name)
            return {
                "success": all(results.values()),
                "character_name": character_name,
                "clear_results": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def get_character_info(self, character_name: str) -> Dict[str, Any]:
        """Tool: Get character information"""
        try:
            info = self.storage_manager.get_character_info(character_name)
            return {
                "success": True,
                **info
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def search_similar_content(self, query: str, content_type: Optional[str] = None, 
                             character_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Tool: Search for similar content using vector similarity (database storage only)"""
        if not self.use_database:
            return {
                "success": False,
                "error": "Vector search is only available with database storage"
            }
        
        try:
            # Call the search method from MemoryDatabaseManager
            results = self.storage_manager.search_similar_content(
                query=query,
                content_type=content_type,
                character_name=character_name,
                limit=limit
            )
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results),
                "search_type": "vector_similarity"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    # Helper methods for LLM analysis
    
    def _analyze_session_for_events(
        self, character_name: str, conversation: str, session_date: str, existing_events: str
    ) -> str:
        """Analyze conversation session to extract new events"""
        if not self.llm_client:
            logger.error("No LLM client available for event analysis")
            return ""
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_events")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_events=existing_events if existing_events.strip() else "None",
                session_date=session_date if session_date else "Not specified"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=4000)
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Error analyzing events for {character_name}: {e}")
            return ""
    
    def _analyze_session_for_profile(
        self, character_name: str, conversation: str, existing_profile: str, new_events: str
    ) -> str:
        """Analyze conversation session to update character profile"""
        if not self.llm_client:
            logger.error("No LLM client available for profile analysis")
            return existing_profile
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_profile")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_profile=existing_profile if existing_profile.strip() else "None",
                events=new_events if new_events.strip() else "None"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=4000)
            return response.strip() if response else existing_profile
            
        except Exception as e:
            logger.error(f"Error analyzing profile for {character_name}: {e}")
            return existing_profile

    def _analyze_session_for_reminders(
        self, character_name: str, conversation: str, session_date: str, existing_reminders: str
    ) -> str:
        """Analyze conversation session to extract new reminders"""
        if not self.llm_client:
            logger.error("No LLM client available for reminder analysis")
            return ""
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_reminders")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_reminders=existing_reminders if existing_reminders.strip() else "None",
                session_date=session_date if session_date else "Not specified"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=2000)
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Error analyzing reminders for {character_name}: {e}")
            return ""

    def _analyze_session_for_important_events(
        self, character_name: str, conversation: str, session_date: str, existing_important_events: str
    ) -> str:
        """Analyze conversation session to extract new important events"""
        if not self.llm_client:
            logger.error("No LLM client available for important events analysis")
            return ""
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_important_events")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_important_events=existing_important_events if existing_important_events.strip() else "None",
                session_date=session_date if session_date else "Not specified"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=2000)
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Error analyzing important events for {character_name}: {e}")
            return ""

    def _analyze_session_for_interests(
        self, character_name: str, conversation: str, session_date: str, existing_interests: str
    ) -> str:
        """Analyze conversation session to extract new interests"""
        if not self.llm_client:
            logger.error("No LLM client available for interests analysis")
            return ""
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_interests")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_interests=existing_interests if existing_interests.strip() else "None",
                session_date=session_date if session_date else "Not specified"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=2000)
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Error analyzing interests for {character_name}: {e}")
            return ""

    def _analyze_session_for_study(
        self, character_name: str, conversation: str, session_date: str, existing_study: str
    ) -> str:
        """Analyze conversation session to extract new study information"""
        if not self.llm_client:
            logger.error("No LLM client available for study analysis")
            return ""
        
        try:
            # Use prompt template from file
            prompt_template = self.prompt_loader.load_prompt("analyze_session_for_study")
            prompt = prompt_template.format(
                character_name=character_name,
                conversation=conversation,
                existing_study=existing_study if existing_study.strip() else "None",
                session_date=session_date if session_date else "Not specified"
            )

            response = self.llm_client.simple_chat(prompt, max_tokens=2000)
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Error analyzing study information for {character_name}: {e}")
            return ""
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool by name"""
        if not hasattr(self, tool_name):
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        try:
            tool_function = getattr(self, tool_name)
            return tool_function(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing tool '{tool_name}': {str(e)}"
            }
    
    def execute(self, user_message: str, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Execute recursive function calling agent for memory operations
        
        Args:
            user_message: User's request or question
            max_iterations: Maximum number of function calling iterations
            
        Returns:
            Dict with execution results
        """
        try:
            if not self.llm_client:
                return {
                    "success": False,
                    "error": "No LLM client provided for agent execution"
                }
            
            # Get available tools for function calling
            tools = self.get_available_tools()
            
            # Initialize conversation with prompt template
            system_message = self.prompt_loader.load_prompt("system_message")
            messages = [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ]
            
            # Track execution details
            execution_log = []
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                try:
                    logger.info(f"Function calling iteration {iteration}")
                    
                    # Call LLM with function tools
                    response = self.llm_client.chat_completion(
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        max_tokens=16000
                    )
                    
                    # Check if response was successful
                    if not response.success:
                        return {
                            "success": False,
                            "error": f"LLM call failed: {response.error}",
                            "iterations": iteration,
                            "execution_log": execution_log
                        }
                    
                    # Create message from response
                    message_content = {
                        "role": "assistant",
                        "content": response.content if response.content else None
                    }
                    
                    # Add tool_calls if present
                    if response.tool_calls:
                        message_content["tool_calls"] = [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                            for tool_call in response.tool_calls
                        ]
                    
                    messages.append(message_content)
                    
                    # Check if LLM wants to call tools
                    if response.tool_calls:
                        logger.info(f"LLM made {len(response.tool_calls)} tool calls")
                        
                        # Process each tool call
                        for tool_call in response.tool_calls:
                            tool_name = tool_call.function.name
                            logger.info(f"Calling tool: {tool_name}")
                            
                            try:
                                tool_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError as e:
                                tool_result = {"success": False, "error": f"Invalid JSON arguments: {str(e)}"}
                                logger.error(f"JSON decode error for tool {tool_name}: {e}")
                            else:
                                # Execute the tool
                                tool_result = self.execute_tool(tool_name, **tool_args)
                                logger.info(f"Tool {tool_name} executed, success: {tool_result.get('success', False)}")
                            
                            # Log tool execution
                            execution_log.append({
                                "iteration": iteration,
                                "tool_name": tool_name,
                                "tool_args": tool_args if 'tool_args' in locals() else None,
                                "success": tool_result.get("success", False),
                                "error": tool_result.get("error") if not tool_result.get("success", False) else None
                            })
                            
                            # Add tool result to conversation
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result)
                            })
                    else:
                        # LLM provided final response
                        final_response = response.content.strip()
                        logger.info(f"LLM provided final response after {iteration-1} tool calls")
                        
                        return {
                            "success": True,
                            "response": final_response,
                            "iterations": iteration - 1,
                            "tool_calls_made": len(execution_log),
                            "execution_log": execution_log,
                            "messages": messages
                        }
                        
                except Exception as e:
                    logger.error(f"Error in function calling iteration {iteration}: {e}")
                    return {
                        "success": False,
                        "error": f"Function calling failed at iteration {iteration}: {str(e)}",
                        "iterations": iteration,
                        "execution_log": execution_log
                    }
            
            # Max iterations reached
            logger.warning(f"Maximum iterations ({max_iterations}) reached")
            return {
                "success": False,
                "error": f"Maximum iterations ({max_iterations}) reached without final response",
                "iterations": max_iterations,
                "execution_log": execution_log,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Error in execute: {e}")
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "execution_log": []
            } 