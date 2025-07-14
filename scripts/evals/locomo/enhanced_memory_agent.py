"""
Enhanced Memory Agent for Locomo Evaluation

This agent maintains structured memory files for each character:
- event.md: Records ALL session details, missing nothing, must be accurate
- profile.md: More specific to the person, must be accurate

After each session, the agent:
1. Record all session details accurately to event.md
2. Update profile.md based on event.md and current session (accurate and person-specific)
3. Add Theory of Mind comments under each line in both files

During QA testing, both files are merged as context.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import re
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity

import dotenv
dotenv.load_dotenv()

# 确保标准输出unbuffered
import sys
if not hasattr(sys, '_stdout_line_buffering_set'):
    sys.stdout.reconfigure(line_buffering=True)
    sys._stdout_line_buffering_set = True

from personalab.llm import AzureOpenAIClient
from personalab.utils import get_logger, setup_logging
from personalab.memo.embeddings import create_embedding_manager

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)


class EnhancedMemoryAgent:
    """
    Enhanced Memory Agent
    
    Maintains memory files for each character:
    - event.md: Records ALL session details, missing nothing, must be accurate
    - profile.md: More specific to the person, must be accurate
    
    Session processing flow:
    1. Record all session details accurately to event.md
    2. Update profile.md based on event.md and current session (accurate and person-specific)
    3. Add Theory of Mind comments under each line in both files
    """
    
    def __init__(
        self,
        azure_endpoint: str = None,
        api_key: str = None,
        chat_deployment: str = "gpt-4.1-mini",
        use_entra_id: bool = False,
        api_version: str = "2024-02-01",
        memory_dir: str = "memory"
    ):
        """
        Initialize Enhanced Memory Agent
        
        Args:
            azure_endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            chat_deployment: Azure OpenAI chat deployment name
            use_entra_id: Whether to use Entra ID authentication
            api_version: Azure OpenAI API version
            memory_dir: Directory to store memory files
        """
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
        
        # Initialize embedding manager for retrieval
        self._init_embedding_manager()
        
        # Initialize BM25 and embeddings storage
        self.bm25_index = None
        self.embeddings_cache = {}
        self.memory_chunks = {}
        
        logger.info(f"Enhanced Memory Agent initialized, memory directory: {self.memory_dir}")
    
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
    
    def _init_embedding_manager(self):
        """Initialize embedding manager for retrieval"""
        try:
            self.embedding_manager = create_embedding_manager("auto")
            logger.info("Embedding manager initialized successfully")
        except Exception as e:
            logger.error(f"Embedding manager initialization failed: {e}")
            self.embedding_manager = None
    
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
    
    def _format_conversation_for_analysis(self, session_data: List[Dict], session_date: str) -> str:
        """Format conversation content for analysis"""
        formatted_lines = []
        formatted_lines.append(f"## Session Date: {session_date}")
        formatted_lines.append("")
        
        for i, utterance in enumerate(session_data, 1):
            speaker = utterance.get('speaker', 'Unknown')
            content = utterance.get('text', '')
            formatted_lines.append(f"**{speaker}**: {content}")
        
        return "\n".join(formatted_lines)
    
    def _analyze_session_for_profile(self, character_name: str, conversation: str, existing_profile: str, summarized_events: str) -> str:
        """Update character profile based on events and current session, must be accurate and specific to the person"""
        prompt = f"""
You are updating the character profile for {character_name}. Create a CONCISE, accurate profile using Markdown format.

=== CURRENT SESSION CONVERSATION ===
{conversation}

=== EVENT RECORDS TO CONSIDER ===
{summarized_events}

=== EXISTING CHARACTER PROFILE ===
{existing_profile}

=== TASK ===
Update {character_name}'s profile. Make it EXTREMELY SHORT but keep ALL key details:
- Core personality traits (brief phrases)
- Key relationships (person + role only)
- Primary interests/behaviors (minimal words)
- Important life situation (facts only)

=== REQUIREMENTS ===
1. Must be completely accurate and specific to {character_name}
2. Use EXTREMELY CONCISE language - no redundant words
3. Keep ALL important details but express them briefly
4. Use bullet points with key facts only
5. If existing information conflicts with new information, prioritize new information
6. Each bullet point should be one clear, specific fact
7. No explanatory text, just core information

=== OUTPUT FORMAT ===
Use plain text format with markdown
"""
        
        try:
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to analyze profile for {character_name}: {e}")
            return existing_profile
    
    def _analyze_session_for_events(self, character_name: str, conversation: str, session_date: str, existing_events: str) -> str:
        """Record ALL conversation details in paragraph format - every piece of information mentioned"""
        prompt = f"""
