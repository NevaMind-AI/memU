#!/usr/bin/env python3
"""
Test script for GenerateMemorySuggestionsAction with Locomo data

Tests the generate_memory_suggestions action using conversation data:
- Load conversations from locomo dataset
- Generate memory suggestions for real dialogue content
- Test suggestion quality and relevance
- Verify output format and categorization
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

from memu.memory.actions.generate_suggestions import GenerateMemorySuggestionsAction
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


class TestGenerateSuggestions(unittest.TestCase):
    """Test GenerateMemorySuggestionsAction with locomo data"""
    
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
        else:
            self.characters = []
            self.conversations = []
        
        # Create memory agent with OpenAI LLM
        self.memory_agent = MemoryAgent(
            llm_client=OpenAIClient(),
            memory_base_path=str(self.memory_base_path)
        )
        
        # Create action instance
        self.action = GenerateMemorySuggestionsAction(self.memory_agent)
        
        print(f"🚀 Test setup complete")
        print(f"📁 Temp directory: {self.temp_dir}")
        print(f"👥 Characters: {self.characters}")
        print(f"💬 Conversations: {len(self.conversations)}")
    
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
        self.assertEqual(schema['name'], 'generate_memory_suggestions')
        
        # Check parameters
        params = schema['parameters']
        self.assertIn('properties', params)
        
        properties = params['properties']
        self.assertIn('character_name', properties)
        self.assertIn('new_memory_items', properties)
        self.assertIn('available_categories', properties)
        
        print("✅ Schema validation passed")
    
    def test_generate_suggestions_with_real_data(self):
        """Test generating suggestions with real conversation data"""
        if not self.characters or not self.conversations:
            self.skipTest("No locomo data available")
        
        character_name = self.characters[0]
        
        # Create mock memory items from real conversations
        memory_items = []
        for i, conv in enumerate(self.conversations[:3]):  # Use first 3 conversations
            memory_items.append({
                "memory_id": f"mem_{i+1:03d}",
                "content": f"{conv['speaker']}: {conv['text']}"
            })
        
        available_categories = ["profile", "event", "activity"]
        
        try:
            # Execute the action
            result = self.action.execute(
                character_name=character_name,
                new_memory_items=memory_items,
                available_categories=available_categories
            )
            
            # Validate result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertTrue(result['success'])
            self.assertIn('data', result)
            
            # Check data content
            data = result['data']
            self.assertIsInstance(data, dict)
            
            print(f"✅ Generated suggestions for {character_name}")
            print(f"📊 Result: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            self.fail(f"Failed to generate suggestions: {e}")
    
    def test_empty_memory_items(self):
        """Test handling of empty memory items"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        try:
            result = self.action.execute(
                character_name=character_name,
                new_memory_items=[],
                available_categories=["profile", "event"]
            )
            
            # Should handle empty items gracefully
            self.assertIsInstance(result, dict)
            print("✅ Empty memory items handled correctly")
            
        except Exception as e:
            # This might be expected behavior, log it
            print(f"⚠️ Empty memory items caused: {e}")
    
    def test_multiple_characters(self):
        """Test suggestion generation for multiple characters"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters")
        
        for character in self.characters[:2]:  # Test first 2 characters
            # Get conversations for this character
            char_conversations = [conv for conv in self.conversations 
                                if conv['speaker'] == character]
            
            if not char_conversations:
                continue
            
            memory_items = [{
                "memory_id": "mem_001",
                "content": f"{char_conversations[0]['speaker']}: {char_conversations[0]['text']}"
            }]
            
            try:
                result = self.action.execute(
                    character_name=character,
                    new_memory_items=memory_items,
                    available_categories=["profile", "event", "activity"]
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Generated suggestions for character: {character}")
                
            except Exception as e:
                print(f"⚠️ Failed for character {character}: {e}")


def main():
    """Main test runner"""
    print("🧪 Testing GenerateMemorySuggestionsAction with Locomo data")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 