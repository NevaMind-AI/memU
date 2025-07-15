"""
Memory Agent with Function Tools

This implementation provides memory management capabilities through function tools
that can be used by AI agents to maintain and query character memories.
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


class MemoryAgentTools:
    """
    Memory Agent implemented with Function Tools
    
    Provides memory management capabilities through callable functions:
    - read_character_profile: Read complete character profile
    - read_character_events: Read character event records  
    - search_relevant_events: Search for events relevant to a query
    - update_character_memory: Update memory files from conversation
    - answer_with_memory: Answer questions using memory context
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
        """Initialize Memory Agent Tools"""
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.chat_deployment = chat_deployment
        self.use_entra_id = use_entra_id
        self.api_version = api_version
        self.memory_dir = Path(memory_dir)
        
        # Create memory directory
        self.memory_dir.mkdir(exist_ok=True)
        
        # Initialize LLM client
        self._init_llm_client()
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader(self.memory_dir.parent / "prompts")
        
        logger.info(f"Memory Agent Tools initialized, memory directory: {self.memory_dir}")
    
    def _init_llm_client(self):
        """Initialize LLM client"""
        try:
            self.llm_client = AzureOpenAIClient(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                deployment_name=self.chat_deployment,
                use_entra_id=self.use_entra_id,
                api_version=self.api_version
            )
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"LLM client initialization failed: {e}")
            raise
    
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
                    "name": "search_relevant_events",
                    "description": "Search for events relevant to a specific query across all characters",
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
                                "description": "List of character names to search in"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of top results to return",
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
                    "description": "Update character memory files from conversation session",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "speaker": {"type": "string"},
                                        "text": {"type": "string"}
                                    }
                                },
                                "description": "List of conversation utterances"
                            },
                            "session_date": {
                                "type": "string",
                                "description": "Date of the conversation session"
                            },
                            "characters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of character names involved"
                            }
                        },
                        "required": ["session_data", "session_date", "characters"]
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
                    "description": "Clear memory files for specified characters",
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
                    "name": "analyze_session_for_events",
                    "description": "Analyze a conversation session to extract event records for a character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to analyze events for"
                            },
                            "conversation": {
                                "type": "string",
                                "description": "The conversation text to analyze"
                            },
                            "session_date": {
                                "type": "string",
                                "description": "Date of the conversation session"
                            },
                            "existing_events": {
                                "type": "string",
                                "description": "Existing event records for the character"
                            }
                        },
                        "required": ["character_name", "conversation", "session_date", "existing_events"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_session_for_profile",
                    "description": "Analyze a conversation session to update character profile",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to analyze profile for"
                            },
                            "conversation": {
                                "type": "string",
                                "description": "The conversation text to analyze"
                            },
                            "existing_profile": {
                                "type": "string",
                                "description": "Existing profile for the character"
                            },
                            "events": {
                                "type": "string",
                                "description": "Event records for the character"
                            }
                        },
                        "required": ["character_name", "conversation", "existing_profile", "events"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_answer",
                    "description": "Evaluate if a generated answer contains the content from a standard answer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question being answered"
                            },
                            "generated_answer": {
                                "type": "string",
                                "description": "The generated answer to evaluate"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The standard/correct answer to compare against"
                            }
                        },
                        "required": ["question", "generated_answer", "standard_answer"]
                    }
                }
            }
        ]
    
    def _get_memory_file_path(self, character_name: str, memory_type: str) -> Path:
        """Get memory file path"""
        return self.memory_dir / f"{character_name.lower()}_{memory_type}.md"
    
    def _read_memory_file(self, character_name: str, memory_type: str) -> str:
        """Read memory file content"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def _write_memory_file(self, character_name: str, memory_type: str, content: str):
        """Write memory file"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Updated {character_name}'s {memory_type}.md")
    
    # Function Tools Implementation
    
    def read_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Tool: Read character profile information"""
        try:
            profile_content = self._read_memory_file(character_name, "profile")
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
            events_content = self._read_memory_file(character_name, "event")
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
    
    def search_relevant_events(self, query: str, characters: List[str], top_k: int = 10) -> Dict[str, Any]:
        """Tool: Search for events relevant to query"""
        try:
            all_chunks = []
            
            # Prepare event chunks from all characters
            for character in characters:
                events = self._read_memory_file(character, "event")
                if not events.strip():
                    continue
                
                lines = events.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        i += 1
                        continue
                    
                    # Check if next line is a TOM comment
                    combined_text = line
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('<!--'):
                        tom_comment = lines[i + 1].strip()
                        combined_text = f"{line} {tom_comment}"
                        i += 2
                    else:
                        i += 1
                    
                    chunk = {
                        'text': combined_text,
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
                        "original_line": chunk['original_line'],
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
    
    def update_character_memory(self, session_data: List[Dict], session_date: str, characters: List[str]) -> Dict[str, Any]:
        """Tool: Update character memory from conversation session"""
        try:
            # Format conversation
            conversation_lines = [f"## Session Date: {session_date}", ""]
            for utterance in session_data:
                speaker = utterance.get('speaker', 'Unknown')
                content = utterance.get('text', '')
                conversation_lines.append(f"**{speaker}**: {content}")
            conversation = "\n".join(conversation_lines)
            
            update_results = {}
            
            for character in characters:
                try:
                    # Read existing memory
                    existing_profile = self._read_memory_file(character, "profile")
                    existing_events = self._read_memory_file(character, "event")
                    
                    # Update events
                    new_events = self._analyze_session_for_events(character, conversation, session_date, existing_events)
                    if existing_events.strip():
                        accumulated_events = existing_events + "\n\n" + new_events
                    else:
                        accumulated_events = new_events
                    
                    # Update profile
                    updated_profile = self._analyze_session_for_profile(character, conversation, existing_profile, new_events)
                    
                    # Save updates
                    self._write_memory_file(character, "profile", updated_profile)
                    self._write_memory_file(character, "event", accumulated_events)
                    
                    update_results[character] = {
                        "success": True,
                        "profile_updated": True,
                        "events_updated": True
                    }
                    
                except Exception as char_error:
                    update_results[character] = {
                        "success": False,
                        "error": str(char_error)
                    }
            
            return {
                "success": True,
                "session_date": session_date,
                "characters_processed": len(characters),
                "update_results": update_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_date": session_date
            }
    
    def analyze_session_for_events(self, character_name: str, conversation: str, session_date: str, existing_events: str) -> Dict[str, Any]:
        """Tool: Analyze session for events"""
        try:
            prompt = self.prompt_loader.format_prompt(
                "analyze_session_for_events",
                character_name=character_name,
                conversation=conversation,
                session_date=session_date,
                existing_events=existing_events
            )
            
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            new_events = response.strip()
            
            return {
                "success": True,
                "character_name": character_name,
                "session_date": session_date,
                "new_events": new_events
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str, events: str) -> Dict[str, Any]:
        """Tool: Analyze session for profile updates"""
        try:
            prompt = self.prompt_loader.format_prompt(
                "analyze_session_for_profile",
                character_name=character_name,
                conversation=conversation,
                existing_profile=existing_profile,
                events=events
            )
            
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            updated_profile = response.strip()
            
            return {
                "success": True,
                "character_name": character_name,
                "updated_profile": updated_profile
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name
            }
    
    def evaluate_answer(self, question: str, generated_answer: str, standard_answer: str) -> Dict[str, Any]:
        """Tool: Evaluate answer correctness"""
        try:
            prompt = self.prompt_loader.format_prompt(
                "evaluate_answer",
                question=question,
                generated_answer=generated_answer,
                standard_answer=standard_answer
            )
            
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            is_correct = "yes" in response.split("Answer:")[1].split("\n")[0].lower() if "Answer:" in response else False
            
            return {
                "success": True,
                "question": question,
                "is_correct": is_correct,
                "explanation": response,
                "evaluation_text": response
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def list_available_characters(self) -> Dict[str, Any]:
        """Tool: List characters with memory files"""
        try:
            characters = set()
            for file_path in self.memory_dir.glob("*_*.md"):
                if file_path.is_file() and file_path.stat().st_size > 0:
                    filename = file_path.stem
                    if "_" in filename:
                        character_name = filename.rsplit("_", 1)[0]
                        characters.add(character_name)
            
            return {
                "success": True,
                "characters": sorted(list(characters)),
                "total_characters": len(characters)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_character_memory(self, characters: List[str]) -> Dict[str, Any]:
        """Tool: Clear memory files for characters"""
        try:
            cleared_results = {}
            
            for character in characters:
                try:
                    cleared_files = []
                    for memory_type in ["profile", "event"]:
                        file_path = self._get_memory_file_path(character, memory_type)
                        if file_path.exists():
                            file_path.unlink()
                            cleared_files.append(f"{memory_type}.md")
                    
                    cleared_results[character] = {
                        "success": True,
                        "cleared_files": cleared_files
                    }
                except Exception as char_error:
                    cleared_results[character] = {
                        "success": False,
                        "error": str(char_error)
                    }
            
            return {
                "success": True,
                "characters_processed": len(characters),
                "clear_results": cleared_results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
        Execute recursive function calling agent
        
        Args:
            user_message: User's request or question
            max_iterations: Maximum number of function calling iterations
            
        Returns:
            Dict with execution results
        """
        try:
            # Get available tools for function calling
            tools = self.get_available_tools()
            
            # Initialize conversation
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
                        print(f"LLM provided final response after {iteration-1} tool calls: {final_response}")
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
    
    # Helper methods for memory analysis (simplified versions)
    
    def _analyze_session_for_events(self, character_name: str, conversation: str, session_date: str, existing_events: str) -> str:
        """Analyze session for events (using function calling)"""
        try:
            result = self.analyze_session_for_events(character_name, conversation, session_date, existing_events)
            if result["success"]:
                return result["new_events"]
            else:
                logger.error(f"Failed to analyze events for {character_name}: {result.get('error', 'Unknown error')}")
                return ""
        except Exception as e:
            logger.error(f"Failed to analyze events for {character_name}: {e}")
            return ""
    
    def _analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str, events: str) -> str:
        """Analyze session for profile updates (using function calling)"""
        try:
            result = self.analyze_session_for_profile(character_name, conversation, existing_profile, events)
            if result["success"]:
                return result["updated_profile"]
            else:
                logger.error(f"Failed to analyze profile for {character_name}: {result.get('error', 'Unknown error')}")
                return existing_profile
        except Exception as e:
            logger.error(f"Failed to analyze profile for {character_name}: {e}")
            return existing_profile 