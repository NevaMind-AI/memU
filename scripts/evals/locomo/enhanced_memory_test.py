"""
Enhanced Memory Test for Locomo Evaluation

This test uses the EnhancedMemoryAgent to:
1. Process each session sequentially in order
2. For each session:
   - Summarize session content and update event.md with natural language descriptions
   - Update profile.md based on events and current session in natural language
   - Add Theory of Mind comments under each line in both files
3. Use merged memory context for QA testing
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

from enhanced_memory_agent import EnhancedMemoryAgent
from personalab.utils import get_logger, setup_logging

# 设置带有flush的logger
logger = setup_logging(__name__, enable_flush=True)


class EnhancedMemoryTester:
    """
    增强记忆测试器
    
    使用EnhancedMemoryAgent处理Locomo数据：
    1. 按顺序逐个session处理对话
    2. 每个session处理流程：
       - 总结session内容，用自然语言更新event.md
       - 根据event.md和当前session用自然语言更新profile.md
       - 使用Theory of Mind在两个文件的每一行下面添加心理分析注释
    3. QA测试时使用合并的记忆上下文
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
        初始化增强记忆测试器
        
        Args:
            azure_endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            chat_deployment: Azure OpenAI chat deployment name
            use_entra_id: Whether to use Entra ID authentication
            api_version: Azure OpenAI API version
            memory_dir: Directory to store memory files
        """
        self.memory_agent = EnhancedMemoryAgent(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            use_entra_id=use_entra_id,
            api_version=api_version,
            memory_dir=memory_dir
        )
        
        self.results = []
        self.processing_time = 0.0
        
        logger.info("增强记忆测试器初始化完成")
    
    def _extract_session_data(self, conversation_data: Dict) -> List[Tuple[str, List[Dict], str]]:
        """
        从对话数据中提取session信息
        
        Args:
            conversation_data: 对话数据字典
            
        Returns:
            List of (session_name, utterances, date) tuples
        """
        sessions = []
        
        # 提取角色名称
        speaker_a = conversation_data.get('speaker_a', 'Speaker A')
        speaker_b = conversation_data.get('speaker_b', 'Speaker B')
        
        # 查找所有session
        session_keys = [key for key in conversation_data.keys() if key.startswith('session_') and not key.endswith('_date_time')]
        
        # 按session编号排序，确保按顺序读取
        session_keys.sort(key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
        
        for session_key in session_keys:
            # 获取session数据
            session_data = conversation_data.get(session_key, [])
            if not session_data:
                continue
            
            # 获取对应的日期
            date_key = f"{session_key}_date_time"
            session_date = conversation_data.get(date_key, "Unknown Date")
            
            # 转换为标准格式
            utterances = []
            for utterance in session_data:
                if isinstance(utterance, dict):
                    utterances.append(utterance)
                elif isinstance(utterance, str):
                    # 如果是字符串，需要解析speaker
                    # 这里假设格式是alternating speakers
                    speaker = speaker_a if len(utterances) % 2 == 0 else speaker_b
                    utterances.append({
                        'speaker': speaker,
                        'content': utterance
                    })
            
            sessions.append((session_key, utterances, session_date))
        
        # 按session编号排序
        sessions.sort(key=lambda x: int(x[0].split('_')[1]) if x[0].split('_')[1].isdigit() else 0)
        
        return sessions
    
    def _evaluate_answer(self, question: str, generated_answer: str, standard_answer: str) -> Dict:
        """
        评估生成答案是否包含标准答案内容
        
        Args:
            question: 问题
            generated_answer: 生成的答案
            standard_answer: 标准答案
            
        Returns:
            评估结果字典
        """
        prompt = f"""
Check if the generated answer contains the content from the standard answer.

Question: {question}

Generated Answer: {generated_answer}

Standard Answer: {standard_answer}

Task: Determine if the generated answer contains the key information and core content from the standard answer.

