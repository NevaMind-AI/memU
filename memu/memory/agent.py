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
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi

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
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available memory tools"""
        return [
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
                    "description": "Clear memory files for a specific character",
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
        
        # Add vector search tool if using database storage
        if self.use_database:
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_similar_content",
                    "description": "Search for similar content using vector similarity (database storage only)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query text"},
                            "content_type": {
                                "type": "string", 
                                "description": "Filter by content type",
                                "enum": ["profile", "event", "mind"]
                            },
                            "character_name": {"type": "string", "description": "Filter by character name"},
                            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
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
    
    def update_character_memory(self, character_name: str, conversation: str, session_date: str = "") -> Dict[str, Any]:
        """Tool: Update character memory from conversation"""
        try:
            if not self.llm_client:
                return {
                    "success": False,
                    "error": "No LLM client provided for memory analysis",
                    "character_name": character_name
                }
            
            # Read existing memory
            existing_profile = self.storage_manager.read_profile(character_name)
            existing_events = self.storage_manager.read_events(character_name)
            
            # Update events first
            new_events = self._analyze_session_for_events(
                character_name, conversation, session_date, existing_events
            )
            
            success_events = True
            if new_events.strip():
                success_events = self.storage_manager.append_events(character_name, new_events)
                
            # Update profile based on conversation and new events
            updated_profile = self._analyze_session_for_profile(
                character_name, conversation, existing_profile, new_events
            )
            
            success_profile = True
            if updated_profile.strip() and updated_profile != existing_profile:
                success_profile = self.storage_manager.write_profile(character_name, updated_profile)
            
            return {
                "success": success_events and success_profile,
                "character_name": character_name,
                "session_date": session_date,
                "profile_updated": success_profile and updated_profile != existing_profile,
                "events_updated": success_events and bool(new_events.strip()),
                "new_events": new_events,
                "updated_profile": updated_profile if updated_profile != existing_profile else ""
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
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