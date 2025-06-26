#!/usr/bin/env python3
"""
Memory usage example for PersonaLab.

This example demonstrates how to use ProfileMemory and EventMemory classes
to manage AI persona profiles and event memories.
"""

import time
from datetime import datetime, timedelta
from personalab import ProfileMemory, EventMemory
from personalab.utils import setup_logging


def main():
    """Demonstrate memory management functionality."""
    
    logger = setup_logging("INFO")
    logger.info("Starting memory usage example")
    
    # === ProfileMemory Example ===
    logger.info("\n=== ProfileMemory Example ===")
    
    # Create a persona profile
    persona_profile = ProfileMemory("ai_assistant_v1")
    
    # Set basic profile information
    persona_profile.update_profile({
        "name": "ARIA",
        "personality": "helpful, curious, analytical",
        "specializations": ["python", "ai", "data_science"],
        "communication_style": "friendly and professional",
        "knowledge_domains": {
            "programming": 9,
            "science": 8,
            "arts": 6,
            "history": 7
        },
        "preferences": {
            "verbosity": "moderate",
            "examples": True,
            "technical_depth": "adaptive"
        }
    })
    
    logger.info(f"Created profile: {persona_profile}")
    logger.info(f"Profile fields: {list(persona_profile.get_profile().keys())}")
    logger.info(f"Name: {persona_profile.get_field('name')}")
    logger.info(f"Specializations: {persona_profile.get_field('specializations')}")
    
    # Update specific fields
    persona_profile.set_field("version", "1.2.0")
    persona_profile.set_field("last_training_date", "2024-01-15")
    
    logger.info(f"Updated profile has {len(persona_profile.get_profile())} fields")
    
    # === EventMemory Example ===
    logger.info("\n=== EventMemory Example ===")
    
    # Create event memory for the same persona
    persona_memory = EventMemory("ai_assistant_v1", max_events=100)
    logger.info(f"Created event memory: {persona_memory}")
    
    # Simulate various types of interactions and events
    interactions = [
        ("conversation", "User asked about Python best practices", {"user_id": "user_123", "session": "sess_001"}, 6),
        ("action", "Provided code example for list comprehension", {"code_lines": 3}, 5),
        ("observation", "User seems to prefer detailed explanations", {"user_behavior": "engagement_high"}, 7),
        ("conversation", "User thanked for the help", {"sentiment": "positive"}, 4),
        ("system", "Session ended", {"duration_minutes": 15}, 3),
        ("conversation", "New user started conversation about machine learning", {"user_id": "user_456"}, 6),
        ("action", "Explained difference between supervised and unsupervised learning", {"topic": "ml_basics"}, 8),
        ("observation", "User has strong math background", {"user_skill_level": "advanced"}, 9),
        ("conversation", "User asked about neural networks", {"complexity": "intermediate"}, 7),
        ("action", "Drew conceptual diagram explanation", {"visual_aid": True}, 6),
    ]
    
    # Add events with small delays to simulate real timing
    for event_type, content, metadata, importance in interactions:
        event = persona_memory.add_event(event_type, content, metadata, importance)
        logger.info(f"Added event: {event}")
        time.sleep(0.1)  # Small delay
    
    logger.info(f"\nTotal events stored: {persona_memory.get_events_count()}")
    
    # === Query and Filter Events ===
    logger.info("\n=== Querying Events ===")
    
    # Get all conversation events
    conversations = persona_memory.get_events(event_type="conversation")
    logger.info(f"Found {len(conversations)} conversations:")
    for conv in conversations:
        logger.info(f"  - {conv.content[:50]}...")
    
    # Get important events (importance >= 7)
    important_events = persona_memory.get_important_events(min_importance=7)
    logger.info(f"\nFound {len(important_events)} important events:")
    for event in important_events:
        logger.info(f"  - [{event.importance}/10] {event.content[:50]}...")
    
    # Search events by content
    search_results = persona_memory.search_events("user")
    logger.info(f"\nFound {len(search_results)} events mentioning 'user':")
    for event in search_results[:3]:  # Show first 3
        logger.info(f"  - {event.event_type}: {event.content[:50]}...")
    
    # Get recent events (last hour)
    recent_events = persona_memory.get_recent_events(hours=1)
    logger.info(f"\nFound {len(recent_events)} recent events (last hour)")
    
    # Show event types
    event_types = persona_memory.get_event_types()
    logger.info(f"Event types in memory: {event_types}")
    
    # === Advanced Queries ===
    logger.info("\n=== Advanced Queries ===")
    
    # Get events with metadata filtering (manual filtering for demonstration)
    ml_related = [e for e in persona_memory.get_events() 
                  if e.metadata and ('ml' in str(e.metadata).lower() or 'machine learning' in e.content.lower())]
    logger.info(f"Found {len(ml_related)} machine learning related events")
    
    # Get high-engagement events
    high_engagement = [e for e in persona_memory.get_events() 
                      if e.metadata and e.metadata.get('user_behavior') == 'engagement_high']
    logger.info(f"Found {len(high_engagement)} high-engagement events")
    
    # === Memory Persistence ===
    logger.info("\n=== Memory Persistence ===")
    
    # Save profile to file
    profile_file = "persona_profile.json"
    persona_profile.save_to_file(profile_file)
    logger.info(f"Saved profile to {profile_file}")
    
    # Save events to file
    events_file = "persona_events.json"
    persona_memory.save_to_file(events_file)
    logger.info(f"Saved events to {events_file}")
    
    # Demonstrate loading (in real usage, this would be in a new session)
    loaded_profile = ProfileMemory.load_from_file(profile_file)
    loaded_memory = EventMemory.load_from_file(events_file)
    
    logger.info(f"Loaded profile: {loaded_profile.get_field('name')} (v{loaded_profile.get_field('version')})")
    logger.info(f"Loaded memory: {loaded_memory.get_events_count()} events")
    
    # === Memory Analytics ===
    logger.info("\n=== Memory Analytics ===")
    
    # Analyze event patterns
    events_by_type = {}
    for event in persona_memory.get_events():
        events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
    
    logger.info("Event distribution:")
    for event_type, count in events_by_type.items():
        logger.info(f"  - {event_type}: {count} events")
    
    # Calculate average importance
    all_events = persona_memory.get_events()
    avg_importance = sum(e.importance for e in all_events) / len(all_events)
    logger.info(f"Average event importance: {avg_importance:.1f}/10")
    
    # Find most recent high-importance event
    high_importance_events = [e for e in all_events if e.importance >= 8]
    if high_importance_events:
        most_recent_important = max(high_importance_events, key=lambda e: e.timestamp)
        logger.info(f"Most recent high-importance event: {most_recent_important.content[:50]}...")
    
    # === Memory Management ===
    logger.info("\n=== Memory Management ===")
    
    # Simulate memory cleanup (in this case, no old events to clean)
    removed_count = persona_memory.clear_old_events(older_than_days=7)
    logger.info(f"Cleaned up {removed_count} old events (older than 7 days)")
    
    # Profile updates
    persona_profile.set_field("last_interaction", datetime.now().isoformat())
    persona_profile.set_field("total_interactions", persona_memory.get_events_count())
    
    logger.info(f"Profile last updated: {persona_profile.updated_at}")
    logger.info(f"Total interactions recorded: {persona_profile.get_field('total_interactions')}")
    
    logger.info("\n=== Example completed successfully ===")
    
    # Clean up example files
    import os
    try:
        os.remove(profile_file)
        os.remove(events_file)
        logger.info("Cleaned up example files")
    except:
        pass


if __name__ == "__main__":
    main() 