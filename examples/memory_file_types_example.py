#!/usr/bin/env python3
"""
Memory File Types Example

This example demonstrates how to use the expanded memory system with multiple file types:
- profile.md: Character profile information
- event.md: Character event records  
- reminder.md: Important reminders and todo items
- important_event.md: Significant life events and milestones
- interests.md: Hobbies, interests, and preferences
- study.md: Learning goals, courses, and educational content
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import memu
sys.path.insert(0, str(Path(__file__).parent.parent))

from memu import (
    MemoryFileManager, 
    Memory,
    ProfileMemory,
    EventMemory,
    ReminderMemory,
    ImportantEventMemory,
    InterestsMemory,
    StudyMemory
)


def main():
    # Create a test memory directory
    memory_dir = "test_memory_files"
    os.makedirs(memory_dir, exist_ok=True)
    
    print("=== MemU Enhanced Memory File Types Example ===\n")
    
    # Initialize file manager
    file_manager = MemoryFileManager(memory_dir)
    print(f"✅ Initialized MemoryFileManager with directory: {memory_dir}")
    print(f"📁 Supported memory types: {', '.join(file_manager.MEMORY_TYPES)}\n")
    
    # Character name for this example
    character_name = "Alice"
    
    # 1. Profile Information
    print("1️⃣ Working with Profile Information")
    profile_content = """
## Personal Information
- Name: Alice Johnson
- Age: 28
- Occupation: Software Engineer
- Location: San Francisco, CA
- Education: BS Computer Science, Stanford University

## Personality Traits
- Creative problem solver
- Enjoys collaborative work
- Values work-life balance
- Strong communication skills
    """.strip()
    
    file_manager.write_profile(character_name, profile_content)
    print("✅ Profile information saved")
    
    # 2. Event Records
    print("\n2️⃣ Working with Event Records")
    event_content = """
2024-01-15: Started new project at work - building a machine learning pipeline for customer recommendations
2024-01-20: Had coffee with mentor Sarah to discuss career goals and next steps
2024-01-25: Attended team building event at the office, played board games with colleagues
2024-02-01: Completed first sprint on ML project, received positive feedback from team lead
    """.strip()
    
    file_manager.write_events(character_name, event_content)
    print("✅ Event records saved")
    
    # 3. Reminders and Todo Items
    print("\n3️⃣ Working with Reminders")
    reminder_content = """
- Submit Q1 performance review by March 15th
- Schedule dentist appointment for next month
- Buy birthday gift for mom (birthday is March 10th)
- Finish reading "Clean Code" book
- Update LinkedIn profile with new skills
- Plan weekend hiking trip with friends
    """.strip()
    
    file_manager.write_reminders(character_name, reminder_content)
    print("✅ Reminders saved")
    
    # 4. Important Life Events
    print("\n4️⃣ Working with Important Life Events")
    important_events_content = """
2020-06-15: Graduated from Stanford University with BS in Computer Science, summa cum laude
2020-08-01: Started first job as Junior Software Engineer at TechCorp
2022-03-15: Promoted to Software Engineer II, received 20% salary increase
2023-01-10: Moved to San Francisco for new job opportunity at InnovateTech
2023-06-20: Completed AWS Solutions Architect certification
2024-01-01: Started leading ML project team, first time in leadership role
    """.strip()
    
    file_manager.write_important_events(character_name, important_events_content)
    print("✅ Important life events saved")
    
    # 5. Interests and Hobbies
    print("\n5️⃣ Working with Interests")
    interests_content = """
## Technology & Learning
- Machine Learning and AI research
- Cloud computing (AWS, Azure)
- Open source contribution (GitHub projects)
- Programming languages: Python, Go, JavaScript

## Outdoor Activities
- Hiking in Bay Area trails
- Rock climbing (indoor and outdoor)
- Photography (nature and landscape)
- Weekend camping trips

## Creative Pursuits
- Playing acoustic guitar
- Cooking international cuisines
- Reading science fiction novels
- Board games and strategy games
    """.strip()
    
    file_manager.write_interests(character_name, interests_content)
    print("✅ Interests and hobbies saved")
    
    # 6. Study and Learning
    print("\n6️⃣ Working with Study Information")
    study_content = """
## Current Learning Goals
- Complete Advanced Machine Learning Specialization on Coursera (Progress: 60%)
- Study for AWS Machine Learning Specialty certification (Exam scheduled: April 2024)
- Learn Go programming language for backend development

## Courses & Certifications
- AWS Solutions Architect Associate (Completed: June 2023)
- Stanford CS229 Machine Learning (Audit, Fall 2023)
- Deep Learning Specialization by Andrew Ng (Completed: March 2023)

## Books Currently Reading
- "Designing Data-Intensive Applications" by Martin Kleppmann
- "The Pragmatic Programmer" by Hunt & Thomas
- "Hands-On Machine Learning" by Aurélien Géron

## Study Schedule
- Monday/Wednesday/Friday: 1 hour ML theory and practice
- Tuesday/Thursday: 1 hour cloud certification prep
- Weekends: Project work and experimentation
    """.strip()
    
    file_manager.write_study(character_name, study_content)
    print("✅ Study information saved")
    
    # 7. Demonstrate file reading and content access
    print("\n📖 Reading and Displaying All Memory Content")
    print("=" * 60)
    
    # Create Memory object to demonstrate unified access
    memory = Memory(character_name, memory_dir)
    
    # Display all memory content organized by type
    all_content = memory.get_all_memory_content()
    
    for memory_type, content in all_content.items():
        if content:  # Only show non-empty content
            print(f"\n🔹 {memory_type.upper().replace('_', ' ')}:")
            print("-" * 40)
            if isinstance(content, list):
                for item in content[:3]:  # Show first 3 items
                    print(f"  • {item}")
                if len(content) > 3:
                    print(f"  ... and {len(content) - 3} more items")
            else:
                print(f"  {content[:200]}...")  # Show first 200 chars
    
    # 8. Display memory statistics
    print("\n📊 Memory Statistics")
    print("=" * 60)
    stats = memory.get_memory_stats()
    for key, value in stats.items():
        if key.endswith('_count'):
            memory_type = key.replace('_count', '').replace('_', ' ').title()
            print(f"  {memory_type}: {value} items")
    
    # 9. Demonstrate character info with file details
    print("\n📋 Character Information Summary")
    print("=" * 60)
    character_info = file_manager.get_character_info(character_name)
    
    for memory_type in file_manager.MEMORY_TYPES:
        has_file = character_info.get(f"has_{memory_type}", False)
        file_size = character_info.get(f"{memory_type}_size", 0)
        status = "✅" if has_file else "❌"
        print(f"  {status} {memory_type.replace('_', ' ').title()}: {file_size} bytes")
    
    # 10. Show formatted prompt output
    print("\n📝 Formatted Memory Prompt")
    print("=" * 60)
    prompt = memory.to_prompt()
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    print(f"\n🎉 Successfully demonstrated all 6 memory file types!")
    print(f"📁 Memory files created in: {os.path.abspath(memory_dir)}")
    print(f"🔍 You can examine the .md files directly to see the organized content")


if __name__ == "__main__":
    main() 