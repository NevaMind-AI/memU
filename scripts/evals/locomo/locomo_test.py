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
        
        logger.info(f"Tool-based Memory Tester initialized with unified MemAgent (max_workers={max_workers})")

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

    def _process_single_qa(self, qa_data: Tuple[str, str, str, int], characters: List[str]) -> Dict:
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
            
            Please provide a comprehensive answer based on the memory information.
            """
            
            answer_result = self.mem_agent.execute(answer_prompt)
            
            if answer_result.get("success", False):
                generated_answer = answer_result.get("final_response", "No answer generated")
            else:
                generated_answer = f"Error: {answer_result.get('error', 'Failed to generate answer')}"
            
            # Evaluate the answer
            evaluation = self._evaluate_answer(question, generated_answer, answer)
            
            result = {
                'qa_index': qa_index,
                'question': question,
                'generated_answer': generated_answer,
                'standard_answer': answer,
                'category': category,
                'is_correct': evaluation['is_correct'],
                'explanation': evaluation['explanation']
            }
            
            status = "✓" if evaluation['is_correct'] else "✗"
            logger.info(f"[QA {qa_index+1}] {status} Question completed (Category: {category})")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA {qa_index+1}] Exception processing question: {e}")
            return {
                'qa_index': qa_index,
                'question': question,
                'generated_answer': f"Error: {e}",
                'standard_answer': answer,
                'category': category,
                'is_correct': False,
                'explanation': f"Processing failed: {e}"
            }

    def _process_qa_parallel(self, qa_data: List[Dict], characters: List[str], max_workers: int = 3) -> List[Dict]:
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
                qa_items.append((qa_item['question'], qa_item['answer'], qa_item.get('category', 'Unknown'), i))
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
            # Submit all QA processing tasks
            future_to_qa = {
                executor.submit(self._process_single_qa, qa_item, characters): qa_item[3] 
                for qa_item in qa_items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_qa):
                qa_index = future_to_qa[future]
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
                        'question': f"Question {qa_index+1}",
                        'generated_answer': f"Error: {e}",
                        'standard_answer': "",
                        'category': 'Unknown',
                        'is_correct': False,
                        'explanation': f"Exception: {e}"
                    })
        
        # Sort results by qa_index for consistent output
        question_results.sort(key=lambda x: x['qa_index'])
        
        successful_qa = sum(1 for r in question_results if r['is_correct'])
        processed_qa = len(question_results)
        logger.info(f"Parallel QA processing completed: {successful_qa}/{processed_qa} questions answered correctly")
        
        return question_results

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
                session_results = self._process_sessions_parallel(sessions, characters_without_memory, self.max_workers)
                
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
            question_results = self._process_qa_parallel(qa_data, characters, self.max_workers)
            
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
        print(f"Overall accuracy: {overall_accuracy:.2%}")
        print(f"Total processing time: {self.processing_time:.2f}s")
        print(f"Average time per sample: {self.processing_time / total_samples:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"CATEGORY-WISE ACCURACY")
        print(f"{'='*60}")
        
        for category in sorted(category_stats.keys()):
            stats = category_stats[category]
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0
            print(f"{category:30} {stats['correct']:3}/{stats['total']:3} ({accuracy:.1%})")
        
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
    else:
        logger.error(f"Test failed: {results.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 