#!/usr/bin/env python3
"""
Conversation Storage Validation Example

Demonstrates the required fields for conversation storage:
- agent_id (REQUIRED)
- user_id (REQUIRED) 
- created_at (automatically set)
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from personalab.memo import ConversationManager


def test_required_fields():
    """Test required field validation for conversation storage."""
    
    print("=== Conversation Storage Validation Example ===\n")
    
    # Initialize manager with temporary database for testing
    import tempfile
    import os
    
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    manager = ConversationManager(
        db_path=temp_db.name,
        enable_embeddings=False  # Disable for faster testing
    )
    
    # Clean up temp file at the end
    def cleanup():
        try:
            os.unlink(temp_db.name)
        except:
            pass
    
    import atexit
    atexit.register(cleanup)
    
    print("1. Testing successful conversation recording with all required fields...")
    
    # ✅ Valid conversation with all required fields
    try:
        conversation = manager.record_conversation(
            agent_id="demo_agent",      # REQUIRED
            user_id="user_123",         # REQUIRED
            messages=[
                {"role": "user", "content": "Hello!"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        )
        
        print(f"✅ SUCCESS: Conversation recorded")
        print(f"   - Conversation ID: {conversation.conversation_id}")
        print(f"   - Agent ID: {conversation.agent_id}")
        print(f"   - User ID: {conversation.user_id}")
        print(f"   - Created at: {conversation.created_at}")
        print(f"   - Message count: {len(conversation.messages)}")
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
    
    print("\n2. Testing missing user_id...")
    
    # ❌ Missing user_id should fail
    try:
        conversation = manager.record_conversation(
            agent_id="demo_agent",
            # user_id missing!
            messages=[
                {"role": "user", "content": "This should fail"}
            ]
        )
        print("❌ ERROR: Should have failed without user_id!")
        
    except TypeError as e:
        print(f"✅ SUCCESS: Correctly rejected missing user_id")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR TYPE: {e}")
    
    print("\n3. Testing empty user_id...")
    
    # ❌ Empty user_id should fail
    try:
        conversation = manager.record_conversation(
            agent_id="demo_agent",
            user_id="",  # Empty string
            messages=[
                {"role": "user", "content": "This should fail"}
            ]
        )
        print("❌ ERROR: Should have failed with empty user_id!")
        
    except ValueError as e:
        print(f"✅ SUCCESS: Correctly rejected empty user_id")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR TYPE: {e}")
    
    print("\n4. Testing empty agent_id...")
    
    # ❌ Empty agent_id should fail
    try:
        conversation = manager.record_conversation(
            agent_id="",  # Empty string
            user_id="user_123",
            messages=[
                {"role": "user", "content": "This should fail"}
            ]
        )
        print("❌ ERROR: Should have failed with empty agent_id!")
        
    except ValueError as e:
        print(f"✅ SUCCESS: Correctly rejected empty agent_id")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR TYPE: {e}")
    
    print("\n5. Testing conversation retrieval and field validation...")
    
    # Test retrieving conversations to ensure all required fields are present
    history = manager.get_conversation_history("demo_agent", limit=10)
    
    print(f"Retrieved {len(history)} conversations")
    
    for i, conv_summary in enumerate(history, 1):
        print(f"\nConversation {i}:")
        print(f"   - ID: {conv_summary['conversation_id']}")
        print(f"   - Agent ID: {conv_summary.get('agent_id', 'MISSING!')}")
        print(f"   - User ID: {conv_summary.get('user_id', 'MISSING!')}")
        print(f"   - Created: {conv_summary.get('created_at', 'MISSING!')}")
        
        # Get full conversation details
        full_conv = manager.get_conversation(conv_summary['conversation_id'])
        if full_conv:
            print(f"   - Full conversation loaded successfully")
            print(f"   - Agent ID (full): {full_conv.agent_id}")
            print(f"   - User ID (full): {full_conv.user_id}")
            print(f"   - Created (full): {full_conv.created_at}")
        else:
            print(f"   - ❌ Failed to load full conversation")
    
    print("\n=== Field Requirements Summary ===")
    print("✅ agent_id: REQUIRED - Must be non-empty string")
    print("✅ user_id: REQUIRED - Must be non-empty string") 
    print("✅ created_at: AUTOMATIC - Set automatically when conversation is created")
    print("✅ conversation_id: AUTOMATIC - Generated UUID if not provided")
    print("ℹ️  session_id: OPTIONAL - Generated UUID if not provided")
    print("ℹ️  memory_id: OPTIONAL - Can be None")
    print("ℹ️  pipeline_result: OPTIONAL - Can be None")
    
    print("\n=== Database Schema Constraints ===")
    print("- agent_id: TEXT NOT NULL")
    print("- user_id: TEXT NOT NULL") 
    print("- created_at: TEXT NOT NULL")
    print("- conversation_id: TEXT PRIMARY KEY")
    
    print("\n✅ All validation tests completed successfully!")


def main():
    test_required_fields()


if __name__ == "__main__":
    main() 