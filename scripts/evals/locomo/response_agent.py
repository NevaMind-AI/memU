"""
ResponseAgent - Specialized Agent for Question Answering

This agent provides comprehensive question answering capabilities by:
1. Retrieving relevant character profiles and events
2. Synthesizing information from multiple sources
3. Generating comprehensive, contextual answers
4. Supporting multi-character queries and cross-reference analysis
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
from pathlib import Path
import math
from collections import Counter, defaultdict
import difflib
import numpy as np
import threading

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


class ResponseAgent:
    """
    Specialized response agent for question answering using memory data.
    
    Provides tools for:
    - Answering questions about characters and their situations
    - Retrieving and synthesizing information from profiles and events
    - Cross-referencing multiple characters and data sources
    - Generating comprehensive, contextual responses
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
        """Initialize ResponseAgent with LLM configuration and memory directory"""
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.chat_deployment = chat_deployment
        self.use_entra_id = use_entra_id
        self.api_version = api_version
        self.memory_dir = Path(memory_dir)
        
        # Ensure memory directory exists
        self.memory_dir.mkdir(exist_ok=True)
        
        # Initialize thread lock for file operations and cache access
        self._file_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        # Initialize LLM client
        self.llm_client = self._init_llm_client()
        
        # Initialize embedding client for semantic search
        self.embedding_client = self._init_embedding_client()
        
        # Initialize embedding cache for events to prevent repeated API calls
        self.event_embedding_cache = {}
        
        if self.embedding_client:
            logger.info("Embedding client initialized for semantic search")
        else:
            logger.warning("No embedding client available - semantic search will use fallback method")
        
        logger.info(f"ResponseAgent initialized with memory directory: {self.memory_dir}")

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
        except Exception as e:
            logger.warning(f"Failed to initialize embedding client: {e} - semantic search will use fallback method")
        
        logger.warning("No embedding client configuration found - semantic search will use fallback method")
        return None

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available response tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "answer_question",
                    "description": "Answer a question using iterative retrieval - automatically determines if retrieved content is sufficient and performs additional searches if needed",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question to answer"
                            },
                            "characters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of character names to search for information. If not specified, will search all available characters."
                            },
                            "max_iterations": {
                                "type": "integer",
                                "description": "Maximum number of retrieval iterations (default: 3)",
                                "default": 3
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_character_profile",
                    "description": "Retrieve the complete profile information for a specific character",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to get profile for"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_character_events",
                    "description": "Search for events related to specific characters using keywords",
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
                    "name": "list_characters",
                    "description": "List all characters that have memory data available",
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
        try:
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            else:
                return f"No {memory_type} file found for {character_name}"
        except Exception as e:
            logger.error(f"Error reading {memory_type} file for {character_name}: {e}")
            return f"Error reading {memory_type} file for {character_name}: {str(e)}"

    def _get_available_characters(self) -> List[str]:
        """Get list of characters with available memory files"""
        characters = set()
        try:
            for file_path in self.memory_dir.glob("*_profile.txt"):
                character_name = file_path.stem.replace("_profile", "")
                characters.add(character_name)
            return sorted(list(characters))
        except Exception as e:
            logger.error(f"Error getting available characters: {e}")
            return []

    def clear_embedding_cache(self):
        """Clear the event embedding cache"""
        with self._cache_lock:
            cache_size = len(self.event_embedding_cache)
            self.event_embedding_cache.clear()
        logger.info(f"Cleared event embedding cache (removed {cache_size} entries)")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the embedding cache"""
        with self._cache_lock:
            cache_size = len(self.event_embedding_cache)
        return {
            "cache_size": cache_size,
            "cached_events": cache_size
        }


    def _multi_modal_search(self, original_query: str, processed_query: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform multi-modal search combining semantic search, BM25, and string matching
        """
        if not events:
            return []
        
        results = []
        
        # Calculate scores using different methods with appropriate queries
        string_scores = self._string_match_search(processed_query, events)
        bm25_scores = self._bm25_search(processed_query, events)
        semantic_scores = self._semantic_search(original_query, events)  # Use original query for semantic search
        
        # Combine scores for each event
        for i, event in enumerate(events):
            # Get individual scores
            string_score = string_scores.get(event["id"], 0.0)
            bm25_score = bm25_scores.get(event["id"], 0.0)
            semantic_score = semantic_scores.get(event["id"], 0.0)
            
            # Weighted combination of scores - prioritizing semantic search
            combined_score = (
                0.3 * string_score +    # String matching - disabled when semantic is primary
                0.3 * bm25_score +      # BM25 - disabled when semantic is primary  
                1.0 * semantic_score    # Semantic - primary scoring method using embeddings
            )
            
            # Only include events with non-zero scores
            if combined_score > 0:
                result = {
                    **event,
                    "string_score": string_score,
                    "bm25_score": bm25_score,
                    "semantic_score": semantic_score,
                    "combined_score": combined_score,
                    "score": combined_score  # For backward compatibility
                }
                results.append(result)
        
        return results

    def _string_match_search(self, query: str, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """String-based matching with multiple techniques"""
        scores = {}
        query_words = set(query.split())
        
        for event in events:
            event_text = event["text"].lower()
            event_words = set(event_text.split())
            
            # 1. Exact word overlap
            overlap = len(query_words.intersection(event_words))
            overlap_score = overlap / len(query_words) if query_words else 0
            
            # 2. Substring matching
            substring_score = 0
            for query_word in query_words:
                if query_word in event_text:
                    substring_score += 1
            substring_score = substring_score / len(query_words) if query_words else 0
            
            # 3. Fuzzy string matching using difflib
            fuzzy_score = difflib.SequenceMatcher(None, query, event_text).ratio()
            
            # 4. Partial ratio for better fuzzy matching
            partial_scores = []
            for query_word in query_words:
                best_partial = 0
                for event_word in event_words:
                    partial = difflib.SequenceMatcher(None, query_word, event_word).ratio()
                    best_partial = max(best_partial, partial)
                partial_scores.append(best_partial)
            partial_score = sum(partial_scores) / len(partial_scores) if partial_scores else 0
            
            # Combine string matching scores
            final_score = (
                0.4 * overlap_score +      # Exact word matches
                0.3 * substring_score +    # Substring matches
                0.2 * fuzzy_score +        # Overall fuzzy similarity
                0.1 * partial_score        # Best partial word matches
            )
            
            scores[event["id"]] = final_score
        
        return scores

    def _bm25_search(self, query: str, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """BM25 scoring algorithm for information retrieval"""
        if not events:
            return {}
        
        # BM25 parameters
        k1 = 1.2  # Controls term frequency impact
        b = 0.75  # Controls document length normalization
        
        # Prepare documents and calculate statistics
        documents = [event["text"].lower() for event in events]
        doc_tokens = [doc.split() for doc in documents]
        
        # Calculate document frequencies
        doc_freqs = defaultdict(int)
        total_docs = len(documents)
        doc_lengths = [len(tokens) for tokens in doc_tokens]
        avg_doc_length = sum(doc_lengths) / total_docs if total_docs > 0 else 0
        
        # Count document frequency for each term
        for tokens in doc_tokens:
            unique_terms = set(tokens)
            for term in unique_terms:
                doc_freqs[term] += 1
        
        # Calculate BM25 scores
        query_terms = query.split()
        scores = {}
        
        for i, (event, tokens) in enumerate(zip(events, doc_tokens)):
            score = 0.0
            term_freqs = Counter(tokens)
            doc_length = doc_lengths[i]
            
            for term in query_terms:
                if term in term_freqs:
                    # Term frequency in document
                    tf = term_freqs[term]
                    
                    # Document frequency
                    df = doc_freqs[term]
                    
                    # Inverse document frequency
                    idf = math.log((total_docs - df + 0.5) / (df + 0.5)) if df > 0 else 0
                    
                    # BM25 score component
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
                    
                    score += idf * (numerator / denominator)
            
            # Normalize score by query length
            normalized_score = score / len(query_terms) if query_terms else 0
            scores[event["id"]] = max(0, normalized_score)  # Ensure non-negative
        
        # Normalize scores to 0-1 range
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}
        
        return scores

    def _semantic_search(self, query: str, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Embedding-based semantic similarity using the original query (not processed keywords)"""
        scores = {}
        
        try:
            if not self.embedding_client:
                logger.warning("No embedding client available, using fallback semantic search")
                return self._fallback_semantic_search(query, events)
            
            # Generate query embedding using original query (not keywords)
            query_embedding = self.embedding_client.embed(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding, using fallback")
                return self._fallback_semantic_search(query, events)
            
            # Generate embeddings for all events (with caching)
            event_embeddings = {}
            cache_hits = 0
            cache_misses = 0
            
            for event in events:
                try:
                    event_text = event["text"]
                    
                    # Thread-safe cache access
                    with self._cache_lock:
                        # Check cache first
                        if event_text in self.event_embedding_cache:
                            event_embeddings[event["id"]] = self.event_embedding_cache[event_text]
                            cache_hits += 1
                            continue
                    
                    # Generate new embedding (outside lock to avoid blocking other threads)
                    event_embedding = self.embedding_client.embed(event_text)
                    if event_embedding:
                        event_embeddings[event["id"]] = event_embedding
                        # Cache the embedding for future use (thread-safe)
                        with self._cache_lock:
                            # Double-check pattern: another thread might have added it while we were computing
                            if event_text not in self.event_embedding_cache:
                                self.event_embedding_cache[event_text] = event_embedding
                        cache_misses += 1
                    else:
                        event_embeddings[event["id"]] = [0.0] * len(query_embedding)  # Zero vector fallback
                        cache_misses += 1
                except Exception as e:
                    logger.warning(f"Failed to embed event {event['id']}: {e}")
                    event_embeddings[event["id"]] = [0.0] * len(query_embedding)  # Zero vector fallback
                    cache_misses += 1
            
            logger.debug(f"Event embedding cache: {cache_hits} hits, {cache_misses} misses, cache size: {len(self.event_embedding_cache)}")
            
            # Calculate cosine similarities
            query_vector = np.array(query_embedding)
            
            for event in events:
                try:
                    event_vector = np.array(event_embeddings[event["id"]])
                    
                    # Calculate cosine similarity
                    query_norm = np.linalg.norm(query_vector)
                    event_norm = np.linalg.norm(event_vector)
                    
                    if query_norm > 0 and event_norm > 0:
                        similarity = np.dot(query_vector, event_vector) / (query_norm * event_norm)
                        scores[event["id"]] = float(max(0, similarity))  # Ensure non-negative
                    else:
                        scores[event["id"]] = 0.0
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity for event {event['id']}: {e}")
                    scores[event["id"]] = 0.0
            
            return scores
            
        except Exception as e:
            logger.error(f"Embedding search failed: {e}, using fallback")
            return self._fallback_semantic_search(query, events)

    def _fallback_semantic_search(self, query: str, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Fallback semantic search when embedding client is not available"""
        scores = {}
        query_words = set(query.lower().split())
        
        for event in events:
            event_text = event["text"].lower()
            event_words = set(event_text.split())
            
            # Simple word overlap scoring
            if query_words:
                overlap = len(query_words.intersection(event_words))
                scores[event["id"]] = overlap / len(query_words)
            else:
                scores[event["id"]] = 0.0
        
        return scores

    def get_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Retrieve the complete profile information for a specific character"""
        try:
            profile_content = self._read_memory_file(character_name, "profile")
            
            if "No profile file found" in profile_content:
                return {
                    "success": False,
                    "error": f"No profile found for character '{character_name}'",
                    "profile": None
                }
            elif "Error reading" in profile_content:
                return {
                    "success": False,
                    "error": profile_content,
                    "profile": None
                }
            else:
                return {
                    "success": True,
                    "character": character_name,
                    "profile": profile_content
                }

        except Exception as e:
            logger.error(f"Error getting character profile: {e}")
            return {
                "success": False,
                "error": str(e),
                "profile": None
            }

    def search_character_events(self, query: str, characters: List[str], top_k: int = 10, processed_query: Optional[str] = None) -> Dict[str, Any]:
        """Search for events using multi-modal approach: semantic search, BM25, and string matching"""
        try:
            all_events = []
            
            # Read events for each character
            for character in characters:
                events_content = self._read_memory_file(character, "events")
                if "No events file found" not in events_content and "Error reading" not in events_content:
                    # Split events by lines and filter non-empty
                    character_events = [line.strip() for line in events_content.split('\n') if line.strip()]
                    for i, event in enumerate(character_events):
                        all_events.append({
                            "character": character,
                            "event": event,
                            "text": event,
                            "id": f"{character}_{i}"
                        })

            if not all_events:
                return {
                    "success": True,
                    "events": [],
                    "message": "No events found for the specified characters"
                }

            # If no processed query provided, create keywords for string/BM25 search
            if processed_query is None:
                # Simple keyword extraction - remove common stop words
                stop_words = {'what', 'where', 'when', 'who', 'why', 'how', 'is', 'are', 'was', 'were', 
                             'do', 'does', 'did', 'can', 'could', 'would', 'should', 'about', 'the', 
                             'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
                words = re.findall(r'\b\w+\b', query.lower())
                keywords = [word for word in words if word not in stop_words and len(word) > 2]
                processed_query = " ".join(keywords)

            # Multi-modal search and scoring
            search_results = self._multi_modal_search(query, processed_query, all_events)
            
            # Filter out zero-score results
            search_results = [r for r in search_results if r.get("combined_score", 0) > 0]
            
            # Sort by combined score and return top_k
            search_results.sort(key=lambda x: x["combined_score"], reverse=True)
            top_events = search_results[:top_k]

            # Add rank information
            for i, event in enumerate(top_events):
                event["rank"] = i + 1

            return {
                "success": True,
                "events": top_events,
                "total_found": len(search_results),
                "search_method": "multi_modal",
                "query_processed": processed_query,
                "characters_searched": characters
            }

        except Exception as e:
            logger.error(f"Error searching character events: {e}")
            return {
                "success": False,
                "error": str(e),
                "events": []
            }

    def list_characters(self) -> Dict[str, Any]:
        """List all characters that have memory data available"""
        try:
            characters = self._get_available_characters()
            
            # Get additional info for each character
            character_info = []
            for character in characters:
                profile_exists = self._get_memory_file_path(character, "profile").exists()
                events_exists = self._get_memory_file_path(character, "events").exists()
                
                character_info.append({
                    "name": character,
                    "has_profile": profile_exists,
                    "has_events": events_exists
                })

            return {
                "success": True,
                "characters": character_info,
                "total_count": len(characters)
            }

        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return {
                "success": False,
                "error": str(e),
                "characters": []
            }

    def answer_question(self, question: str, characters: Optional[List[str]] = None, 
                                max_iterations: int = 3) -> Dict[str, Any]:
        """
        Answer a question using iterative retrieval with automatic sufficiency checking.
        
        This method:
        1. Performs initial retrieval
        2. Checks if content is sufficient to answer the question
        3. If not, identifies missing information and generates new queries
        4. Repeats up to max_iterations times
        5. Deduplicates and combines all retrieved content
        6. Generates final answer
        """
        try:
            # Get available characters if not specified
            if not characters:
                characters = self._get_available_characters()
                if not characters:
                    return {
                        "success": False,
                        "error": "No character data available",
                        "answer": "I don't have any character information available to answer your question."
                    }

            all_retrieved_content = []
            all_events = []
            iteration_log = []
            
            # Start with the original question for initial search
            current_search_query = question
            
            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}: Searching with query '{current_search_query}'")
                
                # Search for relevant events using the current search query
                events_result = self.search_character_events(current_search_query, characters)
                current_events = []
                if events_result.get("success"):
                    current_events = events_result.get("events", [])
                    
                    # Add new events to all_events (will deduplicate later)
                    for event in current_events:
                        all_events.append(event)
                        all_retrieved_content.append(f"Event - {event.get('character', 'Unknown')}: {event.get('event', '')}")
                
                iteration_log.append({
                    "iteration": iteration + 1,
                    "query": current_search_query,
                    "events_found": len(current_events),
                    "is_original_question": iteration == 0
                })
                
                # Check if we have sufficient information to answer the question
                current_content = "\n".join(all_retrieved_content)
                sufficiency_result = self._check_content_sufficiency(question, current_content)
                
                if sufficiency_result.get("sufficient", False):
                    logger.info(f"Sufficient content found after {iteration + 1} iterations")
                    break
                
                # If not sufficient and not the last iteration, generate new query
                if iteration < max_iterations - 1:
                    missing_info = sufficiency_result.get("missing_info", "")
                    new_query_result = self._generate_new_query(question, missing_info, current_content)
                    
                    if new_query_result.get("success"):
                        current_search_query = new_query_result.get("new_query", current_search_query)
                        logger.info(f"Generated new query for iteration {iteration + 2}: '{current_search_query}'")
                        
                        iteration_log[-1]["missing_info"] = missing_info
                        iteration_log[-1]["new_query_generated"] = current_search_query
                    else:
                        logger.warning(f"Failed to generate new query: {new_query_result.get('error')}")
                        break
                else:
                    logger.info(f"Reached maximum iterations ({max_iterations})")
                    iteration_log[-1]["missing_info"] = sufficiency_result.get("missing_info", "")
            
            # Deduplicate content
            deduplicated_content = self._deduplicate_content(all_retrieved_content)
            deduplicated_events = self._deduplicate_events(all_events)
            
            # Generate final answer using all collected content
            final_context_data = {
                "question": question,
                "relevant_events": deduplicated_events,
                "all_content": deduplicated_content
            }

            answer = self._generate_answer(final_context_data)

            return {
                "success": True,
                "answer": answer,
                "iterations_performed": len(iteration_log),
                "iteration_log": iteration_log,
                "context_used": {
                    "characters_searched": characters,
                    "total_events_found": len(deduplicated_events),
                    "content_pieces": len(deduplicated_content)
                },
                "final_content": deduplicated_content,
                "retrieved_events": deduplicated_events  # Add detailed events for evaluation
            }

        except Exception as e:
            logger.error(f"Error in iterative answer question: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error while trying to answer your question: {str(e)}"
            }

    def _generate_answer(self, context_data: Dict[str, Any]) -> str:
        """Generate a comprehensive answer using the LLM with collected context"""
        try:
            # Prepare context for the LLM
            question = context_data["question"]
            events = context_data.get("relevant_events", [])
            all_content = context_data.get("all_content", [])
            
            # Build context string - only use events, not profiles
            context_parts = []
            
            if events:
                context_parts.append("RELEVANT EVENTS:")
                for i, event in enumerate(events, 1):
                    event_text = event.get('event', event.get('text', str(event)))
                    character = event.get('character', 'Unknown')
                    context_parts.append(f"\n{i}. {character}: {event_text}")
            
            # If we have additional content from iterative search
            if all_content and len(all_content) > len(events):
                context_parts.append("\nADDITIONAL CONTEXT:")
                for i, content in enumerate(all_content[len(events):], len(events) + 1):
                    context_parts.append(f"\n{i}. {content}")
            
            context_text = "\n".join(context_parts)
            
            # Create prompt for answer generation with reasoning
            prompt = f"""You are a knowledgeable assistant with access to character information and event records. 
Answer the following question comprehensively based on the provided context.

Question: {question}

Context:
{context_text}

Instructions:
1. First, use <thinking>...</thinking> tags to analyze the question and available information:
   - Break down what the question is asking
   - Identify relevant information from the context
   - Consider different perspectives or interpretations
   - Note any gaps or limitations in the available information
   - Plan your approach to answering
   - **IMPORTANT**: Look for multiple answers that may be scattered across different events
   - **IMPORTANT**: Think of the time carefully, the time of an event can be relative to when it is mentioned by the speaker, you need to find out the real time of the event

2. Then, provide your final answer using <result>...</result> tags:
   - Give a complete, accurate answer based on the available information
   - **IMPORTANT**: If there are multiple answers to the question found in different events, include ALL of them
   - Include specific details and examples from the context when relevant
   - If information is insufficient, clearly state what is missing
   - Be factual and avoid speculation beyond what the context supports
   - Reference specific characters and events when applicable
   - Synthesize information from multiple sources when available
   - Ensure completeness - don't miss any relevant answers from the provided events

Format:
<thinking>
[Your step-by-step reasoning process here]
</thinking>

<result>
[Your final comprehensive answer here, the result should be concise and to the query, no more than 20 words]
</result>"""

            # Get response from LLM
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000, 
                temperature=0.2
            )

            if response.success:
                raw_response = response.content.strip()
                
                # Extract the final answer from <result> tags
                # result_match = re.search(r'<result>(.*?)</result>', raw_response, re.DOTALL)
                result_match = re.search(r'<result>(.*?)(?:</result>|$)', raw_response, re.DOTALL)
                if result_match:
                    final_answer = result_match.group(1).strip()
                    
                    # Also extract thinking for potential logging/debugging
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_response, re.DOTALL)
                    if thinking_match:
                        thinking_content = thinking_match.group(1).strip()
                        logger.info(f"LLM Reasoning: {thinking_content[:200]}...")  # Log first 200 chars
                    
                    return final_answer
                else:
                    # Fallback: if no <result> tags found, return the full response
                    logger.warning("No <result> tags found in LLM response, returning full content")
                    return raw_response
            else:
                logger.error(f"LLM call failed: {response.error}")
                return f"I'm unable to generate a response at the moment due to a technical issue: {response.error}"

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"I encountered an error while generating the answer: {str(e)}"

    def _check_content_sufficiency(self, question: str, current_content: str) -> Dict[str, Any]:
        """Check if the current content is sufficient to answer the question"""
        try:
            if not current_content.strip():
                return {
                    "sufficient": False,
                    "missing_info": "No relevant information found",
                    "confidence": 0.0
                }

            prompt = f"""You are evaluating whether the provided information is sufficient to answer a question.

Question: {question}

Available Information:
{current_content}

Please evaluate if the available information is sufficient to provide a complete and accurate answer to the question.

Respond with a JSON object containing:
- "sufficient": true/false - whether the information is sufficient
- "missing_info": string - what specific information is missing (if any)
- "confidence": number between 0-1 - confidence in the sufficiency assessment

JSON Response:"""

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
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
                logger.error(f"LLM call failed for sufficiency check: {response.error}")
                return {"sufficient": False, "missing_info": "Unable to assess sufficiency", "confidence": 0.0}

        except Exception as e:
            logger.error(f"Error checking content sufficiency: {e}")
            return {"sufficient": False, "missing_info": f"Error in assessment: {str(e)}", "confidence": 0.0}

    def _generate_new_query(self, original_question: str, missing_info: str, current_content: str) -> Dict[str, Any]:
        """Generate a new search query based on missing information"""
        try:
            prompt = f"""You need to generate a new search query to find missing information.

Original Question: {original_question}
Missing Information: {missing_info}

Current Retrieved Content Summary:
{current_content[:500]}...

Based on the missing information, generate a new search query that would help find the specific information needed to answer the original question.

The query should be:
- Focused on the missing information
- Use specific keywords that would match relevant events or profile information
- Be concise but comprehensive

Respond with a JSON object containing:
- "new_query": string - the new search query
- "keywords": array of strings - key search terms
- "reasoning": string - why this query should find the missing information

JSON Response:"""

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.2
            )

            if response.success:
                try:
                    content = response.content.strip()
                    if content.startswith("```json"):
                        content = content.replace("```json", "").replace("```", "").strip()
                    elif content.startswith("```"):
                        content = content.replace("```", "").strip()
                    
                    result = json.loads(content)
                    return {
                        "success": True,
                        "new_query": result.get("new_query", ""),
                        "keywords": result.get("keywords", []),
                        "reasoning": result.get("reasoning", "")
                    }
                except json.JSONDecodeError:
                    # Fallback: generate simple query from missing info
                    stop_words = {'what', 'where', 'when', 'who', 'why', 'how', 'is', 'are', 'was', 'were', 
                                 'do', 'does', 'did', 'can', 'could', 'would', 'should', 'about', 'the', 
                                 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
                    words = re.findall(r'\b\w+\b', missing_info.lower())
                    fallback_keywords = [word for word in words if word not in stop_words and len(word) > 2]
                    return {
                        "success": True,
                        "new_query": " ".join(fallback_keywords),
                        "keywords": fallback_keywords,
                        "reasoning": "Fallback query generated from missing info keywords"
                    }
            else:
                logger.error(f"LLM call failed for new query generation: {response.error}")
                return {"success": False, "error": response.error}

        except Exception as e:
            logger.error(f"Error generating new query: {e}")
            return {"success": False, "error": str(e)}

    def _deduplicate_content(self, content_list: List[str]) -> List[str]:
        """Remove duplicate content while preserving order"""
        seen = set()
        deduplicated = []
        
        for content in content_list:
            # Use a simplified version for comparison (lowercase, stripped)
            content_key = content.lower().strip()
            if content_key not in seen and content_key:
                seen.add(content_key)
                deduplicated.append(content)
        
        return deduplicated

    def _deduplicate_events(self, events_list: List[Dict]) -> List[Dict]:
        """Remove duplicate events based on content"""
        seen_events = set()
        deduplicated = []
        
        for event in events_list:
            event_text = event.get("event", "").strip().lower()
            character = event.get("character", "")
            event_key = f"{character}:{event_text}"
            
            if event_key not in seen_events and event_text:
                seen_events.add(event_key)
                deduplicated.append(event)
        
        return deduplicated

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool by name"""
        try:
            if tool_name == "answer_question":
                return self.answer_question(**kwargs)
            elif tool_name == "get_character_profile":
                return self.get_character_profile(**kwargs)
            elif tool_name == "search_character_events":
                return self.search_character_events(**kwargs)
            elif tool_name == "list_characters":
                return self.list_characters(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def execute(self, user_message: str, max_iterations: int = 5) -> Dict[str, Any]:
        """Execute user message with function calling support"""
        try:
            tools = self.get_available_tools()
            
            # Load the response system message
            try:
                system_message = self.prompt_loader.get_prompt("response_system_message")
            except:
                # Fallback if response_system_message doesn't exist
                system_message = "You are a specialized question answering assistant. Use the available tools to answer user questions about character information."
            
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
                    max_tokens=2000,
                    temperature=0.1
                )

                # Check if LLM response was successful
                if not llm_response.success:
                    raise Exception(f"LLM call failed: {llm_response.error}")
                
                # Convert LLMResponse to dict format
                response = {
                    "content": llm_response.content or "",
                    "tool_calls": llm_response.tool_calls if llm_response.tool_calls else None
                }
                
                # Add assistant message
                assistant_message = {
                    "role": "assistant", 
                    "content": response.get("content", "")
                }
                
                if response.get("tool_calls"):
                    assistant_message["tool_calls"] = response["tool_calls"]
                
                messages.append(assistant_message)
                
                # Process tool calls if any
                if response.get("tool_calls"):
                    for tool_call in response["tool_calls"]:
                        try:
                            # Handle different tool call formats
                            if hasattr(tool_call, 'function'):
                                tool_name = tool_call.function.name
                                arguments = json.loads(tool_call.function.arguments)
                                tool_call_id = tool_call.id
                            elif isinstance(tool_call, dict):
                                tool_name = tool_call["function"]["name"]
                                arguments = json.loads(tool_call["function"]["arguments"])
                                tool_call_id = tool_call["id"]
                            else:
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
                            # Add error response
                            messages.append({
                                "role": "tool",
                                "tool_call_id": getattr(tool_call, 'id', 'unknown'),
                                "content": json.dumps({
                                    "success": False,
                                    "error": f"Tool execution failed: {str(e)}"
                                }, indent=2)
                            })
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