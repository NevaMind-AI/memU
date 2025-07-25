#!/usr/bin/env python3
"""
Comprehensive Memory Agent Test with Locomo Data

This script demonstrates the complete memory processing workflow using real locomo data:
- Process ALL sessions from locomo dataset
- Use the full memory agent workflow (8 steps)
- Real-time display of each action's results
- Complete memory generation and linking
"""

import sys
import os
import json
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not found. Install with: pip install python-dotenv")
    # Manual .env loading
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("✅ Manually loaded environment variables from .env file")

# Add the parent directory to the path so we can import memu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from memu.memory.memory_agent import MemoryAgent
from memu.llm.openai_client import OpenAIClient
from memu.llm.azure_openai_client import AzureOpenAIClient


def create_llm_client():
    """Create LLM client based on environment configuration"""
    provider = os.environ.get('LLM_PROVIDER', 'azure').lower()
    
    if provider == 'azure':
        # Check Azure configuration
        api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        deployment = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o-mini')
        api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')
        
        if not api_key or api_key == 'your_azure_openai_api_key_here':
            raise ValueError("Azure OpenAI API key not configured")
        if not endpoint or endpoint == 'https://your-resource-name.openai.azure.com/':
            raise ValueError("Azure OpenAI endpoint not configured")
        
        print(f"✅ Using Azure OpenAI: {endpoint}")
        print(f"   Deployment: {deployment}")
        print(f"   API Version: {api_version}")
        
        return AzureOpenAIClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            deployment_name=deployment,
            api_version=api_version
        )
    
    elif provider == 'openai':
        # Check OpenAI configuration
        api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key or api_key == 'your_openai_api_key_here':
            raise ValueError("OpenAI API key not configured")
        
        print(f"✅ Using OpenAI: {api_key[:12]}...")
        
        return OpenAIClient()
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'openai' or 'azure'")


class LocomoDataLoader:
    """Enhanced Locomo data loader with comprehensive session handling"""
    
    def __init__(self, data_path="./data/locomo10.json"):
        self.data_path = data_path
        self.data = None
        self.load_data()
    
    def load_data(self):
        """Load locomo data from JSON file"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✅ Loaded {len(self.data)} samples from locomo data")
        except Exception as e:
            print(f"❌ Failed to load locomo data: {e}")
            self.data = []
    
    def get_sample(self, index=0):
        """Get a specific sample from the data"""
        if not self.data or index >= len(self.data):
            return None
        return self.data[index]
    
    def get_characters(self, sample):
        """Extract character names from a sample"""
        if not sample or 'conversation' not in sample:
            return []
        
        characters = set()
        for session_key in sample['conversation']:
            if session_key.startswith('session_') and not session_key.endswith('_date_time'):
                for dialog in sample['conversation'][session_key]:
                    characters.add(dialog['speaker'])
        
        return list(characters)
    
    def get_all_sessions(self, sample):
        """Get all available session numbers"""
        if not sample or 'conversation' not in sample:
            return []
        
        sessions = []
        for key in sample['conversation']:
            if key.startswith('session_') and not key.endswith('_date_time'):
                session_num = int(key.split('_')[1])
                sessions.append(session_num)
        
        return sorted(sessions)
    
    def get_session_conversations(self, sample, session_num=1):
        """Get conversations from a specific session"""
        session_key = f"session_{session_num}"
        if not sample or 'conversation' not in sample or session_key not in sample['conversation']:
            return []
        
        return sample['conversation'][session_key]
    
    def get_session_date(self, sample, session_num=1):
        """Get session date"""
        session_date_key = f"session_{session_num}_date_time"
        if not sample or 'conversation' not in sample:
            return "2025-01-15"
        
        return sample['conversation'].get(session_date_key, "2025-01-15")
    
    def format_session_as_conversation(self, conversations):
        """Format entire session as a single conversation text"""
        if not conversations:
            return ""
        
        session_text = ""
        for dialog in conversations:
            session_text += f"{dialog['speaker']}: {dialog['text']}\n"
        
        return session_text.strip()
    
    def get_session_summary(self, conversations):
        """Get a brief summary of the session"""
        if not conversations:
            return "Empty session"
        
        speakers = set(d['speaker'] for d in conversations)
        return f"{len(conversations)} dialogues between {', '.join(speakers)}"


def print_section_header(title, level=1):
    """Print a formatted section header"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"🎯 {title}")
        print(f"{'='*80}")
    elif level == 2:
        print(f"\n{'-'*60}")
        print(f"📋 {title}")
        print(f"{'-'*60}")
    else:
        print(f"\n💡 {title}")