Output Format:
Answer: [yes/no]
"""
        
        try:
            response = self.memory_agent.llm_client.simple_chat(prompt, max_tokens=16000)
            
            # 解析评估结果
            is_correct = "yes" in response.split("Answer:")[1].split("\n")[0].lower() if "Answer:" in response else False
            
            return {
                'is_correct': is_correct,
                'explanation': response,
                'evaluation_text': response
            }
            
        except Exception as e:
            logger.error(f"评估答案失败: {e}")
            return {
                'is_correct': False,
                'explanation': f"Evaluation failed: {e}",
                'evaluation_text': ""
            }
    
    def process_sample(self, sample: Dict) -> Dict:
        """
        处理一个样本数据
        
        按照以下流程处理：
        1. 加载样本数据
        2. 从session1开始按顺序读取
        3. 每个session处理后更新记忆文件：
           - 总结session内容，用自然语言加入event.md
           - 根据event.md和当前session用自然语言更新profile.md
           - 调用theory of mind在profile.md和event.md的每一行下面添加注释
        4. 处理完所有session后，逐个回答QA问题
        5. 判断答案是否正确
        
        Args:
            sample: 样本数据
            
        Returns:
            处理结果
        """
        start_time = time.time()
        
        sample_id = sample.get('sample_id', 'unknown')
        conversation_data = sample.get('conversation', {})
        qa_data = sample.get('qa', [])
        
        logger.info(f"=== 开始处理样本: {sample_id} ===")
        
        # 提取角色名称
        speaker_a = conversation_data.get('speaker_a', 'Speaker A')
        speaker_b = conversation_data.get('speaker_b', 'Speaker B')
        characters = [speaker_a, speaker_b]
        
        logger.info(f"角色: {characters}")
        
        # 步骤1: 清空记忆文件，开始新的样本处理
        logger.info("步骤1: 清空记忆文件")
        self.memory_agent.clear_memory(characters)
        
        # 步骤2: 提取并排序session数据
        sessions = self._extract_session_data(conversation_data)
        logger.info(f"步骤2: 找到 {len(sessions)} 个sessions，将按顺序处理")
        
        # 步骤3: 逐个处理session，按顺序更新记忆文件
        session_processing_details = []
        
        for i, (session_name, utterances, session_date) in enumerate(sessions, 1):
            if not utterances:  # 跳过空session
                logger.info(f"跳过空session: {session_name}")
                continue
                
            logger.info(f"--- 步骤3.{i}: 处理 {session_name} (日期: {session_date}) ---")
            logger.info(f"  对话轮数: {len(utterances)}")
            
            # 处理session前的记忆状态
            before_memory = {}
            for char in characters:
                before_memory[char] = {
                    'profile': len(self.memory_agent._read_memory_file(char, "profile")),
                    'event': len(self.memory_agent._read_memory_file(char, "event"))
                }
            
            # 调用EnhancedMemoryAgent处理session
            # 这会自动完成以下步骤：
            # - 总结session内容并用自然语言加入event.md
            # - 根据event.md和当前session用自然语言更新profile.md
            # - 调用theory of mind在profile.md和event.md的每一行下面添加注释
            session_start_time = time.time()
            self.memory_agent.process_session(utterances, session_date, characters)
            session_processing_time = time.time() - session_start_time
            
            # 处理session后的记忆状态
            after_memory = {}
            for char in characters:
                after_memory[char] = {
                    'profile': len(self.memory_agent._read_memory_file(char, "profile")),
                    'event': len(self.memory_agent._read_memory_file(char, "event"))
                }
            
            # 记录处理详情
            session_detail = {
                'session_name': session_name,
                'session_date': session_date,
                'utterances_count': len(utterances),
                'processing_time': session_processing_time,
                'memory_changes': {}
            }
            
            for char in characters:
                session_detail['memory_changes'][char] = {
                    'profile_change': after_memory[char]['profile'] - before_memory[char]['profile'],
                    'event_change': after_memory[char]['event'] - before_memory[char]['event']
                }
            
            session_processing_details.append(session_detail)
            
            logger.info(f"  {session_name} 处理完成，用时: {session_processing_time:.2f}s")
            for char in characters:
                changes = session_detail['memory_changes'][char]
                logger.info(f"    {char}: profile({changes['profile_change']:+}), event({changes['event_change']:+})")
        
        # 步骤4: 处理QA问题
        logger.info(f"--- 步骤4: 开始处理 {len(qa_data)} 个QA问题 ---")
        
        qa_results = []
        for i, qa_item in enumerate(qa_data, 1):
            question = qa_item.get('question', '')
            standard_answer = qa_item.get('answer', '')
            category = qa_item.get('category', 0)
            evidence = qa_item.get('evidence', [])
            
            logger.info(f"  问题 {i}/{len(qa_data)}: {question[:50]}...")
            
            # 使用记忆代理回答问题
            qa_start_time = time.time()
            generated_answer = self.memory_agent.answer_question(question, characters)
            qa_processing_time = time.time() - qa_start_time
            print('-'*100)
            print("standard_answer:")
            print(standard_answer)
            print("generated_answer:")
            print(generated_answer)

            # 步骤5: 评估答案是否正确
            evaluation = self._evaluate_answer(question, generated_answer, standard_answer)
            
            # 记录结果
            qa_result = {
                'question_id': i,
                'question': question,
                'standard_answer': standard_answer,
                'generated_answer': generated_answer,
                'category': category,
                'evidence': evidence,
                'processing_time': qa_processing_time,
                'evaluation': evaluation
            }
            
            qa_results.append(qa_result)
            
            # 日志输出结果
            if evaluation['is_correct']:
                logger.info(f"    ✓ 答案正确")
            else:
                logger.info(f"    ✗ 答案错误")
        
        # 计算统计信息
        total_qa = len(qa_results)
        correct_qa = sum(1 for result in qa_results if result['evaluation']['is_correct'])
        
        processing_time = time.time() - start_time
        
        # 获取最终的合并上下文
        final_context = self.memory_agent.get_merged_context(characters)
        
        # 生成样本处理结果
        sample_result = {
            'sample_id': sample_id,
            'characters': characters,
            'sessions_processed': len([s for s in sessions if s[1]]),  # 非空session数量
            'session_processing_details': session_processing_details,
            'total_qa': total_qa,
            'correct_qa': correct_qa,
            'correctness_rate': correct_qa / total_qa if total_qa > 0 else 0,
            'processing_time': processing_time,
            'qa_results': qa_results,
            'final_context': final_context
        }
        
        # 输出样本处理摘要
        logger.info(f"=== 样本 {sample_id} 处理完成 ===")
        logger.info(f"  处理的Sessions: {len(session_processing_details)}")
        logger.info(f"  QA总数: {total_qa}")
        logger.info(f"  正确答案: {correct_qa}/{total_qa} ({correct_qa/total_qa*100:.1f}%)")
        logger.info(f"  总处理时间: {processing_time:.2f}s")
        logger.info(f"  记忆文件已更新: profile.md, event.md (每一行都包含Theory of Mind注释)")
        
        return sample_result
    
    def run_test(self, data_file: str) -> Dict:
        """
        运行完整测试
        
        Args:
            data_file: 数据文件路径
            
        Returns:
            测试结果
        """
        logger.info(f"开始增强记忆测试: {data_file}")
        
        # 读取数据
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"加载了 {len(data)} 个样本")
        
        start_time = time.time()
        
        # 处理每个样本
        sample_results = []
        for i, sample in enumerate(data):
            logger.info(f"=== 处理样本 {i+1}/{len(data)} ===")
            
            result = self.process_sample(sample)
            sample_results.append(result)
            
                    # 保存中间结果
        if (i + 1) % 5 == 0:
            self._save_intermediate_results(sample_results, i + 1)
            # 强制刷新输出
            sys.stdout.flush()
        
        total_time = time.time() - start_time
        
        # 计算总体统计
        total_qa = sum(result['total_qa'] for result in sample_results)
        total_correct = sum(result['correct_qa'] for result in sample_results)
        overall_correctness = total_correct / total_qa if total_qa > 0 else 0
        
        avg_processing_time = sum(result['processing_time'] for result in sample_results) / len(sample_results) if sample_results else 0
        
        # 生成最终结果
        final_results = {
            'test_info': {
                'test_type': 'enhanced_memory_test',
                'data_file': data_file,
                'total_samples': len(data),
                'total_time': total_time,
                'timestamp': datetime.now().isoformat()
            },
            'overall_statistics': {
                'total_qa': total_qa,
                'correct_qa': total_correct,
                'correctness_rate': overall_correctness,
                'avg_processing_time': avg_processing_time
            },
            'sample_results': sample_results
        }
        
        # 保存最终结果
        self._save_final_results(final_results)
        
        logger.info("=== 测试完成 ===")
        logger.info(f"总样本数: {len(data)}")
        logger.info(f"总QA数: {total_qa}")
        logger.info(f"正确率: {total_correct}/{total_qa} ({overall_correctness*100:.1f}%)")
        logger.info(f"平均处理时间: {avg_processing_time:.2f}s/样本")
        logger.info(f"总时间: {total_time:.2f}s")
        
        return final_results
    
    def _save_intermediate_results(self, results: List[Dict], processed_count: int):
        """保存中间结果"""
        filename = f"enhanced_memory_test_intermediate_{processed_count}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"已保存中间结果: {filename}")
    
    def _save_final_results(self, results: Dict):
        """保存最终结果"""
        filename = f"enhanced_memory_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"已保存最终结果: {filename}")


def main():
    """主函数"""
    # 配置参数
    config = {
        'azure_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'chat_deployment': os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4.1-mini'),
        'use_entra_id': os.getenv('USE_ENTRA_ID', 'false').lower() == 'true',
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01'),
        'memory_dir': 'memory'
    }
    
    # 创建agent实例来检查memory文件
    agent = EnhancedMemoryAgent(**config)
    
    # 检查是否存在memory文件
    available_characters = agent.list_available_characters()
    if available_characters:
        print("=" * 60, flush=True)
        print("🔍 DETECTED EXISTING MEMORY FILES", flush=True)
        print("=" * 60, flush=True)
        print(f"📂 Found memory files for: {', '.join(available_characters)}", flush=True)
        print("", flush=True)
        print("Choose an option:", flush=True)
        print("1. Enter QA mode directly (recommended if you want to ask questions)", flush=True)
        print("2. Run full test (process sessions + evaluate QA)", flush=True)
        print("3. Clear existing memory and start fresh", flush=True)
        print("", flush=True)
        
        try:
            choice = input("Enter your choice (1/2/3): ").strip()
            
            if choice == "1":
                print("\n🧠 Starting QA mode with existing memory files...", flush=True)
                agent.start_qa_mode(available_characters)
                return
            elif choice == "2":
                print("\n🚀 Running full test...", flush=True)
                # Continue to normal test flow
            elif choice == "3":
                print(f"\n🗑️ Clearing memory files for: {', '.join(available_characters)}", flush=True)
                agent.clear_memory(available_characters)
                print("✅ Memory files cleared. Running full test...", flush=True)
            else:
                print("❌ Invalid choice. Running full test by default...", flush=True)
                
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!", flush=True)
            return
    else:
        print("📝 No existing memory files found. Running full test...", flush=True)
    
    # 数据文件
    data_file = 'data/locomo10.json'
    
    if not os.path.exists(data_file):
        logger.error(f"数据文件不存在: {data_file}")
        return
    
    # 创建测试器
    tester = EnhancedMemoryTester(**config)
    
    # 运行测试
    results = tester.run_test(data_file)
    
    # 显示结果摘要
    print("\n" + "="*50, flush=True)
    print("测试结果摘要", flush=True)
    print("="*50, flush=True)
    print(f"总样本数: {results['test_info']['total_samples']}", flush=True)
    print(f"总QA数: {results['overall_statistics']['total_qa']}", flush=True)
    print(f"正确率: {results['overall_statistics']['correctness_rate']:.1%}", flush=True)
    print(f"平均处理时间: {results['overall_statistics']['avg_processing_time']:.2f}s/样本", flush=True)
    print(f"总时间: {results['test_info']['total_time']:.2f}s", flush=True)
    print("="*50, flush=True)
    
    # 测试完成后询问是否进入QA模式
    try:
        print("\n" + "="*50, flush=True)
        print("🎯 TEST COMPLETED", flush=True)
        print("="*50, flush=True)
        qa_choice = input("Would you like to enter QA mode to ask questions? (y/n): ").strip().lower()
        if qa_choice in ['y', 'yes']:
            agent.start_qa_mode()
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Goodbye!", flush=True)


if __name__ == "__main__":
    main() 