"""
Enhanced Memory Test with Dual Agents

This test uses RecallAgent and ManageAgent to:
1. Process each session sequentially using ManageAgent
2. For each session:
   - Update character memory using memory management tools
3. Use RecallAgent for QA testing with category statistics
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path

import dotenv
dotenv.load_dotenv()

# 确保标准输出unbuffered
if not hasattr(sys, '_stdout_line_buffering_set'):
    sys.stdout.reconfigure(line_buffering=True)
    sys._stdout_line_buffering_set = True

from recall_agent import RecallAgent
from manage_agent import ManageAgent
from personalab.utils import get_logger, setup_logging

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)


class ToolBasedMemoryTester:
    """
    Tool-based Memory Tester
    
    Uses RecallAgent and ManageAgent for processing Locomo data:
    1. Process sessions sequentially using ManageAgent
    2. Answer QA questions using RecallAgent
    3. Display category-based accuracy statistics
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
        """Initialize Tool-based Memory Tester"""
        # Initialize both agents
        self.recall_agent = RecallAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        self.manage_agent = ManageAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        self.results = []
        self.processing_time = 0.0
        
        logger.info("Tool-based Memory Tester initialized with RecallAgent and ManageAgent")
    
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
            # Use the evaluate_answer tool from recall agent
            result = self.recall_agent.evaluate_answer(question, generated_answer, standard_answer)
            
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
        
        sample_id = sample.get('sample_id', 'unknown')
        conversation_data = sample.get('conversation', {})
        qa_data = sample.get('qa', [])
        
        logger.info(f"=== Processing sample: {sample_id} ===")
        
        # Extract character names
        speaker_a = conversation_data.get('speaker_a', 'Speaker A')
        speaker_b = conversation_data.get('speaker_b', 'Speaker B')
        characters = [speaker_a, speaker_b]
        
        logger.info(f"Characters: {characters}")
        
        # Step 1: Check existing memory files
        char_list_result = self.recall_agent.list_available_characters()
        existing_characters = char_list_result.get("characters", []) if char_list_result["success"] else []
        
        characters_have_memory = all(char.lower() in [c.lower() for c in existing_characters] for char in characters)
        
        if characters_have_memory:
            logger.info("Step 1: Found existing memory files for all characters, skipping session processing")
            session_processing_details = []
        else:
            logger.info("Step 1: Memory files incomplete, clearing and processing all sessions")
            
            # Clear existing memory
            clear_result = self.manage_agent.clear_character_memory(characters)
            if not clear_result["success"]:
                logger.warning(f"Failed to clear memory: {clear_result['error']}")
            
            # Step 2: Extract and sort session data
            sessions = self._extract_session_data(conversation_data)
            logger.info(f"Step 2: Found {len(sessions)} sessions, processing in order")
            
            # Step 3: Process sessions using memory tools
            session_processing_details = []
            
            for i, (session_name, utterances, session_date) in enumerate(sessions, 1):
                if not utterances:
                    logger.info(f"Skipping empty session: {session_name}")
                    continue
                    
                logger.info(f"--- Step 3.{i}: Processing {session_name} (Date: {session_date}) ---")
                logger.info(f"  Utterances: {len(utterances)}")
                
                # Process session using agent execute method
                session_start_time = time.time()
                
                # Format session data for agent
                session_summary = f"Session {session_name} on {session_date} with {len(utterances)} utterances between {', '.join(characters)}"
                utterances_text = "\n".join([f"**{ut['speaker']}**: {ut['text']}" for ut in utterances])
                
                # Use manage agent to process session
                agent_request = f"""Please update character memory for the following conversation session:

{session_summary}

Conversation:
{utterances_text}

Characters involved: {', '.join(characters)}
Session date: {session_date}

Please update the memory files for all characters based on this conversation."""
                
                execute_result = self.manage_agent.execute(
                    user_message=agent_request,
                    max_iterations=10
                )
                session_processing_time = time.time() - session_start_time
                
                # Record processing details
                session_detail = {
                    'session_name': session_name,
                    'session_date': session_date,
                    'utterances_count': len(utterances),
                    'processing_time': session_processing_time,
                    'update_success': execute_result["success"],
                    'tool_calls_made': execute_result.get("tool_calls_made", 0)
                }
                
                if execute_result["success"]:
                    session_detail['agent_response'] = execute_result["response"]
                    logger.info(f"  {session_name} processed successfully by agent, time: {session_processing_time:.2f}s")
                    logger.info(f"    Tool calls made: {execute_result.get('tool_calls_made', 0)}")
                else:
                    session_detail['error'] = execute_result.get("error", "Unknown error")
                    logger.error(f"  {session_name} processing failed: {execute_result.get('error', 'Unknown error')}")
                
                session_processing_details.append(session_detail)
        
        # Step 4: Process QA questions using answer_with_memory tool
        logger.info(f"--- Step 4: Processing {len(qa_data)} QA questions ---")
        
        qa_results = []
        for i, qa_item in enumerate(qa_data, 1):
            question = qa_item.get('question', '')
            standard_answer = qa_item.get('answer', '')
            category = qa_item.get('category', 0)
            evidence = qa_item.get('evidence', [])
            
            logger.info(f"  Question {i}/{len(qa_data)}: {question[:50]}...")
            
            # Answer question using recall agent
            qa_start_time = time.time()
            
            # Use execute method for recursive function calling
            execute_result = self.recall_agent.execute(
                user_message=f"Answer this question: {question}\n\nCharacters involved: {', '.join(characters)}",
                max_iterations=10
            )
            qa_processing_time = time.time() - qa_start_time
            
            if execute_result["success"]:
                generated_answer = execute_result["response"]
                tool_calls_made = execute_result.get("tool_calls_made", 0)
                
                # Evaluate answer
                evaluation = self._evaluate_answer(question, generated_answer, standard_answer)
                
                # Create QA result
                qa_result = {
                    'question_id': i,
                    'question': question,
                    'category': category,
                    'evidence': evidence,
                    'standard_answer': standard_answer,
                    'generated_answer': generated_answer,
                    'evaluation': evaluation,
                    'processing_time': qa_processing_time,
                    'tool_calls_made': tool_calls_made
                }
                
                # Log result with category stats
                status = "✓" if evaluation['is_correct'] else "✗"
                logger.info(f"    {status} {'Correct' if evaluation['is_correct'] else 'Incorrect'} | Current accuracy: {sum(1 for r in qa_results if r['evaluation']['is_correct']) + (1 if evaluation['is_correct'] else 0)}/{i} ({((sum(1 for r in qa_results if r['evaluation']['is_correct']) + (1 if evaluation['is_correct'] else 0))/i)*100:.1f}%)")
                
                # Calculate and display current category statistics
                qa_results.append(qa_result)
                category_stats = {}
                for result in qa_results:
                    cat = result['category']
                    if cat not in category_stats:
                        category_stats[cat] = {'correct': 0, 'total': 0}
                    category_stats[cat]['total'] += 1
                    if result['evaluation']['is_correct']:
                        category_stats[cat]['correct'] += 1
                
                # Display category stats
                stats_parts = []
                for cat in sorted(category_stats.keys()):
                    stats = category_stats[cat]
                    rate = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
                    stats_parts.append(f"Cat{cat}: {stats['correct']}/{stats['total']}({rate:.1f}%)")
                
                logger.info(f"    Current category stats: {' | '.join(stats_parts)}")
                
            else:
                # Handle execution failure
                qa_result = {
                    'question_id': i,
                    'question': question,
                    'category': category,
                    'evidence': evidence,
                    'standard_answer': standard_answer,
                    'generated_answer': '',
                    'evaluation': {'is_correct': False, 'explanation': 'Function calling execution failed'},
                    'processing_time': qa_processing_time,
                    'error': execute_result.get('error', 'Unknown error'),
                    'tool_calls_made': 0
                }
                
                logger.error(f"    ✗ QA execution failed: {execute_result.get('error', 'Unknown error')}")
                qa_results.append(qa_result)
        
        # Calculate statistics
        total_qa = len(qa_results)
        correct_qa = sum(1 for result in qa_results if result['evaluation']['is_correct'])
        
        # Calculate category statistics
        category_stats = {}
        for result in qa_results:
            category = result['category']
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'correct': 0}
            category_stats[category]['total'] += 1
            if result['evaluation']['is_correct']:
                category_stats[category]['correct'] += 1
        
        # Calculate category rates
        for category in category_stats:
            total = category_stats[category]['total']
            correct = category_stats[category]['correct']
            category_stats[category]['rate'] = correct / total if total > 0 else 0
        
        processing_time = time.time() - start_time
        
        # Generate sample result
        sample_result = {
            'sample_id': sample_id,
            'characters': characters,
            'sessions_processed': len([s for s in session_processing_details if s.get('update_success', False)]),
            'session_processing_details': session_processing_details,
            'total_qa': total_qa,
            'correct_qa': correct_qa,
            'correctness_rate': correct_qa / total_qa if total_qa > 0 else 0,
            'category_stats': category_stats,
            'processing_time': processing_time,
            'qa_results': qa_results
        }
        
        # Output sample summary
        logger.info(f"=== Sample {sample_id} completed ===")
        logger.info(f"  Sessions processed: {len(session_processing_details)}")
        logger.info(f"  QA total: {total_qa}")
        logger.info(f"  Correct answers: {correct_qa}/{total_qa} ({correct_qa/total_qa*100:.1f}%)")
        
        # Display category statistics
        logger.info(f"  Category statistics:")
        for category in sorted(category_stats.keys()):
            stats = category_stats[category]
            logger.info(f"    Category {category}: {stats['correct']}/{stats['total']} ({stats['rate']*100:.1f}%)")
        
        logger.info(f"  Total processing time: {processing_time:.2f}s")
        
        return sample_result
    
    def run_test(self, data_file: str) -> Dict:
        """Run complete test using function tools"""
        logger.info(f"Starting tool-based memory test: {data_file}")
        
        # Load data
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} samples")
        
        start_time = time.time()
        
        # Process each sample
        sample_results = []
        for i, sample in enumerate(data):
            logger.info(f"=== Processing sample {i+1}/{len(data)} ===")
            
            result = self.process_sample(sample)
            sample_results.append(result)
            
            # Save intermediate results
            if (i + 1) % 5 == 0:
                self._save_intermediate_results(sample_results, i + 1)
                sys.stdout.flush()
        
        total_time = time.time() - start_time
        
        # Calculate overall statistics
        total_qa = sum(result['total_qa'] for result in sample_results)
        total_correct = sum(result['correct_qa'] for result in sample_results)
        overall_correctness = total_correct / total_qa if total_qa > 0 else 0
        
        # Merge category statistics
        overall_category_stats = {}
        for result in sample_results:
            for category, stats in result['category_stats'].items():
                if category not in overall_category_stats:
                    overall_category_stats[category] = {'total': 0, 'correct': 0}
                overall_category_stats[category]['total'] += stats['total']
                overall_category_stats[category]['correct'] += stats['correct']
        
        # Calculate overall category rates
        for category in overall_category_stats:
            total = overall_category_stats[category]['total']
            correct = overall_category_stats[category]['correct']
            overall_category_stats[category]['rate'] = correct / total if total > 0 else 0
        
        avg_processing_time = sum(result['processing_time'] for result in sample_results) / len(sample_results) if sample_results else 0
        
        # Generate final results
        final_results = {
            'test_info': {
                'test_type': 'tool_based_memory_test',
                'data_file': data_file,
                'total_samples': len(data),
                'total_time': total_time,
                'timestamp': datetime.now().isoformat()
            },
            'overall_statistics': {
                'total_qa': total_qa,
                'correct_qa': total_correct,
                'correctness_rate': overall_correctness,
                'category_stats': overall_category_stats,
                'avg_processing_time': avg_processing_time
            },
            'sample_results': sample_results
        }
        
        # Save final results
        self._save_final_results(final_results)
        
        logger.info("=== Test completed ===")
        logger.info(f"Total samples: {len(data)}")
        logger.info(f"Total QA: {total_qa}")
        logger.info(f"Accuracy: {total_correct}/{total_qa} ({overall_correctness*100:.1f}%)")
        
        # Display overall category statistics
        logger.info(f"Overall category statistics:")
        for category in sorted(overall_category_stats.keys()):
            stats = overall_category_stats[category]
            logger.info(f"  Category {category}: {stats['correct']}/{stats['total']} ({stats['rate']*100:.1f}%)")
        
        logger.info(f"Average processing time: {avg_processing_time:.2f}s/sample")
        logger.info(f"Total time: {total_time:.2f}s")
        
        return final_results
    
    def _save_intermediate_results(self, results: List[Dict], processed_count: int):
        """Save intermediate results"""
        filename = f"tool_based_memory_test_intermediate_{processed_count}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved intermediate results: {filename}")
    
    def _save_final_results(self, results: Dict):
        """Save final results"""
        filename = f"tool_based_memory_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved final results: {filename}")


