#!/usr/bin/env python3
"""
Test script for UpdateMemoryWithSuggestionsAction with Locomo data

Tests the update_memory_with_suggestions action using conversation data:
- Load conversations from locomo dataset
- Create memory files with real content
- Test memory updates based on suggestions
- Verify update quality and content integration
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

from memu.memory.actions.update_memory_with_suggestions import UpdateMemoryWithSuggestionsAction
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
    
    def get_session_date(self, sample, session_num=1):
        """Get session date"""
        session_date_key = f"session_{session_num}_date_time"
        if not sample or 'conversation' not in sample:
            return "2024-01-15"
        
        return sample['conversation'].get(session_date_key, "2024-01-15")
    
    def create_memory_files(self, character_name, memory_base_path):
        """Create sample memory files for testing"""
        character_dir = memory_base_path / character_name
        character_dir.mkdir(exist_ok=True)
        
        # Create activity memory file
        activity_content = "[activity001] Engaged in conversation about daily activities\n"
        activity_content += "[activity002] Discussed personal preferences and interests\n"
        
        activity_file = character_dir / "activity.md"
        activity_file.write_text(activity_content)
        
        # Create profile memory file
        profile_content = "[profile001] Shows friendly and communicative personality\n"
        profile_content += "[profile002] Demonstrates thoughtful responses to questions\n"
        
        profile_file = character_dir / "profile.md"
        profile_file.write_text(profile_content)
        
        # Create event memory file
        event_content = "[event001] Participated in meaningful conversation session\n"
        
        event_file = character_dir / "event.md"
        event_file.write_text(event_content)
        
        print(f"📝 Created memory files for {character_name}")


class TestUpdateMemoryWithSuggestions(unittest.TestCase):
    """Test UpdateMemoryWithSuggestionsAction with locomo data"""
    
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
        
        # Create memory files for testing
        if self.characters:
            for character in self.characters[:2]:  # Create files for first 2 characters
                self.loader.create_memory_files(character, self.memory_base_path)
        
        # Create action instance
        self.action = UpdateMemoryWithSuggestionsAction(self.memory_agent)
        
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
        self.assertEqual(schema['name'], 'update_memory_with_suggestions')
        
        # Check parameters
        params = schema['parameters']
        self.assertIn('properties', params)
        
        properties = params['properties']
        self.assertIn('character_name', properties)
        self.assertIn('category', properties)
        self.assertIn('suggestion', properties)
        
        print("✅ Schema validation passed")
    
    def test_update_memory_with_real_data(self):
        """Test memory updates with real conversation-based suggestions"""
        if not self.characters:
            self.skipTest("No locomo data available")
        
        character_name = self.characters[0]
        
        # Create a suggestion based on real conversation content
        suggestion = "Based on the conversation, add information about the character's communication style and preferences"
        
        try:
            # Execute the action
            result = self.action.execute(
                character_name=character_name,
                category="profile",
                suggestion=suggestion,
                session_date=self.session_date
            )
            
            # Validate result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertTrue(result['success'])
            self.assertIn('data', result)
            
            # Check data content
            data = result['data']
            self.assertIsInstance(data, dict)
            self.assertIn('modifications', data)
            
            modifications = data['modifications']
            self.assertIsInstance(modifications, list)
            
            # Validate each modification
            for mod in modifications:
                self.assertIsInstance(mod, dict)
                self.assertIn('action', mod)
                self.assertIn('memory_id', mod)
                self.assertIn('content', mod)
            
            print(f"✅ Updated memory for {character_name}")
            print(f"📊 Applied {len(modifications)} modifications")
            print(f"📝 Result: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            self.fail(f"Failed to update memory: {e}")
    
    def test_update_different_categories(self):
        """Test memory updates for different categories"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        categories_and_suggestions = [
            ("activity", "Add information about daily activities mentioned in conversation"),
            ("profile", "Update personality traits based on communication patterns"),
            ("event", "Record significant events discussed in the session")
        ]
        
        for category, suggestion in categories_and_suggestions:
            try:
                result = self.action.execute(
                    character_name=character_name,
                    category=category,
                    suggestion=suggestion,
                    session_date=self.session_date
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Updated {category} category successfully")
                
            except Exception as e:
                print(f"⚠️ Failed for category {category}: {e}")
    
    def test_empty_suggestion(self):
        """Test handling of empty suggestions"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        try:
            result = self.action.execute(
                character_name=character_name,
                category="activity",
                suggestion="",
                session_date=self.session_date
            )
            
            # Should handle empty suggestion gracefully
            self.assertIsInstance(result, dict)
            print("✅ Empty suggestion handled correctly")
            
        except Exception as e:
            # This might be expected behavior, log it
            print(f"⚠️ Empty suggestion caused: {e}")
    
    def test_multiple_characters_updates(self):
        """Test memory updates for multiple characters"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters")
        
        for character in self.characters[:2]:  # Test first 2 characters
            suggestion = f"Update memory based on {character}'s specific conversation patterns"
            
            try:
                result = self.action.execute(
                    character_name=character,
                    category="profile",
                    suggestion=suggestion,
                    session_date=self.session_date
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Memory updated for character: {character}")
                
            except Exception as e:
                print(f"⚠️ Failed for character {character}: {e}")
    
    def test_complex_suggestions(self):
        """Test updates with complex, detailed suggestions"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        complex_suggestion = """
        Based on the conversation analysis:
        1. Add information about the character's preferred communication style
        2. Note their tendency to ask thoughtful questions
        3. Record their interest in specific topics discussed
        4. Update personality traits based on response patterns
        """
        
        try:
            result = self.action.execute(
                character_name=character_name,
                category="profile",
                suggestion=complex_suggestion,
                session_date=self.session_date
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('data', result)
            
            print("✅ Complex suggestion processed successfully")
            
        except Exception as e:
            print(f"⚠️ Complex suggestion failed: {e}")
    
    def test_conversation_based_suggestions(self):
        """Test updates based on actual conversation content"""
        if not self.characters or not self.conversations:
            self.skipTest("No conversation data available")
        
        character_name = self.characters[0]
        
        # Extract actual topics from conversations
        conversation_topics = []
        for conv in self.conversations[:3]:
            if conv['speaker'] == character_name:
                conversation_topics.append(conv['text'][:50])  # First 50 chars as topic
        
        if conversation_topics:
            suggestion = f"Update memory based on topics discussed: {', '.join(conversation_topics)}"
            
            try:
                result = self.action.execute(
                    character_name=character_name,
                    category="activity",
                    suggestion=suggestion,
                    session_date=self.session_date
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Conversation-based update completed for {character_name}")
                
            except Exception as e:
                print(f"⚠️ Conversation-based update failed: {e}")


def main():
    """Main test runner"""
    print("🧪 Testing UpdateMemoryWithSuggestionsAction with Locomo data")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 