#!/usr/bin/env python3
"""
Conversation Analysis Example

This example demonstrates how the enhanced MemoryAgent analyzes conversations 
and extracts information for all memory file types:
- events: Daily activities and interactions
- reminders: Todo items and scheduled tasks
- important_events: Significant life milestones
- interests: Hobbies and preferences
- study: Learning goals and educational activities
- profile: Updated character information

NOTE: This example requires an LLM client to be configured.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memu import MemoryAgent, MemoryFileManager
from memu.llm import AzureOpenAIClient, OpenAIClient


def setup_llm_client():
    """Setup LLM client for conversation analysis"""
    # Try Azure OpenAI first, then OpenAI
    if os.getenv('AZURE_OPENAI_API_KEY'):
        print("🔧 Using Azure OpenAI client")
        return AzureOpenAIClient()
    elif os.getenv('OPENAI_API_KEY'):
        print("🔧 Using OpenAI client")
        return OpenAIClient()
    else:
        print("❌ No LLM API key found. Please set AZURE_OPENAI_API_KEY or OPENAI_API_KEY")
        print("   This example requires an LLM client for conversation analysis.")
        return None


def main():
    print("=== MemU Conversation Analysis Example ===\n")
    
    # Setup LLM client
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    # Create memory directory
    memory_dir = "test_conversation_memory"
    os.makedirs(memory_dir, exist_ok=True)
    print(f"📁 Using memory directory: {memory_dir}")
    
    # Initialize MemoryAgent with file storage
    agent = MemoryAgent(
        llm_client=llm_client,
        memory_dir=memory_dir,
        use_database=False  # Use file storage for this example
    )
    print("✅ MemoryAgent initialized with LLM client")
    
    # Character for this example
    character_name = "Emma"
    session_date = "2024-03-20"
    
    # Sample conversation with rich content for analysis
    sample_conversation = """
    Emma: Hey! I had such an exciting day today. I finally got the promotion to Senior Marketing Manager I've been working towards for months! 
    
    Friend: That's amazing! Congratulations Emma! How do you feel?
    
    Emma: I'm thrilled! The salary increase is 30%, and I'll be leading a team of 5 people. I start the new role on April 1st. I need to schedule a celebration dinner with my family this weekend to share the news.
    
    Friend: You deserve it! What are your plans now?
    
    Emma: Well, I want to enhance my leadership skills, so I'm thinking of taking that "Advanced Leadership in Marketing" course on LinkedIn Learning. I've also been getting more into rock climbing lately - there's this amazing indoor climbing gym downtown that I discovered. And I really need to remember to book my flight for Sarah's wedding in May.
    
    Friend: Rock climbing sounds fun! Any other hobbies you're picking up?
    
    Emma: Actually yes! I've started learning Spanish on Duolingo. My goal is to be conversational by the end of the year so I can travel to Spain. I'm also really into podcast lately, especially ones about marketing trends and entrepreneurship. Oh, and I've been cooking more Italian food recently - trying to master pasta from scratch.
    
    Friend: That's a lot! How do you manage everything?
    
    Emma: I have a system now. I wake up at 6 AM for my Spanish practice, then hit the climbing gym three times a week. I also need to submit my expense reports by the end of this month, and I promised my mom I'd help her set up her new smartphone this weekend. The course I mentioned starts next Monday, so I need to clear my schedule for that.
    
    Friend: Sounds like you have everything planned out!
    
    Emma: Pretty much! Though I do need to remember to renew my car insurance - it expires next month. And I'm thinking of getting a certification in Google Analytics to complement my new role. The company said they'd pay for professional development courses.
    """
    
    print(f"\n📝 Analyzing conversation for {character_name}...")
    print("=" * 60)
    
    # Analyze the conversation and update all memory types
    result = agent.update_character_memory(
        character_name=character_name,
        conversation=sample_conversation,
        session_date=session_date
    )
    
    if result["success"]:
        print("✅ Conversation analysis completed successfully!\n")
        
        # Display what was updated
        print("📊 Update Results:")
        print("-" * 40)
        for memory_type, was_updated in result.get("update_results", {}).items():
            status = "✅" if was_updated else "⏹️"
            print(f"  {status} {memory_type.replace('_', ' ').title()}: {'Updated' if was_updated else 'No new content'}")
        
        print(f"\n🎯 Specific Updates:")
        print("-" * 40)
        updates = [
            ("Profile", result.get("profile_updated", False)),
            ("Events", result.get("events_updated", False)),
            ("Reminders", result.get("reminders_updated", False)), 
            ("Important Events", result.get("important_events_updated", False)),
            ("Interests", result.get("interests_updated", False)),
            ("Study Info", result.get("study_updated", False))
        ]
        
        for update_type, was_updated in updates:
            status = "🆕" if was_updated else "⏹️"
            print(f"  {status} {update_type}: {'New content added' if was_updated else 'No changes'}")
        
        # Show extracted content
        new_content = result.get("new_content", {})
        
        print(f"\n📄 Extracted Content Preview:")
        print("=" * 60)
        
        content_types = [
            ("events", "Daily Events"),
            ("reminders", "Reminders & Todo Items"),
            ("important_events", "Important Life Events"),
            ("interests", "New Interests Discovered"),
            ("study", "Learning & Study Plans")
        ]
        
        for content_key, content_title in content_types:
            content = new_content.get(content_key, "")
            if content.strip():
                print(f"\n🔹 {content_title}:")
                print("-" * 30)
                # Show first few lines
                lines = content.strip().split('\n')
                for line in lines[:3]:
                    if line.strip():
                        print(f"  {line}")
                if len(lines) > 3:
                    print(f"  ... and {len(lines) - 3} more items")
                print()
        
        # Display file information
        print(f"📁 Memory Files Created/Updated:")
        print("-" * 40)
        
        file_manager = MemoryFileManager(memory_dir)
        character_info = file_manager.get_character_info(character_name)
        
        for memory_type in file_manager.MEMORY_TYPES:
            has_file = character_info.get(f"has_{memory_type}", False)
            file_size = character_info.get(f"{memory_type}_size", 0)
            filename = f"{character_name.lower()}_{memory_type}.md"
            status = "📄" if has_file else "⭕"
            print(f"  {status} {filename}: {file_size} bytes")
        
        print(f"\n🎉 All memory files for {character_name} have been analyzed and updated!")
        print(f"📍 Files location: {os.path.abspath(memory_dir)}")
        print(f"💡 You can examine the .md files to see the extracted and organized content")
        
    else:
        print(f"❌ Failed to analyze conversation: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 