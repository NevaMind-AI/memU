"""
RecallAgent for MemU Memory System

A specialized agent for retrieving and importing content from markdown files.
This agent handles:
- Scanning local file systems for documents
- Importing specific documents or directories
- Retrieving and searching existing memory content with multiple search methods
- File type detection and categorization

Enhanced with multiple search capabilities:
- Semantic search using content embeddings
- BM25 ranking for relevance scoring
- String matching for exact term matching

Separated from MemoryAgent to simplify the architecture.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading
import math
from collections import defaultdict, Counter

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .embeddings import get_default_embedding_client
from ..config.markdown_config import get_config_manager, detect_file_type

logger = get_logger(__name__)


class BM25:
    """Simple BM25 implementation for text ranking"""
    
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len = [len(doc.split()) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_count = len(corpus)
        
        # Build document frequencies and IDF
        for doc in corpus:
            doc_freq = Counter(doc.lower().split())
            self.doc_freqs.append(doc_freq)
            
            for word in doc_freq.keys():
                if word not in self.idf:
                    containing_docs = sum(1 for d in corpus if word in d.lower())
                    self.idf[word] = math.log((self.doc_count - containing_docs + 0.5) / (containing_docs + 0.5) + 1.0)
    
    def score(self, query: str, doc_idx: int) -> float:
        """Calculate BM25 score for a query against a document"""
        if doc_idx >= len(self.doc_freqs):
            return 0.0
            
        score = 0.0
        doc_freq = self.doc_freqs[doc_idx]
        doc_len = self.doc_len[doc_idx]
        
        for word in query.lower().split():
            if word in doc_freq and word in self.idf:
                freq = doc_freq[word]
                idf = self.idf[word]
                score += idf * (freq * (self.k1 + 1)) / (freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
        
        return score
    
    def get_scores(self, query: str) -> List[float]:
        """Get BM25 scores for query against all documents"""
        return [self.score(query, i) for i in range(len(self.corpus))]


class RecallAgent:
    """
    Specialized agent for retrieving content from markdown files and local file system.
    
    This agent provides tools for:
    1. scan_local_documents - Scan local file system for documents
    2. import_local_document - Import a specific local document
    3. import_directory - Import all documents from a directory
    4. list_local_files - List available local files
    5. search_memory_content - Advanced multi-method search of memory content
    6. get_memory_summary - Get summary of all memory for a character
    7. find_similar_content - Find similar content using semantic, BM25, and string methods
    """
    
    # Supported file extensions (default: only markdown)
    SUPPORTED_EXTENSIONS = {".md", ".txt"}
    
    def __init__(
        self,
        memory_dir: str = "memory",
        documents_dir: str = None
    ):
        """
        Initialize Recall Agent
        
        Args:
            memory_dir: Directory where memory files are stored
            documents_dir: Directory to scan for local documents
        """
        self.memory_dir = Path(memory_dir)
        self.documents_dir = Path(documents_dir) if documents_dir else Path.cwd()
        self._stop_flag = threading.Event()
        
        # Initialize config manager to get available categories
        self.config_manager = get_config_manager()
        self.memory_types = self.config_manager.get_file_types_mapping()
        
        # Initialize file-based storage manager
        self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize embedding client for semantic search
        try:
            self.embedding_client = get_default_embedding_client()
            self.semantic_search_enabled = True
            logger.info("Semantic search enabled with embedding client")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding client: {e}. Semantic search disabled.")
            self.embedding_client = None
            self.semantic_search_enabled = False
        
        logger.info(f"Recall Agent initialized with documents directory: {self.documents_dir}")

    def scan_local_documents(
        self, 
        directory: str = None, 
        recursive: bool = True,
        file_extensions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Tool 1: Scan local file system for documents
        
        Args:
            directory: Directory to scan (defaults to documents_dir)
            recursive: Whether to scan subdirectories recursively
            file_extensions: List of file extensions to include (e.g., ['.md', '.txt'])
            
        Returns:
            Dict containing discovered files and their information
        """
        try:
            scan_dir = Path(directory) if directory else self.documents_dir
            
            if not scan_dir.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {scan_dir}",
                    "files": []
                }
            
            # Use specified extensions or defaults
            extensions = set(file_extensions) if file_extensions else self.SUPPORTED_EXTENSIONS
            
            discovered_files = []
            
            if recursive:
                # Recursive search
                for ext in extensions:
                    pattern = f"**/*{ext}"
                    for file_path in scan_dir.glob(pattern):
                        if file_path.is_file():
                            file_info = self._get_file_info(file_path)
                            discovered_files.append(file_info)
            else:
                # Non-recursive search
                for file_path in scan_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in extensions:
                        file_info = self._get_file_info(file_path)
                        discovered_files.append(file_info)
            
            # Sort by modification time (newest first)
            discovered_files.sort(key=lambda x: x.get("modified_time", 0), reverse=True)
            
            return {
                "success": True,
                "directory": str(scan_dir),
                "recursive": recursive,
                "extensions": list(extensions),
                "files": discovered_files,
                "total_files": len(discovered_files),
                "message": f"Found {len(discovered_files)} documents in {scan_dir}"
            }
            
        except Exception as e:
            logger.error(f"Error scanning local documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": []
            }

    def list_local_files(self, directory: str = None, pattern: str = "*") -> Dict[str, Any]:
        """
        Tool 4: List available local files with filtering
        
        Args:
            directory: Directory to list (defaults to documents_dir)
            pattern: File pattern to match (e.g., "*.md", "*profile*")
            
        Returns:
            Dict containing file listing
        """
        try:
            list_dir = Path(directory) if directory else self.documents_dir
            
            if not list_dir.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {list_dir}",
                    "files": []
                }
            
            files = []
            for file_path in list_dir.glob(pattern):
                if file_path.is_file():
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix,
                        "modified_time": file_path.stat().st_mtime,
                        "readable": os.access(file_path, os.R_OK),
                        "detected_type": detect_file_type(file_path.name)
                    }
                    files.append(file_info)
            
            return {
                "success": True,
                "directory": str(list_dir),
                "pattern": pattern,
                "files": files,
                "total_files": len(files),
                "message": f"Listed {len(files)} files matching '{pattern}'"
            }
            
        except Exception as e:
            logger.error(f"Error listing local files: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": []
            }

    def import_local_document(
        self, 
        file_path: str, 
        character_name: str,
        category: str = None,
        auto_detect_category: bool = True
    ) -> Dict[str, Any]:
        """
        Tool 2: Import a specific local document into memory
        
        Args:
            file_path: Path to the document to import
            character_name: Character to associate the document with
            category: Memory category to store in (None for auto-detection)
            auto_detect_category: Whether to auto-detect category from filename/content
            
        Returns:
            Dict containing import result
        """
        try:
            if self._stop_flag.is_set():
                return {
                    "success": False,
                    "error": "Operation was stopped"
                }
            
            doc_path = Path(file_path)
            if not doc_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}"
                }
            
            # Read document content
            content = self._read_document_content(doc_path)
            if not content:
                return {
                    "success": False,
                    "error": f"Could not read content from {file_path}"
                }
            
            # Determine category
            if not category and auto_detect_category:
                category = detect_file_type(doc_path.name, content)
            
            if not category:
                category = "activity"  # Default category
            
            if category not in self.memory_types:
                return {
                    "success": False,
                    "error": f"Invalid category '{category}'. Available: {list(self.memory_types.keys())}"
                }
            
            # Save to memory file
            success = self._save_imported_content(character_name, category, content, doc_path.name)
            
            if success:
                return {
                    "success": True,
                    "file_path": str(doc_path),
                    "character_name": character_name,
                    "category": category,
                    "content_length": len(content),
                    "detected_category": auto_detect_category,
                    "message": f"Successfully imported {doc_path.name} into {category} for {character_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to save imported content"
                }
                
        except Exception as e:
            logger.error(f"Error importing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def import_directory(
        self, 
        directory: str,
        character_name: str,
        file_pattern: str = "*",
        max_files: int = 50
    ) -> Dict[str, Any]:
        """
        Tool 3: Import all documents from a directory
        
        Args:
            directory: Directory containing documents to import
            character_name: Character to associate documents with
            file_pattern: Pattern to match files (e.g., "*.md", "*profile*")
            max_files: Maximum number of files to import
            
        Returns:
            Dict containing batch import results
        """
        try:
            if self._stop_flag.is_set():
                return {
                    "success": False,
                    "error": "Operation was stopped"
                }
            
            import_dir = Path(directory)
            if not import_dir.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {directory}",
                    "imported_files": [],
                    "failed_files": []
                }
            
            # Get list of files to import
            files_to_import = list(import_dir.glob(file_pattern))[:max_files]
            
            imported_files = []
            failed_files = []
            
            for file_path in files_to_import:
                if self._stop_flag.is_set():
                    break
                
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    import_result = self.import_local_document(
                        str(file_path), 
                        character_name,
                        auto_detect_category=True
                    )
                    
                    if import_result["success"]:
                        imported_files.append({
                            "file": file_path.name,
                            "category": import_result["category"],
                            "size": import_result["content_length"]
                        })
                    else:
                        failed_files.append({
                            "file": file_path.name,
                            "error": import_result["error"]
                        })
            
            return {
                "success": len(failed_files) == 0,
                "directory": str(import_dir),
                "character_name": character_name,
                "imported_files": imported_files,
                "failed_files": failed_files,
                "total_imported": len(imported_files),
                "total_failed": len(failed_files),
                "message": f"Imported {len(imported_files)} files, {len(failed_files)} failed"
            }
            
        except Exception as e:
            logger.error(f"Error importing directory {directory}: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_files": [],
                "failed_files": []
            }

    def search_memory_content(
        self, 
        character_name: str, 
        query: str, 
        categories: List[str] = None, 
        limit: int = 5,
        search_methods: List[str] = None
    ) -> Dict[str, Any]:
        """
        Tool 5: Advanced multi-method search of existing memory content
        
        Uses three search methods:
        1. Semantic search (embeddings) - for meaning-based matching
        2. BM25 search - for relevance ranking based on term frequency
        3. String matching - for exact term matching
        
        Args:
            character_name: Name of the character
            query: Search query
            categories: Specific categories to search (None for all)
            limit: Maximum number of results
            search_methods: Methods to use ['semantic', 'bm25', 'string'] (None for all)
            
        Returns:
            Dict containing search results with combined scores
        """
        try:
            search_categories = categories or list(self.memory_types.keys())
            available_methods = search_methods or ['semantic', 'bm25', 'string']
            
            # Collect all content for search
            documents = []
            doc_metadata = []
            
            for category in search_categories:
                content = self._read_memory_content(character_name, category)
                if content:
                    documents.append(content)
                    doc_metadata.append({
                        "category": category,
                        "character": character_name,
                        "content_length": len(content)
                    })
            
            if not documents:
                return {
                    "success": True,
                    "character_name": character_name,
                    "query": query,
                    "searched_categories": search_categories,
                    "search_methods": available_methods,
                    "results": [],
                    "total_results": 0,
                    "message": "No content found to search"
                }
            
            # Perform different search methods
            search_results = []
            
            # 1. Semantic Search using embeddings
            if 'semantic' in available_methods and self.semantic_search_enabled:
                semantic_results = self._semantic_search(query, documents, doc_metadata)
                search_results.extend(semantic_results)
            
            # 2. BM25 Search
            if 'bm25' in available_methods:
                bm25_results = self._bm25_search(query, documents, doc_metadata)
                search_results.extend(bm25_results)
            
            # 3. String Matching Search
            if 'string' in available_methods:
                string_results = self._string_search(query, documents, doc_metadata)
                search_results.extend(string_results)
            
            # Combine and deduplicate results
            combined_results = self._combine_search_results(search_results, limit)
            
            return {
                "success": True,
                "character_name": character_name,
                "query": query,
                "searched_categories": search_categories,
                "search_methods": available_methods,
                "results": combined_results,
                "total_results": len(combined_results),
                "semantic_enabled": self.semantic_search_enabled,
                "message": f"Found {len(combined_results)} results using {len(available_methods)} search methods"
            }
            
        except Exception as e:
            logger.error(f"Error searching memory content for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def get_memory_summary(self, character_name: str) -> Dict[str, Any]:
        """
        Tool 6: Get summary of all memory for a character
        
        Args:
            character_name: Name of the character
            
        Returns:
            Dict containing memory summary
        """
        try:
            summary = {
                "character_name": character_name,
                "memory_categories": {},
                "total_content_length": 0,
                "available_categories": list(self.memory_types.keys())
            }
            
            for category in self.memory_types.keys():
                content = self._read_memory_content(character_name, category)
                
                summary["memory_categories"][category] = {
                    "exists": bool(content),
                    "content_length": len(content) if content else 0,
                    "preview": content[:200] + "..." if content and len(content) > 200 else content or ""
                }
                
                if content:
                    summary["total_content_length"] += len(content)
            
            return {
                "success": True,
                "summary": summary,
                "message": f"Memory summary for {character_name} - {summary['total_content_length']} total characters"
            }
            
        except Exception as e:
            logger.error(f"Error getting memory summary for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": {}
            }

    def find_similar_content(
        self, 
        character_name: str, 
        reference_text: str, 
        categories: List[str] = None,
        similarity_threshold: float = 0.3,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Tool 7: Find similar content using multiple search methods
        
        Args:
            character_name: Name of the character
            reference_text: Text to find similar content to
            categories: Categories to search in (None for all)
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing similar content results with combined scores
        """
        try:
            search_categories = categories or list(self.memory_types.keys())
            
            # Use the enhanced search with reference text as query
            search_result = self.search_memory_content(
                character_name=character_name,
                query=reference_text,
                categories=search_categories,
                limit=max_results * 2,  # Get more results initially
                search_methods=['semantic', 'bm25', 'string']
            )
            
            if not search_result["success"]:
                return search_result
            
            # Filter by similarity threshold and add additional analysis
            similar_content = []
            for result in search_result["results"]:
                if result["combined_score"] >= similarity_threshold:
                    # Add reference text analysis
                    analysis = self._analyze_similarity(reference_text, result["content"])
                    result.update(analysis)
                    similar_content.append(result)
            
            # Sort by combined score and limit results
            similar_content.sort(key=lambda x: x["combined_score"], reverse=True)
            similar_content = similar_content[:max_results]
            
            return {
                "success": True,
                "character_name": character_name,
                "reference_text": reference_text[:100] + "..." if len(reference_text) > 100 else reference_text,
                "similarity_threshold": similarity_threshold,
                "similar_content": similar_content,
                "total_matches": len(similar_content),
                "search_methods_used": search_result.get("search_methods", []),
                "message": f"Found {len(similar_content)} similar content pieces above threshold {similarity_threshold}"
            }
            
        except Exception as e:
            logger.error(f"Error finding similar content for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "similar_content": []
            }

    def stop_action(self) -> Dict[str, Any]:
        """
        Stop current operations
        
        Returns:
            Dict containing stop result
        """
        try:
            self._stop_flag.set()
            logger.info("Recall Agent: Stop flag set")
            
            return {
                "success": True,
                "message": "Stop signal sent to Recall Agent operations",
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
        logger.debug("Recall Agent: Stop flag reset")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all available tools with their descriptions
        
        Returns:
            List of tool descriptions
        """
        return [
            {
                "name": "scan_local_documents",
                "description": "Scan local file system for documents",
                "parameters": ["directory (optional)", "recursive (optional)", "file_extensions (optional)"],
                "returns": "Dict with discovered files"
            },
            {
                "name": "import_local_document",
                "description": "Import a specific local document into memory",
                "parameters": ["file_path", "character_name", "category (optional)", "auto_detect_category (optional)"],
                "returns": "Dict with import result"
            },
            {
                "name": "import_directory",
                "description": "Import all documents from a directory",
                "parameters": ["directory", "character_name", "file_pattern (optional)", "max_files (optional)"],
                "returns": "Dict with batch import results"
            },
            {
                "name": "list_local_files",
                "description": "List available local files with filtering",
                "parameters": ["directory (optional)", "pattern (optional)"],
                "returns": "Dict with file listing"
            },
            {
                "name": "search_memory_content",
                "description": "Advanced multi-method search using semantic, BM25, and string matching",
                "parameters": ["character_name", "query", "categories (optional)", "limit (optional)", "search_methods (optional)"],
                "returns": "Dict with combined search results and scores"
            },
            {
                "name": "get_memory_summary",
                "description": "Get summary of all memory for a character",
                "parameters": ["character_name"],
                "returns": "Dict with memory summary"
            },
            {
                "name": "find_similar_content",
                "description": "Find similar content using multiple search methods with similarity scoring",
                "parameters": ["character_name", "reference_text", "categories (optional)", "similarity_threshold (optional)", "max_results (optional)"],
                "returns": "Dict with similar content results and analysis"
            }
        ]

    # ================================
    # Enhanced Search Methods
    # ================================

    def _semantic_search(self, query: str, documents: List[str], metadata: List[Dict]) -> List[Dict]:
        """Perform semantic search using embeddings"""
        if not self.semantic_search_enabled:
            return []
        
        try:
            # Generate embeddings for query and documents
            query_embedding = self.embedding_client.generate_embedding(query)
            doc_embeddings = [self.embedding_client.generate_embedding(doc) for doc in documents]
            
            results = []
            for i, (doc, meta) in enumerate(zip(documents, metadata)):
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, doc_embeddings[i])
                
                if similarity > 0.1:  # Minimum threshold for semantic similarity
                    results.append({
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "full_content_length": len(doc),
                        "semantic_score": similarity,
                        "search_method": "semantic",
                        "category": meta["category"],
                        "character": meta["character"]
                    })
            
            return results
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    def _bm25_search(self, query: str, documents: List[str], metadata: List[Dict]) -> List[Dict]:
        """Perform BM25 search for relevance ranking"""
        try:
            # Initialize BM25 with documents
            bm25 = BM25(documents)
            scores = bm25.get_scores(query)
            
            results = []
            max_score = max(scores) if scores else 1.0
            
            for i, (doc, meta, score) in enumerate(zip(documents, metadata, scores)):
                if score > 0:
                    # Normalize score to 0-1 range
                    normalized_score = score / max_score if max_score > 0 else 0
                    
                    results.append({
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "full_content_length": len(doc),
                        "bm25_score": normalized_score,
                        "search_method": "bm25",
                        "category": meta["category"],
                        "character": meta["character"]
                    })
            
            return results
            
        except Exception as e:
            logger.warning(f"BM25 search failed: {e}")
            return []

    def _string_search(self, query: str, documents: List[str], metadata: List[Dict]) -> List[Dict]:
        """Perform string matching search"""
        try:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            results = []
            for doc, meta in zip(documents, metadata):
                doc_lower = doc.lower()
                
                # Calculate string matching score
                exact_match = 1.0 if query_lower in doc_lower else 0.0
                
                # Word overlap score
                doc_words = set(doc_lower.split())
                word_overlap = len(query_words.intersection(doc_words)) / len(query_words) if query_words else 0
                
                # Combined string score
                string_score = max(exact_match, word_overlap * 0.8)
                
                if string_score > 0.1:
                    results.append({
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "full_content_length": len(doc),
                        "string_score": string_score,
                        "exact_match": exact_match > 0,
                        "word_overlap": word_overlap,
                        "search_method": "string",
                        "category": meta["category"],
                        "character": meta["character"]
                    })
            
            return results
            
        except Exception as e:
            logger.warning(f"String search failed: {e}")
            return []

    def _combine_search_results(self, search_results: List[Dict], limit: int) -> List[Dict]:
        """Combine results from different search methods and calculate final scores"""
        # Group results by category to avoid duplicates
        category_results = defaultdict(lambda: {
            "semantic_score": 0.0,
            "bm25_score": 0.0,
            "string_score": 0.0,
            "exact_match": False,
            "word_overlap": 0.0,
            "methods_used": [],
            "content": "",
            "category": "",
            "character": "",
            "full_content_length": 0
        })
        
        # Aggregate scores by category
        for result in search_results:
            category = result["category"]
            method = result["search_method"]
            
            category_results[category]["methods_used"].append(method)
            category_results[category]["content"] = result["content"]
            category_results[category]["category"] = result["category"]
            category_results[category]["character"] = result["character"]
            category_results[category]["full_content_length"] = result["full_content_length"]
            
            # Update scores
            if method == "semantic":
                category_results[category]["semantic_score"] = result.get("semantic_score", 0.0)
            elif method == "bm25":
                category_results[category]["bm25_score"] = result.get("bm25_score", 0.0)
            elif method == "string":
                category_results[category]["string_score"] = result.get("string_score", 0.0)
                category_results[category]["exact_match"] = result.get("exact_match", False)
                category_results[category]["word_overlap"] = result.get("word_overlap", 0.0)
        
        # Calculate combined scores
        combined_results = []
        for category, data in category_results.items():
            # Weighted combination of scores
            semantic_weight = 0.5
            bm25_weight = 0.3
            string_weight = 0.2
            
            combined_score = (
                data["semantic_score"] * semantic_weight +
                data["bm25_score"] * bm25_weight +
                data["string_score"] * string_weight
            )
            
            # Boost for exact matches
            if data["exact_match"]:
                combined_score = min(1.0, combined_score + 0.2)
            
            combined_results.append({
                "category": data["category"],
                "character": data["character"],
                "content": data["content"],
                "full_content_length": data["full_content_length"],
                "combined_score": combined_score,
                "semantic_score": data["semantic_score"],
                "bm25_score": data["bm25_score"],
                "string_score": data["string_score"],
                "exact_match": data["exact_match"],
                "word_overlap": data["word_overlap"],
                "search_methods_used": list(set(data["methods_used"])),
                "relevance": "high" if combined_score > 0.7 else "medium" if combined_score > 0.4 else "low"
            })
        
        # Sort by combined score and limit results
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined_results[:limit]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception as e:
            logger.warning(f"Cosine similarity calculation failed: {e}")
            return 0.0

    def _analyze_similarity(self, reference_text: str, content: str) -> Dict[str, Any]:
        """Analyze similarity between reference text and content"""
        try:
            ref_words = set(reference_text.lower().split())
            content_words = set(content.lower().split())
            
            common_words = ref_words.intersection(content_words)
            unique_words = ref_words.symmetric_difference(content_words)
            
            jaccard_similarity = len(common_words) / len(ref_words.union(content_words)) if ref_words.union(content_words) else 0
            
            return {
                "common_words_count": len(common_words),
                "common_words": list(common_words)[:10],  # First 10 common words
                "unique_words_count": len(unique_words),
                "jaccard_similarity": jaccard_similarity,
                "content_length_ratio": len(content) / len(reference_text) if reference_text else 0
            }
            
        except Exception as e:
            logger.warning(f"Similarity analysis failed: {e}")
            return {
                "common_words_count": 0,
                "common_words": [],
                "unique_words_count": 0,
                "jaccard_similarity": 0.0,
                "content_length_ratio": 0.0
            }

    # ================================
    # Helper Methods
    # ================================

    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive information about a file"""
        try:
            stat = file_path.stat()
            return {
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "extension": file_path.suffix.lower(),
                "modified_time": stat.st_mtime,
                "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "readable": os.access(file_path, os.R_OK),
                "relative_path": str(file_path.relative_to(self.documents_dir)) if self.documents_dir in file_path.parents else str(file_path),
                "detected_type": detect_file_type(file_path.name)
            }
        except Exception as e:
            logger.warning(f"Error getting file info for {file_path}: {e}")
            return {
                "name": file_path.name,
                "path": str(file_path),
                "error": str(e)
            }

    def _read_document_content(self, file_path: Path) -> str:
        """Read content from markdown files"""
        try:
            extension = file_path.suffix.lower()
            
            if extension in {".md", ".txt"}:
                return file_path.read_text(encoding='utf-8', errors='ignore')
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                return ""
                
        except Exception as e:
            logger.error(f"Error reading document {file_path}: {e}")
            return ""

    def _read_memory_content(self, character_name: str, category: str) -> str:
        """Read memory content from storage"""
        try:
            if hasattr(self.storage_manager, 'read_memory_file'):
                return self.storage_manager.read_memory_file(character_name, category)
            else:
                method_name = f"read_{category}"
                if hasattr(self.storage_manager, method_name):
                    return getattr(self.storage_manager, method_name)(character_name)
                else:
                    logger.warning(f"No read method available for {category}")
                    return ""
        except Exception as e:
            logger.warning(f"Failed to read {category} for {character_name}: {e}")
            return ""

    def _save_imported_content(self, character_name: str, category: str, content: str, source_file: str) -> bool:
        """Save imported content to memory"""
        try:
            # Add source information to the content
            timestamped_content = f"# Imported from {source_file}\n\n*Imported on {datetime.now().isoformat()}*\n\n{content}"
            
            # Try to append to existing content
            if hasattr(self.storage_manager, 'append_memory_file'):
                return self.storage_manager.append_memory_file(character_name, category, timestamped_content)
            else:
                # Fallback to writing (may overwrite existing content)
                if hasattr(self.storage_manager, 'write_memory_file'):
                    return self.storage_manager.write_memory_file(character_name, category, timestamped_content)
                else:
                    logger.error(f"No write method available for {category}")
                    return False
        except Exception as e:
            logger.error(f"Failed to save imported content for {character_name}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the recall agent"""
        return {
            "agent_name": "recall_agent",
            "memory_types": list(self.memory_types.keys()),
            "storage_type": "file_system",
            "memory_dir": str(self.memory_dir),
            "documents_dir": str(self.documents_dir),
            "tools_available": len(self.get_available_tools()),
            "stop_flag_set": self._stop_flag.is_set(),
            "supported_extensions": list(self.SUPPORTED_EXTENSIONS),
            "config_source": "markdown_config.py (dynamic folder structure)",
            "search_capabilities": {
                "semantic_search_enabled": self.semantic_search_enabled,
                "bm25_search_enabled": True,
                "string_search_enabled": True,
                "embedding_client": str(type(self.embedding_client)) if self.embedding_client else None
            }
        } 