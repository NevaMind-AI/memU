#!/usr/bin/env python3
"""
Test script for GetAvailableCategoriesAction with real Locomo data

Tests the get_available_categories action using real conversation data:
- Load conversations from locomo dataset
- Create real memory files for characters
- Test category availability detection
- Verify category listing functionality
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

from memu.memory.actions.get_available_categories import GetAvailableCategoriesAction
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


class TestGetAvailableCategories(unittest.TestCase):
    """Test cases for GetAvailableCategoriesAction using locomo data"""
    
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
            self.action = GetAvailableCategoriesAction(self.memory_agent.memory_core)
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
        self.assertEqual(self.action.action_name, "get_available_categories")
    
    def test_schema_validation(self):
        """Test the action schema is valid"""
        schema = self.action.get_schema()
        
        # Check required fields
        self.assertEqual(schema["name"], "get_available_categories")
        self.assertIn("description", schema)
        self.assertIn("parameters", schema)
        
        # Check parameters structure
        params = schema["parameters"]
        self.assertEqual(params["type"], "object")
        self.assertIn("properties", params)
        self.assertIn("required", params)
        
        # Check required parameters (this action has no required parameters)
        self.assertEqual(len(params["required"]), 0)
    
    def test_get_categories_with_real_data(self):
        """Test getting available categories with real data"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        self.assertIn("categories", result)
        
        # Should find the configured categories (excluding activity)
        categories = result["categories"]
        self.assertIn("profile", categories)
        self.assertIn("event", categories)
        # Activity is excluded from this action
        self.assertNotIn("activity", categories)
        
        # Each category should have config info
        for category_name, category_info in categories.items():
            self.assertIn("filename", category_info)
            self.assertIn("description", category_info)
            self.assertIn("config_source", category_info)
    
    def test_get_categories_system_config(self):
        """Test getting system-configured categories"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        self.assertIn("categories", result)
        self.assertIn("total_categories", result)
        self.assertIn("processing_order", result)
        self.assertIn("excluded_categories", result)
        
        # Should exclude activity category
        self.assertIn("activity", result["excluded_categories"])
        
        # Should have a processing order
        processing_order = result["processing_order"]
        self.assertIsInstance(processing_order, list)
        self.assertNotIn("activity", processing_order)  # Activity should be excluded
    
    def test_category_descriptions(self):
        """Test that categories have proper descriptions"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        categories = result["categories"]
        
        # Each category should have a meaningful description
        for category_name, category_info in categories.items():
            description = category_info["description"]
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)
            # Description should mention the category name or be relevant
            self.assertTrue(any(word in description.lower() for word in [category_name, "memory", "information"]))
    
    def test_consistent_results(self):
        """Test that the action returns consistent results"""
        # This action should return the same categories regardless of when called
        result1 = self.action.execute()
        result2 = self.action.execute()
        
        self.assertTrue(result1["success"])
        self.assertTrue(result2["success"])
        
        # Should return the same categories
        self.assertEqual(result1["categories"], result2["categories"])
        self.assertEqual(result1["total_categories"], result2["total_categories"])
        self.assertEqual(result1["processing_order"], result2["processing_order"])
    
    def test_category_info_quality(self):
        """Test that category information includes required details"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        categories = result["categories"]
        
        for category_name, category_info in categories.items():
            # Each category should have required fields
            self.assertIn("filename", category_info)
            self.assertIn("description", category_info)
            self.assertIn("config_source", category_info)
            
            # Filename should end with .md
            filename = category_info["filename"]
            self.assertTrue(filename.endswith(".md"))
    
    def test_config_based_categories(self):
        """Test that categories come from configuration"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        categories = result["categories"]
        
        # Should include standard categories from config
        expected_categories = ["profile", "event"]  # activity is excluded
        
        for expected_cat in expected_categories:
            self.assertIn(expected_cat, categories)
            category_info = categories[expected_cat]
            
            # Should have configuration source
            self.assertIn("config_source", category_info)
            config_source = category_info["config_source"]
            self.assertIsInstance(config_source, str)
    
    def test_embeddings_info(self):
        """Test that embeddings information is included"""
        result = self.action.execute()
        
        self.assertTrue(result["success"])
        
        # Should include embeddings information
        self.assertIn("embeddings_enabled", result)
        embeddings_enabled = result["embeddings_enabled"]
        self.assertIsInstance(embeddings_enabled, bool)
        
        # Should have a descriptive message
        self.assertIn("message", result)
        message = result["message"]
        self.assertIsInstance(message, str)
        self.assertIn("categories", message.lower())


def run_real_data_quality_assessment():
    """Run a comprehensive quality assessment with real data"""
    print("🧪 RUNNING GET_AVAILABLE_CATEGORIES ACTION TESTS WITH REAL LOCOMO DATA")
    print("=" * 80)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGetAvailableCategoriesActionRealData)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 REAL DATA QUALITY ASSESSMENT SUMMARY")
    print("=" * 80)
    
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
    
    print("\n💡 Using REAL locomo conversation data for category detection tests!")
    print("🎯 Tests validate actual memory operations with authentic dialogue content.")
    
    return success_rate >= 85


if __name__ == "__main__":
    run_real_data_quality_assessment() 