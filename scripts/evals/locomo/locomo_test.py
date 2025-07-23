"""
Enhanced Memory Test with Specialized Agents

This test uses specialized agents:
1. MemAgent for memory management:
   - Process each session sequentially using memory management tools
   - Update character memory from conversation sessions
2. ResponseAgent for question answering:
   - Answer QA questions using character memory data
   - Provide comprehensive responses with context information
3. Display category-based accuracy statistics
"""

import json
import os
import sys
import ast
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import dotenv
dotenv.load_dotenv()

# 确保标准输出unbuffered
if not hasattr(sys, '_stdout_line_buffering_set'):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)  # type: ignore
    except (AttributeError, TypeError):
        # Fallback for older Python versions or different stdout types
        pass
    sys._stdout_line_buffering_set = True  # type: ignore

from mem_agent import MemAgent
from response_agent import ResponseAgent
from evaluate_agent import EvaluateAgent
from memu.utils import get_logger, setup_logging

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)

args_global = None

class ToolBasedMemoryTester:
    """
    Tool-based Memory Tester
    
    Uses unified MemAgent for processing Locomo data:
    1. Process sessions sequentially using MemAgent
    2. Answer QA questions using MemAgent
    3. Display category-based accuracy statistics
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        chat_deployment: str = "gpt-4.1-mini-2",
        use_entra_id: bool = False,
        api_version: str = "2024-02-01",
        memory_dir: str = "memory",
        max_workers: int = 3,
        category_filter: Optional[List[str]] = None
    ):
        """Initialize Tool-based Memory Tester"""
        # Initialize MemAgent for memory management
        self.mem_agent = MemAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        # Initialize ResponseAgent for question answering
        self.response_agent = ResponseAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        # Initialize EvaluateAgent for answer evaluation
        # Ensure azure_endpoint and api_key are not None for EvaluateAgent
        eval_azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT") or ""
        eval_api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY") or ""
        
        self.evaluate_agent = EvaluateAgent(
            azure_endpoint=eval_azure_endpoint,
            api_key=eval_api_key,
            # chat_deployment=chat_deployment,
            chat_deployment="gpt-4.1",
            use_entra_id=use_entra_id,
            api_version=api_version
            # api_version="2025-01-01-preview"
        )
        
        self.max_workers = max_workers
        self.category_filter = category_filter
        self.results = []
        self.processing_time = 0.0
        self.memory_dir = Path(memory_dir)
        
        # Initialize error log file
        self.log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.error_log_file = f"qa_error_log_{self.log_timestamp}.txt"
        self._init_error_log()
        
        logger.info(f"Tool-based Memory Tester initialized with MemAgent (memory) and ResponseAgent (QA) (max_workers={max_workers})")
        if category_filter:
            logger.info(f"Category filter enabled: {category_filter}")
        logger.info(f"QA error log file: {self.error_log_file}")

    def _init_error_log(self):
        """Initialize error log file with header"""
        try:
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                f.write(f"QA Error Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n")
                f.write("This log contains detailed information for incorrectly answered QA questions.\n\n")
        except Exception as e:
            logger.error(f"Failed to initialize error log file: {e}")

    def _get_category_error_log(self, category: str) -> str:
        """Initialize category-specific error log file with header if it doesn't exist"""
        category_log_file = f"qa_error_log_{self.log_timestamp}_CAT_{category}.txt"
        
        try:
            # Check if file already exists to avoid overwriting headers
            if not os.path.exists(category_log_file):
                with open(category_log_file, 'w', encoding='utf-8') as f:
                    f.write(f"QA Error Log - Category {category} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"This log contains detailed information for incorrectly answered QA questions in category {category}.\n\n")
            return category_log_file
        except Exception as e:
            logger.error(f"Failed to initialize category error log file for category {category}: {e}")
            return category_log_file

    def _log_qa_error(self, qa_index: int, question: str, generated_answer: str, standard_answer: str, 
                     category: str, retrieved_content: str = "", evidence: str = "", explanation: str = "", 
                     session_context: str = "", evaluation_details: Optional[Dict] = None, retrieved_events: Optional[List] = None):
        """Log detailed information for incorrect QA answers with comprehensive evaluation to both main and category-specific files"""
        
        try:
            # Build the complete error content as a string
            content_lines = []
            content_lines.append(f"\n{'='*80}")
            content_lines.append(f"QA INDEX: {qa_index + 1}")
            content_lines.append(f"CATEGORY: {category}")
            content_lines.append(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"{'='*80}\n")
            
            content_lines.append(f"QUESTION:\n{question}\n")
            
            content_lines.append(f"EVIDENCE (Referenced Conversations):\n{evidence if evidence else 'No evidence provided'}\n")
            
            content_lines.append(f"RETRIEVED CONTENT (From Memory):\n{retrieved_content if retrieved_content else 'No content retrieved'}\n")
            
            content_lines.append(f"GENERATED ANSWER:\n{generated_answer}\n")
            
            content_lines.append(f"STANDARD ANSWER:\n{standard_answer}\n")
            
            content_lines.append(f"BASIC EVALUATION EXPLANATION:\n{explanation}\n")
            
            # Add comprehensive evaluation details if available
            if evaluation_details:
                content_lines.append(f"{'='*60}")
                content_lines.append(f"COMPREHENSIVE EVALUATION RESULTS")
                content_lines.append(f"{'='*60}\n")
                
                # Answer accuracy details
                if evaluation_details.get('answer_accuracy'):
                    acc = evaluation_details['answer_accuracy']
                    content_lines.append(f"ANSWER ACCURACY:")
                    content_lines.append(f"  ✓ Correct: {acc.get('is_correct', False)}")
                    content_lines.append(f"  📝 Detailed Explanation: {acc.get('explanation', 'N/A')}\n")
                
                # Events evaluation details
                if evaluation_details.get('events_evaluation') and evaluation_details['events_evaluation'].get('success'):
                    events_eval = evaluation_details['events_evaluation']
                    content_lines.append(f"RETRIEVED EVENTS EVALUATION:")
                    content_lines.append(f"  📊 Total Events: {events_eval.get('total_events', 0)}")
                    content_lines.append(f"  ✅ Relevant Events: {events_eval.get('relevant_count', 0)}")
                    content_lines.append(f"  ❌ Irrelevant Events: {events_eval.get('irrelevant_count', 0)}")
                    content_lines.append(f"  📈 Relevance Rate: {events_eval.get('relevance_rate', 0):.2%}\n")
                    
                    # Individual event relevance details
                    event_details = events_eval.get('event_details', [])
                    if event_details:
                        content_lines.append(f"  EVENT-BY-EVENT ANALYSIS:")
                        for i, event_detail in enumerate(event_details[:5], 1):  # Show top 5
                            relevance_icon = "✅" if event_detail.get('is_relevant') else "❌"
                            content_lines.append(f"    {relevance_icon} Event {i} (Rank {event_detail.get('rank', i)}):")
                            content_lines.append(f"      Character: {event_detail.get('character', 'Unknown')}")
                            content_lines.append(f"      Event: {event_detail.get('event', '')[:100]}...")
                            content_lines.append(f"      Relevant: {event_detail.get('is_relevant', False)}")
                            content_lines.append(f"      Explanation: {event_detail.get('explanation', 'N/A')}\n")
                
                # Error analysis details
                if evaluation_details.get('error_analysis') and evaluation_details['error_analysis'].get('performed'):
                    error_analysis = evaluation_details['error_analysis']
                    content_lines.append(f"ERROR ANALYSIS:")
                    content_lines.append(f"  🔍 Error Type: {error_analysis.get('error_type', 'Unknown')}")
                    content_lines.append(f"  ⚠️ Specific Issues: {error_analysis.get('specific_issues', 'N/A')}")
                    content_lines.append(f"  🔎 Root Cause: {error_analysis.get('root_cause', 'N/A')}")
                    content_lines.append(f"  📋 Missing Information: {error_analysis.get('missing_information', 'N/A')}")
                    content_lines.append(f"  💡 Recommendations: {error_analysis.get('recommendations', 'N/A')}\n")
            
            content_lines.append(f"{'='*80}\n")
            
            # Join all content lines into a single string
            error_content = "\n".join(content_lines)
            
            # Write to main error log file
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(error_content)
            
            category_log_file = self._get_category_error_log(str(category).strip())
            with open(category_log_file, 'a', encoding='utf-8') as f:
                f.write(error_content)
                
        except Exception as e:
            logger.error(f"Failed to write to error log: {e}")

    def _get_session_context(self, conversation_data: Dict) -> str:
        """Get session context information (dates and speakers)"""
        try:
            context_lines = []
            speaker_a = conversation_data.get('speaker_a', 'Speaker A')
            speaker_b = conversation_data.get('speaker_b', 'Speaker B')
            
            context_lines.append(f"Speakers: {speaker_a} and {speaker_b}")
            
            # Find all sessions and their dates
            session_keys = [key for key in conversation_data.keys() if key.startswith('session_') and not key.endswith('_date_time')]
            session_keys.sort(key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
            
            for session_key in session_keys:
                date_key = f"{session_key}_date_time"
                session_date = conversation_data.get(date_key, "Unknown Date")
                session_data = conversation_data.get(session_key, [])
                utterance_count = len(session_data) if session_data else 0
                context_lines.append(f"{session_key}: {session_date} ({utterance_count} utterances)")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            return f"Error extracting session context: {e}"

    def _check_memory_exists(self, characters: List[str]) -> Dict[str, bool]:
        """Check if memory files exist and are non-empty for given characters"""
        memory_status = {}
        
        for character in characters:
            profile_path = self.memory_dir / f"{character}_profile.txt"
            events_path = self.memory_dir / f"{character}_events.txt"
            
            profile_exists = profile_path.exists() and profile_path.stat().st_size > 0
            events_exists = events_path.exists() and events_path.stat().st_size > 0
            
            # Character has memory if either profile or events exist and are non-empty
            memory_status[character] = profile_exists or events_exists
        
        return memory_status

    def _process_single_session(self, session_data: Tuple[str, List[Dict], str], characters: List[str]) -> Dict:
        """Process a single session using MemAgent"""
        session_key, session_utterances, session_date = session_data
        
        try:
            logger.info(f"Processing {session_key} with {len(session_utterances)} utterances on {session_date}")
            
            _use_image = getattr(args_global, 'use_image', False)
            # Directly call update_character_memory function
            update_result = self.mem_agent.update_character_memory(
                session_data=session_utterances,
                session_date=session_date,
                characters=characters,
                use_image=_use_image
            )
            
            if update_result.get("success", False):
                logger.info(f"Successfully processed {session_key}")
                return {
                    'session_key': session_key,
                    'success': True,
                    'utterances_count': len(session_utterances),
                    'session_date': session_date
                }
            else:
                error_msg = update_result.get('error', 'Unknown error')
                logger.error(f"Failed to process {session_key}: {error_msg}")
                return {
                    'session_key': session_key,
                    'success': False,
                    'error': error_msg,
                    'utterances_count': len(session_utterances),
                    'session_date': session_date
                }
                
        except Exception as e:
            logger.error(f"Exception processing {session_key}: {e}")
            return {
                'session_key': session_key,
                'success': False,
                'error': str(e),
                'utterances_count': len(session_utterances) if session_utterances else 0,
                'session_date': session_date
            }

    def _process_sessions_parallel(self, sessions: List[Tuple[str, List[Dict], str]], characters: List[str], max_workers: int = 3) -> List[Dict]:
        """Process multiple sessions in parallel"""
        if not sessions:
            return []
        
        session_results = []
        completed_count = 0
        total_sessions = len(sessions)
        
        logger.info(f"Starting parallel processing of {total_sessions} sessions with {max_workers} workers")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all session processing tasks
            future_to_session = {
                executor.submit(self._process_single_session, session, characters): session[0] 
                for session in sessions
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_session):
                session_key = future_to_session[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    session_results.append(result)
                    status = "✓" if result['success'] else "✗"
                    logger.info(f"[{completed_count}/{total_sessions}] {status} {session_key} completed")
                except Exception as e:
                    logger.error(f"[{completed_count}/{total_sessions}] ✗ {session_key} generated exception: {e}")
                    session_results.append({
                        'session_key': session_key,
                        'success': False,
                        'error': str(e),
                        'utterances_count': 0,
                        'session_date': 'Unknown'
                    })

        for character_name in characters:
            self.mem_agent.clean_profile(character_name)
        
        # Sort results by session key for consistent output
        session_results.sort(key=lambda x: x['session_key'])
        
        logger.info(f"Parallel processing completed: {sum(1 for r in session_results if r['success'])}/{total_sessions} sessions successful")
        
        return session_results

    def _build_retrieved_content_summary(self, answer_result: Dict) -> str:
        """Build detailed retrieved content summary from ResponseAgent result"""
        context_used = answer_result.get("context_used", {})
        retrieved_contents = []
        
        characters_searched = context_used.get("characters_searched", [])
        search_keywords = context_used.get("search_keywords", [])
        
        # Get actual retrieved content details from ResponseAgent
        # final_content = answer_result.get("final_content", [])
        final_content = answer_result.get("retrieved_events", [])
        retrieved_events = answer_result.get("retrieved_events", [])
        iteration_log = answer_result.get("iteration_log", [])
        total_events_found = context_used.get("total_events_found", 0)
        content_pieces = context_used.get("content_pieces", 0)
        
        # Add summary information (no profiles, events only)
        if total_events_found > 0:
            retrieved_contents.append(f"Relevant Events Found: {total_events_found} events")
            if search_keywords:
                retrieved_contents.append(f"Search Keywords: {', '.join(search_keywords)}")
        
        if characters_searched:
            retrieved_contents.append(f"Characters Searched: {', '.join(characters_searched)}")
        
        if content_pieces > 0:
            retrieved_contents.append(f"Content Pieces Retrieved: {content_pieces}")
        
        # Add actual retrieved content from final_content
        if final_content:
            retrieved_contents.append("\n--- ACTUAL RETRIEVED CONTENT ---")
            for i, content in enumerate(final_content[:20], 1):  # Show top 20 content pieces
                if isinstance(content, dict):
                    content_text = content.get('text', content.get('event', str(content)))
                    character = content.get('character', 'Unknown')
                    retrieved_contents.append(f"\n{i}. {content_text}")
                    
                    # Add scoring information if available
                    string_score = content.get('string_score', 0.0)
                    bm25_score = content.get('bm25_score', 0.0)
                    semantic_score = content.get('semantic_score', 0.0)
                    combined_score = content.get('combined_score', 0.0)
                    retrieved_contents.append(f"    Scores - String: {string_score:.3f}, BM25: {bm25_score:.3f}, Semantic: {semantic_score:.3f}, Combined: {combined_score:.3f}")
                else:
                    retrieved_contents.append(f"\n{i}. {content}")
        
        # Add actual retrieved events content
        # if retrieved_events:
        #     retrieved_contents.append("\n--- ACTUAL RETRIEVED EVENTS ---")
        #     for i, event in enumerate(retrieved_events[:15], 1):  # Show top 15 events
        #         if isinstance(event, dict):
        #             event_text = event.get('event', event.get('text', str(event)))
        #             character = event.get('character', 'Unknown')
        #             retrieved_contents.append(f"\nEvent {i}: [{character}] {event_text}")
        #         else:
        #             retrieved_contents.append(f"\nEvent {i}: {event}")
        
        # Add iteration log for debugging retrieval process
        if iteration_log:
            retrieved_contents.append("\n--- RETRIEVAL ITERATIONS ---")
            for i, iteration in enumerate(iteration_log, 1):
                if isinstance(iteration, dict):
                    iteration_summary = iteration.get('summary', str(iteration))
                    retrieved_contents.append(f"\nIteration {i}: {iteration_summary}")
                else:
                    retrieved_contents.append(f"\nIteration {i}: {iteration}")
        
        return "\n".join(retrieved_contents) if retrieved_contents else "ResponseAgent provided direct answer"

    def _process_single_qa(self, qa_data: Tuple[str, str, str, int], characters: List[str], evidence_content: str = "", conversation_data: Optional[Dict] = None) -> Dict:
        """Process a single QA question using ResponseAgent"""
        question, answer, category, qa_index = qa_data
        
        try:
            logger.info(f"[QA {qa_index+1}] Answering question in category '{category}': {question[:100]}...")
            
            use_profile = getattr(args_global, 'use_profile', "none")
            
            # Use ResponseAgent to answer the question directly
            answer_result = self.response_agent.execute_tool("answer_question", 
                                                             question=question,
                                                             characters=characters,
                                                             use_profile=use_profile)
            
            # Extract information from ResponseAgent result
            if answer_result.get("success", False):
                generated_answer = answer_result.get("answer", "No answer generated")
                retrieved_content = self._build_retrieved_content_summary(answer_result)
                search_results_for_eval = answer_result.get("retrieved_events", [])                
            else:
                error_msg = answer_result.get('error', 'Failed to generate answer')
                generated_answer = f"Error: {error_msg}"
                retrieved_content = f"Error occurred during answer generation: {error_msg}"
                search_results_for_eval = []
            
            # Evaluate the answer
            evaluation = self._evaluate_answer(question, generated_answer, answer)
            
            result = {
                'qa_index': qa_index,
                'question': question,
                'generated_answer': generated_answer,
                'standard_answer': answer,
                'category': category,
                'is_correct': evaluation['is_correct'],
                'explanation': evaluation['explanation'],
                'retrieved_content': retrieved_content,
                'evidence': evidence_content
            }
            
            # Log error details if answer is incorrect
            analyze_on = getattr(args_global, 'analyze_on', "wrong")
            if analyze_on == "all" or (analyze_on == "wrong" and not evaluation['is_correct']):
                # For comprehensive evaluation, we'll use the full comprehensive evaluation
                # Since ResponseAgent abstracts the detailed retrieval process
                comprehensive_evaluation = None
                try:
                    # Perform comprehensive evaluation using EvaluateAgent
                    comprehensive_evaluation = self.evaluate_agent.comprehensive_evaluation(
                        question=question,
                        generated_answer=generated_answer,
                        standard_answer=answer,
                        retrieved_events=search_results_for_eval
                    )
                    
                    if comprehensive_evaluation.get('success'):
                        logger.info(f"[QA {qa_index+1}] Error analysis completed")
                    else:
                        logger.warning(f"[QA {qa_index+1}] Error analysis failed: {comprehensive_evaluation.get('error', 'Unknown error')}")
                        comprehensive_evaluation = None
                        
                except Exception as e:
                    logger.error(f"[QA {qa_index+1}] Failed to perform error analysis: {e}")
                    comprehensive_evaluation = None
                
                session_context = self._get_session_context(conversation_data) if conversation_data else ""
                self._log_qa_error(
                    qa_index=qa_index,
                    question=question,
                    generated_answer=generated_answer,
                    standard_answer=answer,
                    category=category,
                    retrieved_content=retrieved_content,
                    evidence=evidence_content,
                    explanation=evaluation['explanation'],
                    session_context=session_context,
                    evaluation_details=comprehensive_evaluation,
                    retrieved_events=search_results_for_eval
                )
                logger.warning(f"[QA {qa_index+1}] ✗ Incorrect answer logged to error file with comprehensive evaluation")
            
            status = "✓" if evaluation['is_correct'] else "✗"
            logger.info(f"[QA {qa_index+1}] {status} Question completed (Category: {category})")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA {qa_index+1}] Exception processing question: {e}")
            
            # Log exception details
            error_result = {
                'qa_index': qa_index,
                'question': question,
                'generated_answer': f"Error: {e}",
                'standard_answer': answer,
                'category': category,
                'is_correct': False,
                'explanation': f"Processing failed: {e}",
                'retrieved_content': f"Exception prevented retrieval: {e}",
                'evidence': evidence_content
            }
            
            session_context = self._get_session_context(conversation_data) if conversation_data else ""
            self._log_qa_error(
                qa_index=qa_index,
                question=question,
                generated_answer=f"Error: {e}",
                standard_answer=answer,
                category=category,
                retrieved_content=f"Exception prevented retrieval: {e}",
                evidence=evidence_content,
                explanation=f"Processing failed: {e}",
                session_context=session_context,
                evaluation_details=None,  # No evaluation details for exceptions
                retrieved_events=None
            )
            
            return error_result

    def _map_evidence_to_conversation(self, evidence_refs: List[str], conversation_data: Dict) -> str:
        """Map evidence references (like 'D1:3') to actual conversation content"""
        evidence_conversations = []
        
        for ref in evidence_refs:
            try:
                # Parse reference like 'D1:3' -> day=1, utterance=3
                if ':' in ref and ref.startswith('D'):
                    parts = ref.split(':')
                    day_part = parts[0][1:]  # Remove 'D' prefix
                    utterance_id = int(parts[1])
                    
                    # Find the session data
                    session_key = f"session_{day_part}"
                    if session_key in conversation_data:
                        session_data = conversation_data[session_key]
                        
                        # Get session date/time for context
                        date_key = f"{session_key}_date_time"
                        session_time = conversation_data.get(date_key, "Unknown Date")
                        
                        # Find the utterance with matching dia_id
                        target_dia_id = ref
                        for utterance in session_data:
                            if isinstance(utterance, dict) and utterance.get('dia_id') == target_dia_id:
                                speaker = utterance.get('speaker', 'Unknown')
                                text = utterance.get('text', '')
                                # Include session time in evidence
                                evidence_conversations.append(f"[{session_time}] {speaker}: {text}")
                                break
                        else:
                            evidence_conversations.append(f"[Evidence {ref} not found in {session_time}]")
                    else:
                        evidence_conversations.append(f"[Session {session_key} not found]")
                else:
                    evidence_conversations.append(f"[Invalid evidence format: {ref}]")
                    
            except Exception as e:
                evidence_conversations.append(f"[Error parsing evidence {ref}: {e}]")
        
        return "\n".join(evidence_conversations) if evidence_conversations else "No evidence provided"

    def _process_qa_parallel(self, qa_data: List[Dict], characters: List[str], conversation_data: Optional[Dict] = None, max_workers: int = 3) -> List[Dict]:
        """Process multiple QA questions in parallel"""
        if not qa_data:
            return []
        
        question_results = []
        completed_count = 0
        total_questions = len(qa_data)
        
        logger.info(f"Starting parallel processing of {total_questions} QA questions with {max_workers} workers")
        
        # Prepare QA items with index for processing, skip items missing required fields
        qa_items = []
        skipped_count = 0
        category_filtered_count = 0
        for i, qa_item in enumerate(qa_data):
            if 'question' in qa_item and 'answer' in qa_item:
                # Check category filter
                if self.category_filter:
                    item_category = str(qa_item.get('category', 'Unknown'))
                    if item_category not in self.category_filter:
                        category_filtered_count += 1
                        # skipped_count += 1
                        continue
                
                # Extract evidence and map to conversation content
                evidence_refs = qa_item.get('evidence', [])
                evidence_content = ""
                if evidence_refs and conversation_data:
                    evidence_content = self._map_evidence_to_conversation(evidence_refs, conversation_data)
                
                qa_items.append((qa_item['question'], qa_item['answer'], qa_item.get('category', 'Unknown'), i, evidence_content))
            else:
                skipped_count += 1
                logger.warning(f"Skipping QA item {i}: missing required fields (question or answer)")
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} QA items due to missing fields, processing {len(qa_items)} valid items")
        
        if category_filtered_count > 0:
            logger.info(f"Filtered out {category_filtered_count} QA items due to category filter {self.category_filter}, processing {len(qa_items)} items")
        
        if not qa_items:
            logger.warning("No valid QA items to process")
            return []
        
        logger.info(f"Caching event semantic embeddings for characters: {characters}")
        self.response_agent.cache_events_semantic(characters)
        if getattr(args_global, 'use_profile', "none") == "search":
            logger.info(f"Caching profile semantic embeddings for characters: {characters}")
            self.response_agent.cache_profile_semantic(characters)
        logger.info("Caching completed")

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all QA processing tasks and store qa_item info for exception handling
            future_to_qa_info = {}
            for qa_item in qa_items:
                future = executor.submit(self._process_single_qa_with_evidence, qa_item, characters, conversation_data)
                qa_index = qa_item[3]  # qa_index is at position 3
                evidence_content = qa_item[4]  # evidence_content is at position 4
                question = qa_item[0]  # question is at position 0
                answer = qa_item[1]  # answer is at position 1
                category = qa_item[2]  # category is at position 2
                
                future_to_qa_info[future] = {
                    'qa_index': qa_index,
                    'question': question,
                    'answer': answer,
                    'category': category,
                    'evidence': evidence_content
                }
            
            # Collect results as they complete
            for future in as_completed(future_to_qa_info):
                qa_info = future_to_qa_info[future]
                qa_index = qa_info['qa_index']
                completed_count += 1
                
                try:
                    result = future.result()
                    question_results.append(result)
                    status = "✓" if result['is_correct'] else "✗"
                    logger.info(f"[{completed_count}/{len(qa_items)}] {status} QA {qa_index+1} completed - Category: {result['category']}")
                except Exception as e:
                    logger.error(f"[{completed_count}/{len(qa_items)}] ✗ QA {qa_index+1} generated exception: {e}")
                    question_results.append({
                        'qa_index': qa_index,
                        'question': qa_info['question'],
                        'generated_answer': f"Error: {e}",
                        'standard_answer': qa_info['answer'],
                        'category': qa_info['category'],
                        'is_correct': False,
                        'explanation': f"Exception: {e}",
                        'retrieved_content': f"Exception: {e}",
                        'evidence': qa_info['evidence']
                    })
        
        # Sort results by qa_index for consistent output
        question_results.sort(key=lambda x: x['qa_index'])
        
        successful_qa = sum(1 for r in question_results if r['is_correct'])
        processed_qa = len(question_results)
        logger.info(f"Parallel QA processing completed: {successful_qa}/{processed_qa} questions answered correctly")
        
        return question_results

    def _process_single_qa_with_evidence(self, qa_data: Tuple[str, str, str, int, str], characters: List[str], conversation_data: Optional[Dict] = None) -> Dict:
        """Process a single QA question with evidence content"""
        question, answer, category, qa_index, evidence_content = qa_data
        
        # Call the processing method with evidence content and conversation data
        return self._process_single_qa((question, answer, category, qa_index), characters, evidence_content, conversation_data)

    def _extract_session_data(self, conversation_data: Dict) -> List[Tuple[str, List[Dict], str]]:
        """Extract session information from conversation data"""
        sessions = []
        
        # Extract speaker names
        speaker_a = conversation_data.get('speaker_a', 'Speaker A')
        speaker_b = conversation_data.get('speaker_b', 'Speaker B')
        
        # Find all sessions
        session_keys = [key for key in conversation_data.keys() if key.startswith('session_') and not key.endswith('_date_time')]
        
        # Sort by session number
        session_keys.sort(key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
        
        for session_key in session_keys:
            session_data = conversation_data.get(session_key, [])
            if not session_data:
                continue
            
            # Get corresponding date
            date_key = f"{session_key}_date_time"
            session_date = conversation_data.get(date_key, "Unknown Date")
            
            # Convert to standard format
            utterances = []
            for utterance in session_data:
                if isinstance(utterance, dict):
                    utterances.append(utterance)
                elif isinstance(utterance, str):
                    speaker = speaker_a if len(utterances) % 2 == 0 else speaker_b
                    utterances.append({
                        'speaker': speaker,
                        'text': utterance
                    })
            
            sessions.append((session_key, utterances, session_date))
        
        # Sort by session number
        sessions.sort(key=lambda x: int(x[0].split('_')[1]) if x[0].split('_')[1].isdigit() else 0)
        
        return sessions
    
    def _evaluate_answer(self, question: str, generated_answer: str, standard_answer: str) -> Dict:
        """Evaluate if generated answer contains standard answer content (using EvaluateAgent)"""
        try:
            # Use the evaluate_answer_accuracy tool from EvaluateAgent
            result = self.evaluate_agent.evaluate_answer_accuracy(question, generated_answer, standard_answer)
            
            if result["success"]:
                return {
                    'is_correct': result['is_correct'],
                    'explanation': result['explanation'],
                    'evaluation_text': result['evaluation_text']
                }
            else:
                logger.error(f"Failed to evaluate answer: {result.get('error', 'Unknown error')}")
                return {
                    'is_correct': False,
                    'explanation': f"Evaluation failed: {result.get('error', 'Unknown error')}",
                    'evaluation_text': ""
                }
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            return {
                'is_correct': False,
                'explanation': f"Evaluation failed: {e}",
                'evaluation_text': ""
            }
    
    def process_sample(self, sample: Dict) -> Dict:
        """Process one sample using function tools"""
        start_time = time.time()
        
        try:
            conversation_data = sample['conversation']
            qa_data = sample.get('qa', [])
            
            # Extract characters from conversation data
            characters = []
            speaker_a = conversation_data.get('speaker_a', 'Speaker A')
            speaker_b = conversation_data.get('speaker_b', 'Speaker B')
            if speaker_a and speaker_a not in characters:
                characters.append(speaker_a)
            if speaker_b and speaker_b not in characters:
                characters.append(speaker_b)
            

            if getattr(args_global, 'force_resum', False):
                logger.info("Force redo the memory summarization")
                self.mem_agent.clear_character_memory(characters)

                characters_with_memory = []
                characters_without_memory = characters
            else:
                memory_status = self._check_memory_exists(characters)
                characters_with_memory = [char for char, has_memory in memory_status.items() if has_memory]
                characters_without_memory = [char for char, has_memory in memory_status.items() if not has_memory]
            
                if characters_with_memory:
                    logger.info(f"Memory files already exist for characters: {characters_with_memory}, skipping session processing")
            
            session_results = []
            sessions = self._extract_session_data(conversation_data)
            
            # Only process sessions for characters without existing memory
            if characters_without_memory:
                logger.info(f"Processing {len(sessions)} sessions for characters without memory: {characters_without_memory}")
                
                # Process sessions in parallel using MemAgent
                # session_results = self._process_sessions_parallel(sessions, characters_without_memory, self.max_workers)
                session_results = self._process_sessions_parallel(sessions, characters_without_memory, max_workers=1)
                
                # Log results
                successful_sessions = sum(1 for result in session_results if result.get('success', False))
                logger.info(f"Successfully processed {successful_sessions}/{len(sessions)} sessions")
            else:
                logger.info("All characters already have memory files, skipping session processing entirely")
                # Create placeholder session results
                for i, session in enumerate(sessions):
                    session_results.append({
                        'session_key': session[0],
                        'success': True,
                        'utterances_count': len(session[1]),
                        'session_date': session[2],
                        'skipped': True,
                        'reason': 'Memory already exists'
                    })


            if getattr(args_global, 'no_eval', False):
                question_results = []
            else:
                # Answer QA questions in parallel
                question_results = self._process_qa_parallel(qa_data, characters, conversation_data, self.max_workers)
            
            # Calculate category statistics
            category_stats = {}
            for result in question_results:
                category = result['category']
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'correct': 0}
                category_stats[category]['total'] += 1
                if result['is_correct']:
                    category_stats[category]['correct'] += 1
            
            processing_time = time.time() - start_time
            
            # Calculate skipped sessions count
            sessions_skipped = sum(1 for result in session_results if result.get('skipped', False))
            sessions_actually_processed = len(session_results) - sessions_skipped
            
            return {
                'characters': characters,
                'characters_with_existing_memory': characters_with_memory,
                'characters_without_memory': characters_without_memory,
                'sessions_total': len(sessions),
                'sessions_processed': sessions_actually_processed,
                'sessions_skipped': sessions_skipped,
                'questions_total': len(qa_data),
                'questions_processed': len(question_results),
                'questions_skipped': len(qa_data) - len(question_results),
                'question_results': question_results,
                'category_stats': category_stats,
                'processing_time': processing_time,
                'success': True
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to process sample: {e}")
            return {
                'characters': [],
                'sessions_processed': 0,
                'questions_processed': 0,
                'question_results': [],
                'category_stats': {},
                'processing_time': processing_time,
                'success': False,
                'error': str(e)
            }

    def _print_realtime_category_stats(self, all_results: List[Dict], current_sample: int, total_samples: int):
        """Print real-time category statistics after each sample"""
        # Calculate current accumulated statistics
        overall_category_stats = {}
        total_questions = 0
        total_questions_skipped = 0
        total_correct = 0
        
        for result in all_results:
            if result['success']:
                # Aggregate category statistics
                for category, stats in result['category_stats'].items():
                    if category not in overall_category_stats:
                        overall_category_stats[category] = {'total': 0, 'correct': 0}
                    overall_category_stats[category]['total'] += stats['total']
                    overall_category_stats[category]['correct'] += stats['correct']
                
                total_questions += result['questions_processed']
                total_questions_skipped += result['questions_skipped']
                total_correct += sum(1 for qr in result['question_results'] if qr['is_correct'])
        
        # Print current statistics
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
        
        print(f"\n{'='*60}")
        print(f"REAL-TIME RESULTS - Sample {current_sample}/{total_samples}")
        print(f"{'='*60}")
        print(f"Total questions answered: {total_questions}")
        print(f"Total questions skipped: {total_questions_skipped}")
        print(f"Overall accuracy: {total_correct}/{total_questions} ({overall_accuracy:.1%})")
        
        if overall_category_stats:
            print(f"\nCategory-wise accuracy:")
            print(f"{'Category':<20} {'Correct/Total':<12} {'Accuracy':<10}")
            print(f"{'-'*45}")
            
            for category in sorted(overall_category_stats.keys()):
                stats = overall_category_stats[category]
                accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0
                print(f"{str(category):<20} {stats['correct']:3}/{stats['total']:<3} {accuracy:>10.1%}")
        
        print(f"{'='*60}\n")

    def run_test(self, data_file: str, sample_use: Optional[str] = None) -> Dict:
        """Run the memory test on the dataset"""
        start_time = time.time()
        
        try:
            # Load the data
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Filter data based on sample_use indices
            if sample_use:
                try:
                    # Parse the string as either a number or a list of indices
                    parsed_value = ast.literal_eval(sample_use)
                    
                    if isinstance(parsed_value, int):
                        # Single number: use first N samples (like original sample_limit)
                        if parsed_value <= 0:
                            raise ValueError("sample_use number must be positive")
                        
                        sample_count = min(parsed_value, len(data))
                        data = data[:sample_count]
                        logger.info(f"Using first {sample_count} samples (indices 0-{sample_count-1})")
                        
                        if parsed_value > len(data):
                            logger.warning(f"Requested {parsed_value} samples but only {len(data)} available")
                            
                    elif isinstance(parsed_value, list):
                        # List of indices: use specific samples
                        sample_indices = parsed_value
                        
                        # Filter valid indices and select corresponding samples
                        valid_indices = [i for i in sample_indices if isinstance(i, int) and 0 <= i < len(data)]
                        data = [data[i] for i in valid_indices]
                        
                        logger.info(f"Using samples at specific indices: {valid_indices}")
                        if len(valid_indices) < len(sample_indices):
                            invalid_indices = [i for i in sample_indices if i not in valid_indices]
                            logger.warning(f"Ignored invalid/out-of-range indices: {invalid_indices}")
                    else:
                        raise ValueError("sample_use must be either an integer or a list of integers")
                        
                except Exception as e:
                    logger.error(f"Failed to parse sample_use '{sample_use}': {e}")
                    logger.info("Using all samples instead")
            else:
                logger.info("No sample_use specified, using all samples")
            
            logger.info(f"Starting test with {len(data)} samples")
            
            # Process each sample
            all_results = []
            overall_category_stats = {}
            total_questions = 0
            total_processed = 0
            total_correct = 0
            sample_wise_stats = {}
            
            try:
                for i, sample in enumerate(data, 1):
                    logger.info(f"\n=== Processing Sample {i}/{len(data)} ===")
                    
                    result = self.process_sample(sample)
                    all_results.append(result)
                    
                    if result['success']:
                        # Aggregate category statistics
                        sample_stats = {}
                        for category, stats in result['category_stats'].items():
                            if category not in overall_category_stats:
                                overall_category_stats[category] = {'total': 0, 'correct': 0}
                            overall_category_stats[category]['total'] += stats['total']
                            overall_category_stats[category]['correct'] += stats['correct']
                            sample_stats[category] = {"total": stats['total'], 
                                                    "correct": stats['correct'],
                                                    "accuracy": stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0}
                        
                        total_questions += result['questions_total']
                        total_processed += result['questions_processed']
                        total_correct += sum(1 for qr in result['question_results'] if qr['is_correct'])

                        sample_stats = {key: sample_stats[key] for key in sorted(sample_stats.keys())}
                        sample_wise_stats[i] = sample_stats
                    
                    logger.info(f"Sample {i} completed in {result['processing_time']:.2f}s")
                    
                    # Print real-time category statistics after each sample
                    self._print_realtime_category_stats(all_results, i, len(data))
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt detected. Stopping test...")
                pass
            except Exception as e:
                raise
            
            total_time = time.time() - start_time
            
            # Calculate overall accuracy
            # overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
            overall_accuracy = total_correct / total_processed if total_processed > 0 else 0.0
            
            # Calculate category accuracies
            overall_category_stats = {key: overall_category_stats[key] for key in sorted(overall_category_stats.keys())}
            category_accuracies = {}
            for category, stats in overall_category_stats.items():
                accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0
                category_accuracies[category] = accuracy
            
            # Calculate session statistics
            total_sessions = sum(r.get('sessions_total', 0) for r in all_results if r['success'])
            sessions_processed = sum(r.get('sessions_processed', 0) for r in all_results if r['success'])
            sessions_skipped = sum(r.get('sessions_skipped', 0) for r in all_results if r['success'])
            
            # Create summary
            summary = {
                'total_samples': len(data),
                'successful_samples': sum(1 for r in all_results if r['success']),
                'total_sessions': total_sessions,
                'sessions_processed': sessions_processed,
                'sessions_skipped': sessions_skipped,
                'total_questions': total_questions,
                'total_correct': total_correct,
                'overall_accuracy': overall_accuracy,
                'category_stats': overall_category_stats,
                'category_accuracies': category_accuracies,
                'total_time': total_time,
                'avg_time_per_sample': total_time / len(data) if data else 0.0
            }
            
            self.results = all_results
            self.processing_time = total_time
            
            return {
                'success': True,
                'summary': summary,
                'sample_wise_stats': sample_wise_stats,
                'detailed_results': all_results
            }
            
        except Exception as e:
            logger.error(f"Test run failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': {},
                'detailed_results': []
            }

    def print_results(self):
        """Print detailed test results"""
        if not self.results:
            print("No results to display")
            return
        
        # Calculate overall statistics
        total_samples = len(self.results)
        successful_samples = sum(1 for r in self.results if r['success'])
        total_questions = sum(r['questions_total'] for r in self.results if r['success'])
        total_questions_valid = sum(r['questions_processed'] for r in self.results if r['success'])
        total_correct = sum(sum(1 for qr in r['question_results'] if qr['is_correct']) 
                          for r in self.results if r['success'])
        
        # Calculate session statistics
        total_sessions = sum(r.get('sessions_total', 0) for r in self.results if r['success'])
        sessions_processed = sum(r.get('sessions_processed', 0) for r in self.results if r['success'])
        sessions_skipped = sum(r.get('sessions_skipped', 0) for r in self.results if r['success'])
        
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
        overall_accuracy_valid = total_correct / total_questions_valid if total_questions_valid > 0 else 0.0
        
        # Calculate incorrect answers count
        total_incorrect = total_questions_valid - total_correct
        
        # Aggregate category statistics
        category_stats = {}
        for i, result in enumerate(self.results):
            if result['success']:
                print(f"\n{'='*60}")
                print(f"SAMPLE-WISE RESULTS {i+1}/{total_samples}")
                print(f"{'='*60}")

                # for category, stats in result['category_stats'].items():
                for category in sorted(result['category_stats'].keys()):
                    stats = result['category_stats'][category]
                    
                    if category not in category_stats:
                        category_stats[category] = {'total': 0, 'correct': 0}
                    category_stats[category]['total'] += stats['total']
                    category_stats[category]['correct'] += stats['correct']

                    accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0
                    incorrect_count = stats['total'] - stats['correct']
                    print(f"{category:30} {stats['correct']:3}/{stats['total']:3} ({accuracy:.1%}) [{incorrect_count} errors]")
        
        print(f"\n{'='*60}")
        print(f"ENHANCED MEMORY TEST RESULTS - UNIFIED MEMAGENT")
        print(f"{'='*60}")
        if self.category_filter:
            print(f"Category filter applied: {self.category_filter}")
        print(f"Samples processed: {successful_samples}/{total_samples}")
        print(f"Total sessions: {total_sessions}")
        print(f"Sessions processed: {sessions_processed}")
        print(f"Sessions skipped (memory exists): {sessions_skipped}")
        print(f"Total questions: {total_questions_valid} ({total_questions})")
        print(f"Total correct: {total_correct}")
        print(f"Total incorrect: {total_incorrect}")
        print(f"Overall accuracy: {overall_accuracy_valid:.2%} ({overall_accuracy:.2%})")
        print(f"Total processing time: {self.processing_time:.2f}s")
        print(f"Average time per sample: {self.processing_time / total_samples:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"CATEGORY-WISE ACCURACY")
        print(f"{'='*60}")
        
        for category in sorted(category_stats.keys()):
            stats = category_stats[category]
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0
            incorrect_count = stats['total'] - stats['correct']
            print(f"{category:30} {stats['correct']:3}/{stats['total']:3} ({accuracy:.1%}) [{incorrect_count} errors]")
        
        print(f"\n{'='*60}")
        
        # Add error log information
        if total_incorrect > 0:
            print(f"ERROR LOG INFORMATION")
            print(f"{'='*60}")
            print(f"Total incorrect answers: {total_incorrect}")
            print(f"Detailed error information saved to: {self.error_log_file}")
            
            print(f"The error logs contain:")
            print(f"  - Original questions")
            print(f"  - Retrieved content from memory")
            print(f"  - Evidence used for answering")
            print(f"  - Generated answers")
            print(f"  - Standard (correct) answers")
            print(f"  - Evaluation explanations")
            print(f"\nPlease review the error logs to analyze failure patterns and improve memory retrieval.")
        else:
            print(f"🎉 All questions answered correctly! No error log entries generated.")
        
        print(f"\n{'='*60}")


def main():
    """Main function to run the enhanced memory test"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Memory Test with Unified MemAgent')
    parser.add_argument('--data-file', default='data/locomo10.json', help='Path to test data file')
    parser.add_argument('--sample-use', type=str, help='Sample indices to use. Can be a single number (e.g., "5" for first 5 samples) or a list (e.g., "[0, 1, 3, 5]" for specific indices). If not provided, use all samples.')
    parser.add_argument('--memory-dir', default='memory', help='Directory for memory files')
    parser.add_argument('--chat-deployment', default='gpt-4.1-mini-2', help='Azure OpenAI chat deployment')
    # parser.add_argument('--chat-deployment', default='DeepSeek-V3-0324', help='Azure OpenAI chat deployment')
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of parallel workers for session processing')
    parser.add_argument('--category', type=str, help='Filter questions by category. Can be a single category (e.g., "1") or comma-separated categories (e.g., "0,2,3"). If not provided, use all categories.')
    parser.add_argument('--use-image', type=lambda x: x.lower() != 'false', default=True, help='Insert image caption to conversation (default: True)')
    parser.add_argument('--use-profile', type=str, default="none", help='Use the profile to answer the questions')

    parser.add_argument('--force-resum', action='store_true', help='Force to redo the memory summarization')
    parser.add_argument('--no-eval', action='store_true', help='Do not evaluate the results')
    parser.add_argument('--analyze-on', type=str, default="wrong", help='Do detailed analysis on "all", "wrong", or "none"')
    
    args = parser.parse_args()

    global args_global
    args_global = args
    
    # Parse category filter
    category_filter = None
    if args.category:
        try:
            # Handle comma-separated values
            if ',' in args.category:
                category_filter = [cat.strip() for cat in args.category.split(',')]
            else:
                # Single category
                category_filter = [args.category.strip()]
        except Exception as e:
            logger.error(f"Failed to parse category filter '{args.category}': {e}")
            logger.info("Using all categories instead")
            category_filter = None
    
    # Initialize tester
    tester = ToolBasedMemoryTester(
        memory_dir=args.memory_dir,
        chat_deployment=args.chat_deployment,
        max_workers=args.max_workers,
        category_filter=category_filter
    )

    # Prepare results with comprehensive argument information (automatically includes all parser args)
    args_dict = vars(args)  # Convert argparse Namespace to dictionary
    
    # Reconstruct the original command line
    script_command = ' '.join(sys.argv)
    
    results = {
        "args": args_dict,
        "script": script_command
    }
    
    # Run test
    logger.info("Starting Enhanced Memory Test with Unified MemAgent")
    results |= tester.run_test(args.data_file, args.sample_use)
    
    if results['success']:
        # Print results
        tester.print_results()
        
        # Save detailed results
        output_file = f"enhanced_memory_test_results_{tester.log_timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Detailed results saved to: {output_file}")
        
        # Calculate and report error statistics
        total_questions = results['summary'].get('total_questions', 0)
        total_correct = results['summary'].get('total_correct', 0)
        total_incorrect = total_questions - total_correct
        
        if total_incorrect > 0:
            logger.info(f"Error analysis: {total_incorrect} incorrect answers logged to: {tester.error_log_file}")
            logger.info("Review the error log to identify patterns in failed questions and improve memory retrieval.")
        else:
            logger.info("🎉 Perfect score! All questions answered correctly.")
            
    else:
        logger.error(f"Test failed: {results.get('error', 'Unknown error')}")
        # Even if test failed, there might be some error log entries
        logger.info(f"Check error log for any partial results: {tester.error_log_file}")


if __name__ == "__main__":
    main() 