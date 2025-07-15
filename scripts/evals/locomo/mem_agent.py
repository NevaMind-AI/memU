"""
MemAgent - Unified Memory Agent

This implementation provides comprehensive memory management capabilities through function tools
that can be used by AI agents to maintain, query, and analyze character memories.

Combines all memory operations in a single agent:
- Memory Retrieval: read profiles, events, search, evaluate answers
- Memory Management: update memories, analyze conversations, clear data
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi

import dotenv
dotenv.load_dotenv()

from memu.llm import AzureOpenAIClient
from memu.utils import get_logger, setup_logging

# Add prompts directory to path and import prompt loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prompts'))
from prompt_loader import get_prompt_loader

logger = setup_logging(__name__, enable_flush=True)


class MemAgent:
    """
    Unified Memory Agent
    
    Provides comprehensive memory management capabilities through callable functions:
    
    Memory Retrieval:
    - read_character_profile: Read complete character profile
    - read_character_events: Read character event records  
    - search_relevant_events: Search for events relevant to a query
    - evaluate_answer: Evaluate answers using memory context
    - list_available_characters: List all available characters
    
    Memory Management:
    - update_character_memory: Update memory files from conversation
    - analyze_session_for_events: Extract events from conversations
    - analyze_session_for_profile: Update profile from conversations
    - clear_character_memory: Clear memory files for characters
    
    Agent Execution:
    - execute: Process user messages with function calling
    """
    
    def __init__(
        self,
        azure_endpoint: str = None,
        api_key: str = None,
        chat_deployment: str = "gpt-4.1-mini",
        use_entra_id: bool = False,
        api_version: str = "2024-02-15-preview",
        memory_dir: str = "memory"
    ):
        """Initialize MemAgent with LLM configuration and memory directory"""
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.chat_deployment = chat_deployment
        self.use_entra_id = use_entra_id
        self.api_version = api_version
        self.memory_dir = Path(memory_dir)
        
        # Ensure memory directory exists
        self.memory_dir.mkdir(exist_ok=True)
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        # Initialize LLM client
        self.llm_client = self._init_llm_client()
        
        logger.info(f"MemAgent initialized with memory directory: {self.memory_dir}")

    def _init_llm_client(self):
        """Initialize the LLM client"""
        try:
            return AzureOpenAIClient(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                chat_deployment=self.chat_deployment,
                use_entra_id=self.use_entra_id,
                api_version=self.api_version
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available function tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_character_profile",
                    "description": "Read the complete character profile from memory files",
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
                    "description": "Read the character's event records from memory files",
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
                    "name": "search_relevant_events",
                    "description": "Search for events relevant to a query across specified characters using BM25 and semantic matching",
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
                                "description": "List of character names to search through"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of most relevant events to return",
                                "default": 10
                            }
                        },
                        "required": ["query", "characters"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_character_memory",
                    "description": "Update character memory files from conversation session data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_data": {
                                "type": "array",
                                "description": "List of conversation utterances with speaker and text",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "speaker": {"type": "string"},
                                        "text": {"type": "string"}
                                    }
                                }
                            },
                            "session_date": {
                                "type": "string",
                                "description": "Date/timestamp of the conversation session"
                            },
                            "characters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of character names involved in the conversation"
                            }
                        },
                        "required": ["session_data", "session_date", "characters"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_answer",
                    "description": "Evaluate if a generated answer contains the key information from the standard answer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The original question being answered"
                            },
                            "generated_answer": {
                                "type": "string",
                                "description": "The AI-generated answer to evaluate"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The reference/standard answer to compare against"
                            }
                        },
                        "required": ["question", "generated_answer", "standard_answer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_character_memory",
                    "description": "Clear all memory files for specified characters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "characters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of character names to clear memory for"
                            }
                        },
                        "required": ["characters"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_available_characters",
                    "description": "List all characters that have memory files available",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    def _get_memory_file_path(self, character_name: str, memory_type: str) -> Path:
        """Get the file path for a character's memory file"""
        return self.memory_dir / f"{character_name}_{memory_type}.txt"

    def _read_memory_file(self, character_name: str, memory_type: str) -> str:
        """Read content from a character's memory file"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return ""

    def _write_memory_file(self, character_name: str, memory_type: str, content: str):
        """Write content to a character's memory file"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

    def read_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Read the complete character profile from memory files"""
        try:
            profile_content = self._read_memory_file(character_name, "profile")
            
            return {
                "success": True,
                "character_name": character_name,
                "profile": profile_content,
                "file_exists": bool(profile_content.strip())
            }
            
        except Exception as e:
            logger.error(f"Failed to read profile for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "profile": "",
                "file_exists": False
            }

    def read_character_events(self, character_name: str) -> Dict[str, Any]:
        """Read the character's event records from memory files"""
        try:
            events_content = self._read_memory_file(character_name, "events")
            
            return {
                "success": True,
                "character_name": character_name,
                "events": events_content,
                "file_exists": bool(events_content.strip())
            }
            
        except Exception as e:
            logger.error(f"Failed to read events for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "events": "",
                "file_exists": False
            }

    def search_relevant_events(self, query: str, characters: List[str], top_k: int = 10) -> Dict[str, Any]:
        """Search for events relevant to a query across specified characters using BM25 and semantic matching"""
        try:
            all_events = []
            character_event_map = {}
            
            # Collect all events from specified characters
            for character in characters:
                events_content = self._read_memory_file(character, "events")
                if events_content.strip():
                    # Split events by common delimiters
                    events = re.split(r'\n\s*\n|\n-|\n•|\n\d+\.', events_content)
                    events = [event.strip() for event in events if event.strip()]
                    
                    for event in events:
                        all_events.append(event)
                        character_event_map[len(all_events) - 1] = character
            
            if not all_events:
                return {
                    "success": True,
                    "query": query,
                    "relevant_events": [],
                    "total_events_searched": 0,
                    "characters_searched": characters
                }
            
            # Tokenize for BM25
            tokenized_events = [event.lower().split() for event in all_events]
            tokenized_query = query.lower().split()
            
            # Initialize BM25
            bm25 = BM25Okapi(tokenized_events)
            
            # Get BM25 scores
            bm25_scores = bm25.get_scores(tokenized_query)
            
            # Get top results with scores and character info
            event_scores = [(i, score) for i, score in enumerate(bm25_scores)]
            event_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            relevant_events = []
            for i, (event_idx, score) in enumerate(event_scores[:top_k]):
                relevant_events.append({
                    "rank": i + 1,
                    "character": character_event_map[event_idx],
                    "event": all_events[event_idx],
                    "score": float(score),
                    "relevance": "high" if score > 1.0 else "medium" if score > 0.5 else "low"
                })
            
            return {
                "success": True,
                "query": query,
                "relevant_events": relevant_events,
                "total_events_searched": len(all_events),
                "characters_searched": characters
            }
            
        except Exception as e:
            logger.error(f"Failed to search events for query '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "relevant_events": [],
                "total_events_searched": 0,
                "characters_searched": characters
            }

    def update_character_memory(self, session_data: List[Dict], session_date: str, characters: List[str]) -> Dict[str, Any]:
        """Update character memory files from conversation session data"""
        try:
            # Convert session data to conversation string
            conversation = ""
            for utterance in session_data:
                speaker = utterance.get('speaker', 'Unknown')
                text = utterance.get('text', '')
                conversation += f"{speaker}: {text}\n"
            
            update_results = {}
            
            # Process each character
            for character_name in characters:
                try:
                    # Read existing memory files
                    existing_events = self._read_memory_file(character_name, "events")
                    existing_profile = self._read_memory_file(character_name, "profile")
                    
                    # Analyze session for new events
                    events_result = self.analyze_session_for_events(
                        character_name, conversation, session_date, existing_events
                    )
                    
                    if events_result["success"]:
                        new_events = events_result["new_events"]
                        
                        # Update events file
                        if new_events.strip():
                            updated_events = existing_events + "\n" + new_events if existing_events.strip() else new_events
                            self._write_memory_file(character_name, "events", updated_events)
                            
                            # Analyze session for profile updates
                            profile_result = self.analyze_session_for_profile(
                                character_name, conversation, existing_profile, new_events
                            )
                            
                            if profile_result["success"]:
                                updated_profile = profile_result["updated_profile"]
                                if updated_profile.strip():
                                    self._write_memory_file(character_name, "profile", updated_profile)
                        
                        update_results[character_name] = {
                            "success": True,
                            "events_updated": bool(new_events.strip()),
                            "profile_updated": profile_result.get("success", False) if new_events.strip() else False
                        }
                    else:
                        update_results[character_name] = {
                            "success": False,
                            "error": events_result.get("error", "Failed to analyze events")
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to update memory for {character_name}: {e}")
                    update_results[character_name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "success": True,
                "session_date": session_date,
                "characters_processed": characters,
                "update_results": update_results
            }
            
        except Exception as e:
            logger.error(f"Failed to update character memory: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_date": session_date,
                "characters_processed": characters,
                "update_results": {}
            }

    def analyze_session_for_events(self, character_name: str, conversation: str, session_date: str, existing_events: str) -> Dict[str, Any]:
        """Extract events from conversations"""
        try:
            new_events = self._analyze_session_for_events(character_name, conversation, session_date, existing_events)
            
            return {
                "success": True,
                "character_name": character_name,
                "session_date": session_date,
                "new_events": new_events
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze session for events for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "session_date": session_date,
                "new_events": ""
            }

    def analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str, events: str) -> Dict[str, Any]:
        """Update profile from conversations"""
        try:
            updated_profile = self._analyze_session_for_profile(character_name, conversation, existing_profile, events)
            
            return {
                "success": True,
                "character_name": character_name,
                "updated_profile": updated_profile
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze session for profile for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "updated_profile": existing_profile
            }

    def evaluate_answer(self, question: str, generated_answer: str, standard_answer: str) -> Dict[str, Any]:
        """Evaluate if a generated answer contains the key information from the standard answer"""
        try:
            # Load evaluation prompt
            evaluation_prompt = self.prompt_loader.format_prompt(
                "evaluate_answer",
                question=question,
                generated_answer=generated_answer,
                standard_answer=standard_answer
            )
            
            # Get evaluation from LLM
            messages = [{"role": "user", "content": evaluation_prompt}]
            llm_response = self.llm_client.chat_completion(messages, max_tokens=500, temperature=0.1)
            
            if not llm_response.success:
                raise Exception(f"LLM evaluation failed: {llm_response.error}")
                
            evaluation_text = llm_response.content.strip()
            
            # Parse the evaluation result
            is_correct = False
            explanation = evaluation_text
            
            # Look for explicit judgment
            if "CORRECT" in evaluation_text.upper():
                is_correct = True
            elif "INCORRECT" in evaluation_text.upper():
                is_correct = False
            else:
                # Fallback: look for positive/negative indicators
                positive_indicators = ["yes", "contains", "accurate", "correct", "appropriate"]
                negative_indicators = ["no", "missing", "incorrect", "inaccurate", "inappropriate"]
                
                text_lower = evaluation_text.lower()
                positive_count = sum(1 for indicator in positive_indicators if indicator in text_lower)
                negative_count = sum(1 for indicator in negative_indicators if indicator in text_lower)
                
                is_correct = positive_count > negative_count
            
            return {
                "success": True,
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "is_correct": is_correct,
                "explanation": explanation,
                "evaluation_text": evaluation_text
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "is_correct": False,
                "explanation": f"Evaluation failed: {e}",
                "evaluation_text": ""
            }

    def clear_character_memory(self, characters: List[str]) -> Dict[str, Any]:
        """Clear all memory files for specified characters"""
        try:
            clear_results = {}
            
            for character_name in characters:
                try:
                    profile_path = self._get_memory_file_path(character_name, "profile")
                    events_path = self._get_memory_file_path(character_name, "events")
                    
                    profile_deleted = False
                    events_deleted = False
                    
                    if profile_path.exists():
                        profile_path.unlink()
                        profile_deleted = True
                    
                    if events_path.exists():
                        events_path.unlink()
                        events_deleted = True
                    
                    clear_results[character_name] = {
                        "success": True,
                        "profile_deleted": profile_deleted,
                        "events_deleted": events_deleted
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to clear memory for {character_name}: {e}")
                    clear_results[character_name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "success": True,
                "characters_processed": characters,
                "clear_results": clear_results
            }
            
        except Exception as e:
            logger.error(f"Failed to clear character memory: {e}")
            return {
                "success": False,
                "error": str(e),
                "characters_processed": characters,
                "clear_results": {}
            }

    def list_available_characters(self) -> Dict[str, Any]:
        """List all characters that have memory files available"""
        try:
            characters = set()
            
            # Scan memory directory for character files
            if self.memory_dir.exists():
                for file_path in self.memory_dir.glob("*_profile.txt"):
                    character_name = file_path.stem.replace("_profile", "")
                    characters.add(character_name)
                
                for file_path in self.memory_dir.glob("*_events.txt"):
                    character_name = file_path.stem.replace("_events", "")
                    characters.add(character_name)
            
            character_list = sorted(list(characters))
            
            return {
                "success": True,
                "characters": character_list,
                "total_count": len(character_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to list available characters: {e}")
            return {
                "success": False,
                "error": str(e),
                "characters": [],
                "total_count": 0
            }

    def _analyze_session_for_events(self, character_name: str, conversation: str, session_date: str, existing_events: str) -> str:
        """Internal method to analyze session for events using LLM"""
        events_prompt = self.prompt_loader.format_prompt(
            "analyze_session_for_events",
            character_name=character_name,
            conversation=conversation,
            session_date=session_date,
            existing_events=existing_events
        )
        
        messages = [{"role": "user", "content": events_prompt}]
        llm_response = self.llm_client.chat_completion(messages, max_tokens=1000, temperature=0.3)
        
        if not llm_response.success:
            raise Exception(f"LLM events analysis failed: {llm_response.error}")
            
        return llm_response.content.strip()

    def _analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str, events: str) -> str:
        """Internal method to analyze session for profile using LLM"""
        profile_prompt = self.prompt_loader.format_prompt(
            "analyze_session_for_profile",
            character_name=character_name,
            conversation=conversation,
            existing_profile=existing_profile,
            events=events
        )
        
        messages = [{"role": "user", "content": profile_prompt}]
        llm_response = self.llm_client.chat_completion(messages, max_tokens=1500, temperature=0.3)
        
        if not llm_response.success:
            raise Exception(f"LLM profile analysis failed: {llm_response.error}")
            
        return llm_response.content.strip()

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool by name"""
        tool_methods = {
            "read_character_profile": self.read_character_profile,
            "read_character_events": self.read_character_events,
            "search_relevant_events": self.search_relevant_events,
            "update_character_memory": self.update_character_memory,
            "analyze_session_for_events": self.analyze_session_for_events,
            "analyze_session_for_profile": self.analyze_session_for_profile,
            "evaluate_answer": self.evaluate_answer,
            "clear_character_memory": self.clear_character_memory,
            "list_available_characters": self.list_available_characters
        }
        
        if tool_name not in tool_methods:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(tool_methods.keys())
            }
        
        try:
            return tool_methods[tool_name](**kwargs)
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "arguments": kwargs
            }

    def execute(self, user_message: str, max_iterations: int = 10) -> Dict[str, Any]:
        """Execute user message with function calling support"""
        try:
            tools = self.get_available_tools()
            messages = [{"role": "user", "content": user_message}]
            
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                
                # Get response from LLM with tools
                llm_response = self.llm_client.chat_completion(
                    messages=messages,
                    tools=tools,
                    max_tokens=2000,
                    temperature=0.1
                )
                
                # Check if LLM response was successful
                if not llm_response.success:
                    raise Exception(f"LLM call failed: {llm_response.error}")
                
                # Convert LLMResponse to dict format expected by the rest of the code
                response = {
                    "content": llm_response.content,
                    "tool_calls": llm_response.tool_calls or []
                }
                
                # Add assistant message
                messages.append({
                    "role": "assistant", 
                    "content": response.get("content", ""),
                    "tool_calls": response.get("tool_calls", [])
                })
                
                # Process tool calls if any
                if response.get("tool_calls"):
                    for tool_call in response["tool_calls"]:
                        try:
                            # Handle different possible tool call formats
                            if hasattr(tool_call, 'function'):
                                # OpenAI API format
                                tool_name = tool_call.function.name
                                arguments = json.loads(tool_call.function.arguments)
                                tool_call_id = tool_call.id
                            elif isinstance(tool_call, dict):
                                # Dict format
                                tool_name = tool_call["function"]["name"]
                                arguments = json.loads(tool_call["function"]["arguments"])
                                tool_call_id = tool_call["id"]
                            else:
                                logger.error(f"Unknown tool call format: {type(tool_call)}")
                                continue
                            
                            # Execute tool
                            result = self.execute_tool(tool_name, **arguments)
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(result, indent=2)
                            })
                        except Exception as e:
                            logger.error(f"Error processing tool call: {e}")
                            continue
                else:
                    # No more tool calls, we're done
                    break
            
            return {
                "success": True,
                "final_response": response.get("content", ""),
                "iterations": iteration,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Failed to execute user message: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_response": "",
                "iterations": 0,
                "messages": []
            } 