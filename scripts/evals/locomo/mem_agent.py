"""
MemAgent - Memory Management Agent

This implementation provides memory management capabilities through function tools
that can be used by AI agents to maintain and store character memories.

Focuses on memory storage and management operations:
- Memory Storage: update character memories from conversation sessions
- Memory Management: clear memory data when needed
- Memory Analysis: analyze conversations to extract events and profile updates

Note: For memory retrieval and question answering, use ResponseAgent instead.
"""

import json
import os
import sys
import threading
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import re
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from difflib import SequenceMatcher
from collections import defaultdict

import dotenv
dotenv.load_dotenv()

from memu.llm import AzureOpenAIClient
from memu.utils import get_logger, setup_logging
from memu.memory.embeddings import get_default_embedding_client
from llm_factory import create_llm_client

# Add prompts directory to path and import prompt loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prompts'))
from prompt_loader import get_prompt_loader

logger = setup_logging(__name__, enable_flush=True)


class MemAgent:
    """
    Memory Management Agent
    
    Provides memory management capabilities through callable functions:
    
    Memory Management:
    - update_character_memory: Update memory files from conversation session data
    - clear_character_memory: Clear memory files for characters
    
    Internal Memory Processing:
    - analyze_session_for_events: Extract events from conversations
    - analyze_session_for_profile: Update profile from conversations
    
    Agent Execution:
    - execute: Process user messages with function calling for memory management tasks
    
    Note: For memory retrieval and question answering, use ResponseAgent instead.
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
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
        
        # Initialize thread lock for file operations
        self._file_lock = threading.Lock()
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        # Initialize LLM client
        self.llm_client = self._init_llm_client()
        
        # Initialize embedding client for semantic search
        self.embedding_client = self._init_embedding_client()
        
        logger.info(f"MemAgent initialized with memory directory: {self.memory_dir}")
        if self.embedding_client:
            logger.info("Embedding client initialized for semantic search")
        else:
            logger.warning("No embedding client available - semantic search will be skipped")

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

    def _init_llm_client(self):
        """Initialize the LLM client"""
        try:
            return create_llm_client(
                chat_deployment=self.chat_deployment,
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                use_entra_id=self.use_entra_id,
                api_version=self.api_version
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def _init_embedding_client(self):
        """Initialize the embedding client for semantic search"""
        try:
            # Try to get default embedding client (checks environment variables)
            embedding_client = get_default_embedding_client()
            if embedding_client:
                return embedding_client
            else:
                logger.warning("No embedding client configuration found - semantic search will be unavailable")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize embedding client: {e} - semantic search will be unavailable")
            return None

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available memory management tools"""
        return [
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
        """Write content to a character's memory file (thread-safe)"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        with self._file_lock:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')

    def _append_memory_file(self, character_name: str, memory_type: str, content: str):
        """Append content to a character's memory file (thread-safe)"""
        file_path = self._get_memory_file_path(character_name, memory_type)
        with self._file_lock:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'a', encoding='utf-8') as f:
                # Add newlines for proper separation if file isn't empty
                if file_path.exists() and file_path.stat().st_size > 0:
                    f.write('\n\n')
                f.write(content)

    def _search_with_bm25(self, query: str, all_events: List[str], character_event_map: Dict[int, str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search events using BM25 ranking"""
        try:
            # Tokenize for BM25
            tokenized_events = [event.lower().split() for event in all_events]
            tokenized_query = query.lower().split()
            
            # Initialize BM25
            bm25 = BM25Okapi(tokenized_events)
            
            # Get BM25 scores
            bm25_scores = bm25.get_scores(tokenized_query)
            
            # Get top results with scores and character info
            event_scores = [(i, float(score)) for i, score in enumerate(bm25_scores)]
            event_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for i, (event_idx, score) in enumerate(event_scores[:top_k]):
                results.append({
                    "rank": i + 1,
                    "character": character_event_map[event_idx],
                    "event": all_events[event_idx],
                    "score": float(score),
                    "method": "bm25",
                    "relevance": "high" if score > 1.0 else "medium" if score > 0.5 else "low"
                })
            
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def _search_with_string_matching(self, query: str, all_events: List[str], character_event_map: Dict[int, str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search events using string similarity and substring matching"""
        try:
            query_lower = query.lower()
            event_scores = []
            
            for i, event in enumerate(all_events):
                event_lower = event.lower()
                
                # Calculate similarity score using multiple methods
                similarity_scores = []
                
                # 1. Exact substring match (highest weight)
                if query_lower in event_lower:
                    substring_score = len(query_lower) / len(event_lower)
                    similarity_scores.append(substring_score * 2.0)  # Double weight for exact matches
                
                # 2. Sequence matcher similarity
                seq_similarity = SequenceMatcher(None, query_lower, event_lower).ratio()
                similarity_scores.append(seq_similarity)
                
                # 3. Word overlap score
                query_words = set(query_lower.split())
                event_words = set(event_lower.split())
                if query_words and event_words:
                    overlap_score = len(query_words.intersection(event_words)) / len(query_words.union(event_words))
                    similarity_scores.append(overlap_score)
                
                # 4. Individual word substring matches
                word_match_score = 0
                for word in query_words:
                    if len(word) > 2:  # Only consider words longer than 2 characters
                        for event_word in event_words:
                            if word in event_word or event_word in word:
                                word_match_score += 1
                if query_words:
                    word_match_score = word_match_score / len(query_words)
                similarity_scores.append(word_match_score)
                
                # Final score is the maximum of all similarity methods
                final_score = max(similarity_scores) if similarity_scores else 0.0
                
                event_scores.append((i, final_score))
            
            # Sort by score
            event_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for i, (event_idx, score) in enumerate(event_scores[:top_k]):
                if score > 0:  # Only include events with some similarity
                    results.append({
                        "rank": i + 1,
                        "character": character_event_map[event_idx],
                        "event": all_events[event_idx],
                        "score": float(score),
                        "method": "string_match",
                        "relevance": "high" if score > 0.7 else "medium" if score > 0.4 else "low"
                    })
            
            return results
        except Exception as e:
            logger.error(f"String matching search failed: {e}")
            return []

    def _search_with_embeddings(self, query: str, all_events: List[str], character_event_map: Dict[int, str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search events using embedding-based semantic similarity"""
        try:
            if not self.embedding_client:
                logger.warning("No embedding client available for semantic search")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_client.embed(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Generate embeddings for all events
            event_embeddings = []
            for event in all_events:
                try:
                    event_embedding = self.embedding_client.embed(event)
                    if event_embedding:
                        event_embeddings.append(event_embedding)
                    else:
                        event_embeddings.append([0.0] * len(query_embedding))  # Zero vector fallback
                except Exception as e:
                    logger.warning(f"Failed to embed event: {e}")
                    event_embeddings.append([0.0] * len(query_embedding))  # Zero vector fallback
            
            # Calculate cosine similarities
            query_vector = np.array(query_embedding)
            similarities = []
            
            for i, event_embedding in enumerate(event_embeddings):
                try:
                    event_vector = np.array(event_embedding)
                    
                    # Calculate cosine similarity
                    query_norm = np.linalg.norm(query_vector)
                    event_norm = np.linalg.norm(event_vector)
                    
                    if query_norm > 0 and event_norm > 0:
                        similarity = np.dot(query_vector, event_vector) / (query_norm * event_norm)
                        similarities.append((i, float(similarity)))
                    else:
                        similarities.append((i, 0.0))
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity for event {i}: {e}")
                    similarities.append((i, 0.0))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for i, (event_idx, similarity) in enumerate(similarities[:top_k]):
                if similarity > 0.1:  # Only include events with reasonable similarity
                    results.append({
                        "rank": i + 1,
                        "character": character_event_map[event_idx],
                        "event": all_events[event_idx],
                        "score": float(similarity),
                        "method": "embedding",
                        "relevance": "high" if similarity > 0.8 else "medium" if similarity > 0.6 else "low"
                    })
            
            return results
        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []

    def _combine_search_results(self, result_lists: List[List[Dict[str, Any]]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Combine and deduplicate results from multiple search methods"""
        try:
            # Use event text as key for deduplication
            seen_events = set()
            combined_results = []
            
            # Create a scoring system that considers both score and method diversity
            event_aggregated_scores = defaultdict(list)
            event_info = {}
            
            # Collect all results and aggregate scores by event
            for method_results in result_lists:
                for result in method_results:
                    event_text = result["event"]
                    event_key = (event_text, result["character"])
                    
                    # Store event info (use the first occurrence)
                    if event_key not in event_info:
                        event_info[event_key] = {
                            "character": result["character"],
                            "event": result["event"]
                        }
                    
                    # Aggregate scores by method
                    method = result["method"]
                    score = result["score"]
                    event_aggregated_scores[event_key].append({
                        "method": method,
                        "score": score,
                        "rank": result["rank"]
                    })
            
            # Calculate final scores for each unique event
            final_scores = []
            for event_key, method_scores in event_aggregated_scores.items():
                # Calculate weighted average score
                total_score = 0
                method_count = len(method_scores)
                
                # Bonus for appearing in multiple methods
                diversity_bonus = 0.1 * (method_count - 1)  # Bonus for each additional method
                
                for method_score in method_scores:
                    # Weight different methods slightly differently
                    method_weight = {
                        "bm25": 1.0,
                        "string_match": 1.1,  # Slightly prefer exact matches
                        "embedding": 1.2       # Slightly prefer semantic matches
                    }.get(method_score["method"], 1.0)
                    
                    total_score += method_score["score"] * method_weight
                
                # Final score is average + diversity bonus
                final_score = (total_score / method_count) + diversity_bonus
                
                final_scores.append((event_key, final_score, method_scores))
            
            # Sort by final score
            final_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Format final results
            for i, (event_key, final_score, method_scores) in enumerate(final_scores[:top_k]):
                methods_used = [ms["method"] for ms in method_scores]
                avg_score = sum(ms["score"] for ms in method_scores) / len(method_scores)
                
                combined_results.append({
                    "rank": i + 1,
                    "character": event_info[event_key]["character"],
                    "event": event_info[event_key]["event"],
                    "score": float(final_score),
                    "avg_score": float(avg_score),
                    "methods": methods_used,
                    "method_count": len(methods_used),
                    "method": "combined",
                    "relevance": "high" if final_score > 1.0 else "medium" if final_score > 0.6 else "low"
                })
            
            return combined_results
        except Exception as e:
            logger.error(f"Failed to combine search results: {e}")
            # Fallback: just return first method's results
            for result_list in result_lists:
                if result_list:
                    return result_list[:top_k]
            return []

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
        """Search for events relevant to a query across specified characters using BM25, string matching, and embedding search"""
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
                    "bm25_results": [],
                    "string_match_results": [],
                    "embedding_results": [],
                    "combined_results": [],
                    "total_events_searched": 0,
                    "characters_searched": characters
                }
            
            # Method 1: BM25 Search (10 results)
            bm25_results = self._search_with_bm25(query, all_events, character_event_map, 10)
            
            # Method 2: String Matching Search (10 results) 
            string_results = self._search_with_string_matching(query, all_events, character_event_map, 10)
            
            # Method 3: Embedding Search (10 results)
            embedding_results = self._search_with_embeddings(query, all_events, character_event_map, 10)
            
            # Combine and deduplicate results
            combined_results = self._combine_search_results([bm25_results, string_results, embedding_results], top_k)
            
            return {
                "success": True,
                "query": query,
                "bm25_results": bm25_results,
                "string_match_results": string_results,
                "embedding_results": embedding_results,
                "combined_results": combined_results,
                "relevant_events": combined_results,  # For backward compatibility
                "total_events_searched": len(all_events),
                "characters_searched": characters
            }
            
        except Exception as e:
            logger.error(f"Failed to search events for query '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "bm25_results": [],
                "string_match_results": [],
                "embedding_results": [],
                "combined_results": [],
                "relevant_events": [],
                "total_events_searched": 0,
                "characters_searched": characters
            }

    def _check_events_completeness(self, character_name: str, conversation: str, extracted_events: str) -> Dict[str, Any]:
        """Check if extracted events are sufficient and complete"""
        try:
            sufficiency_prompt = f"""You are inspecting whether the events about a speaker as they mentioned in the conversation are summarized into the extracted events with no omission.

Speaker: {character_name}

Conversation:
{conversation}

Extracted events:
{extracted_events}

Please compare the conversation and the extracted events, and determine whether all the events about the speaker included in the extracted events without omission.

Consider about:
1. Are all events involving {character_name}, no matter how minor, captured?
2. Are any important details (who, what, when, where, why, how) missing?
3. Are the events about people who are close to {character_name}, such as their family, also captured?

Respond with a JSON object containing:
- "sufficient": true/false - whether the information is sufficient
- "missing_info": string - what specific information is missing (if any). You can copy the original conversation texts if they are missing in the extracted events.
- "confidence": number between 0-1 - confidence in the completeness assessment

JSON Response:"""

            print('>'*100)
            print(sufficiency_prompt)
            print('<'*100)
            
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": sufficiency_prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            
            if response.success:
                try:
                    # Try to extract JSON from response
                    content = response.content.strip()
                    if content.startswith("```json"):
                        content = content.replace("```json", "").replace("```", "").strip()
                    elif content.startswith("```"):
                        content = content.replace("```", "").strip()
                    
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError:
                    # Fallback: try to extract basic assessment
                    content_lower = response.content.lower()
                    if "sufficient" in content_lower and "true" in content_lower:
                        return {"sufficient": True, "missing_info": "", "confidence": 0.7}
                    else:
                        return {"sufficient": False, "missing_info": "Could not determine missing information", "confidence": 0.5}
            else:
                logger.warning(f"Events completeness check failed: {response.error}")
                return {"sufficient": True, "missing_info": "", "confidence": 0.5}

        except Exception as e:
            logger.error(f"Failed to check events completeness: {e}")
            return {"sufficient": True, "missing_info": "", "confidence": 0.5}

    def _refine_events_analysis(self, character_name: str, conversation: str, previous_extraction: str, missing_info: str, session_date: str) -> Dict[str, Any]:
        """Refine the events analysis based on what was missing"""
        try:
            refinement_prompt = self.prompt_loader.format_prompt(
                "refine_events_extraction",
                character_name=character_name,
                conversation=conversation,
                session_date=session_date,
                previous_extraction=previous_extraction,
                missing_info=missing_info
            )
            
            messages = [{"role": "user", "content": refinement_prompt}]
            llm_response = self.llm_client.chat_completion(messages, max_tokens=4000, temperature=0.3)
            
            if not llm_response.success:
                return {
                    "success": False,
                    "error": f"LLM refinement failed: {llm_response.error}",
                    "refined_events": previous_extraction
                }
            
            return {
                "success": True,
                "refined_events": llm_response.content.strip(),
                "method": "refined_analysis"
            }            
            
        except Exception as e:
            logger.error(f"Failed to refine events analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "refined_events": previous_extraction
            }

    def update_character_memory(self, session_data: List[Dict], session_date: str, characters: List[str], max_iterations: int = 3) -> Dict[str, Any]:
        """Update character memory files from conversation session data with iterative self-checking"""
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
                    
                    # Iterative event extraction with self-checking
                    current_events = ""
                    iteration_log = []
                    
                    for iteration in range(max_iterations):
                        logger.info(f"Character {character_name} - Iteration {iteration + 1}/{max_iterations}: Extracting events")
                        
                        # Analyze session for new events
                        if iteration == 0:
                            # First iteration: standard analysis
                            events_result = self.analyze_session_for_events(
                                # character_name, conversation, session_date, existing_events
                                character_name, conversation, session_date, "None"
                            )
                        else:
                            # Subsequent iterations: refined analysis based on missing info
                            missing_info = iteration_log[-1].get("missing_info", "")
                            previous_extraction = iteration_log[-1].get("events", "")
                            refinement_result = self._refine_events_analysis(
                                character_name, conversation, previous_extraction, missing_info, session_date
                            )
                            
                            events_result = {
                                "success": refinement_result["success"],
                                "new_events": refinement_result.get("refined_events", ""),
                                "error": refinement_result.get("error", "")
                            }
                        
                        if not events_result["success"]:
                            logger.warning(f"Events analysis failed for {character_name} at iteration {iteration + 1}: {events_result.get('error')}")
                            iteration_log.append({
                                "iteration": iteration + 1,
                                "success": False,
                                "error": events_result.get("error"),
                                "score": 0.0
                            })
                            continue
                        
                        current_events = events_result["new_events"]
                        
                        # Check sufficiency of extracted events
                        completeness_result = self._check_events_completeness(character_name, conversation, current_events)
                        print("*"*100)
                        print(repr(completeness_result))
                        print("*"*100)
                        
                        if completeness_result.get("sufficient", False):
                            logger.info(f"Character {character_name} - Sufficient events captured after {iteration + 1} iterations")
                            break
                        
                        iteration_log.append({
                            "iteration": iteration + 1,
                            "success": True,
                            "events": current_events,
                            "score": completeness_result.get("confidence", 0.0),
                            "sufficient": completeness_result.get("sufficient", False),
                            "missing_info": completeness_result.get("missing_info", ""),
                        })
                        
                        logger.info(f"Character {character_name} - Iteration {iteration + 1}: Sufficient: {completeness_result.get('sufficient', False)}")
                        
                        # If sufficient, we can stop early
                        if completeness_result.get("sufficient", False):
                            logger.info(f"Character {character_name} - Sufficient events found after {iteration + 1} iterations")
                            break
                        
                        # If this is the last iteration, log that we reached max iterations
                        if iteration == max_iterations - 1:
                            logger.info(f"Character {character_name} - Reached maximum iterations ({max_iterations})")
                    
                    new_events = current_events
                    # Use the best events found across all iterations
                    if new_events.strip():
                        print('>'*100)
                        print(new_events)
                        print('<'*100)
                        
                        # Update events file
                        if existing_events.strip():
                            # updated_events = existing_events + "\n\n" + new_events
                            # self._write_memory_file(character_name, "events", updated_events)
                            self._append_memory_file(character_name, "events", new_events)
                        else:
                            self._append_memory_file(character_name, "events", new_events)
                        
                        # Analyze session for profile updates
                        profile_result = self.analyze_session_for_profile(
                            character_name, conversation, existing_profile, new_events
                        )
                        
                        profile_updated = False
                        if profile_result["success"]:
                            updated_profile = profile_result["updated_profile"]
                            if updated_profile.strip():
                                self._write_memory_file(character_name, "profile", updated_profile)
                                profile_updated = True
                        
                        update_results[character_name] = {
                            "success": True,
                            "events_updated": True,
                            "profile_updated": profile_updated,
                            "iterations": len([log for log in iteration_log if log["success"]]),
                            "iteration_log": iteration_log
                        }
                    else:
                        update_results[character_name] = {
                            "success": False,
                            "error": "No events extracted after all iterations",
                            "events_updated": False,
                            "profile_updated": False,
                            "iterations": len([log for log in iteration_log if log["success"]]),
                            "iteration_log": iteration_log
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to update memory for {character_name}: {e}")
                    update_results[character_name] = {
                        "success": False,
                        "error": str(e),
                        "events_updated": False,
                        "profile_updated": False,
                        "iterations": 0,
                        "iteration_log": []
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
                    
                    with self._file_lock:
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
        
        print('>'*100)
        print(events_prompt)
        print('<'*100)

        messages = [{"role": "user", "content": events_prompt}]
        llm_response = self.llm_client.chat_completion(messages, max_tokens=4000, temperature=0.3)
        
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
        llm_response = self.llm_client.chat_completion(messages, max_tokens=4000, temperature=0.3)
        
        if not llm_response.success:
            raise Exception(f"LLM profile analysis failed: {llm_response.error}")
            
        return llm_response.content.strip()

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific memory management tool by name"""
        tool_methods = {
            "update_character_memory": self.update_character_memory,
            "analyze_session_for_events": self.analyze_session_for_events,
            "analyze_session_for_profile": self.analyze_session_for_profile,
            "clear_character_memory": self.clear_character_memory
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
            
            # Load the memory system message
            try:
                system_message = self.prompt_loader.get_prompt("memory_system_prompt")
            except:
                # Fallback if memory_system_prompt doesn't exist
                system_message = "You are a memory management assistant. Use the available tools to update and manage character memory data."
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                
                # Get response from LLM with tools
                llm_response = self.llm_client.chat_completion(
                    messages=messages,
                    tools=tools,
                    max_tokens=4000,
                    temperature=0.1
                )

                # Check if LLM response was successful
                if not llm_response.success:
                    raise Exception(f"LLM call failed: {llm_response.error}")
                
                # Convert LLMResponse to dict format expected by the rest of the code
                response = {
                    "content": llm_response.content or "",
                    "tool_calls": llm_response.tool_calls if llm_response.tool_calls else None
                }
                
                # Add assistant message
                assistant_message = {
                    "role": "assistant", 
                    "content": response.get("content", "")
                }
                
                # Only add tool_calls if they exist and are not empty
                if response.get("tool_calls"):
                    assistant_message["tool_calls"] = response["tool_calls"]
                
                messages.append(assistant_message)
                
                # Process tool calls if any
                if response.get("tool_calls"):
                    tool_calls_count = len(response['tool_calls'])
                    logger.info(f"Processing {tool_calls_count} tool calls")
                    
                    tools_processed = 0
                    for i, tool_call in enumerate(response["tool_calls"]):
                        tool_call_id = None
                        try:
                            # Handle different possible tool call formats
                            if hasattr(tool_call, 'function'):
                                # OpenAI API format
                                tool_name = tool_call.function.name
                                arguments = self._safe_json_parse(tool_call.function.arguments)
                                tool_call_id = tool_call.id
                            elif isinstance(tool_call, dict):
                                # Dict format
                                tool_name = tool_call["function"]["name"]
                                arguments = self._safe_json_parse(tool_call["function"]["arguments"])
                                tool_call_id = tool_call["id"]
                            else:
                                logger.error(f"Unknown tool call format: {type(tool_call)}")
                                # Even for unknown format, try to extract tool_call_id to respond
                                if hasattr(tool_call, 'id'):
                                    tool_call_id = tool_call.id
                                elif isinstance(tool_call, dict) and 'id' in tool_call:
                                    tool_call_id = tool_call['id']
                                
                                if tool_call_id:
                                    # Add error response for unknown format
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": json.dumps({
                                            "success": False,
                                            "error": f"Unknown tool call format: {type(tool_call)}"
                                        }, indent=2)
                                    })
                                    tools_processed += 1
                                continue
                            
                            # Check if arguments parsing was successful
                            if not arguments:
                                logger.warning(f"Failed to parse arguments for tool {tool_name}, using empty arguments")
                                arguments = {}
                            
                            # Execute tool
                            result = self.execute_tool(tool_name, **arguments)
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(result, indent=2)
                            })
                            tools_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing tool call: {e}")
                            
                            # Always add a response for the tool call, even if it failed
                            if tool_call_id:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": json.dumps({
                                        "success": False,
                                        "error": f"Tool execution failed: {str(e)}"
                                    }, indent=2)
                                })
                                tools_processed += 1
                            else:
                                # Try to extract tool_call_id even from exception case
                                try:
                                    if hasattr(tool_call, 'id'):
                                        emergency_id = getattr(tool_call, 'id', f"unknown_tool_call_{len(messages)}")
                                    elif isinstance(tool_call, dict) and 'id' in tool_call:
                                        emergency_id = tool_call['id']
                                    else:
                                        emergency_id = f"unknown_tool_call_{len(messages)}"
                                    
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": emergency_id,
                                        "content": json.dumps({
                                            "success": False,
                                            "error": f"Tool execution failed: {str(e)}"
                                        }, indent=2)
                                    })
                                    tools_processed += 1
                                except:
                                    logger.error(f"Could not add tool response for failed tool call: {e}")
                    
                    # Log tool processing summary
                    logger.info(f"Processed {tools_processed}/{tool_calls_count} tool calls successfully")
                    
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