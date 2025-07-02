#!/usr/bin/env python3
"""
PersonaLab Example 07: Production-Ready Implementation
=====================================================

This example demonstrates production-ready patterns and best practices for deploying
PersonaLab in real-world applications.

You'll learn how to:
- Implement proper error handling and logging
- Create configuration-driven setups
- Build interactive chat applications
- Handle user sessions and persistence
- Implement monitoring and analytics
- Create scalable conversation flows

Prerequisites:
1. Install PersonaLab: pip install -e .
2. Set up your .env file with API keys:
   - OPENAI_API_KEY="your-openai-key"
   OR
   - ANTHROPIC_API_KEY="your-anthropic-key"
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from personalab import Persona
from personalab.llm import AnthropicClient, CustomLLMClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionChatBot:
    """Production-ready chatbot implementation using PersonaLab"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.personas = {}  # Store active personas by user ID
        self.session_stats = {}  # Track session statistics
        self.error_count = 0
        
        # Configure logging
        if config.get('enable_logging', True):
            self.setup_logging()
        
        logger.info("ProductionChatBot initialized with config: %s", config)
    
    def setup_logging(self):
        """Setup production logging configuration"""
        log_file = self.config.get('log_file', 'chatbot.log')
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.info("Logging configured to file: %s", log_file)
    
    def get_or_create_persona(self, user_id: str) -> Optional[Persona]:
        """Get existing persona or create new one for user"""
        try:
            if user_id not in self.personas:
                logger.info("Creating new persona for user: %s", user_id)
                
                # Create persona based on configuration
                if self.config.get('llm_provider') == 'anthropic':
                    anthropic_client = AnthropicClient()
                    persona = Persona(
                        agent_id=user_id,
                        llm_client=anthropic_client,
                        use_memory=self.config.get('use_memory', True),
                        use_memo=self.config.get('use_memo', True),
                        show_retrieval=self.config.get('show_retrieval', False)
                    )
                elif self.config.get('llm_provider') == 'custom':
                    custom_client = CustomLLMClient(llm_function=self.config.get('custom_llm_function'))
                    persona = Persona(
                        agent_id=user_id,
                        llm_client=custom_client,
                        use_memory=self.config.get('use_memory', True),
                        use_memo=self.config.get('use_memo', True),
                        show_retrieval=self.config.get('show_retrieval', False)
                    )
                else:  # Default to OpenAI
                    persona = Persona(
                        agent_id=user_id,
                        use_memory=self.config.get('use_memory', True),
                        use_memo=self.config.get('use_memo', True),
                        show_retrieval=self.config.get('show_retrieval', False)
                    )
                
                self.personas[user_id] = persona
                self.session_stats[user_id] = {
                    'created_at': datetime.now().isoformat(),
                    'message_count': 0,
                    'error_count': 0,
                    'last_activity': datetime.now().isoformat()
                }
            
            return self.personas[user_id]
            
        except Exception as e:
            logger.error("Failed to create persona for user %s: %s", user_id, e)
            self.error_count += 1
            return None
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Process user message and return response with metadata"""
        start_time = time.time()
        
        try:
            # Input validation
            if not isinstance(message, str) or not message.strip():
                return {
                    'success': False,
                    'error': 'Invalid message: message must be a non-empty string',
                    'response': None,
                    'processing_time': time.time() - start_time
                }
            
            # Length validation
            max_length = self.config.get('max_message_length', 1000)
            if len(message) > max_length:
                message = message[:max_length] + "..."
                logger.warning("Message truncated for user %s (length: %d)", user_id, len(message))
            
            # Get persona
            persona = self.get_or_create_persona(user_id)
            if not persona:
                return {
                    'success': False,
                    'error': 'Failed to initialize chat session',
                    'response': None,
                    'processing_time': time.time() - start_time
                }
            
            # Process message
            response = persona.chat(message, learn=self.config.get('enable_learning', True))
            
            # Update session stats
            self.session_stats[user_id]['message_count'] += 1
            self.session_stats[user_id]['last_activity'] = datetime.now().isoformat()
            
            processing_time = time.time() - start_time
            
            logger.info("Message processed for user %s in %.2fs", user_id, processing_time)
            
            return {
                'success': True,
                'response': response,
                'processing_time': processing_time,
                'session_stats': self.session_stats[user_id].copy()
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.error_count += 1
            
            if user_id in self.session_stats:
                self.session_stats[user_id]['error_count'] += 1
            
            logger.error("Error processing message for user %s: %s", user_id, e)
            
            return {
                'success': False,
                'error': str(e),
                'response': self.config.get('error_fallback_message', 
                                         "I apologize, but I'm experiencing technical difficulties. Please try again."),
                'processing_time': processing_time
            }
    
    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """Get user's memory summary"""
        try:
            persona = self.personas.get(user_id)
            if not persona:
                return {'error': 'User session not found'}
            
            memory = persona.get_memory()
            return {
                'success': True,
                'memory': memory,
                'memory_stats': {
                    'facts': len(memory.get('facts', [])),
                    'preferences': len(memory.get('preferences', [])),
                    'events': len(memory.get('events', []))
                }
            }
            
        except Exception as e:
            logger.error("Error getting memory for user %s: %s", user_id, e)
            return {'error': str(e)}
    
    def search_conversations(self, user_id: str, query: str) -> Dict[str, Any]:
        """Search user's conversation history"""
        try:
            persona = self.personas.get(user_id)
            if not persona:
                return {'error': 'User session not found'}
            
            results = persona.search(query)
            return {
                'success': True,
                'query': query,
                'results': results,
                'result_count': len(results)
            }
            
        except Exception as e:
            logger.error("Error searching conversations for user %s: %s", user_id, e)
            return {'error': str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        return {
            'active_sessions': len(self.personas),
            'total_errors': self.error_count,
            'session_stats': self.session_stats.copy(),
            'config': {
                'llm_provider': self.config.get('llm_provider', 'openai'),
                'use_memory': self.config.get('use_memory', True),
                'use_memo': self.config.get('use_memo', True),
                'enable_learning': self.config.get('enable_learning', True)
            }
        }
    
    def cleanup_session(self, user_id: str) -> bool:
        """Cleanup user session"""
        try:
            if user_id in self.personas:
                self.personas[user_id].close()
                del self.personas[user_id]
                
                if user_id in self.session_stats:
                    del self.session_stats[user_id]
                
                logger.info("Session cleaned up for user: %s", user_id)
                return True
                
        except Exception as e:
            logger.error("Error cleaning up session for user %s: %s", user_id, e)
            
        return False
    
    def shutdown(self):
        """Gracefully shutdown the chatbot"""
        logger.info("Shutting down chatbot...")
        
        for user_id in list(self.personas.keys()):
            self.cleanup_session(user_id)
        
        logger.info("Chatbot shutdown complete")


def demo_production_configuration():
    """Demonstrate production configuration patterns"""
    print("⚙️  Production Configuration Demo")
    print("=" * 50)
    
    # Example configurations for different environments
    configurations = {
        'development': {
            'llm_provider': 'custom',
            'custom_llm_function': lambda messages, **kwargs: f"Dev response: {messages[-1]['content']}",
            'use_memory': True,
            'use_memo': True,
            'show_retrieval': True,
            'enable_learning': True,
            'enable_logging': True,
            'log_file': 'dev_chatbot.log',
            'max_message_length': 500,
            'error_fallback_message': 'Development mode: Something went wrong.'
        },
        'production': {
            'llm_provider': 'openai',  # or 'anthropic' with API key
            'use_memory': True,
            'use_memo': True,
            'show_retrieval': False,
            'enable_learning': True,
            'enable_logging': True,
            'log_file': 'prod_chatbot.log',
            'max_message_length': 1000,
            'error_fallback_message': 'I apologize for the inconvenience. Please try again.'
        },
        'testing': {
            'llm_provider': 'custom',
            'custom_llm_function': lambda messages, **kwargs: "Test response for automated testing",
            'use_memory': False,
            'use_memo': False,
            'show_retrieval': False,
            'enable_learning': False,
            'enable_logging': False,
            'max_message_length': 100,
            'error_fallback_message': 'Test error response'
        }
    }
    
    # Show configuration options
    for env_name, config in configurations.items():
        print(f"\n📋 {env_name.upper()} Configuration:")
        for key, value in config.items():
            if callable(value):
                print(f"  {key}: <function>")
            else:
                print(f"  {key}: {value}")
    
    print("\n✅ Configuration patterns demonstrated")
    print("\n" + "=" * 50 + "\n")


def demo_production_chatbot():
    """Demonstrate production chatbot usage"""
    print("🤖 Production ChatBot Demo")
    print("=" * 50)
    
    # Use development configuration for demo
    def mock_llm_function(messages, **kwargs):
        user_msg = messages[-1]['content']
        return f"I understand you said: '{user_msg}'. This is a production-ready response with proper error handling and logging."
    
    config = {
        'llm_provider': 'custom',
        'custom_llm_function': mock_llm_function,
        'use_memory': True,
        'use_memo': True,
        'show_retrieval': False,
        'enable_learning': True,
        'enable_logging': True,
        'log_file': 'demo_chatbot.log',
        'max_message_length': 1000,
        'error_fallback_message': 'I apologize, but I encountered an error. Please try again.'
    }
    
    # Create production chatbot
    chatbot = ProductionChatBot(config)
    
    # Simulate multiple users
    users = ['alice', 'bob', 'charlie']
    conversations = {
        'alice': [
            "Hello! I'm a data scientist.",
            "I work with Python and machine learning.",
            "What do you remember about me?"
        ],
        'bob': [
            "Hi, I'm learning web development.",
            "I'm interested in React and Node.js.",
            "Can you help me with JavaScript?"
        ],
        'charlie': [
            "Good morning! I'm a product manager.",
            "I work on mobile app development.",
            "What technologies should I learn?"
        ]
    }
    
    # Process conversations
    for user_id, messages in conversations.items():
        print(f"\n👤 User: {user_id}")
        print("-" * 30)
        
        for i, message in enumerate(messages, 1):
            print(f"\n[{i}] {user_id}: {message}")
            
            result = chatbot.process_message(user_id, message)
            
            if result['success']:
                print(f"[{i}] Bot: {result['response']}")
                print(f"     ⏱️  Processing time: {result['processing_time']:.2f}s")
            else:
                print(f"[{i}] Error: {result['error']}")
                print(f"[{i}] Fallback: {result['response']}")
    
    # Demonstrate system monitoring
    print(f"\n📊 System Statistics:")
    stats = chatbot.get_system_stats()
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Total errors: {stats['total_errors']}")
    
    # Demonstrate memory retrieval
    print(f"\n🧠 Memory Examples:")
    for user_id in users[:2]:  # Show first 2 users
        memory_result = chatbot.get_user_memory(user_id)
        if memory_result.get('success'):
            stats = memory_result['memory_stats']
            print(f"  {user_id}: {stats['facts']} facts, {stats['preferences']} preferences, {stats['events']} events")
    
    # Demonstrate search functionality
    print(f"\n🔍 Search Examples:")
    search_result = chatbot.search_conversations('alice', 'data science')
    if search_result.get('success'):
        print(f"  Alice - 'data science': {search_result['result_count']} results found")
    
    # Cleanup
    print(f"\n🧹 Cleaning up sessions...")
    for user_id in users:
        success = chatbot.cleanup_session(user_id)
        print(f"  {user_id}: {'✅' if success else '❌'}")
    
    chatbot.shutdown()
    print("\n" + "=" * 50 + "\n")


def demo_interactive_production_chat():
    """Interactive production chat demo"""
    print("💬 Interactive Production Chat")
    print("=" * 50)
    print("Type 'help' for commands, 'quit' to exit")
    
    # Check if real LLM is available
    has_api_key = bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'))
    
    if has_api_key:
        config = {
            'llm_provider': 'openai',
            'use_memory': True,
            'use_memo': True,
            'show_retrieval': False,
            'enable_learning': True,
            'enable_logging': False,  # Disable for interactive demo
            'max_message_length': 1000
        }
        print("✅ Using real LLM provider")
    else:
        def interactive_mock_llm(messages, **kwargs):
            user_msg = messages[-1]['content']
            return f"Mock response: I understand your message about '{user_msg}'. This demonstrates production-ready PersonaLab integration."
        
        config = {
            'llm_provider': 'custom',
            'custom_llm_function': interactive_mock_llm,
            'use_memory': True,
            'use_memo': True,
            'show_retrieval': True,
            'enable_learning': True,
            'enable_logging': False,
            'max_message_length': 1000
        }
        print("⚠️  Using mock LLM (no API key found)")
    
    chatbot = ProductionChatBot(config)
    user_id = "interactive_user"
    
    print("\nCommands:")
    print("  help     - Show this help")
    print("  memory   - Show your memory")
    print("  search <query> - Search conversations")
    print("  stats    - Show system statistics")
    print("  quit     - Exit chat")
    print("-" * 50)
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            elif user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  memory   - Show your memory")
                print("  search <query> - Search conversations")
                print("  stats    - Show system statistics")
                print("  quit     - Exit chat")
            elif user_input.lower() == 'memory':
                result = chatbot.get_user_memory(user_id)
                if result.get('success'):
                    memory = result['memory']
                    print("\n📋 Your Memory:")
                    for key, values in memory.items():
                        if values:
                            print(f"  {key.upper()}: {len(values)} items")
                            for item in values[:2]:  # Show first 2
                                print(f"    • {item}")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
            elif user_input.lower().startswith('search '):
                query = user_input[7:].strip()
                if query:
                    result = chatbot.search_conversations(user_id, query)
                    if result.get('success'):
                        print(f"\n🔍 Search results for '{query}': {result['result_count']} found")
                        for i, item in enumerate(result['results'][:3], 1):
                            summary = item.get('summary', 'No summary')
                            print(f"  {i}. {summary[:80]}...")
                    else:
                        print(f"❌ Search error: {result.get('error', 'Unknown error')}")
                else:
                    print("❌ Please provide a search query")
            elif user_input.lower() == 'stats':
                stats = chatbot.get_system_stats()
                print("\n📊 System Statistics:")
                print(f"  Active sessions: {stats['active_sessions']}")
                print(f"  Total errors: {stats['total_errors']}")
                print(f"  Configuration: {stats['config']}")
            else:
                # Regular chat message
                result = chatbot.process_message(user_id, user_input)
                
                if result['success']:
                    print(f"AI: {result['response']}")
                    print(f"⏱️  ({result['processing_time']:.2f}s)")
                else:
                    print(f"❌ Error: {result['error']}")
                    if result['response']:
                        print(f"AI: {result['response']}")
    
    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted by user")
    
    finally:
        chatbot.cleanup_session(user_id)
        chatbot.shutdown()
        print("Session ended. Goodbye! 👋")


def main():
    """Main function"""
    print("🏭 PersonaLab Production-Ready Implementation")
    print("=" * 50)
    print("This demo showcases production patterns and best practices.\n")
    
    try:
        # Run production demos
        demo_production_configuration()
        demo_production_chatbot()
        
        # Interactive demo
        print("Would you like to try the interactive chat? (y/n): ", end="")
        choice = input().strip().lower()
        
        if choice in ['y', 'yes']:
            demo_interactive_production_chat()
        
        print("\n✅ Production-Ready Demo Complete!")
        print("=" * 50)
        print("\n💡 Production Best Practices:")
        print("  • Comprehensive error handling and logging")
        print("  • Configuration-driven architecture")
        print("  • Session management and cleanup")
        print("  • Input validation and sanitization")
        print("  • Performance monitoring and statistics")
        print("  • Graceful degradation and fallbacks")
        print("\n🚀 Ready for Production:")
        print("  • Multi-user session handling")
        print("  • Memory persistence across sessions")
        print("  • Conversation search and retrieval")
        print("  • System monitoring and health checks")
        print("  • Scalable architecture patterns")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main() 