#!/usr/bin/env python3
"""
Test script for DeleteMemoryAction with real Locomo data

Tests the quality and functionality of the delete_memory action using
real conversation data from the locomo dataset:
- Load first few sessions from locomo data
- Create real memory files for characters
- Test memory operations with actual data
- Verify functionality without mocking
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

from memu.memory.actions.delete_memory import DeleteMemoryAction
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
    
    def get_conversations_by_character(self, sample, character):
        """Get all conversations for a specific character"""
        conversations = []
        if not sample or 'conversation' not in sample:
            return conversations
        
        for session_key in sample['conversation']:
            if session_key.startswith('session_') and not session_key.endswith('_date_time'):
                session_convs = []
                for dialog in sample['conversation'][session_key]:
                    if dialog['speaker'] == character:
                        session_convs.append(dialog['text'])
                if session_convs:
                    conversations.extend(session_convs)
        
        return conversations
    
    def get_events_by_character(self, sample, character):
        """Get events for a specific character"""
        events = []
        if not sample or 'event_summary' not in sample:
            return events
        
        for session_key, session_data in sample['event_summary'].items():
            if character in session_data and session_data[character]:
                events.extend(session_data[character])
        
        return events


class TestDeleteMemory(unittest.TestCase):
    """Test cases for DeleteMemoryAction using locomo data"""
    
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
        
        # Setup memory agent with real configuration
        try:
            self.memory_agent = MemoryAgent(
                llm_client=OpenAIClient(),
                memory_dir=self.temp_dir,
                enable_embeddings=False  # Disable embeddings for testing
            )
            self.action = DeleteMemoryAction(self.memory_agent.memory_core)
        except Exception as e:
            self.skipTest(f"Failed to setup memory agent: {e}")
        
        # Create sample memory files
        self._create_sample_memories()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_memories(self):
        """Create sample memory files using real data"""
        conversations = self.data_loader.get_conversations_by_character(
            self.sample, self.test_character
        )
        events = self.data_loader.get_events_by_character(
            self.sample, self.test_character
        )
        
        # Create profile memory
        profile_content = f"# {self.test_character}'s Profile\n\n"
        profile_content += f"[profile1] {self.test_character} is a character from the locomo dataset.\n"
        if conversations:
            profile_content += f"[profile2] Based on conversations, {self.test_character} has participated in {len(conversations)} recorded dialogues.\n"
        
        self._write_memory_file(self.test_character, "profile", profile_content)
        
        # Create activity memory
        activity_content = f"# {self.test_character}'s Activities\n\n"
        for i, conv in enumerate(conversations[:3]):  # Use first 3 conversations
            activity_content += f"[activity{i+1}] {self.test_character} said: \"{conv[:100]}...\"\n"
        
        self._write_memory_file(self.test_character, "activity", activity_content)
        
        # Create event memory
        event_content = f"# {self.test_character}'s Events\n\n"
        for i, event in enumerate(events[:3]):  # Use first 3 events
            event_content += f"[event{i+1}] {event}\n"
        
        self._write_memory_file(self.test_character, "event", event_content)
    
    def _write_memory_file(self, character_name, category, content):
        """Write a memory file"""
        file_path = os.path.join(self.temp_dir, f"{character_name}_{category}.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _memory_file_exists(self, character_name, category):
        """Check if a memory file exists"""
        file_path = os.path.join(self.temp_dir, f"{character_name}_{category}.md")
        return os.path.exists(file_path)
    
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
        self.assertIn('event_summary', self.sample)
        self.assertGreater(len(self.characters), 0)
        print(f"✅ Test character: {self.test_character}")
        print(f"✅ Available characters: {self.characters}")
    
    def test_memory_files_created(self):
        """Test that sample memory files are created"""
        for category in ["profile", "activity", "event"]:
            self.assertTrue(
                self._memory_file_exists(self.test_character, category),
                f"Memory file for {category} not created"
            )
    
    def test_delete_specific_category_real_data(self):
        """Test deleting a specific memory category with real data"""
        # Verify file exists before deletion
        self.assertTrue(self._memory_file_exists(self.test_character, "activity"))
        
        # Delete the activity memory
        result = self.action.execute(
            character_name=self.test_character,
            category="activity"
        )
        
        # Verify successful deletion
        self.assertTrue(result["success"])
        self.assertEqual(result["character_name"], self.test_character)
        self.assertIn("activity", result["deleted_categories"])
        
        # Verify file content is cleared (not removed, but empty)
        content = self._get_memory_file_content(self.test_character, "activity")
        self.assertEqual(content.strip(), "")
    
    def test_delete_all_categories_real_data(self):
        """Test deleting all memory categories with real data"""
        # Verify files exist before deletion
        for category in ["profile", "activity", "event"]:
            self.assertTrue(self._memory_file_exists(self.test_character, category))
        
        # Delete all memories
        result = self.action.execute(
            character_name=self.test_character
        )
        
        # Verify successful deletion
        self.assertTrue(result["success"])
        self.assertEqual(result["character_name"], self.test_character)
        
        # Should have deleted all categories
        expected_categories = ["profile", "activity", "event"]
        for category in expected_categories:
            self.assertIn(category, result["deleted_categories"])
        
        # Verify all files are cleared
        for category in expected_categories:
            content = self._get_memory_file_content(self.test_character, category)
            self.assertEqual(content.strip(), "")
    
    def test_delete_nonexistent_character(self):
        """Test deleting memories for a character that doesn't exist"""
        nonexistent_character = "NonExistentCharacter"
        
        result = self.action.execute(
            character_name=nonexistent_character,
            category="profile"
        )
        
        # Should handle gracefully
        self.assertIn("success", result)
        self.assertEqual(result["character_name"], nonexistent_character)
    
    def test_multiple_characters_from_locomo(self):
        """Test handling multiple characters from locomo data"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters for this test")
        
        # Create memories for second character
        second_character = self.characters[1]
        conversations = self.data_loader.get_conversations_by_character(
            self.sample, second_character
        )
        
        if conversations:
            # Create a simple memory for second character
            content = f"# {second_character}'s Profile\n\n[profile1] {second_character} from locomo data.\n"
            self._write_memory_file(second_character, "profile", content)
            
            # Test deletion
            result = self.action.execute(
                character_name=second_character,
                category="profile"
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["character_name"], second_character)
    
    def test_real_conversation_content(self):
        """Test that real conversation content is properly used"""
        # Get the content we created from real data
        activity_content = self._get_memory_file_content(self.test_character, "activity")
        
        # Should contain actual conversation text
        self.assertIsNotNone(activity_content)
        self.assertIn(self.test_character, activity_content)
        
        # Get original conversations to verify
        conversations = self.data_loader.get_conversations_by_character(
            self.sample, self.test_character
        )
        
        if conversations:
            # Should contain part of the actual conversation
            first_conv_snippet = conversations[0][:50]  # First 50 chars
            self.assertIn(first_conv_snippet, activity_content)


def run_real_data_quality_assessment():
    """Run a comprehensive quality assessment with real data"""
    print("🧪 RUNNING DELETE_MEMORY ACTION TESTS WITH REAL LOCOMO DATA")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDeleteMemoryActionRealData)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 REAL DATA QUALITY ASSESSMENT SUMMARY")
    print("=" * 70)
    
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
    
    print("\n💡 Using REAL locomo conversation data instead of mocks!")
    print("🎯 Tests validate actual memory operations with authentic dialogue content.")
    
    return success_rate >= 85


if __name__ == "__main__":
    run_real_data_quality_assessment() 