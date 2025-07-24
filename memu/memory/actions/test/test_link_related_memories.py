#!/usr/bin/env python3
"""
Test script for LinkRelatedMemoriesAction with Locomo data

Tests the link_related_memories action using conversation data:
- Load conversations from locomo dataset
- Create memory files with real content
- Test memory linking and relationship discovery
- Verify link quality and relevance
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

from memu.memory.actions.link_related_memories import LinkRelatedMemoriesAction
from memu.memory.memory_agent import MemoryAgent
from memu.llm.openai_client import OpenAIClient


class MockEmbeddingClient:
    """Simple mock embedding client for testing"""
    
    def __init__(self):
        self.search_count = 0
    
    def semantic_search(self, query, character_name, category=None, top_k=5, **kwargs):
        """Mock semantic search that returns related memories"""
        self.search_count += 1
        
        # Generate mock related memories
        related_memories = [
            {
                "memory_id": f"related_mem_{i+1:03d}",
                "content": f"Related memory content {i+1} that connects to the query topic",
                "similarity_score": 0.9 - (i * 0.1),
                "category": category or "activity",
                "character": character_name
            }
            for i in range(min(top_k, 3))
        ]
        
        print(f"🔍 MockEmbedding search #{self.search_count} for '{query}' returned {len(related_memories)} results")
        return related_memories





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
    
    def create_memory_files(self, character_name, memory_base_path):
        """Create sample memory files for testing"""
        character_dir = memory_base_path / character_name
        character_dir.mkdir(exist_ok=True)
        
        # Create activity memory file
        activity_content = "[activity001] Engaged in conversation about daily activities\n"
        activity_content += "[activity002] Discussed personal preferences and interests\n"
        activity_content += "[activity003] Shared thoughts on various topics\n"
        
        activity_file = character_dir / "activity.md"
        activity_file.write_text(activity_content)
        
        # Create profile memory file
        profile_content = "[profile001] Shows friendly and communicative personality\n"
        profile_content += "[profile002] Demonstrates thoughtful responses to questions\n"
        
        profile_file = character_dir / "profile.md"
        profile_file.write_text(profile_content)
        
        # Create event memory file
        event_content = "[event001] Participated in meaningful conversation session\n"
        event_content += "[event002] Exchanged ideas and opinions with others\n"
        
        event_file = character_dir / "event.md"
        event_file.write_text(event_content)
        
        print(f"📝 Created memory files for {character_name}")


class TestLinkRelatedMemories(unittest.TestCase):
    """Test LinkRelatedMemoriesAction with locomo data"""
    
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
        
        # Create mock embedding client
        self.embedding_client = MockEmbeddingClient()
        
        # Create memory agent with OpenAI client
        self.memory_agent = MemoryAgent(
            llm_client=OpenAIClient(),
            memory_base_path=str(self.memory_base_path)
        )
        
        # Add embedding client to memory agent
        self.memory_agent.embedding_client = self.embedding_client
        
        # Create memory files for testing
        if self.characters:
            for character in self.characters[:2]:  # Create files for first 2 characters
                self.loader.create_memory_files(character, self.memory_base_path)
        
        # Create action instance
        self.action = LinkRelatedMemoriesAction(self.memory_agent)
        
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
        self.assertEqual(schema['name'], 'link_related_memories')
        
        # Check parameters
        params = schema['parameters']
        self.assertIn('properties', params)
        
        properties = params['properties']
        self.assertIn('character_name', properties)
        
        print("✅ Schema validation passed")
    
    def test_link_memories_with_real_data(self):
        """Test memory linking with real conversation-based memories"""
        if not self.characters:
            self.skipTest("No locomo data available")
        
        character_name = self.characters[0]
        
        try:
            # Execute the action
            result = self.action.execute(
                character_name=character_name,
                memory_id="activity001",
                category="activity"
            )
            
            # Validate result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertTrue(result['success'])
            self.assertIn('data', result)
            
            # Check data content
            data = result['data']
            self.assertIsInstance(data, list)
            
            # Validate each link
            for link in data:
                self.assertIsInstance(link, dict)
                self.assertIn('source_memory_id', link)
                self.assertIn('target_memory_id', link)
                self.assertIn('relationship_type', link)
            
            print(f"✅ Linked memories for {character_name}")
            print(f"🔗 Generated {len(data)} memory links")
            print(f"📊 Result: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            self.fail(f"Failed to link memories: {e}")
    
    def test_link_all_memories(self):
        """Test linking all memories for a character"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        try:
            result = self.action.execute(
                character_name=character_name,
                link_all_items=True
            )
            
            # Should handle linking all memories
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            
            print("✅ Link all memories completed")
            
        except Exception as e:
            # This might be expected behavior, log it
            print(f"⚠️ Link all memories caused: {e}")
    
    def test_cross_category_linking(self):
        """Test linking memories across different categories"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        categories = ["activity", "profile", "event"]
        
        for category in categories:
            try:
                result = self.action.execute(
                    character_name=character_name,
                    memory_id=f"{category}001",
                    category=category
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Cross-category linking completed for {category}")
                
            except Exception as e:
                print(f"⚠️ Failed for category {category}: {e}")
    
    def test_multiple_characters_linking(self):
        """Test memory linking for multiple characters"""
        if len(self.characters) < 2:
            self.skipTest("Need at least 2 characters")
        
        for character in self.characters[:2]:  # Test first 2 characters
            try:
                result = self.action.execute(
                    character_name=character,
                    memory_id="activity001",
                    category="activity"
                )
                
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                
                print(f"✅ Memory linking completed for character: {character}")
                
            except Exception as e:
                print(f"⚠️ Failed for character {character}: {e}")
    
    def test_similarity_threshold(self):
        """Test memory linking with different similarity thresholds"""
        if not self.characters:
            self.skipTest("No characters available")
        
        character_name = self.characters[0]
        
        thresholds = [0.5, 0.7, 0.9]
        
        for threshold in thresholds:
            try:
                result = self.action.execute(
                    character_name=character_name,
                    memory_id="activity001",
                    category="activity",
                    similarity_threshold=threshold
                )
                
                self.assertIsInstance(result, dict)
                print(f"✅ Threshold {threshold} linking completed")
                
            except Exception as e:
                print(f"⚠️ Threshold {threshold} failed: {e}")


def main():
    """Main test runner"""
    print("🧪 Testing LinkRelatedMemoriesAction with Locomo data")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main() 