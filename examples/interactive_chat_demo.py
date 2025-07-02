#!/usr/bin/env python3
"""
PersonaLab 交互式聊天演示
"""

import sys
import os
sys.path.append('.')

from personalab import Persona
from personalab.llm import OpenAIClient
from dotenv import load_dotenv
load_dotenv()

class InteractiveChatDemo:
    def __init__(self):
        self.persona = None
        self.user_id = None
        self.session_count = 0
        
    def setup(self):
        print("PersonaLab 交互式聊天演示")
        print("=" * 40)
        
        # 检查API配置
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("错误：请设置 OPENAI_API_KEY 环境变量")
            return False
        
        # 获取用户信息
        self.user_id = input("你的名字: ").strip() or "用户"
        personality = input("AI个性 (回车使用默认): ").strip()
        if not personality:
            personality = f"你是一个友善、聪明的AI助手，正在与{self.user_id}对话。"
        
        # 创建Persona
        try:
            self.persona = Persona(
                agent_id="interactive_assistant",
                personality=personality,
                use_memory=True,
                use_memo=True,
                show_retrieval=False
            )
            print(f"已创建AI助手，准备与 {self.user_id} 对话")
            return True
        except Exception as e:
            print(f"创建AI助手失败: {e}")
            return False
    
    def display_retrieved_conversations(self, user_input: str):
        """显示检索到的相关历史对话"""
        try:
            memo = self.persona._get_or_create_memo(self.user_id)
            if not memo:
                return
                
            similar_conversations = memo.search_similar_conversations(
                agent_id=self.persona.agent_id,
                query=user_input,
                limit=2,
                similarity_threshold=0.6
            )
            
            if not similar_conversations:
                print("未找到相关历史对话")
                return
            
            print(f"找到 {len(similar_conversations)} 条相关历史对话:")
            print("-" * 40)
            
            for i, conv_summary in enumerate(similar_conversations, 1):
                conversation = memo.db.get_conversation(conv_summary['conversation_id'])
                
                if conversation:
                    print(f"对话 {i} (相似度: {conv_summary['similarity_score']:.3f})")
                    print(f"时间: {conversation.created_at.strftime('%m-%d %H:%M')}")
                    
                    # 显示对话内容
                    for msg in conversation.messages[:4]:  # 最多4条消息
                        role = "用户" if msg.role == "user" else "AI"
                        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                        print(f"  {role}: {content}")
                    
                    if len(conversation.messages) > 4:
                        print(f"  ... 还有 {len(conversation.messages) - 4} 条消息")
                    print()
            
        except Exception as e:
            print(f"检索历史对话失败: {e}")
    
    def display_memory(self):
        """显示记忆状态"""
        try:
            memory = self.persona.get_memory(self.user_id)
            
            print("\n=== 记忆状态 ===")
            print(f"Profile: {memory['profile'] or '暂无'}")
            print(f"Events: {len(memory['events'])} 条")
            if memory['events']:
                for event in memory['events'][-3:]:  # 显示最近3条
                    print(f"  - {event}")
            
            print(f"Mind: {len(memory['mind'])} 条")
            if memory['mind']:
                for insight in memory['mind'][-2:]:  # 显示最近2条
                    print(f"  - {insight}")
            
        except Exception as e:
            print(f"获取记忆失败: {e}")
    
    def chat_session(self):
        self.session_count += 1
        print(f"\n=== Session {self.session_count} ===")
        print("输入 'exit' 结束session, 'memory' 查看记忆, 'help' 查看帮助\n")
        
        message_count = 0
        
        while True:
            try:
                user_input = input(f"{self.user_id}: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.lower() in ['memory', 'mem']:
                    self.display_memory()
                    continue
                elif user_input.lower() in ['help', 'h']:
                    print("命令: 直接输入对话 | 'memory' 查看记忆 | 'exit' 退出")
                    continue
                
                # 显示相关历史对话
                self.display_retrieved_conversations(user_input)
                
                # AI对话
                response = self.persona.chat(user_input, user_id=self.user_id)
                print(f"AI: {response}\n")
                
                message_count += 1
                
            except KeyboardInterrupt:
                print("\n退出session...")
                break
            except Exception as e:
                print(f"对话出错: {e}")
        
        # 更新记忆
        if message_count > 0:
            try:
                result = self.persona.endsession(self.user_id)
                print(f"记忆已更新: {result}")
            except Exception as e:
                print(f"记忆更新失败: {e}")
        
        return message_count > 0
    
    def run(self):
        if not self.setup():
            return
        
        try:
            while True:
                had_conversation = self.chat_session()
                
                if had_conversation:
                    self.display_memory()
                
                choice = input("\n继续新session? (y/n): ").strip().lower()
                if choice in ['n', 'no', 'q']:
                    break
        
        except KeyboardInterrupt:
            print("\n程序退出")
        
        finally:
            if self.persona:
                try:
                    self.persona.close()
                except:
                    pass
        
        print(f"总计 {self.session_count} 个session，感谢使用！")

def main():
    demo = InteractiveChatDemo()
    demo.run()

if __name__ == "__main__":
    main() 