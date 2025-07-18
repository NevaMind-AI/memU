"""
Meta Agent System Example - Updated Architecture

This example demonstrates the updated Meta Agent system with modular agent architecture:
1. ActivityAgent: Processes raw conversation → generates activity.md
2. Other Agents: Process activity.md → generate specialized memory files
3. Meta Agent: Orchestrates the fixed workflow and manages all agents

The workflow is now:
Conversation → ActivityAgent → activity.md → ProfileAgent, EventAgent, etc. → Memory Files → Embeddings
"""

import os
from pathlib import Path
from memu import get_llm_config_manager
from memu.memory import MetaAgent
from memu.llm import OpenAIClient, AnthropicClient

# Setup
def setup_llm_client():
    """Setup LLM client based on available API keys"""
    if os.getenv('OPENAI_API_KEY'):
        return OpenAIClient()
    elif os.getenv('ANTHROPIC_API_KEY'):
        return AnthropicClient()
    else:
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        return None

def main():
    """Main example function"""
    
    # Initialize LLM client
    llm_client = setup_llm_client()
    if not llm_client:
        return
    
    # Initialize Meta Agent
    print("Initializing Meta Agent with modular architecture...")
    meta_agent = MetaAgent(
        llm_client=llm_client,
        memory_dir="example_memory",
        agents_dir="example_agents",
        use_database=False  # Using file storage for this example
    )
    
    print(f"Meta Agent initialized with {len(meta_agent.agent_registry.list_agents())} agents")
    
    # Show the fixed workflow
    print("\nFixed Workflow:")
    agents = meta_agent.agent_registry.get_agents_by_priority()
    for i, agent in enumerate(agents, 1):
        print(f"  {i}. {agent.name}: {agent.description}")
        if agent.input_dependencies:
            print(f"     Dependencies: {agent.input_dependencies}")
        else:
            print(f"     Input: Raw conversation")
        print(f"     Output: {agent.output_file}")
    
    # Register a custom agent that depends on activity.md
    custom_prompt = """Task: Extract and organize health and fitness information for {character_name} from the activity summary.

Instructions:
1. Analyze the activity summary to identify NEW health, fitness, and wellness activities
2. Focus on exercise routines, diet, medical appointments, and health goals
3. Include specific metrics, measurements, and progress tracking when mentioned
4. Only include NEW health information not already present in existing health records
5. Organize information in a structured, readable format

Types of health information to extract:
- Exercise activities and workout routines
- Diet and nutrition information
- Medical appointments and health checkups
- Health goals and fitness targets
- Sleep patterns and wellness habits
- Medications and supplements
- Health measurements and progress tracking

Input:
- Activity Summary: 
{conversation}
- Existing Health Information: 
{existing_health}
- Character: 
{character_name}
- Session Date: 
{session_date}

Output Format:
## Exercise & Fitness
[List physical activities, workouts, and exercise routines]

## Diet & Nutrition
[Information about meals, dietary choices, and nutrition]

## Health Monitoring
[Medical appointments, measurements, and health tracking]

## Wellness Goals
[Health and fitness goals, targets, and milestones]

New Health Information:"""
    
    print("\nRegistering custom health agent...")
    health_agent = meta_agent.register_new_agent_from_prompt(
        name="health_agent",
        prompt_content=custom_prompt,
        description="Extract health and fitness information from activity",
        output_file="health.md",
        input_dependencies=["activity.md"],  # Depends on ActivityAgent output
        priority=6  # Higher priority than some default agents
    )
    
    print(f"Registered agent: {health_agent.name}")
    
    # Check agent status
    print("\nAgent Status:")
    status = meta_agent.get_agent_status()
    print(f"Total agents: {status['total_agents']}")
    print(f"Agents with issues: {status['agents_with_issues']}")
    
    print("\nAgent Execution Order:")
    for i, agent in enumerate(meta_agent.agent_registry.get_agents_by_priority(), 1):
        print(f"  {i}. {agent['name']}: {agent['description']} (priority: {agent['priority']})")
        if agent['missing_dependencies']:
            print(f"    Missing: {agent['missing_dependencies']}")
    
    # Sample conversation to process
    sample_conversation = """
    User: Hey Alex, how was your day today?
    
    Alex: It was pretty good! I went for a 5-mile run this morning - managed to do it in 42 minutes, which is a new personal best. I'm really pleased with my progress training for the marathon.
    
    User: That's awesome! What else did you do?
    
    Alex: After the run, I had a healthy breakfast - oatmeal with berries and some protein powder. Then I went to work where I had that important presentation about the Q3 marketing strategy. It went really well, and my manager Sarah said she was impressed.
    
    User: Nice! Any plans for the evening?
    
    Alex: Yeah, I'm meeting my friend Mike for dinner at that new Italian restaurant downtown. We're going to discuss our upcoming hiking trip to Yosemite. Oh, and I need to remember to call my mom later - it's her birthday tomorrow and I still need to arrange the surprise party with my sister.
    
    User: Sounds like a busy but great day!
    
    Alex: Definitely! I'm also planning to read a chapter of that book on machine learning before bed. I'm trying to learn more about AI for my job in software development.
    """
    
    print(f"\nProcessing sample conversation through the agent pipeline...")
    
    # Process the conversation
    results = meta_agent.process_conversation(
        conversation=sample_conversation,
        character_name="Alex",
        session_date="2024-01-15"
    )
    
    # Display results
    print(f"\nProcessing Results for {results['character_name']}:")
    print(f"Session Date: {results['session_date']}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Embeddings Generated: {len(results['embeddings_generated'])}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print(f"\nAgent Outputs (in execution order):")
    
    # Show outputs in execution order
    agents_by_priority = meta_agent.agent_registry.get_agents_by_priority()
    for agent in agents_by_priority:
        if agent.name in results['agent_outputs']:
            output = results['agent_outputs'][agent.name]
            print(f"\n{agent.name} → {agent.output_file}:")
            print(f"  Output length: {len(output)} characters")
            print(f"  Preview: {output[:200]}...")
            
            if agent.name == "activity_agent":
                print(f"  (This output becomes input for other agents)")
    
    # Show file structure created
    memory_path = Path("example_memory") / "Alex"
    if memory_path.exists():
        print(f"\nMemory files created:")
        for file in memory_path.glob("*.md"):
            file_size = file.stat().st_size
            print(f"  - {file.name} ({file_size} bytes)")
    
    print(f"\nAgent configuration files:")
    agents_path = Path("example_agents")
    if agents_path.exists():
        for file in agents_path.glob("*.json"):
            print(f"  - {file.name}")

def demonstrate_agent_workflow():
    """Demonstrate the step-by-step agent workflow"""
    print("=== Agent Workflow Demonstration ===\n")
    
    print("Step-by-Step Workflow:")
    print("1. Raw Conversation Input")
    print("   ↓")
    print("2. ActivityAgent (priority: 10)")
    print("   - Processes: Raw conversation")
    print("   - Generates: activity.md (comprehensive summary)")
    print("   ↓")
    print("3. ProfileAgent (priority: 5)")
    print("   - Processes: activity.md")
    print("   - Generates: profile.md (character information)")
    print("   ↓")
    print("4. EventAgent (priority: 4)")
    print("   - Processes: activity.md")
    print("   - Generates: events.md (event records)")
    print("   ↓")
    print("5. ReminderAgent (priority: 3)")
    print("   - Processes: activity.md")
    print("   - Generates: reminders.md (todo items)")
    print("   ↓")
    print("6. InterestAgent (priority: 2)")
    print("   - Processes: activity.md")
    print("   - Generates: interests.md (hobbies/interests)")
    print("   ↓")
    print("7. StudyAgent (priority: 1)")
    print("   - Processes: activity.md")
    print("   - Generates: study.md (learning information)")
    print("   ↓")
    print("8. Custom Agents (if any)")
    print("   - Process: activity.md or other dependencies")
    print("   - Generate: custom output files")
    print("   ↓")
    print("9. Embedding Generation")
    print("   - Generate vectors for all new content")
    print("   - Store in database or file system")

def create_custom_agent_example():
    """Example of creating a custom agent that fits into the workflow"""
    
    # Create a social analysis agent
    social_prompt = """Task: Analyze social interactions and relationships for {character_name} from the activity summary.

Instructions:
1. Analyze the activity summary to understand social interactions and relationships
2. Identify people mentioned and the nature of relationships
3. Note social activities, meetings, and interpersonal dynamics
4. Track relationship changes and social patterns

Input:
- Activity Summary: 
{conversation}
- Character: 
{character_name}
- Session Date: 
{session_date}

Output Format:
## People Mentioned
[List of people and their relationship to the character]

## Social Activities
[Social events, meetings, gatherings]

## Relationship Dynamics
[Changes in relationships, conflicts, positive interactions]

## Social Patterns
[Regular social habits and patterns]

Social Analysis:"""
    
    print("Creating custom social analysis agent...")
    
    # Save prompt to file
    prompt_file = Path("example_prompts") / "social_analysis.txt"
    prompt_file.parent.mkdir(exist_ok=True)
    
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(social_prompt)
    
    print(f"Custom prompt saved to: {prompt_file}")
    print("This agent would:")
    print("  - Depend on: activity.md (output from ActivityAgent)")
    print("  - Generate: social.md")
    print("  - Priority: Can be set based on importance")
    print("  - Automatically integrate into the workflow")

if __name__ == "__main__":
    print("=== Meta Agent System - Modular Architecture ===\n")
    
    # Run main example
    main()
    
    print("\n" + "="*60)
    demonstrate_agent_workflow()
    
    print("\n" + "="*60)
    print("=== Custom Agent Creation Example ===\n")
    
    # Show how to create custom agents
    create_custom_agent_example()
    
    print("\n=== Example Complete ===")
    print("\nKey Benefits of the New Architecture:")
    print("✅ Fixed, predictable workflow")
    print("✅ ActivityAgent creates standardized input for all other agents")
    print("✅ Each agent has a single, focused responsibility")
    print("✅ Easy to add new agents without disrupting existing ones")
    print("✅ Meta Agent only handles orchestration")
    print("✅ All agents are completely modular and independent") 