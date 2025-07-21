"""
RecallAgent for MemU Memory System

A simple workflow for intelligent memory retrieval based on markdown configurations.
Handles context=all (full content) and context=rag (search with limitations) based on config.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import math
from collections import defaultdict, Counter
import json

from ..llm import BaseLLMClient
from ..utils import get_logger
from .file_manager import MemoryFileManager
from .embeddings import get_default_embedding_client
from ..config.markdown_config import get_config_manager

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
    Simple workflow for intelligent memory retrieval.
    
    Core functionality:
    1. Read markdown configs to understand context and rag_length settings
    2. Load full context for context=all documents  
    3. Search context=rag documents with embedding + BM25 + string matching
    4. Deduplicate and return organized results
    """
    
    def __init__(self, memory_dir: str = "memory"):
        """
        Initialize Recall Agent
        
        Args:
            memory_dir: Directory where memory files are stored
        """
        self.memory_dir = Path(memory_dir)
        
        # Initialize config manager
        self.config_manager = get_config_manager()
        self.memory_types = self.config_manager.get_file_types_mapping()
        
        # Initialize file-based storage manager
        self.storage_manager = MemoryFileManager(memory_dir)
        
        # Initialize embedding client for semantic search
        try:
            self.embedding_client = get_default_embedding_client()
            self.semantic_search_enabled = True
            logger.info("Semantic search enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding client: {e}. Semantic search disabled.")
            self.embedding_client = None
            self.semantic_search_enabled = False
        
        logger.info(f"Recall Agent initialized with memory directory: {self.memory_dir}")

    def search(
        self,
        character_name: str,
        query: str,
        max_results: int = 10,
        rag: bool = True
    ) -> Dict[str, Any]:
        """
        Main workflow: Intelligent memory search based on markdown configs
        
        Args:
            character_name: Character name
            query: Search query  
            max_results: Maximum number of RAG results
            rag: Whether to perform RAG search (if False, only return context=all content)
            
        Returns:
            Dict with full_context_content and rag_search_results
        """
        try:
            # Step 1: Get all config settings
            all_configs = self.config_manager.get_all_context_configs()
            
            # Separate context=all and context=rag types
            all_context_types = []
            rag_context_types = []
            
            for file_type, config in all_configs.items():
                if config["context"] == "all":
                    all_context_types.append(file_type)
                else:
                    rag_context_types.append(file_type)
            
            logger.info(f"Context=all types: {all_context_types}")
            logger.info(f"Context=rag types: {rag_context_types}")
            logger.info(f"RAG search enabled: {rag}")
            
            # Step 2: Load all context=all content
            full_context_content = self._load_full_context_content(character_name, all_context_types)
            
            # Step 3: Search context=rag content (only if rag=True)
            rag_search_results = []
            deduplicated_rag_results = []
            
            if rag:
                rag_search_results = self._search_rag_content(character_name, rag_context_types, query, max_results)
                
                # Step 4: Deduplicate RAG results against full context
                full_content_texts = [item["content"] for item in full_context_content]
                deduplicated_rag_results = self._deduplicate_with_full_context(rag_search_results, full_content_texts)
            else:
                logger.info("RAG search skipped (rag=False)")
            
            # Step 5: Return organized results
            return {
                "success": True,
                "character_name": character_name,
                "query": query,
                "rag_enabled": rag,
                "full_context_content": full_context_content,
                "rag_search_results": deduplicated_rag_results,
                "total_full_context": len(full_context_content),
                "total_rag_results": len(deduplicated_rag_results),
                "config_info": {
                    "all_context_types": all_context_types,
                    "rag_context_types": rag_context_types,
                    "rag_length_configs": {
                        file_type: self.config_manager.get_rag_length(file_type)
                        for file_type in rag_context_types
                    } if rag else {}
                },
                "semantic_search_enabled": self.semantic_search_enabled,
                "message": f"Found {len(full_context_content)} full context items" + 
                          (f" and {len(deduplicated_rag_results)} RAG results" if rag else " (RAG disabled)")
            }
            
        except Exception as e:
            logger.error(f"Error in memory search for {character_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_name": character_name,
                "query": query,
                "rag_enabled": rag
            }

    def _load_full_context_content(self, character_name: str, all_context_types: List[str]) -> List[Dict]:
        """Load complete content for context=all types"""
        full_context_content = []
        
        for file_type in all_context_types:
            content = self._read_memory_content(character_name, file_type)
            if content:
                full_context_content.append({
                    "category": file_type,
                    "content": content,
                    "content_type": "full_context",
                    "length": len(content),
                    "lines": len(content.split('\n'))
                })
        
        return full_context_content

    def _search_rag_content(
        self, 
        character_name: str, 
        rag_context_types: List[str], 
        query: str, 
        max_results: int
    ) -> List[Dict]:
        """Search context=rag content with length limitations"""
        if not rag_context_types:
            return []
        
        # Prepare documents for search
        rag_documents = []
        rag_metadata = []
        
        for file_type in rag_context_types:
            content = self._read_memory_content(character_name, file_type)
            if content:
                # Apply rag_length limitation
                rag_length = self.config_manager.get_rag_length(file_type)
                
                if rag_length == -1:
                    processed_content = content
                else:
                    lines = content.split('\n')
                    processed_content = '\n'.join(lines[:rag_length])
                
                rag_documents.append(processed_content)
                rag_metadata.append({
                    "category": file_type,
                    "character": character_name,
                    "content_length": len(processed_content),
                    "original_length": len(content),
                    "rag_length": rag_length,
                    "truncated": rag_length != -1 and len(content.split('\n')) > rag_length
                })
        
        if not rag_documents:
            return []
        
        # Execute multi-method search
        search_results = []
        
        # Semantic Search
        if self.semantic_search_enabled:
            semantic_results = self._semantic_search(query, rag_documents, rag_metadata)
            search_results.extend(semantic_results)
        
        # BM25 Search
        bm25_results = self._bm25_search(query, rag_documents, rag_metadata)
        search_results.extend(bm25_results)
        
        # String Search
        string_results = self._string_search(query, rag_documents, rag_metadata)
        search_results.extend(string_results)
        
        # Combine and return top results
        return self._combine_search_results(search_results, max_results)

    def _semantic_search(self, query: str, documents: List[str], metadata: List[Dict]) -> List[Dict]:
        """Perform semantic search using stored memory embeddings"""
        if not self.semantic_search_enabled:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_client.embed(query)
            
            results = []
            embeddings_dir = self.memory_dir / "embeddings"
            
            # Group metadata by character for efficient lookup
            char_categories = defaultdict(list)
            for meta in metadata:
                char_categories[meta["character"]].append(meta["category"])
            
            # Search stored embeddings for each character/category
            for character_name, categories in char_categories.items():
                char_embeddings_dir = embeddings_dir / character_name
                
                if not char_embeddings_dir.exists():
                    logger.debug(f"No embeddings directory found for {character_name}")
                    continue
                
                for category in categories:
                    embeddings_file = char_embeddings_dir / f"{category}_embeddings.json"
                    
                    if embeddings_file.exists():
                        try:
                            with open(embeddings_file, 'r', encoding='utf-8') as f:
                                embeddings_data = json.load(f)
                            
                            # Search through stored embeddings
                            for emb_data in embeddings_data.get("embeddings", []):
                                similarity = self._cosine_similarity(query_embedding, emb_data["embedding"])
                                
                                if similarity > 0.1:  # Minimum threshold for semantic similarity
                                    results.append({
                                        "content": emb_data["text"] + "..." if len(emb_data["text"]) > 500 else emb_data["text"],
                                        "full_content_length": len(emb_data["text"]),
                                        "semantic_score": similarity,
                                        "search_method": "semantic",
                                        "category": category,
                                        "character": character_name,
                                        "item_id": emb_data.get("item_id", ""),
                                        "memory_id": emb_data.get("memory_id", ""),
                                        "line_number": emb_data.get("line_number", 0),
                                        "metadata": emb_data.get("metadata", {})
                                    })
                        
                        except Exception as e:
                            logger.warning(f"Failed to load embeddings for {character_name}:{category}: {e}")
                    else:
                        logger.debug(f"No embeddings file found for {character_name}:{category}")
            
            logger.debug(f"Semantic search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    def _bm25_search(self, query: str, documents: List[str], metadata: List[Dict]) -> List[Dict]:
        """Perform BM25 search for relevance ranking"""
        try:
            bm25 = BM25(documents)
            scores = bm25.get_scores(query)
            
            results = []
            max_score = max(scores) if scores else 1.0
            
            for i, (doc, meta, score) in enumerate(zip(documents, metadata, scores)):
                if score > 0:
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
                
                exact_match = 1.0 if query_lower in doc_lower else 0.0
                
                doc_words = set(doc_lower.split())
                word_overlap = len(query_words.intersection(doc_words)) / len(query_words) if query_words else 0
                
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
        
        for result in search_results:
            category = result["category"]
            method = result["search_method"]
            
            category_results[category]["methods_used"].append(method)
            category_results[category]["content"] = result["content"]
            category_results[category]["category"] = result["category"]
            category_results[category]["character"] = result["character"]
            category_results[category]["full_content_length"] = result["full_content_length"]
            
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
            combined_score = (
                data["semantic_score"] * 0.5 +
                data["bm25_score"] * 0.3 +
                data["string_score"] * 0.2
            )
            
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
        
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined_results[:limit]

    def _deduplicate_with_full_context(
        self, 
        rag_results: List[Dict], 
        full_content_list: List[str],
        similarity_threshold: float = 0.8
    ) -> List[Dict]:
        """Remove RAG results that are too similar to full context content"""
        if not rag_results or not full_content_list:
            return rag_results
        
        deduplicated_results = []
        
        for rag_result in rag_results:
            rag_content = rag_result.get("content", "")
            is_duplicate = False
            
            for full_content in full_content_list:
                # String containment check
                if len(rag_content) > 100:
                    rag_snippet = rag_content[:200]
                    if rag_snippet in full_content:
                        is_duplicate = True
                        break
                
                # Word overlap check
                rag_words = set(rag_content.lower().split())
                full_words = set(full_content.lower().split())
                
                if rag_words and full_words:
                    overlap_ratio = len(rag_words.intersection(full_words)) / len(rag_words)
                    if overlap_ratio > similarity_threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                rag_result["deduplicated"] = True
                deduplicated_results.append(rag_result)
        
        return deduplicated_results

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

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the recall agent"""
        return {
            "agent_name": "recall_agent",
            "agent_type": "simple_workflow",
            "memory_types": list(self.memory_types.keys()),
            "memory_dir": str(self.memory_dir),
            "semantic_search_enabled": self.semantic_search_enabled,
            "config_source": "markdown_config.py",
            "main_method": "search(character_name, query, max_results, rag)"
        } 