def print_action_result(action_name, result, step_num=None):
    """Print formatted action result"""
    step_prefix = f"STEP {step_num}: " if step_num else ""
    print(f"\n🔧 {step_prefix}{action_name.upper()} RESULT:")
    print("-" * 50)
    
    if isinstance(result, dict):
        success = result.get('success', False)
        print(f"✅ Success: {success}")
        
        if success:
            # Handle different action types
            if action_name == 'add_activity_memory':
                print(f"📊 Memory items added: {result.get('memory_items_added', 0)}")
                print(f"👤 Character: {result.get('character_name', 'N/A')}")
            
            elif action_name == 'get_available_categories':
                categories = result.get('available_categories', [])
                print(f"📋 Available categories: {categories}")
            
            elif action_name == 'generate_memory_suggestions':
                suggestions = result.get('suggestions', {})
                print(f"💡 Suggestions generated for {len(suggestions)} categories")
                for cat, suggestion in suggestions.items():
                    print(f"   - {cat}: {suggestion[:100]}...")
            
            elif action_name == 'update_memory_with_suggestions':
                modifications = result.get('modifications', [])
                category = result.get('category', 'unknown')
                print(f"📝 Category: {category}")
                print(f"✏️  Modifications: {len(modifications)}")
                for mod in modifications[:2]:  # Show first 2
                    memory_id = mod.get('memory_id', 'N/A')
                    content = mod.get('content', '')[:100]
                    print(f"   [{memory_id}] {content}...")
            
            elif action_name == 'link_related_memories':
                links_added = result.get('links_added', 0)
                category = result.get('category', 'unknown')
                print(f"🔗 Category: {category}")
                print(f"🔗 Links added: {links_added}")
            
            elif action_name == 'run_theory_of_mind':
                analysis = result.get('analysis', {})
                character = result.get('character_name', 'N/A')
                print(f"🧠 Character: {character}")
                if isinstance(analysis, dict):
                    for key, value in analysis.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"   {key}: {value[:100]}...")
                        else:
                            print(f"   {key}: {value}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Error: {error}")
    else:
        print(f"📊 Result: {result}")


