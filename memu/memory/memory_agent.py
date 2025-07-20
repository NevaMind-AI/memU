"""
MemU Memory Agent - Simple Conversation Processing

Clean memory agent that handles:
- Conversation processing into memory types
- Memory content generation and storage in markdown files  
- Embedding generation for semantic retrieval
- Dynamic memory categories from config
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading
import hashlib
import json

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .embeddings import get_default_embedding_client
from ..config.markdown_config import get_config_manager

logger = get_logger(__name__)








class MemoryAgent:
    """
    Clean Memory Agent for conversation processing.
    
    Handles:
    - Conversation processing into memory types
    - Memory content generation and storage in markdown files
    - Embedding generation for semantic retrieval
    - CRUD operations on memory content
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        memory_dir: str = "memory",
        enable_embeddings: bool = True
    ):
        """
        Initialize Memory Agent
        
        Args:
            llm_client: LLM client for processing conversations and session splitting
            memory_dir: Directory to store memory files
            enable_embeddings: Whether to generate embeddings for semantic search
        """
        self.llm_client = llm_client
        self.memory_dir = Path(memory_dir)
        self._stop_flag = threading.Event()
        
        # Initialize memory types from config
        self.config_manager = get_config_manager()
        self.memory_types = self.config_manager.get_file_types_mapping()
        self.processing_order = self.config_manager.get_processing_order()
        
        # Initialize file-based storage manager
        self.storage_manager = MemoryFileManager(memory_dir)
        

        
        # Initialize embedding client
        self.enable_embeddings = enable_embeddings
        if enable_embeddings:
            try:
                self.embedding_client = get_default_embedding_client()
                self.embeddings_enabled = True
                logger.info("Embeddings enabled for semantic retrieval")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding client: {e}. Embeddings disabled.")
                self.embedding_client = None
                self.embeddings_enabled = False
        else:
            self.embedding_client = None
            self.embeddings_enabled = False
        
        # Create storage directories
        self.embeddings_dir = self.memory_dir / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)
        
        logger.info(f"Memory Agent initialized: {len(self.memory_types)} memory types, embeddings: {self.embeddings_enabled}")

    def process_conversation(
        self,
        conversation: List[Dict],
        character_name: str,
        session_date: str = "",
        selected_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation into memory types:
        1. Convert conversation to text format
        2. Process into memory types (activity, profile, events, etc.)
        3. Save to markdown files with embeddings
        
        Args:
            conversation: List of message dicts with 'role' and 'content' fields
                         [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            character_name: Name of the character
            session_date: Date of the session
            selected_types: Specific memory types to process (None for all)
            
        Returns:
            Dict containing processing results
        """
        # Reset stop flag at start of new conversation processing
        self.reset_stop_flag()
        
        results = {
            "success": True,
            "character_name": character_name,
            "session_date": session_date or datetime.now().strftime("%Y-%m-%d"),
            "memory_outputs": {},
            "errors": []
        }
        
        try:
            # Validate conversation format
            if not isinstance(conversation, list):
                logger.error("Conversation must be a list of message objects with 'role' and 'content' fields")
                results["errors"].append("Invalid conversation format - expected list of message objects")
                results["success"] = False
                return results
            
            if not conversation:
                logger.warning("Empty conversation provided")
                results["errors"].append("Empty conversation provided")
                results["success"] = False
                return results
            
            logger.info(f"Processing conversation for {character_name} ({len(conversation)} messages)")
            
            # Convert conversation to text format for LLM processing
            conversation_text = self._convert_conversation_to_text(conversation)
            
            # Determine which types to process
            types_to_process = selected_types or self.processing_order
            
            # Load existing memory content
            existing_memory = self._load_existing_memory(character_name)
            
            # Process each memory type and add to markdown files
            for memory_type in types_to_process:
                # Check stop flag
                if self._stop_flag.is_set():
                    results["errors"].append("Operation was stopped by user")
                    results["success"] = False
                    break
                
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
                
        except Exception as e:
            error_msg = f"Failed to process conversation: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            results["success"] = False
        
        return results

    def add_memory(
        self, 
        character_name: str, 
        category: str, 
        content: str, 
        append: bool = True,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Add new memory content to a category with optional embedding generation
        
        Args:
            character_name: Name of the character
            category: Memory category to add to
            content: Content to add
            append: Whether to append to existing content or replace it
            generate_embeddings: Whether to generate embeddings for the content
            
        Returns:
            Dict containing operation result including embedding info
        """
        try:
            if self._stop_flag.is_set():
                return {
                    "success": False,
                    "error": "Operation was stopped"
                }
            
            if category not in self.memory_types:
                return {
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                }
            
            if append:
                # Append to existing content
                existing = self.read_memory(character_name, category)
                if isinstance(existing, str):
                    new_content = existing + "\n\n" + content if existing else content
                else:
                    new_content = content
            else:
                # Replace existing content
                new_content = content
            
            # Save content with embeddings if enabled
            if generate_embeddings and self.embeddings_enabled:
                success = self._save_memory_with_embeddings(character_name, category, new_content)
                embeddings_info = "Generated embeddings for content"
            else:
                success = self._save_memory(character_name, category, new_content)
                embeddings_info = "No embeddings generated"
            
            if success:
                return {
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "operation": "append" if append else "replace",
                    "content_added": len(content),
                    "embeddings_generated": generate_embeddings and self.embeddings_enabled,
                    "embeddings_info": embeddings_info,
                    "message": f"Successfully {'appended to' if append else 'replaced'} {category} for {character_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to save memory to {category}"
                }
                
        except Exception as e:
            logger.error(f"Error adding memory to {category} for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_memory(
        self, 
        character_name: str, 
        category: str, 
        new_content: str,
        regenerate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Update existing memory content with optional embedding regeneration
        
        Args:
            character_name: Name of the character
            category: Memory category to update
            new_content: New content to replace existing content
            regenerate_embeddings: Whether to regenerate embeddings for the new content
            
        Returns:
            Dict containing update result including embedding info
        """
        try:
            if self._stop_flag.is_set():
                return {
                    "success": False,
                    "error": "Operation was stopped"
                }
            
            if category not in self.memory_types:
                return {
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                }
            
            # Get old content for comparison
            old_content = self.read_memory(character_name, category)
            old_length = len(old_content) if isinstance(old_content, str) else 0
            
            # Update with new content and embeddings
            if regenerate_embeddings and self.embeddings_enabled:
                success = self._save_memory_with_embeddings(character_name, category, new_content)
                embeddings_info = "Regenerated embeddings for updated content"
            else:
                success = self._save_memory(character_name, category, new_content)
                embeddings_info = "No embedding regeneration"
            
            if success:
                return {
                    "success": True,
                    "character_name": character_name,
                    "category": category,
                    "old_content_length": old_length,
                    "new_content_length": len(new_content),
                    "content_change": len(new_content) - old_length,
                    "embeddings_regenerated": regenerate_embeddings and self.embeddings_enabled,
                    "embeddings_info": embeddings_info,
                    "message": f"Successfully updated {category} for {character_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update {category}"
                }
                
        except Exception as e:
            logger.error(f"Error updating {category} for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def read_memory(self, character_name: str, memory_type: str = None, include_embeddings: bool = False) -> Dict[str, str] | str:
        """
        Read memory content for a character with optional embedding info
        
        Args:
            character_name: Name of the character
            memory_type: Specific memory type to read (None for all)
            include_embeddings: Whether to include embedding information
            
        Returns:
            Dict of memory type -> content (if memory_type is None)
            or string content (if memory_type is specified)
        """
        if memory_type:
            # Read specific memory type
            try:
                content = ""
                if hasattr(self.storage_manager, 'read_memory_file'):
                    content = self.storage_manager.read_memory_file(character_name, memory_type)
                else:
                    method_name = f"read_{memory_type}"
                    if hasattr(self.storage_manager, method_name):
                        content = getattr(self.storage_manager, method_name)(character_name)
                    else:
                        logger.warning(f"No read method available for {memory_type}")
                        return ""
                
                if include_embeddings and self.embeddings_enabled:
                    # Return content with embedding metadata
                    embedding_info = self._get_embedding_info(character_name, memory_type)
                    return {
                        "content": content,
                        "embedding_info": embedding_info
                    }
                
                return content
                
            except Exception as e:
                logger.warning(f"Failed to read {memory_type} for {character_name}: {e}")
                return ""
        else:
            # Read all memory types
            return self._load_existing_memory(character_name)

    def search_memory(
        self,
        character_name: str,
        query: str,
        memory_types: List[str] = None,
        limit: int = 5,
        use_embeddings: bool = True
    ) -> List[Dict]:
        """
        Search memory content using embeddings and text matching
        
        Args:
            character_name: Name of the character
            query: Search query
            memory_types: Specific memory types to search (None for all)
            limit: Maximum number of results
            use_embeddings: Whether to use embedding-based semantic search
            
        Returns:
            List of search results with similarity scores
        """
        try:
            results = []
            search_types = memory_types or list(self.memory_types.keys())
            
            if use_embeddings and self.embeddings_enabled:
                # Use embedding-based semantic search
                results = self._semantic_memory_search(character_name, query, search_types, limit)
            else:
                # Fallback to text-based search
                for memory_type in search_types:
                    content = self.read_memory(character_name, memory_type)
                    if isinstance(content, str) and content and query.lower() in content.lower():
                        results.append({
                            "content": content,
                            "similarity": 1.0,
                            "type": memory_type,
                            "character": character_name,
                            "search_method": "text_matching"
                        })
            
            return results[:limit]
                
        except Exception as e:
            logger.error(f"Failed to search memory for {character_name}: {e}")
            return []

    def delete_memory(self, character_name: str, category: str = None, delete_embeddings: bool = True) -> Dict[str, Any]:
        """
        Delete memory content and associated embeddings
        
        Args:
            character_name: Name of the character
            category: Specific category to delete (None to delete all)
            delete_embeddings: Whether to delete associated embeddings
            
        Returns:
            Dict containing deletion result including embedding cleanup info
        """
        try:
            if self._stop_flag.is_set():
                return {
                    "success": False,
                    "error": "Operation was stopped"
                }
            
            deleted_categories = []
            failed_categories = []
            embeddings_deleted = 0
            
            categories_to_delete = [category] if category else list(self.memory_types.keys())
            
            for cat in categories_to_delete:
                if cat not in self.memory_types:
                    failed_categories.append(f"Invalid category: {cat}")
                    continue
                
                try:
                    # Delete memory content
                    success = self._save_memory(character_name, cat, "")
                    
                    # Delete associated embeddings
                    if delete_embeddings and self.embeddings_enabled:
                        deleted_count = self._delete_embeddings(character_name, cat)
                        embeddings_deleted += deleted_count
                    
                    if success:
                        deleted_categories.append(cat)
                    else:
                        failed_categories.append(cat)
                except Exception as e:
                    failed_categories.append(f"{cat}: {str(e)}")
            
            return {
                "success": len(failed_categories) == 0,
                "character_name": character_name,
                "deleted_categories": deleted_categories,
                "failed_categories": failed_categories,
                "total_deleted": len(deleted_categories),
                "embeddings_deleted": embeddings_deleted,
                "message": f"Deleted {len(deleted_categories)} categories and {embeddings_deleted} embeddings for {character_name}"
            }
            
        except Exception as e:
            logger.error(f"Error deleting memory for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_categories": [],
                "failed_categories": []
            }

    def get_memory_status(self, character_name: str, include_embedding_stats: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive status of memory for a character including embedding info
        
        Args:
            character_name: Name of the character
            include_embedding_stats: Whether to include embedding statistics
            
        Returns:
            Dict containing memory status information with embedding details
        """
        try:
            status = {
                "character_name": character_name,
                "available_categories": list(self.memory_types.keys()),
                "category_status": {},
                "total_content_length": 0,
                "embedding_stats": {},
                "last_updated": datetime.now().isoformat()
            }
            
            total_embeddings = 0
            for category in self.memory_types.keys():
                content = self.read_memory(character_name, category)
                content_str = content if isinstance(content, str) else ""
                
                category_embeddings = 0
                if include_embedding_stats and self.embeddings_enabled:
                    category_embeddings = self._count_embeddings(character_name, category)
                    total_embeddings += category_embeddings
                
                status["category_status"][category] = {
                    "exists": bool(content_str),
                    "content_length": len(content_str),
                    "filename": self.memory_types[category],
                    "description": self.config_manager.get_file_description(category),
                    "embeddings_count": category_embeddings
                }
                
                if content_str:
                    status["total_content_length"] += len(content_str)
            
            if include_embedding_stats:
                status["embedding_stats"] = {
                    "embeddings_enabled": self.embeddings_enabled,
                    "total_embeddings": total_embeddings,
                    "embedding_client": str(type(self.embedding_client)) if self.embedding_client else None,
                    "embeddings_directory": str(self.embeddings_dir)
                }
            
            return {
                "success": True,
                "status": status,
                "message": f"Memory status for {character_name} - {status['total_content_length']} chars, {total_embeddings} embeddings"
            }
            
        except Exception as e:
            logger.error(f"Error getting memory status for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": {}
            }

    def get_available_categories(self) -> Dict[str, Any]:
        """
        Get all available memory categories from config
        
        Returns:
            Dict containing category information
        """
        try:
            categories = {}
            
            for category, filename in self.memory_types.items():
                description = self.config_manager.get_file_description(category)
                
                categories[category] = {
                    "filename": filename,
                    "description": description,
                    "config_source": self.config_manager.get_folder_path(category)
                }
            
            return {
                "success": True,
                "categories": categories,
                "total_categories": len(categories),
                "processing_order": self.processing_order,
                "embeddings_enabled": self.embeddings_enabled,
                "message": f"Found {len(categories)} memory categories from config"
            }
            
        except Exception as e:
            logger.error(f"Error getting available categories: {e}")
            return {
                "success": False,
                "error": str(e),
                "categories": {},
                "total_categories": 0
            }

    def stop_action(self) -> Dict[str, Any]:
        """
        Stop current operations
        
        Returns:
            Dict containing stop result
        """
        try:
            self._stop_flag.set()
            logger.info("Memory Agent: Stop flag set")
            
            return {
                "success": True,
                "message": "Stop signal sent to Memory Agent operations",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error stopping operations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def reset_stop_flag(self):
        """Reset the stop flag to allow new operations"""
        self._stop_flag.clear()
        logger.debug("Memory Agent: Stop flag reset")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all available tools with their descriptions
        
        Returns:
            List of tool descriptions
        """
        return [
            {
                "name": "process_conversation",
                "description": "Process a conversation into memory types with embedding generation",
                "parameters": ["conversation", "character_name", "session_date (optional)", "selected_types (optional)"],
                "returns": "Dict with processing results including memory outputs in markdown files"
            },
            {
                "name": "add_memory",
                "description": "Add new memory content with optional embedding generation",
                "parameters": ["character_name", "category", "content", "append (optional)", "generate_embeddings (optional)"],
                "returns": "Dict with operation result including embedding info"
            },
            {
                "name": "update_memory",
                "description": "Update existing memory content with embedding regeneration",
                "parameters": ["character_name", "category", "new_content", "regenerate_embeddings (optional)"],
                "returns": "Dict with update result including embedding info"
            },
            {
                "name": "read_memory",
                "description": "Read memory content with optional embedding information",
                "parameters": ["character_name", "memory_type (optional)", "include_embeddings (optional)"],
                "returns": "String content or Dict of all memory types with embedding info"
            },
            {
                "name": "search_memory",
                "description": "Search memory content using embeddings and text matching",
                "parameters": ["character_name", "query", "memory_types (optional)", "limit (optional)", "use_embeddings (optional)"],
                "returns": "List of search results with semantic similarity scores"
            },
            {
                "name": "delete_memory",
                "description": "Delete memory content and associated embeddings",
                "parameters": ["character_name", "category (optional)", "delete_embeddings (optional)"],
                "returns": "Dict with deletion results including embedding cleanup"
            },
            {
                "name": "get_memory_status",
                "description": "Get comprehensive memory status with embedding statistics",
                "parameters": ["character_name", "include_embedding_stats (optional)"],
                "returns": "Dict with memory status including embedding details"
            },
            {
                "name": "get_available_categories",
                "description": "Get all available memory categories from config",
                "parameters": [],
                "returns": "Dict with category information and embedding capabilities"
            }
        ]

    # ================================
    # Enhanced Embedding Methods
    # ================================







    def _convert_conversation_to_text(self, conversation: List[Dict]) -> str:
        """Convert conversation list to text format for LLM processing"""
        if not conversation or not isinstance(conversation, list):
            return ""
        
        text_parts = []
        for message in conversation:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            text_parts.append(f"{role.upper()}: {content}")
        
        return "\n".join(text_parts)



    def _save_memory_with_embeddings(self, character_name: str, memory_type: str, content: str) -> bool:
        """Save memory content and generate embeddings"""
        try:
            # Save the main content
            success = self._save_memory(character_name, memory_type, content)
            
            if success and self.embeddings_enabled and content.strip():
                # Generate embeddings for the content
                self._generate_memory_embeddings(character_name, memory_type, content)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save memory with embeddings for {character_name}: {e}")
            return False

    def _generate_memory_embeddings(self, character_name: str, memory_type: str, content: str):
        """Generate and store embeddings for memory content"""
        try:
            if not content.strip():
                return
            
            # Split content into chunks for embedding
            chunks = self.chunker.split_conversation(content, f"{character_name}_{memory_type}")
            
            # Generate embeddings for chunks
            embeddings = self._generate_chunk_embeddings(chunks)
            
            if embeddings:
                # Store embeddings
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

    def _semantic_memory_search(self, character_name: str, query: str, memory_types: List[str], limit: int) -> List[Dict]:
        """Perform semantic search using stored embeddings"""
        try:
            if not self.embeddings_enabled:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_client.generate_embedding(query)
            
            results = []
            char_embeddings_dir = self.embeddings_dir / character_name
            
            if not char_embeddings_dir.exists():
                return []
            
            for memory_type in memory_types:
                embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
                
                if embeddings_file.exists():
                    try:
                        with open(embeddings_file, 'r', encoding='utf-8') as f:
                            embeddings_data = json.load(f)
                        
                        for emb_data in embeddings_data.get("embeddings", []):
                            similarity = self._cosine_similarity(query_embedding, emb_data["embedding"])
                            
                            if similarity > 0.3:  # Similarity threshold
                                results.append({
                                    "content": emb_data["text"],
                                    "similarity": similarity,
                                    "type": memory_type,
                                    "character": character_name,
                                    "search_method": "semantic_embedding",
                                    "chunk_id": emb_data.get("chunk_id", ""),
                                    "metadata": emb_data.get("metadata", {})
                                })
                    
                    except Exception as e:
                        logger.warning(f"Failed to load embeddings for {memory_type}: {e}")
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search failed for {character_name}: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            import math
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception as e:
            logger.warning(f"Cosine similarity calculation failed: {e}")
            return 0.0

    def _get_embedding_info(self, character_name: str, memory_type: str) -> Dict[str, Any]:
        """Get embedding information for a memory type"""
        try:
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
            
            if embeddings_file.exists():
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                
                return {
                    "has_embeddings": True,
                    "embedding_count": embeddings_data.get("total_embeddings", 0),
                    "last_updated": embeddings_data.get("timestamp", ""),
                    "content_hash": embeddings_data.get("content_hash", "")
                }
            else:
                return {
                    "has_embeddings": False,
                    "embedding_count": 0,
                    "last_updated": "",
                    "content_hash": ""
                }
                
        except Exception as e:
            logger.warning(f"Failed to get embedding info for {character_name}:{memory_type}: {e}")
            return {"has_embeddings": False, "embedding_count": 0, "error": str(e)}

    def _count_embeddings(self, character_name: str, memory_type: str) -> int:
        """Count embeddings for a specific memory type"""
        try:
            embedding_info = self._get_embedding_info(character_name, memory_type)
            return embedding_info.get("embedding_count", 0)
        except Exception:
            return 0

    def _delete_embeddings(self, character_name: str, memory_type: str) -> int:
        """Delete embeddings for a memory type"""
        try:
            char_embeddings_dir = self.embeddings_dir / character_name
            embeddings_file = char_embeddings_dir / f"{memory_type}_embeddings.json"
            
            deleted_count = 0
            if embeddings_file.exists():
                # Get count before deletion
                deleted_count = self._count_embeddings(character_name, memory_type)
                embeddings_file.unlink()
                logger.debug(f"Deleted {deleted_count} embeddings for {character_name}:{memory_type}")
            
            return deleted_count
            
        except Exception as e:
            logger.warning(f"Failed to delete embeddings for {character_name}:{memory_type}: {e}")
            return 0

    # ================================
    # Helper Methods
    # ================================

    def _load_existing_memory(self, character_name: str) -> Dict[str, str]:
        """Load existing memory content for all types"""
        existing_memory = {}
        
        for memory_type in self.memory_types:
            try:
                content = self.read_memory(character_name, memory_type)
                existing_memory[memory_type] = content if isinstance(content, str) else ""
            except Exception as e:
                logger.warning(f"Failed to load existing {memory_type} for {character_name}: {e}")
                existing_memory[memory_type] = ""
        
        return existing_memory

    def _process_memory_type(
        self,
        memory_type: str,
        character_name: str,
        input_content: str,
        session_date: str,
        existing_memory: Dict[str, str]
    ) -> str:
        """Process a specific memory type"""
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

    def _save_memory(self, character_name: str, memory_type: str, content: str) -> bool:
        """Save memory content"""
        try:
            if hasattr(self.storage_manager, 'write_memory_file'):
                return self.storage_manager.write_memory_file(character_name, memory_type, content)
            else:
                method_name = f"write_{memory_type}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name, content)
                else:
                    logger.error(f"No write method available for {memory_type}")
                    return False
        except Exception as e:
            logger.error(f"Failed to save {memory_type} for {character_name}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the memory agent"""
        return {
            "agent_name": "memory_agent",
            "memory_types": list(self.memory_types.keys()),
            "processing_order": self.processing_order,
            "storage_type": "file_system",
            "memory_dir": str(self.memory_dir),
            "config_source": "markdown_config.py (dynamic folder structure)",
            "tools_available": len(self.get_available_tools()),
            "stop_flag_set": self._stop_flag.is_set(),

            "embedding_capabilities": {
                "embeddings_enabled": self.embeddings_enabled,
                "embedding_client": str(type(self.embedding_client)) if self.embedding_client else None,
                "embeddings_directory": str(self.embeddings_dir)
            },
            "config_details": {
                "total_file_types": len(self.memory_types),
                "categories_from_config": True,
                "config_structure": "Dynamic folder configuration"
            }
        } 