You are recording NEW event details for {character_name}. Your task is to capture EVERY detail from the conversation session - do not summarize or omit anything.

=== CONVERSATION TO ANALYZE ===
{conversation}

=== CURRENT TASK ===
Record ALL details from the conversation for {character_name} from {session_date}. Include every piece of information mentioned - do not leave out any details about people, places, times, actions, emotions, or dialogue content.

=== EXISTING EVENT RECORDS ===
{existing_events}

=== INSTRUCTIONS ===
Record EVERY detail from the conversation. Do NOT miss any information.
do not output the conversation content, just the rephraseddetails.


=== OUTPUT FORMAT ===
Record each different piece of information on a separate line, with session date prefix


Requirements:
- Every line must start with "{session_date}: "
- Each different type of content goes on its own line
- Include all specific details from the conversation
- No bullet points or special formatting, just plain text lines

Only output the NEW session records (do not include existing events):

Begin generating ONLY the new session records:
"""
        
        try:
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to analyze events for {character_name}: {e}")
            return existing_events
    
    def _add_theory_of_mind_comments(self, character_name: str, profile_content: str, events_content: str, conversation: str) -> Tuple[str, str]:
        """Add concise Theory of Mind comments under important content lines"""
        
        def add_tom_to_content(content: str, content_type: str) -> str:
            """Add Theory of Mind comments under important content lines"""
            if not content.strip():
                return content
                
            lines = content.split('\n')
            result_lines = []
            
            for line in lines:
                original_line = line
                line = line.strip()
                
                # Keep empty lines and headers as is without comments
                if not line or line.startswith('#') or line.startswith('**') or line.startswith('---'):
                    result_lines.append(original_line)
                    continue
                
                # Check if this line contains important content that needs psychological analysis
                if len(line) > 20 and any(keyword in line.lower() for keyword in 
                    ['said', 'felt', 'thought', 'decided', 'reaction', 'emotion', 'behavior', 'relationship', 'interaction']):
                    
                    # Generate Theory of Mind analysis for this important line
                    tom_prompt = f"""
For this content about {character_name}, provide a different way to express the same information and make contextual connections:

Character: {character_name}
Context: {conversation}
Content type: {content_type}
Current line: {line}

Tasks:
1. Restate the current line using different wording/expression
2. Connect it to the broader context and make reasonable associations

Requirements:
- First restate the content in a different way
- Then add contextual connections or implications
- Keep it concise (max 25 words total)
- Focus on alternative expression + contextual insight

