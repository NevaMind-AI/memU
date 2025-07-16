"""
Enhanced Memory Test with Unified MemAgent

This test uses MemAgent to:
1. Process each session sequentially using memory management tools
2. For each session:
   - Update character memory using memory management tools
3. Use MemAgent for QA testing with category statistics
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import dotenv
dotenv.load_dotenv()

# 确保标准输出unbuffered
if not hasattr(sys, '_stdout_line_buffering_set'):
    sys.stdout.reconfigure(line_buffering=True)
    sys._stdout_line_buffering_set = True

from mem_agent import MemAgent
from memu.utils import get_logger, setup_logging

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)


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
        azure_endpoint: str = None,
        api_key: str = None,
        chat_deployment: str = "gpt-4.1-mini",
        use_entra_id: bool = False,
        api_version: str = "2024-02-01",
        memory_dir: str = "memory",
        max_workers: int = 3
    ):
        """Initialize Tool-based Memory Tester"""
        # Initialize unified MemAgent
        self.mem_agent = MemAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        self.max_workers = max_workers
        self.results = []
        self.processing_time = 0.0
        self.memory_dir = Path(memory_dir)
        
        # Initialize error log file
        self.error_log_file = f"qa_error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._init_error_log()
        
        logger.info(f"Tool-based Memory Tester initialized with unified MemAgent (max_workers={max_workers})")
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

    def _log_qa_error(self, qa_index: int, question: str, generated_answer: str, standard_answer: str, 
                     category: str, retrieved_content: str = "", evidence: str = "", explanation: str = "", 
                     session_context: str = ""):
        """Log detailed information for incorrect QA answers"""
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"QA INDEX: {qa_index + 1}\n")
                f.write(f"CATEGORY: {category}\n")
                f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")
                
                f.write(f"QUESTION:\n{question}\n\n")
                
                f.write(f"EVIDENCE (Referenced Conversations):\n{evidence if evidence else 'No evidence provided'}\n\n")
                
                f.write(f"RETRIEVED CONTENT (From Memory):\n{retrieved_content if retrieved_content else 'No content retrieved'}\n\n")
                
                f.write(f"GENERATED ANSWER:\n{generated_answer}\n\n")
                
                f.write(f"STANDARD ANSWER:\n{standard_answer}\n\n")
                
                f.write(f"EVALUATION EXPLANATION:\n{explanation}\n\n")
                
                f.write(f"{'='*80}\n")
                
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
            
            # Directly call update_character_memory function
            update_result = self.mem_agent.update_character_memory(
                session_data=session_utterances,
                session_date=session_date,
                characters=characters
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
        
        # Sort results by session key for consistent output
        session_results.sort(key=lambda x: x['session_key'])
        
        logger.info(f"Parallel processing completed: {sum(1 for r in session_results if r['success'])}/{total_sessions} sessions successful")
        
        return session_results

    def _process_single_qa(self, qa_data: Tuple[str, str, str, int], characters: List[str], evidence_content: str = "", conversation_data: Dict = None) -> Dict:
        """Process a single QA question using MemAgent"""
        question, answer, category, qa_index = qa_data
        
        try:
            logger.info(f"[QA {qa_index+1}] Answering question in category '{category}': {question[:100]}...")
            
            # Use MemAgent to answer the question with memory context
            answer_prompt = f"""
            Please answer the following question using the available character memory.
            Use the search_relevant_events and read_character_profile functions to gather relevant information.
            
            Question: {question}
            Characters to search: {characters}
            
            Please provide a concise and direct answer based on the memory information.
            Keep your answer brief and focused - avoid lengthy explanations unless specifically needed.
            """
            
            answer_result = self.mem_agent.execute(answer_prompt)
            
            # Extract detailed information from the result
            messages = answer_result.get("messages", [])
            retrieved_contents = []
            tool_executions = []
            
            for message in messages:
                if message.get("role") == "tool" and message.get("content"):
                    try:
                        tool_result_content = message["content"]
                        # Try to parse as JSON to get structured tool result
                        if tool_result_content.startswith('{') and tool_result_content.endswith('}'):
                            tool_result = json.loads(tool_result_content)
                            
                            # Extract different types of tool results
                            if tool_result.get("success", False):
                                # For search_relevant_events results
                                if "relevant_events" in tool_result:
                                    events = tool_result["relevant_events"]
                                    if events:
                                        events_text = "\n".join([f"Event: {event}" for event in events])
                                        retrieved_contents.append(f"Relevant Events:\n{events_text}")
                                        tool_executions.append("search_relevant_events")
                                
                                # For read_character_profile results  
                                elif "profile_content" in tool_result:
                                    profile = tool_result["profile_content"]
                                    if profile:
                                        retrieved_contents.append(f"Character Profile:\n{profile}")
                                        tool_executions.append("read_character_profile")
                                
                                # For read_character_events results
                                elif "events_content" in tool_result:
                                    events = tool_result["events_content"]
                                    if events:
                                        retrieved_contents.append(f"Character Events:\n{events}")
                                        tool_executions.append("read_character_events")
                                
                                # For any other successful tool result, capture the full content
                                elif any(key in tool_result for key in ["content", "result", "data"]):
                                    content = tool_result.get("content") or tool_result.get("result") or tool_result.get("data")
                                    if content:
                                        retrieved_contents.append(f"Tool Result:\n{content}")
                                        tool_executions.append("unknown_tool")
                            else:
                                # Tool failed, but still capture the error for context
                                error_msg = tool_result.get("error", "Unknown tool error")
                                retrieved_contents.append(f"Tool Error:\n{error_msg}")
                        else:
                            # Non-JSON content, treat as plain text result
                            retrieved_contents.append(f"Tool Output:\n{tool_result_content}")
                            
                    except json.JSONDecodeError:
                        # Content is not JSON, treat as plain text
                        retrieved_contents.append(f"Tool Output:\n{tool_result_content}")
                    except Exception as e:
                        logger.warning(f"Failed to parse tool result: {e}")
                        retrieved_contents.append(f"Tool Output (parse error):\n{tool_result_content}")
            
            # Combine all retrieved content
            retrieved_content = "\n\n---\n\n".join(retrieved_contents) if retrieved_contents else "No content retrieved from tools"
            
            if answer_result.get("success", False):
                generated_answer = answer_result.get("final_response", "No answer generated")
            else:
                error_msg = answer_result.get('error', 'Failed to generate answer')
                generated_answer = f"Error: {error_msg}"
                retrieved_content = f"Error occurred during retrieval: {error_msg}"
            
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
            if not evaluation['is_correct']:
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
                    session_context=session_context
                )
                logger.warning(f"[QA {qa_index+1}] ✗ Incorrect answer logged to error file")
            
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
                session_context=session_context
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

    def _process_qa_parallel(self, qa_data: List[Dict], characters: List[str], conversation_data: Dict = None, max_workers: int = 3) -> List[Dict]:
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
        for i, qa_item in enumerate(qa_data):
            if 'question' in qa_item and 'answer' in qa_item:
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
        
        if not qa_items:
            logger.warning("No valid QA items to process")
            return []
        
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

    def _process_single_qa_with_evidence(self, qa_data: Tuple[str, str, str, int, str], characters: List[str], conversation_data: Dict = None) -> Dict:
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
        """Evaluate if generated answer contains standard answer content (using function calling)"""
        try:
            # Use the evaluate_answer tool from MemAgent
            result = self.mem_agent.evaluate_answer(question, generated_answer, standard_answer)
            
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
            
            # Check if memory files already exist for these characters
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
                'questions_answered': len(qa_data),
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
                'questions_answered': 0,
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
        total_correct = 0
        
        for result in all_results:
            if result['success']:
                # Aggregate category statistics
                for category, stats in result['category_stats'].items():
                    if category not in overall_category_stats:
                        overall_category_stats[category] = {'total': 0, 'correct': 0}
                    overall_category_stats[category]['total'] += stats['total']
                    overall_category_stats[category]['correct'] += stats['correct']
                
                total_questions += result['questions_answered']
                total_correct += sum(1 for qr in result['question_results'] if qr['is_correct'])
        
        # Print current statistics
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
        
        print(f"\n{'='*60}")
        print(f"REAL-TIME RESULTS - Sample {current_sample}/{total_samples}")
        print(f"{'='*60}")
        print(f"Total questions answered: {total_questions}")
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

    def run_test(self, data_file: str, sample_limit: Optional[int] = None) -> Dict:
        """Run the memory test on the dataset"""
        start_time = time.time()
        
        try:
            # Load the data
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if sample_limit:
                data = data[:sample_limit]
            
            logger.info(f"Starting test with {len(data)} samples")
            
            # Process each sample
            all_results = []
            overall_category_stats = {}
            total_questions = 0
            total_correct = 0
            
            for i, sample in enumerate(data, 1):
                logger.info(f"\n=== Processing Sample {i}/{len(data)} ===")
                
                result = self.process_sample(sample)
                all_results.append(result)
                
                if result['success']:
                    # Aggregate category statistics
                    for category, stats in result['category_stats'].items():
                        if category not in overall_category_stats:
                            overall_category_stats[category] = {'total': 0, 'correct': 0}
                        overall_category_stats[category]['total'] += stats['total']
                        overall_category_stats[category]['correct'] += stats['correct']
                    
                    total_questions += result['questions_answered']
                    total_correct += sum(1 for qr in result['question_results'] if qr['is_correct'])
                
                logger.info(f"Sample {i} completed in {result['processing_time']:.2f}s")
                
                # Print real-time category statistics after each sample
                self._print_realtime_category_stats(all_results, i, len(data))
            
            total_time = time.time() - start_time
            
            # Calculate overall accuracy
            overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
            
            # Calculate category accuracies
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
        total_questions = sum(r['questions_answered'] for r in self.results if r['success'])
        total_correct = sum(sum(1 for qr in r['question_results'] if qr['is_correct']) 
                          for r in self.results if r['success'])
        
        # Calculate session statistics
        total_sessions = sum(r.get('sessions_total', 0) for r in self.results if r['success'])
        sessions_processed = sum(r.get('sessions_processed', 0) for r in self.results if r['success'])
        sessions_skipped = sum(r.get('sessions_skipped', 0) for r in self.results if r['success'])
        
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0.0
        
        # Calculate incorrect answers count
        total_incorrect = total_questions - total_correct
        
        # Aggregate category statistics
        category_stats = {}
        for result in self.results:
            if result['success']:
                for category, stats in result['category_stats'].items():
                    if category not in category_stats:
                        category_stats[category] = {'total': 0, 'correct': 0}
                    category_stats[category]['total'] += stats['total']
                    category_stats[category]['correct'] += stats['correct']
        
        print(f"\n{'='*60}")
        print(f"ENHANCED MEMORY TEST RESULTS - UNIFIED MEMAGENT")
        print(f"{'='*60}")
        print(f"Samples processed: {successful_samples}/{total_samples}")
        print(f"Total sessions: {total_sessions}")
        print(f"Sessions processed: {sessions_processed}")
        print(f"Sessions skipped (memory exists): {sessions_skipped}")
        print(f"Total questions: {total_questions}")
        print(f"Total correct: {total_correct}")
        print(f"Total incorrect: {total_incorrect}")
        print(f"Overall accuracy: {overall_accuracy:.2%}")
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
            print(f"The error log contains:")
            print(f"  - Original questions")
            print(f"  - Retrieved content from memory")
            print(f"  - Evidence used for answering")
            print(f"  - Generated answers")
            print(f"  - Standard (correct) answers")
            print(f"  - Evaluation explanations")
            print(f"\nPlease review the error log to analyze failure patterns and improve memory retrieval.")
        else:
            print(f"🎉 All questions answered correctly! No error log entries generated.")
        
        print(f"\n{'='*60}")


def main():
    """Main function to run the enhanced memory test"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Memory Test with Unified MemAgent')
    parser.add_argument('--data-file', default='data/locomo10.json', help='Path to test data file')
    parser.add_argument('--sample-limit', type=int, help='Limit number of samples to process')
    parser.add_argument('--memory-dir', default='memory', help='Directory for memory files')
    parser.add_argument('--chat-deployment', default='gpt-4o-mini', help='Azure OpenAI chat deployment')
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of parallel workers for session processing')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = ToolBasedMemoryTester(
        memory_dir=args.memory_dir,
        chat_deployment=args.chat_deployment,
        max_workers=args.max_workers
    )
    
    # Run test
    logger.info("Starting Enhanced Memory Test with Unified MemAgent")
    results = tester.run_test(args.data_file, args.sample_limit)
    
    if results['success']:
        # Print results
        tester.print_results()
        
        # Save detailed results
        output_file = f"enhanced_memory_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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