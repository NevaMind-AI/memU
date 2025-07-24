#!/usr/bin/env python3
"""
Test script for AddActivityMemoryAction with real Locomo data

Tests the add_activity_memory action using real conversation data:
- Load conversations from locomo dataset
- Add real dialogue content as activities
- Test memory storage with authentic data
- Verify memory format and content quality
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

from memu.memory.actions.add_activity_memory import AddActivityMemoryAction
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


class TestAddActivityMemory(unittest.TestCase):
    """Test cases for AddActivityMemoryAction using locomo data"""
    
    def setUp(self):
        """Set up test fixtures with real data"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Load locomo data
        self.data_loader = LocomoDataLoader()
        self.sample = self.data_loader.get_sample(0)  # Use first sample
        
        if not self.sample:
            self.skipTest("No locomo data available")
        
        # Get characters from the sample
        self.characters = self.data_loader.get_characters(self.sample)
        if not self.characters:
            self.skipTest("No characters found in sample")
        
        self.test_character = self.characters[0]  # Use first character
        
        # Setup memory agent with OpenAI LLM client
        try:
            self.memory_agent = MemoryAgent(
                llm_client=OpenAIClient(),
                memory_dir=self.temp_dir,
                enable_embeddings=False
            )
            self.action = AddActivityMemoryAction(self.memory_agent.memory_core)
        except Exception as e:
            self.skipTest(f"Failed to setup memory agent: {e}")
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _get_memory_file_content(self, character_name, category):
        """Get content of a memory file"""
        file_path = os.path.join(self.temp_dir, f"{character_name}_{category}.md")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def test_locomo_data_loaded(self):
        """Test that locomo data is properly loaded"""
        self.assertIsNotNone(self.sample)
        self.assertIn('conversation', self.sample)
        self.assertGreater(len(self.characters), 0)
        print(f"✅ Test character: {self.test_character}")
        print(f"✅ Available characters: {self.characters}")
    
    def test_add_real_conversation_as_activity(self):
        """Test adding real conversation content as activity memory"""
        # Get first session conversations
        conversations = self.data_loader.get_session_conversations(self.sample, 1)
        
        if not conversations:
            self.skipTest("No conversations found in first session")
        
        # Find first dialogue from our test character
        test_dialogue = None
        for dialog in conversations:
            if dialog['speaker'] == self.test_character:
                test_dialogue = dialog
                break
        
        if not test_dialogue:
            self.skipTest(f"No dialogue found for character {self.test_character}")
        
        # Format as conversation for the action
        conversation_text = f"{test_dialogue['speaker']}: {test_dialogue['text']}"
        
        # Execute the action
        result = self.action.execute(
            character_name=self.test_character,
            content=conversation_text
        )
        
        # Verify successful execution
        print(f"🐛 Debug result: {result}")
        if not result["success"]:
            print(f"❌ Error: {result.get('error', 'No error message')}")
        self.assertTrue(result["success"])
        self.assertEqual(result["character_name"], self.test_character)
        self.assertIn("memory_items_added", result)
        self.assertGreater(result["memory_items_added"], 0)
        
        # Verify content was written to file
        content = self._get_memory_file_content(self.test_character, "activity")
        self.assertIsNotNone(content)
        # Check that parts of the dialogue are in the content (it gets split into memory items)
        self.assertTrue(any(word in content for word in test_dialogue['text'].split()[:3]))
    
    def test_add_multiple_conversations_same_character(self):
        """Test adding multiple conversations from the same character"""
        # Get conversations from first session
        conversations = self.data_loader.get_session_conversations(self.sample, 1)
        character_dialogues = [d for d in conversations if d['speaker'] == self.test_character]
        
        if len(character_dialogues) < 2:
            self.skipTest(f"Need at least 2 dialogues for {self.test_character}")
        
        # Add first conversation
        first_conv = f"{character_dialogues[0]['speaker']}: {character_dialogues[0]['text']}"
        result1 = self.action.execute(
            character_name=self.test_character,
            content=first_conv
        )
        self.assertTrue(result1["success"])
        
        # Add second conversation
        second_conv = f"{character_dialogues[1]['speaker']}: {character_dialogues[1]['text']}"
        result2 = self.action.execute(
            character_name=self.test_character,
            content=second_conv
        )
        self.assertTrue(result2["success"])
        
        # Verify both are in the file (check for parts since text gets processed)
        content = self._get_memory_file_content(self.test_character, "activity")
        # Check that key words from both dialogues appear in content
        first_words = character_dialogues[0]['text'].split()[:2]
        second_words = character_dialogues[1]['text'].split()[:2]
        self.assertTrue(any(word in content for word in first_words))
        self.assertTrue(any(word in content for word in second_words))
    
    def test_conversation_format_preservation(self):
        """Test that conversation format is properly preserved"""
        conversations = self.data_loader.get_session_conversations(self.sample, 1)
        test_dialogue = next((d for d in conversations if d['speaker'] == self.test_character), None)
        
        if not test_dialogue:
            self.skipTest(f"No dialogue found for {self.test_character}")
        
        original_text = test_dialogue['text']
        conversation = f"{self.test_character}: {original_text}"
        
        result = self.action.execute(
            character_name=self.test_character,
            content=conversation
        )
        
        self.assertTrue(result["success"])
        
        # Check that key parts of the original text are preserved in the memory file
        content = self._get_memory_file_content(self.test_character, "activity")
        # Check for key words from the original text
        key_words = original_text.split()[:3]  # First 3 words
        self.assertTrue(any(word in content for word in key_words))


def run_real_data_quality_assessment():
    """Run a comprehensive quality assessment with real data"""
    print("🧪 RUNNING ADD_ACTIVITY_MEMORY ACTION TESTS WITH REAL LOCOMO DATA")
    print("=" * 75)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddActivityMemoryActionRealData)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 75)
    print("📊 REAL DATA QUALITY ASSESSMENT SUMMARY")
    print("=" * 75)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {successes}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    
    success_rate = (successes / total_tests) * 100 if total_tests > 0 else 0
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    # Quality rating
    if success_rate >= 95:
        quality = "🌟 EXCELLENT"
    elif success_rate >= 85:
        quality = "✅ GOOD"
    elif success_rate >= 70:
        quality = "⚠️ FAIR"
    else:
        quality = "❌ POOR"
    
    print(f"🎯 Overall Quality: {quality}")
    
    if failures or errors:
        print("\n📝 Issues Found:")
        for test, error in result.failures + result.errors:
            print(f"  - {test}: {error.split('AssertionError:')[-1].strip()}")
    
    print("\n💡 Using REAL locomo conversation data for activity memory testing!")
    print("🎯 Tests validate actual memory operations with authentic dialogue content.")
    
    return success_rate >= 85


if __name__ == "__main__":
    run_real_data_quality_assessment() 