Output:
"""
                    
                    try:
                        tom_analysis = self.llm_client.simple_chat(tom_prompt, max_tokens=16000).strip()
                        
                        # Add original content line
                        result_lines.append(original_line)
                        # Add Theory of Mind comment
                        result_lines.append(f"<!-- {tom_analysis} -->")
                        result_lines.append('')  # Empty line separator
                        
                    except Exception as e:
                        logger.error(f"Failed to generate Theory of Mind analysis for content line: {e}")
                        # If analysis fails, keep only original content
                        result_lines.append(original_line)
                else:
                    # Regular content without psychological analysis
                    result_lines.append(original_line)
            
            return '\n'.join(result_lines)
        
        try:
            # Add Theory of Mind comments to profile.md
            profile_with_tom = add_tom_to_content(profile_content, "character profile")
            
            # Add Theory of Mind comments to event.md
            events_with_tom = add_tom_to_content(events_content, "event records")
            
            return profile_with_tom, events_with_tom
            
        except Exception as e:
            logger.error(f"Theory of Mind analysis failed: {e}")
            return profile_content, events_content
    
    def process_session(self, session_data: List[Dict], session_date: str, characters: List[str]):
        """
        Process session conversation content and update all character memory files
        
        Processing flow:
        1. Generate new event content only (without existing events)
        2. Add Theory of Mind comments to new events only
        3. Manually accumulate new events to existing events
        4. Update profile based on accumulated events and current session
        5. Add Theory of Mind comments to profile
        
        Args:
            session_data: List of conversation data
            session_date: Date of conversation
            characters: List of character names
        """
        logger.info(f"Processing Session: {session_date}")
        
        # Format conversation content
        conversation = self._format_conversation_for_analysis(session_data, session_date)
        
        # Update memory files for each character
        for character in characters:
            logger.info(f"Updating memory files for {character}...")
            
            # Read existing memory files
            existing_profile = self._read_memory_file(character, "profile")
            existing_events = self._read_memory_file(character, "event")
            
            # Step 1: Generate new event content only
            logger.info(f"  Step 1: Generating new events for {character}")
            new_events = self._analyze_session_for_events(character, conversation, session_date, existing_events)
            
            # Step 2: Add Theory of Mind comments to new events only
            logger.info(f"  Step 2: Adding Theory of Mind to new events for {character}")
            _, new_events_with_tom = self._add_theory_of_mind_comments(
                character, "", new_events, conversation
            )
            
            # Step 3: Accumulate new events to existing events
            logger.info(f"  Step 3: Accumulating events for {character}")
            if existing_events.strip():
                accumulated_events = existing_events + "\n\n" + new_events_with_tom
            else:
                accumulated_events = new_events_with_tom
            
            # Step 4: Update profile based on accumulated events and current session
            logger.info(f"  Step 4: Updating {character}'s profile")
            updated_profile = self._analyze_session_for_profile(character, conversation, existing_profile, accumulated_events)
            
            # Step 5: Add Theory of Mind comments to profile
            logger.info(f"  Step 5: Adding Theory of Mind to profile for {character}")
            profile_with_tom, _ = self._add_theory_of_mind_comments(
                character, updated_profile, "", conversation
            )
            
            # Write updated memory files
            self._write_memory_file(character, "profile", profile_with_tom)
            self._write_memory_file(character, "event", accumulated_events)
        
        logger.info(f"Session {session_date} processing completed")
    
    def get_merged_context(self, characters: List[str]) -> str:
        """
        Get merged context content for QA testing
        
        Args:
            characters: List of character names
            
        Returns:
            Merged context content
        """
        context_parts = []
        
        for character in characters:
            context_parts.append(f"# Memory Information for {character}")
            context_parts.append("")
            
            # Read memory files
            profile = self._read_memory_file(character, "profile")
            events = self._read_memory_file(character, "event")
            
            # Add character profile
            if profile:
                context_parts.append("## Character Profile")
                context_parts.append(profile)
                context_parts.append("")
            
            # Add event records
            if events:
                context_parts.append("## Event Records")
                context_parts.append(events)
                context_parts.append("")
            
            context_parts.append("---")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _prepare_memory_chunks(self, characters: List[str]) -> List[Dict]:
        """
        Prepare memory chunks for retrieval
        Each line becomes a chunk, with comments attached to previous line
        """
        all_chunks = []
        
        for character in characters:
            # Process both profile and event files
            for memory_type in ["profile", "event"]:
                content = self._read_memory_file(character, memory_type)
                if not content.strip():
                    continue
                
                lines = content.split('\n')
                processed_lines = []
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        i += 1
                        continue
                    
                    # Check if next line is a TOM comment
                    combined_text = line
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('<!--'):
                        # Combine with TOM comment
                        tom_comment = lines[i + 1].strip()
                        combined_text = f"{line} {tom_comment}"
                        i += 2  # Skip both lines
                    else:
                        i += 1
                    
                    # Create chunk
                    chunk = {
                        'text': combined_text,
                        'character': character,
                        'memory_type': memory_type,
                        'original_line': line
                    }
                    all_chunks.append(chunk)
        
        return all_chunks
    
    def _build_bm25_index(self, chunks: List[Dict]):
        """Build BM25 index from memory chunks"""
        if not chunks:
            self.bm25_index = None
            return
        
        # Tokenize texts for BM25
        tokenized_corpus = [chunk['text'].lower().split() for chunk in chunks]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        self.memory_chunks = {i: chunk for i, chunk in enumerate(chunks)}
        logger.info(f"Built BM25 index with {len(chunks)} chunks")
    
    def _build_embeddings(self, chunks: List[Dict]):
        """Build embeddings for memory chunks with validation"""
        if not chunks or not self.embedding_manager:
            return
        
        texts = [chunk['text'] for chunk in chunks]
        try:
            embeddings = self.embedding_manager.provider.generate_embeddings_batch(texts)
            
            # Validate and store only valid embeddings
            self.embeddings_cache = {}
            valid_count = 0
            
            for i, emb in enumerate(embeddings):
                embedding_array = np.array(emb)
                if self._validate_embedding(embedding_array):
                    self.embeddings_cache[i] = embedding_array
                    valid_count += 1
                else:
                    logger.warning(f"Invalid embedding for chunk {i}, skipping")
            
            logger.info(f"Built {valid_count} valid embeddings out of {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to build embeddings: {e}")
            self.embeddings_cache = {}
    
    def _bm25_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search using BM25"""
        if not self.bm25_index or not self.memory_chunks:
            return []
        
        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        
        for idx in top_indices:
            if idx in self.memory_chunks and scores[idx] > 0:
                chunk = self.memory_chunks[idx].copy()
                chunk['bm25_score'] = float(scores[idx])
                results.append(chunk)
        
        return results
    
    def _validate_embedding(self, embedding: np.ndarray) -> bool:
        """Validate an embedding vector for safe mathematical operations"""
        if embedding is None or len(embedding) == 0:
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            return False
        
        # Check for zero vector (would cause division by zero in cosine similarity)
        if np.allclose(embedding, 0, atol=1e-10):
            return False
        
        return True
    
    def _calculate_robust_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity with robust handling of edge cases"""
        try:
            # Calculate norms
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # Check for zero norms
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate dot product
            dot_product = np.dot(vec1, vec2)
            
            # Check for overflow/underflow
            if np.isnan(dot_product) or np.isinf(dot_product):
                return 0.0
            
            # Calculate similarity
            similarity = dot_product / (norm1 * norm2)
            
            # Clamp to valid range [-1, 1]
            similarity = np.clip(similarity, -1.0, 1.0)
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    def _embedding_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search using embeddings with robust similarity calculation"""
        if not self.embeddings_cache or not self.embedding_manager:
            return []
        
        try:
            # Generate query embedding
            query_embedding = np.array(self.embedding_manager.provider.generate_embedding(query))
            
            # Validate query embedding
            if not self._validate_embedding(query_embedding):
                logger.warning("Invalid query embedding, skipping embedding search")
                return []
            
            # Calculate similarities
            similarities = {}
            for idx, chunk_embedding in self.embeddings_cache.items():
                # Validate chunk embedding
                if not self._validate_embedding(chunk_embedding):
                    continue
                    
                # Calculate robust cosine similarity
                similarity = self._calculate_robust_cosine_similarity(query_embedding, chunk_embedding)
                if similarity is not None:
                    similarities[idx] = similarity
            
            # Get top-k results
            top_indices = sorted(similarities.keys(), key=lambda x: similarities[x], reverse=True)[:top_k]
            results = []
            
            for idx in top_indices:
                if idx in self.memory_chunks and similarities[idx] > 0.1:  # Threshold
                    chunk = self.memory_chunks[idx].copy()
                    chunk['embedding_score'] = float(similarities[idx])
                    results.append(chunk)
            
            return results
        
        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []
    
    def _retrieve_relevant_chunks(self, question: str, characters: List[str], top_k: int = 20) -> Tuple[str, List[Dict]]:
        """
        Retrieve relevant memory chunks using both BM25 and embedding search
        Returns both context string and detailed results for display
        """
        # Prepare memory chunks
        chunks = self._prepare_memory_chunks(characters)
        if not chunks:
            return self.get_merged_context(characters), []
        
        # Build indices
        self._build_bm25_index(chunks)
        self._build_embeddings(chunks)
        
        # Perform searches
        bm25_results = self._bm25_search(question, top_k//2)
        embedding_results = self._embedding_search(question, top_k//2)
        
        # Combine and deduplicate results
        all_results = {}
        
        # Add BM25 results
        for result in bm25_results:
            key = f"{result['character']}_{result['memory_type']}_{result['original_line']}"
            if key not in all_results:
                all_results[key] = result
                all_results[key]['retrieval_method'] = 'bm25'
        
        # Add embedding results
        for result in embedding_results:
            key = f"{result['character']}_{result['memory_type']}_{result['original_line']}"
            if key not in all_results:
                all_results[key] = result
                all_results[key]['retrieval_method'] = 'embedding'
            else:
                # Mark as found by both methods
                all_results[key]['retrieval_method'] = 'both'
        
        # Sort by relevance (prioritize 'both', then by scores)
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: (
                x['retrieval_method'] == 'both',
                x.get('bm25_score', 0) + x.get('embedding_score', 0)
            ),
            reverse=True
        )
        
        # Build retrieved context
        retrieved_lines = []
        for result in sorted_results[:top_k]:
            retrieved_lines.append(f"[{result['character']} {result['memory_type']}] {result['text']}")
        
        if retrieved_lines:
            logger.info(f"Retrieved {len(retrieved_lines)} relevant chunks using BM25 and embedding search")
            return "\n".join(retrieved_lines), sorted_results[:top_k]
        else:
            # Fallback to full context
            logger.info("No relevant chunks found, using full context")
            return self.get_merged_context(characters), []

    def answer_question(self, question: str, characters: List[str], show_retrieved: bool = True) -> str:
        """
        Answer question based on memory files using retrieval (BM25 + embeddings)
        
        Args:
            question: Question to answer
            characters: List of character names
            show_retrieved: Whether to display retrieved content
            
        Returns:
            Answer content with optional retrieved content display
        """
        # Retrieve relevant context using BM25 and embedding search
        context, retrieved_results = self._retrieve_relevant_chunks(question, characters)
        
        # Display retrieved content if requested
        output_lines = []
        if show_retrieved and retrieved_results:
            output_lines.append("=" * 60)
            output_lines.append("📍 RETRIEVED MEMORY CONTENT")
            output_lines.append("=" * 60)
            
            for i, result in enumerate(retrieved_results, 1):
                # Extract method info
                method = result.get('retrieval_method', 'unknown')
                bm25_score = result.get('bm25_score', 0)
                embedding_score = result.get('embedding_score', 0)
                
                # Format score display
                score_info = []
                if bm25_score > 0:
                    score_info.append(f"BM25: {bm25_score:.3f}")
                if embedding_score > 0:
                    score_info.append(f"Embedding: {embedding_score:.3f}")
                score_str = f" ({', '.join(score_info)})" if score_info else ""
                
                output_lines.append(f"\n[{i}] {result['character']} ({result['memory_type']}) - {method}{score_str}")
                output_lines.append(f"Content: {result['text']}")
            
            output_lines.append("\n" + "=" * 60)
            output_lines.append("🤖 AI RESPONSE")
            output_lines.append("=" * 60)
        
        # Build answer prompt
        prompt = f"""
Answer the question based on the following retrieved character memory information.

Retrieved Memory Information:
{context}

Question: {question}

Please answer the question accurately based on the retrieved memory information. If there is insufficient information to answer the question, please specify what information is missing.

Answer:
"""
        
        try:
            response = self.llm_client.simple_chat(prompt, max_tokens=16000)
            if show_retrieved and retrieved_results:
                output_lines.append(response.strip())
                return "\n".join(output_lines)
            else:
                return response.strip()
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return "Sorry, unable to answer this question."
    
    def has_memory_files(self, characters: List[str]) -> bool:
        """
        Check if memory files exist for any of the specified characters
        
        Args:
            characters: List of character names to check
            
        Returns:
            True if any memory files exist, False otherwise
        """
        for character in characters:
            for memory_type in ["profile", "event"]:
                file_path = self._get_memory_file_path(character, memory_type)
                if file_path.exists() and file_path.stat().st_size > 0:
                    return True
        return False
    
    def list_available_characters(self) -> List[str]:
        """
        List all characters that have memory files
        
        Returns:
            List of character names with existing memory files
        """
        characters = set()
        for file_path in self.memory_dir.glob("*_*.md"):
            if file_path.is_file() and file_path.stat().st_size > 0:
                # Extract character name from filename (e.g., "caroline_profile.md" -> "caroline")
                filename = file_path.stem
                if "_" in filename:
                    character_name = filename.rsplit("_", 1)[0]
                    characters.add(character_name)
        return sorted(list(characters))
    
    def start_qa_mode(self, characters: List[str] = None):
        """
        Start interactive QA mode using existing memory files
        
        Args:
            characters: List of character names, if None will auto-detect from memory files
        """
        if characters is None:
            characters = self.list_available_characters()
        
        if not characters:
            print("❌ No memory files found. Please process some sessions first.")
            return
        
        print("=" * 60)
        print("🧠 ENHANCED MEMORY AGENT - QA MODE")
        print("=" * 60)
        print(f"📂 Available characters: {', '.join(characters)}")
        print("💡 Type 'quit' or 'exit' to end the session")
        print("💡 Type 'show context' to display all memory content")
        print("💡 Type 'list characters' to see available characters")
        print("=" * 60)
        
        while True:
            try:
                question = input("\n🤔 Question: ").strip()
                
                if question.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                elif question.lower() == 'show context':
                    print("\n📖 Complete Memory Context:")
                    print("-" * 40)
                    print(self.get_merged_context(characters))
                elif question.lower() == 'list characters':
                    print(f"\n👥 Available characters: {', '.join(characters)}")
                elif question:
                    print("\n🔍 Retrieving relevant memories...")
                    answer = self.answer_question(question, characters, show_retrieved=True)
                    print(f"\n{answer}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in QA mode: {e}")
                print(f"❌ Error: {e}")
    
    def clear_memory(self, characters: List[str]):
        """Clear memory files for specified characters"""
        for character in characters:
            for memory_type in ["profile", "event"]:
                file_path = self._get_memory_file_path(character, memory_type)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleared {character}'s {memory_type}.md") 