def comprehensive_memory_test():
    """Run comprehensive memory processing test with all sessions"""
    
    print_section_header("COMPREHENSIVE MEMORY AGENT TEST WITH LOCOMO DATA")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check LLM provider configuration
    provider = os.environ.get('LLM_PROVIDER', 'azure').lower()
    print(f"🔧 LLM Provider: {provider.upper()}")
    
    try:
        llm_client = create_llm_client()
    except ValueError as e:
        print(f"❌ LLM configuration error: {e}")
        print("📝 Please configure your .env file properly")
        return
    
    # Load data
    data_loader = LocomoDataLoader()
    sample = data_loader.get_sample(0)
    
    if not sample:
        print("❌ No locomo data available")
        return
    
    # Get characters and sessions
    characters = data_loader.get_characters(sample)
    sessions = data_loader.get_all_sessions(sample)
    
    print(f"📊 Available characters: {characters}")
    print(f"📊 Total sessions available: {len(sessions)}")
    print(f"📊 Session range: {min(sessions)} - {max(sessions)}")
    print()
    
    if not characters or not sessions:
        print("❌ No characters or sessions found")
        return
    
    # Setup memory agent
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")
    
    try:
        # Create memory agent
        memory_agent = MemoryAgent(
            llm_client=llm_client,
            memory_dir=temp_dir,
            enable_embeddings=False
        )
        print("✅ Memory agent initialized successfully")
        
        # Test with first character across ALL sessions
        test_character = characters[0]
        print_section_header(f"PROCESSING ALL SESSIONS FOR {test_character}")
        
        total_processed = 0
        total_errors = 0
        session_results = []
        
        # Process each session
        for session_idx, session_num in enumerate(sessions, 1):
            print_section_header(f"SESSION {session_num} ({session_idx}/{len(sessions)})", level=2)
            
            # Get session data
            conversations = data_loader.get_session_conversations(sample, session_num)
            if not conversations:
                print(f"⚠️ No conversations in session {session_num}")
                continue
            
            # Check character participation
            character_dialogues = [d for d in conversations if d['speaker'] == test_character]
            if not character_dialogues:
                print(f"⚠️ {test_character} not in session {session_num}")
                continue
            
            session_date = data_loader.get_session_date(sample, session_num)
            session_text = data_loader.format_session_as_conversation(conversations)
            session_summary = data_loader.get_session_summary(conversations)
            
            print(f"📅 Date: {session_date}")
            print(f"📊 Summary: {session_summary}")
            print(f"👤 {test_character} has {len(character_dialogues)} dialogues")
            
            # Display session content (first few dialogues)
            print(f"\n📝 Session Content Preview:")
            for i, dialog in enumerate(conversations[:5], 1):
                print(f"  {i:2d}. {dialog['speaker']}: {dialog['text'][:80]}...")
            if len(conversations) > 5:
                print(f"     ... and {len(conversations) - 5} more dialogues")
            
            try:
                # Use Memory Agent's complete workflow
                print(f"\n🚀 Starting Memory Agent workflow for session {session_num}...")
                start_time = time.time()
                
                # Convert conversations to the format expected by memory agent
                conversation_list = []
                for dialog in conversations:
                    conversation_list.append({
                        "speaker": dialog['speaker'],
                        "message": dialog['text']
                    })
                
                result = memory_agent.run(
                    conversation=conversation_list,
                    character_name=test_character,
                    max_iterations=15  # Allow for complete workflow
                )
                
                processing_time = time.time() - start_time
                
                # Display workflow results
                print_section_header(f"WORKFLOW RESULTS - SESSION {session_num}", level=3)
                print(f"⏱️  Processing time: {processing_time:.2f} seconds")
                print(f"✅ Success: {result.get('success', False)}")
                print(f"🔄 Iterations: {result.get('iterations', 0)}")
                
                if result.get('success'):
                    # Show function call results
                    function_calls = result.get('function_calls', [])
                    print(f"🔧 Total function calls: {len(function_calls)}")
                    
                    for i, func_result in enumerate(function_calls, 1):
                        func_name = func_result.get('function_name', 'unknown')
                        func_success = func_result.get('success', False)
                        print_action_result(func_name, func_result, step_num=i)
                    
                    # Show memory file status
                    print(f"\n📁 Memory Files Created:")
                    memory_files = []
                    for category in ['activity', 'profile', 'event']:
                        memory_file = os.path.join(temp_dir, f"{test_character}_{category}.md")
                        if os.path.exists(memory_file):
                            size = os.path.getsize(memory_file)
                            memory_files.append(f"{category}: {size} bytes")
                    
                    if memory_files:
                        for file_info in memory_files:
                            print(f"   📄 {file_info}")
                    else:
                        print("   ⚠️ No memory files found")
                    
                    total_processed += 1
                    session_results.append({
                        'session': session_num,
                        'success': True,
                        'processing_time': processing_time,
                        'function_calls': len(function_calls)
                    })
                    
                else:
                    print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                    total_errors += 1
                    session_results.append({
                        'session': session_num,
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    })
                
            except Exception as e:
                print(f"❌ Exception during session {session_num}: {e}")
                total_errors += 1
                session_results.append({
                    'session': session_num,
                    'success': False,
                    'error': str(e)
                })
            
            # Small delay between sessions to avoid rate limits
            if session_idx < len(sessions):
                print("\n⏳ Waiting 2 seconds before next session...")
                time.sleep(2)
        
        # Final summary
        print_section_header("COMPREHENSIVE TEST SUMMARY")
        print(f"👤 Character processed: {test_character}")
        print(f"📊 Total sessions attempted: {len(sessions)}")
        print(f"✅ Successfully processed: {total_processed}")
        print(f"❌ Errors encountered: {total_errors}")
        print(f"📈 Success rate: {(total_processed / len(sessions)) * 100:.1f}%")
        
        # Show session breakdown
        print(f"\n📋 Session Results:")
        for result in session_results:
            session = result['session']
            success = result['success']
            status = "✅ PASS" if success else "❌ FAIL"
            
            if success:
                time_taken = result.get('processing_time', 0)
                func_calls = result.get('function_calls', 0)
                print(f"   Session {session:2d}: {status} ({time_taken:.1f}s, {func_calls} calls)")
            else:
                error = result.get('error', 'Unknown')
                print(f"   Session {session:2d}: {status} - {error[:50]}...")
        
        # Show final memory state
        print(f"\n📁 Final Memory State:")
        for category in ['activity', 'profile', 'event']:
            memory_file = os.path.join(temp_dir, f"{test_character}_{category}.md")
            if os.path.exists(memory_file):
                with open(memory_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.count('\n') + 1
                size = len(content)
                print(f"   📄 {category}: {lines} lines, {size} characters")
                
                # Show a few sample memory items
                memory_items = [line for line in content.split('\n') if line.strip().startswith('[')]
                if memory_items:
                    print(f"      Sample items: {len(memory_items)} total")
                    for item in memory_items[:2]:
                        item_id = item.split(']')[0] + ']' if ']' in item else 'N/A'
                        item_preview = item[item.find(']') + 1:].strip()[:60] if ']' in item else item[:60]
                        print(f"        {item_id} {item_preview}...")
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            print(f"\n🧹 Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
    
    print(f"\n✅ Comprehensive test completed!")
    print(f"🕒 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    comprehensive_memory_test() 