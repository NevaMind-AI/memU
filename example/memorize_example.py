from memu.llm import OpenAIClient
from memu.memory import MemoryAgent
from datetime import datetime

import re
import os
import shutil

character_test = None

def get_sample_conversation():
    """Get sample conversation from the first session"""
    conversation = [
        {"role": "Caroline", "content": "Hey Mel! Good to see you! How have you been?"},
        {"role": "Melanie", "content": "Hey Caroline! Good to see you! I'm swamped with the kids & work. What's up with you? Anything new?"},
        {"role": "Caroline", "content": "I went to a LGBTQ support group yesterday and it was so powerful."},
        {"role": "Melanie", "content": "Wow, that's cool, Caroline! What happened that was so awesome? Did you hear any inspiring stories?"},
        {"role": "Caroline", "content": "The transgender stories were so inspiring! I was so happy and thankful for all the support."},
        {"role": "Melanie", "content": "Wow, love that painting! So cool you found such a helpful group. What's it done for you?"},
        {"role": "Caroline", "content": "The support group has made me feel accepted and given me courage to embrace myself."},
        {"role": "Melanie", "content": "That's really cool. You've got guts. What now?"},
        {"role": "Caroline", "content": "Gonna continue my edu and check out career options, which is pretty exciting!"},
        {"role": "Melanie", "content": "Wow, Caroline! What kinda jobs are you thinkin' of? Anything that stands out?"},
        {"role": "Caroline", "content": "I'm keen on counseling or working in mental health - I'd love to support those with similar issues."},
        {"role": "Melanie", "content": "You'd be a great counselor! Your empathy and understanding will really help the people you work with. By the way, take a look at this."},
        {"role": "Caroline", "content": "Thanks, Melanie! That's really sweet. Is this your own painting?"},
        {"role": "Melanie", "content": "Yeah, I painted that lake sunrise last year! It's special to me."},
        {"role": "Caroline", "content": "Wow, Melanie! The colors really blend nicely. Painting looks like a great outlet for expressing yourself."},
        {"role": "Melanie", "content": "Thanks, Caroline! Painting's a fun way to express my feelings and get creative. It's a great way to relax after a long day."},
        {"role": "Caroline", "content": "Totally agree, Mel. Relaxing and expressing ourselves is key. Well, I'm off to go do some research."},
        {"role": "Melanie", "content": "Yep, Caroline. Taking care of ourselves is vital. I'm off to go swimming with the kids. Talk to you soon!"}
    ]
    speakers = ["Caroline", "Melanie"]
    return [conversation], speakers

def load_debug_conversation(file_name: str):
    if '.' not in file_name:
        file_name = f"{file_name}.txt"
    with open(f"debug/{file_name}", "r") as f:
        raw = f.readlines()

    conversation = []
    speakers = set()
    for line in raw:
        if ": " in line:
            role, content = line.split(": ", 1)
            speakers.add(role)
            conversation.append({"role": role, "content": content.strip()})

    return conversation, list(speakers)

def process_conversation(conversation=None):
    """Process conversation with memory agent"""
    if conversation is None:
        conversation = []
    
    # Initialize LLM client
    llm_client = OpenAIClient(model="gpt-4o-mini")
    memory_agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")
    
    # Process conversation
    result = memory_agent.run(
        conversation=conversation,
        character_name=character_test or conversation[0]["role"],
        max_iterations=20
    )
    
    if result.get("success"):
        print(f"✅ Processing completed - Iterations: {result.get('iterations', 0)}")
        print(f"📁 Files generated: {len(result.get('files_generated', []))}")
    else:
        print(f"❌ Processing failed: {result.get('error')}")
    
    return result

if __name__ == "__main__":
    print("🌟 MEMORY AGENT DEMONSTRATION")
    print("Loading and processing conversations...")
    
    conversations, speakers = get_sample_conversation()
    character_test = speakers[1]
    
    print(f"Loaded {len(conversations)} conversations for character: {character_test}")
    
    # Process each conversation
    for i, conversation in enumerate(conversations):
        print(f"\n🔄 Processing conversation {i+1} of {len(conversations)}")
        process_conversation(conversation)

    print("\n✅ All conversations processed.")
