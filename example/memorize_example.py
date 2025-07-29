from memu.llm import OpenAIClient
from memu.memory import MemoryAgent
import json
from datetime import datetime

import re
import os
import shutil

character_test = None

def load_locomo_conversation(sample_id: int, session_id: int|str|list, add_image_caption: bool = False, perserve_role: bool = True):

    try:
        with open(f"locomo/locomo10.json", "r") as f:
            data = json.load(f)

        sample = data[sample_id]
        conversation = sample["conversation"]

        speaker_a = conversation.get("speaker_a", "Speaker A")
        speaker_b = conversation.get("speaker_b", "Speaker B")
        speakers = [speaker_a, speaker_b]

        if not perserve_role:
            remap_role = {
                speaker_a: "user",
                speaker_b: "assistant"
            }
        
        if isinstance(session_id, int):
            session_ids = [session_id]
        elif isinstance(session_id, str):
            session_ids = [int(session_id)]
        elif isinstance(session_id, list):
            session_ids = [int(sid) for sid in session_id]

        conversation_messages = []
        for session_id in session_ids:
            conversation_single = []
            if f"session_{session_id+1}" in conversation:
                session = conversation[f"session_{session_id+1}"]
                
                for message in session:
                    speaker = message["speaker"]
                    content = message["text"]

                    if not perserve_role:
                        speaker = remap_role.get(speaker, "Unknown")

                    if add_image_caption and "blip_caption" in message:
                        content = f"({speaker} shares {message['blip_caption']}.) {content}"

                    conversation_single.append({
                        "role": speaker,
                        "content": content
                    })
            conversation_messages.append(conversation_single)

        return conversation_messages, speakers

    except Exception as e:
        raise

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

def process_conversation(conversation: list[dict] = []):
    """Process conversation with memory agent"""
    
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
    
    conversations, speakers = load_locomo_conversation(sample_id=2, session_id=[0,1], add_image_caption=True, perserve_role=True)
    character_test = speakers[1]
    
    print(f"Loaded {len(conversations)} conversations for character: {character_test}")
    
    # Process each conversation
    for i, conversation in enumerate(conversations):
        print(f"\n🔄 Processing conversation {i+1} of {len(conversations)}")
        process_conversation(conversation)

    print("\n✅ All conversations processed.")