def main():
    """Main function"""
    # Configuration parameters
    config = {
        'azure_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'chat_deployment': os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4.1-mini'),
        'use_entra_id': os.getenv('USE_ENTRA_ID', 'false').lower() == 'true',
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01'),
        'memory_dir': 'memory'
    }
    
    # Data file
    data_file = 'data/locomo10.json'
    
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return
    
    print("🚀 Starting Tool-based Locomo QA test...", flush=True)
    
    # Create tester
    tester = ToolBasedMemoryTester(**config)
    
    # Run test
    results = tester.run_test(data_file)
    
    # Display results summary
    print("\n" + "="*50, flush=True)
    print("Test Results Summary", flush=True)
    print("="*50, flush=True)
    print(f"Total samples: {results['test_info']['total_samples']}", flush=True)
    print(f"Total QA: {results['overall_statistics']['total_qa']}", flush=True)
    print(f"Accuracy: {results['overall_statistics']['correctness_rate']:.1%}", flush=True)
    
    # Display category statistics
    print("Category statistics:", flush=True)
    category_stats = results['overall_statistics']['category_stats']
    for category in sorted(category_stats.keys()):
        stats = category_stats[category]
        print(f"  Category {category}: {stats['correct']}/{stats['total']} ({stats['rate']*100:.1f}%)", flush=True)
    
    print(f"Average processing time: {results['overall_statistics']['avg_processing_time']:.2f}s/sample", flush=True)
    print(f"Total time: {results['test_info']['total_time']:.2f}s", flush=True)
    print("="*50, flush=True)


if __name__ == "__main__":
    main() 