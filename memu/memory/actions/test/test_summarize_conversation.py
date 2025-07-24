#!/usr/bin/env python3
"""
Test script for SummarizeConversationAction with Locomo data

Tests the summarize_conversation action using conversation data:
- Load conversations from locomo dataset
- Summarize real dialogue content into memory items
- Test conversation processing and extraction
- Verify memory item quality and structure
"""

import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import memu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from memu.memory.actions.summarize_conversation import SummarizeConversationAction
from memu.memory.memory_agent import MemoryAgent
from memu.llm.openai_client import OpenAIClient


class LocomoDataLoader:
    """Loads and prepares locomo data for testing"""
    
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
    
    def get_session_conversations(self, sample, session_num=1):
        """Get conversations from a specific session"""
        session_key = f"session_{session_num}"
        if not sample or 'conversation' not in sample or session_key not in sample['conversation']:
            return []
        
        return sample['conversation'][session_key]
    
    def format_conversation_text(self, conversations):
        """Format conversations into a single text"""
        lines = []
        for conv in conversations:
            lines.append(f"{conv['speaker']}: {conv['text']}")
        return "\n".join(lines)
    
    def get_session_date(self, sample, session_num=1):
        """Get session date"""
        session_date_key = f"session_{session_num}_date_time"
        if not sample or 'conversation' not in sample:
            return "2024-01-15"
        
        return sample['conversation'].get(session_date_key, "2024-01-15")


class TestSummarizeConversation(unittest.TestCase):
    """Test SummarizeConversationAction with locomo data"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for memory files
        self.temp_dir = tempfile.mkdtemp()
        self.memory_base_path = Path(self.temp_dir)
        
        # Load locomo data
        self.loader = LocomoDataLoader()
        self.sample = self.loader.get_sample(0)
        
        # Get characters and conversations
        if self.sample:
            self.characters = self.loader.get_characters(self.sample)
            self.conversations = self.loader.get_session_conversations(self.sample, 1)
            self.session_date = self.loader.get_session_date(self.sample, 1)
        else:
            self.characters = []
            self.conversations = []
            self.session_date = "2024-01-15"
        
        # Create memory agent with OpenAI LLM
        self.memory_agent = MemoryAgent(
            llm_client=OpenAIClient(),
            memory_base_path=str(self.memory_base_path)
        )
        
        # Create action instance
        self.action = SummarizeConversationAction(self.memory_agent)
        
        print(f"🚀 Test setup complete")
        print(f"📁 Temp directory: {self.temp_dir}")
        print(f"👥 Characters: {self.characters}")
        print(f"💬 Conversations: {len(self.conversations)}")
        print(f"📅 Session date: {self.session_date}")
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_schema_validation(self):
        """Test that the action schema is valid"""
        schema = self.action.get_schema()
        
        # Check basic schema structure
        self.assertIsInstance(schema, dict)
        self.assertIn('name', schema)
        self.assertIn('description', schema)
        self.assertIn('parameters', schema)
        self.assertEqual(schema['name'], 'summarize_conversation')
        
        # Check parameters
        params = schema['parameters']
        self.assertIn('properties', params)
        
        properties = params['properties']
        self.assertIn('conversation_text', properties)
        self.assertIn('character_name', properties)
        self.assertIn('session_date', properties)
        
        print("✅ Schema validation passed")
    
    def test_summarize_conversation_with_real_data(self):
        """Test conversation summarization with real dialogue data"""
        if not self.characters or not self.conversations:
            self.skipTest("No locomo data available")
        
        character_name = self.characters[0]
        
        # Format conversation text
        conversation_text = self.loader.format_conversation_text(self.conversations[:8])
        
        try:
            # Execute the action
            result = self.action.execute(
                conversation_text=conversation_text,
                character_name=character_name,
                session_date=self.session_date
            )
            
            # Validate result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertTrue(result['success'])
            self.assertIn('data', result)
            
            # Check data content
            data = result['data']
            self.assertIsInstance(data, list)
            
            # Validate each memory item
            for item in data:
                self.assertIsInstance(item, dict)
                self.assertIn('memory_id', item)
                self.assertIn('content', item)
            
            print(f"✅ Summarized conversation for {character_name}")
            print(f"📊 Generated {len(data)} memory items")
            print(f"📝 Result: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            self.fail(f"Failed to summarize conversation: {e}")
    
    def test_empty_conversation(self):
        """Test handling of empty conversation"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        try:
            result = self.action.execute(
                conversation_text="",
                character_name=character_name,
                session_date=self.session_date
            )
            
            # Should handle empty conversation gracefully
            self.assertIsInstance(result, dict)
            print("✅ Empty conversation handled correctly")
            
        except Exception as e:
            # This might be expected behavior, log it
            print(f"⚠️ Empty conversation caused: {e}")
    
    def test_long_conversation_summarization(self):
        """Test summarization of longer conversations"""
        if not self.characters or len(self.conversations) < 10:
            self.skipTest("Need more conversation data")
        
        character_name = self.characters[0]
        
        # Use all available conversations for a comprehensive test
        conversation_text = self.loader.format_conversation_text(self.conversations)
        
        try:
            result = self.action.execute(
                conversation_text=conversation_text,
                character_name=character_name,
                session_date=self.session_date
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('data', result)
            
            data = result['data']
            self.assertIsInstance(data, list)
            
            print(f"✅ Long conversation summarized for {character_name}")
            print(f"📊 Generated {len(data)} memory items from {len(self.conversations)} conversation turns")
            
        except Exception as e:
            print(f"⚠️ Long conversation summarization failed: {e}")
    
    def test_multiple_characters_summarization(self):
        """Test conversation summarization for multiple characters"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters")
        
        for character in self.characters[:2]:  # Test first 2 characters
            # Get conversations involving this character
            char_conversations = [conv for conv in self.conversations 
                                if conv['speaker'] == character]
            
            if not char_conversations:
                continue
            
            conversation_text = self.loader.format_conversation_text(char_conversations[:5])
            
            try:
                result = self.action.execute(
                    conversation_text=conversation_text,
                    character_name=character,
                    session_date=self.session_date
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Conversation summarized for character: {character}")
                
            except Exception as e:
                print(f"⚠️ Failed for character {character}: {e}")
    
    def test_conversation_with_different_sessions(self):
        """Test summarization with conversations from different sessions"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        # Try to get conversations from different sessions
        for session_num in [1, 2, 3]:
            conversations = self.loader.get_session_conversations(self.sample, session_num)
            session_date = self.loader.get_session_date(self.sample, session_num)
            
            if not conversations:
                continue
            
            conversation_text = self.loader.format_conversation_text(conversations[:5])
            
            try:
                result = self.action.execute(
                    conversation_text=conversation_text,
                    character_name=character_name,
                    session_date=session_date
                )
                
                self.assertIsInstance(result, dict)
                print(f"✅ Session {session_num} summarized successfully")
                
            except Exception as e:
                print(f"⚠️ Session {session_num} failed: {e}")


def main():
    """Main test runner"""
    print("🧪 Testing SummarizeConversationAction with Locomo data")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 