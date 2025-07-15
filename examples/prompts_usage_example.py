#!/usr/bin/env python3
"""
Example: Using Prompts System in MemU

This example demonstrates how to use the prompts system that is now integrated
into the memu module.
"""

import sys
from pathlib import Path

# Add parent directory to path to import memu
sys.path.insert(0, str(Path(__file__).parent.parent))

from memu import PromptLoader, get_prompt_loader, MemoryAgent
from memu.llm import AnthropicClient

def example_direct_prompt_loading():
    """Example of directly using the prompt loader"""
    print("=== Direct Prompt Loading ===")
    
    # Method 1: Direct PromptLoader initialization
    prompts_dir = Path(__file__).parent.parent / "memu" / "prompts"
    loader = PromptLoader(str(prompts_dir))
    
    # List available prompts
    available = loader.list_available_prompts()
    print(f"Available prompts: {available}")
    
    # Load specific prompts
    system_message = loader.load_prompt("system_message")
    print(f"System message: {system_message[:100]}...")
    
    # Method 2: Using the global prompt loader function
    global_loader = get_prompt_loader(str(prompts_dir))
    events_template = global_loader.load_prompt("analyze_session_for_events")
    print(f"Events template: {events_template[:100]}...")

def example_prompt_formatting():
    """Example of formatting prompts with variables"""
    print("\n=== Prompt Formatting ===")
    
    # Get prompt loader
    prompts_dir = Path(__file__).parent.parent / "memu" / "prompts" 
    loader = get_prompt_loader(str(prompts_dir))
    
    # Load and format events analysis prompt
    events_template = loader.load_prompt("analyze_session_for_events")
    formatted_prompt = events_template.format(
        character_name="Alice",
        conversation="Alice: Hello! How are you?\nBob: I'm doing great, thanks!",
        existing_events="None",
        session_date="2024-01-15"
    )
    
    print("Formatted events prompt:")
    print(formatted_prompt)
    
    # Load and format profile analysis prompt  
    profile_template = loader.load_prompt("analyze_session_for_profile")
    formatted_profile = profile_template.format(
        character_name="Alice",
        conversation="Alice mentioned she works as a software engineer in San Francisco.",
        events="2024-01-15: Alice discussed her work as a software engineer.",
        existing_profile="None"
    )
    
    print("\nFormatted profile prompt:")
    print(formatted_profile)

def example_memory_agent_with_prompts():
    """Example of MemoryAgent using the integrated prompts"""
    print("\n=== MemoryAgent with Prompts ===")
    
    # Create memory agent (automatically uses prompts from memu/prompts)
    agent = MemoryAgent(memory_dir="example_memory")
    
    print("MemoryAgent automatically has access to all prompts:")
    print(f"- System message: {len(agent.prompt_loader.load_prompt('system_message'))} chars")
    print(f"- Events template: {len(agent.prompt_loader.load_prompt('analyze_session_for_events'))} chars") 
    print(f"- Profile template: {len(agent.prompt_loader.load_prompt('analyze_session_for_profile'))} chars")
    
    # The agent's internal methods now use these prompts automatically
    # when analyze_session_for_events and analyze_session_for_profile are called
    
    print("\nMemoryAgent tools that use prompts:")
    tools = agent.get_available_tools()
    for tool in tools:
        if 'analyze' in tool['function']['name']:
            print(f"- {tool['function']['name']}: {tool['function']['description']}")

def example_custom_prompts():
    """Example of working with custom prompts"""
    print("\n=== Working with Custom Prompts ===")
    
    # You can still load prompts from any directory
    custom_dir = Path("custom_prompts")  # hypothetical directory
    
    # For now, let's work with the default prompts
    prompts_dir = Path(__file__).parent.parent / "memu" / "prompts"
    loader = get_prompt_loader(str(prompts_dir))
    
    # You can modify prompts at runtime
    base_template = loader.load_prompt("analyze_session_for_events")
    
    # Add custom instructions
    custom_template = base_template + "\n\nAdditional instruction: Focus on emotional content."
    
    # Use the modified template
    formatted = custom_template.format(
        character_name="Bob",
        conversation="Bob seemed upset about something.",
        existing_events="",
        session_date="2024-01-15"
    )
    
    print("Custom modified prompt:")
    print(formatted)

def main():
    """Run all examples"""
    print("MemU Prompts System Examples")
    print("=" * 40)
    
    try:
        example_direct_prompt_loading()
        example_prompt_formatting()
        example_memory_agent_with_prompts()
        example_custom_prompts()
        
        print("\n" + "=" * 40)
        print("✓ All examples completed successfully!")
        print("\nKey benefits of the integrated prompts system:")
        print("- Prompts are now part of the memu module")
        print("- Easy to import: from memu import PromptLoader, get_prompt_loader")
        print("- MemoryAgent automatically uses prompts for analysis")
        print("- Centralized prompt management")
        print("- Template formatting with variables")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 