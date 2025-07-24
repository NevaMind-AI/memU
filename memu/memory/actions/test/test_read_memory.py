#!/usr/bin/env python3
"""
Test script for ReadMemoryAction with real Locomo data

Tests the read_memory action using real conversation data:
- Load conversations from locomo dataset
- Create real memory files for characters
- Test memory reading with authentic data
- Verify content retrieval and format
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

from memu.memory.actions.read_memory import ReadMemoryAction
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
                for dialog in sample['conversation'][session_key]:
                    if dialog['speaker'] == character:
                        conversations.append(dialog['text'])
        
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


class TestReadMemory(unittest.TestCase):
    """Test cases for ReadMemoryAction using locomo data"""
    
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
        
        # Setup memory agent
        try:
            self.memory_agent = MemoryAgent(
                llm_client=OpenAIClient(),
                memory_dir=self.temp_dir,
                enable_embeddings=False
            )
            self.action = ReadMemoryAction(self.memory_agent.memory_core)
        except Exception as e:
            self.skipTest(f"Failed to setup memory agent: {e}")
        
        # Create sample memory files with real data
        self._create_sample_memories()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_memories(self):
        """Create sample memory files using real locomo data"""
        conversations = self.data_loader.get_conversations_by_character(
            self.sample, self.test_character
        )
        events = self.data_loader.get_events_by_character(
            self.sample, self.test_character
        )
        
        # Create profile memory
        profile_content = f"# {self.test_character}'s Profile\n\n"
        profile_content += f"[profile1][mentioned at 2025-07-24] {self.test_character} is a character from the locomo dataset. []\n"
        if conversations:
            profile_content += f"[profile2][mentioned at 2025-07-24] Based on conversations, {self.test_character} has participated in {len(conversations)} recorded dialogues. []\n"
        
        self._write_memory_file(self.test_character, "profile", profile_content)
        
        # Create activity memory
        activity_content = f"# {self.test_character}'s Activities\n\n"
        for i, conv in enumerate(conversations[:3]):  # Use first 3 conversations
            activity_content += f"[activity{i+1}][mentioned at 2025-07-24] {self.test_character} said: \"{conv[:100]}...\" []\n"
        
        self._write_memory_file(self.test_character, "activity", activity_content)
        
        # Create event memory
        event_content = f"# {self.test_character}'s Events\n\n"
        for i, event in enumerate(events[:3]):  # Use first 3 events
            event_content += f"[event{i+1}][mentioned at 2025-07-24] {event} []\n"
        
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
    
    def test_locomo_data_loaded(self):
        """Test that locomo data is properly loaded"""
        self.assertIsNotNone(self.sample)
        self.assertIn('conversation', self.sample)
        self.assertIn('event_summary', self.sample)
        self.assertGreater(len(self.characters), 0)
        print(f"✅ Test character: {self.test_character}")
        print(f"✅ Available characters: {self.characters}")
    
    def test_action_name(self):
        """Test action name property"""
        self.assertEqual(self.action.action_name, "read_memory")
    
    def test_schema_validation(self):
        """Test the action schema is valid"""
        schema = self.action.get_schema()
        
        # Check required fields
        self.assertEqual(schema["name"], "read_memory")
        self.assertIn("description", schema)
        self.assertIn("parameters", schema)
        
        # Check parameters structure
        params = schema["parameters"]
        self.assertEqual(params["type"], "object")
        self.assertIn("properties", params)
        self.assertIn("required", params)
        
        # Check required parameters
        self.assertIn("character_name", params["required"])
    
    def test_read_specific_category_real_data(self):
        """Test reading a specific memory category with real data"""
        result = self.action.execute(
            character_name=self.test_character,
            category="activity"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["character_name"], self.test_character)
        self.assertEqual(result["category"], "activity")
        self.assertIn("content", result)
        
        # Content should contain real conversation data
        content = result["content"]
        self.assertIn(self.test_character, content)
        self.assertIn("Activities", content)  # Should have the header
    
    def test_read_all_categories_real_data(self):
        """Test reading all memory categories with real data"""
        result = self.action.execute(
            character_name=self.test_character
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["character_name"], self.test_character)
        self.assertIn("content", result)
        
        # Should contain content from all categories (content is a dict)
        content = result["content"]
        if isinstance(content, dict):
            # Check that all memory types are present
            self.assertIn("profile", content)
            self.assertIn("activity", content)
            self.assertIn("event", content)
            # Check that character name is in each category
            self.assertIn(self.test_character, content["profile"])
        else:
            # If it's a string, check for headers
            self.assertIn("Profile", content)
            self.assertIn("Activities", content)
            self.assertIn("Events", content)
            self.assertIn(self.test_character, content)
    
    def test_read_nonexistent_character(self):
        """Test reading memories for a character that doesn't exist"""
        nonexistent_character = "NonExistentCharacter"
        
        result = self.action.execute(
            character_name=nonexistent_character,
            category="profile"
        )
        
        # Should handle gracefully
        self.assertIn("success", result)
        self.assertEqual(result["character_name"], nonexistent_character)
    
    def test_read_nonexistent_category(self):
        """Test reading a nonexistent memory category"""
        result = self.action.execute(
            character_name=self.test_character,
            category="nonexistent_category"
        )
        
        # Should handle gracefully
        self.assertIn("success", result)
        if "character_name" in result:
            self.assertEqual(result["character_name"], self.test_character)
    
    def test_memory_content_quality(self):
        """Test that real memory content maintains quality"""
        result = self.action.execute(
            character_name=self.test_character,
            category="activity"
        )
        
        self.assertTrue(result["success"])
        content = result["content"]
        
        # Should be properly formatted markdown
        self.assertTrue(content.startswith('#'))
        
        # Should contain memory entry markers
        self.assertIn('[', content)
        self.assertIn(']', content)
        
        # Should contain real conversation snippets
        conversations = self.data_loader.get_conversations_by_character(
            self.sample, self.test_character
        )
        if conversations:
            # At least one conversation snippet should be in the content
            found_conversation = any(conv[:20] in content for conv in conversations[:3])
            self.assertTrue(found_conversation)
    
    def test_multiple_characters_from_locomo(self):
        """Test reading memories for multiple characters from locomo data"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters for this test")
        
        char1 = self.characters[0]
        char2 = self.characters[1]
        
        # Create basic memory for second character
        profile_content = f"# {char2}'s Profile\n\n[profile1][mentioned at 2025-07-24] {char2} from locomo data. []\n"
        self._write_memory_file(char2, "profile", profile_content)
        
        # Read memories for both characters
        result1 = self.action.execute(character_name=char1, category="profile")
        result2 = self.action.execute(character_name=char2, category="profile")
        
        self.assertTrue(result1["success"])
        self.assertTrue(result2["success"])
        
        # Should contain different character names
        self.assertIn(char1, result1["content"])
        self.assertIn(char2, result2["content"])
        self.assertNotEqual(result1["content"], result2["content"])
    
    def test_real_events_content(self):
        """Test reading event memories with real event data"""
        events = self.data_loader.get_events_by_character(self.sample, self.test_character)
        
        if not events:
            self.skipTest(f"No events found for {self.test_character}")
        
        result = self.action.execute(
            character_name=self.test_character,
            category="event"
        )
        
        self.assertTrue(result["success"])
        content = result["content"]
        
        # Should contain real event content
        self.assertIn("Events", content)
        
        # At least one real event should be referenced in the content
        found_event = any(event[:20] in content for event in events[:3])
        self.assertTrue(found_event)


def run_real_data_quality_assessment():
    """Run a comprehensive quality assessment with real data"""
    print("🧪 RUNNING READ_MEMORY ACTION TESTS WITH REAL LOCOMO DATA")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReadMemoryActionRealData)
    
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
    
    print("\n💡 Using REAL locomo conversation data for memory reading tests!")
    print("🎯 Tests validate actual memory operations with authentic dialogue content.")
    
    return success_rate >= 85


if __name__ == "__main__":
    run_real_data_quality_assessment() 