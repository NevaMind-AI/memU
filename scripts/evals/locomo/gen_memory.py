import json
import os
import sys
from typing import Dict, List
import dotenv
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# Load environment variables
dotenv.load_dotenv()

from personalab.llm import OpenAIClient
from personalab.memory.base import Memory, ProfileMemory, EventMemory, MindMemory

def update_profile_memory(conversation: List[Dict], session_time: str, llm_client: OpenAIClient, previous_profile: List[str] = None) -> Dict:
    """
    Update profile memory based on conversation content using modification stage prompt
    """
    # Format conversation for analysis
    conv_text = f"Session Time: {session_time}\n"
    for msg in conversation:
        conv_text += f"{msg['speaker']}: {msg['text']}\n"
    
    # Format current profile and events
    current_profile = previous_profile if previous_profile else []
    current_events = []  # For this demo, we'll use empty events
    
    # Use PersonaLab's modification stage prompt
    prompt = f"""Please analyze the following conversation content and extract user profile updates and important events.

Current User Profile:
{format_profile(current_profile) if current_profile else "None"}

Current Event Records:
{format_events(current_events) if current_events else "None"}

Current Conversation Content:
{conv_text}

Note:
1. the profile must be factual and accurate.
2. the profile must be very concise and clear.
3. the events must be very concise and clear.
4. the profile and events must be updated based on the conversation content.



Return the updated profile and events suggestion directly in the following XML format:
<update>
Add: profile [new profile item]
Delete: profile [profile item to remove]
Update: profile [profile item to update] -> profile [new profile item]
Add: event [new event item]
Delete: event [event item to remove]
Update: event [event item to update] -> event [new event item]
...
</update>
"""
    
    messages = [{"role": "user", "content": prompt}]
    
    response = llm_client.chat_completion(
        messages=messages,
        model="gpt-4.1-mini",
        temperature=0.2,
        max_tokens=4000
    )
    
    print(f"\n🔍 Memory Update Suggestion LLM Output ({session_time}):")
    print("=" * 80)
    print(response.content)
    print("=" * 80)
    
    # Parse modification result
    profile_items, event_items = parse_modification_result(response.content)
    
    return {
        "success": True,
        "session_time": session_time,
        "profile_items": profile_items,
        "event_items": event_items,
        "item_count": len(profile_items)
    }

def update_event_memory(conversation: List[Dict], session_time: str, llm_client: OpenAIClient, previous_events: List[str] = None, previous_profile: List[str] = None, modification_result: str = None) -> Dict:
    """
    Update event memory using PersonaLab's update stage prompt
    """
    # Format conversation for analysis
    conv_text = f"Session Time: {session_time}\n"
    for msg in conversation:
        conv_text += f"{msg['speaker']}: {msg['text']}\n"
    
    current_profile = previous_profile if previous_profile else []
    current_events = previous_events if previous_events else []
    
    # Use PersonaLab's update stage prompt
    prompt = f"""Please update the user profile based on new information.

Current Conversation Content:
{conv_text}

Current User Profile:
{format_profile(current_profile) if current_profile else "None"}

Current Event Records:
{format_events(current_events) if current_events else "None"}

Update Suggestion:
{modification_result if modification_result else "No specific updates"}

Please integrate the new information into the user profile to generate a complete, coherent user profile description.
Requirements:
1. Based on the update suggestion, update the user profile and event records.
2. must follow the update suggestion.
3. all suggestions should be followed.
4. the profile must be factual and accurate.
5. the profile must be very concise and clear.
6. the events must be very concise and clear.

Please return the updated complete user profile directly in the following XML format:
<memory>
<profile>
<item>profile item 1</item>
<item>profile item 2</item>
</profile>
<events>
<item>event item 1</item>
<item>event item 2</item>
</events>
</memory>
"""
    
    messages = [{"role": "user", "content": prompt}]
    response = llm_client.chat_completion(
        messages=messages,
        model="gpt-4.1-mini",
        temperature=0.2,
        max_tokens=4000
    )
    
    print(f"\n🔍 Update Memory LLM Output ({session_time}):")
    print("=" * 80)
    print(response.content)
    print("=" * 80)

    # Parse update result
    profile_items, event_items = parse_modification_result(response.content)
    
    
    return {
        "success": True,
        "session_time": session_time,
        "profile_items": profile_items,
        "event_items": event_items,
        "item_count": len(event_items)
    }

def update_mind_memory(conversation: List[Dict], session_time: str, llm_client: OpenAIClient, updated_profile: List[str] = None, updated_events: List[str] = None) -> Dict:
    """
    Update mind memory using PersonaLab's theory of mind stage prompt
    """
    # Format conversation for analysis
    conv_text = f"Session Time: {session_time}\n"
    for msg in conversation:
        conv_text += f"{msg['speaker']}: {msg['text']}\n"
    
    # Format updated memory content
    updated_memory_content = ""
    if updated_profile:
        updated_memory_content += "\n".join(updated_profile) + "\n"
    if updated_events:
        updated_memory_content += "\n".join(updated_events)
    
    # Use PersonaLab's theory of mind stage prompt
    prompt = f"""Please conduct a Theory of Mind analysis on the following conversation to deeply understand the user's psychological state and behavioral patterns.

Conversation Content:
{conv_text}
memory:
{updated_memory_content}

Please analyze the conversation and extract:
1. User's main purposes and motivations
2. User's emotional states and changes
3. User's communication style and engagement patterns
4. User's knowledge level and learning tendencies
5. should be concise and clear

Please return the insights directly in the following XML format:
<insights>
<item>Insight 1</item>
<item>Insight 2</item>
<item>Insight 3</item>
</insights>
"""
    
    messages = [{"role": "user", "content": prompt}]
    
    response = llm_client.chat_completion(
        messages=messages,
        model="gpt-4.1-mini",
        temperature=0.3,
        max_tokens=16000
    )
    
    print(f"\n🔍 Theory of Mind Memory LLM Output ({session_time}):")
    print("=" * 80)
    print(f"Response success: {response.success if hasattr(response, 'success') else 'Unknown'}")
    print(f"Response content length: {len(response.content) if response.content else 0}")
    print(f"Response content: '{response.content}'")
    print("=" * 80)
    
    mind_items = parse_insights_content(response.content)
    
    print(f"\n📊 Parsed Mind Memory Results ({session_time}):")
    print(f"  Mind Insights ({len(mind_items)}):")
    for i, item in enumerate(mind_items, 1):
        print(f"    {i}. {item}")
    print("-" * 60)
    
    return {
        "success": True,
        "session_time": session_time,
        "mind_items": mind_items,
        "item_count": len(mind_items)
    }

def parse_modification_result(content: str) -> tuple[List[str], List[str]]:
    """
    Parse LLM returned content, extract profile and events using XML parsing
    """
    profile_updates = []
    events_updates = []
    
    try:
        # Extract XML content
        xml_content = extract_xml_content(content)
        if xml_content:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Handle <memory> format (from update stage)
            if root.tag == 'memory':
                # Extract profile items
                for profile_section in root.findall('.//profile'):
                    for item in profile_section.findall('item'):
                        if item.text and item.text.strip():
                            profile_updates.append(item.text.strip())
                
                # Extract events items
                for events_section in root.findall('.//events'):
                    for item in events_section.findall('item'):
                        if item.text and item.text.strip():
                            events_updates.append(item.text.strip())
            
            # Handle <update> format (from modification stage) - parse text instructions
            elif root.tag == 'update':
                text_content = root.text if root.text else ""
                for child in root:
                    if child.text:
                        text_content += child.text
                    if child.tail:
                        text_content += child.tail
                
                # Parse Add/Update/Remove instructions
                lines = text_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('Add: profile '):
                        item = line.replace('Add: profile ', '').strip('[]"')
                        if item:
                            profile_updates.append(item)
                    elif line.startswith('Update: profile '):
                        # Extract the new profile item after '->'
                        if ' -> profile ' in line:
                            item = line.split(' -> profile ')[1].strip('[]"')
                            if item:
                                profile_updates.append(item)
                    elif line.startswith('Add: event '):
                        item = line.replace('Add: event ', '').strip('[]"')
                        if item:
                            events_updates.append(item)
                    elif line.startswith('Update: event '):
                        # Extract the new event item after '->'
                        if ' -> event ' in line:
                            item = line.split(' -> event ')[1].strip('[]"')
                            if item:
                                events_updates.append(item)
            
            # Handle <analysis> format (legacy)
            elif root.tag == 'analysis':
                # Extract profile items
                for profile_section in root.findall('.//profile'):
                    for item in profile_section.findall('item'):
                        if item.text and item.text.strip():
                            profile_updates.append(item.text.strip())
                
                # Extract events items
                for events_section in root.findall('.//events'):
                    for item in events_section.findall('item'):
                        if item.text and item.text.strip():
                            events_updates.append(item.text.strip())
            

            return profile_updates, events_updates
        
        # Fallback to text parsing if XML parsing fails
        print(f"\n⚠️  XML parsing failed, falling back to text parsing...")
        return parse_text_format(content)
        
    except Exception as e:
        print(f"\n❌ XML parsing error: {e}")
        # Fallback to text parsing
        return parse_text_format(content)

def parse_insights_content(content: str) -> List[str]:
    """
    Parse insights content from LLM response
    """
    insights_list = []
    
    print(f"\n🔧 Parsing insights content...")
    print(f"Content to parse (length {len(content) if content else 0}): '{content[:200] if content else 'None'}{'...' if content and len(content) > 200 else ''}'")
    
    if not content or not content.strip():
        print("❌ Content is empty or None")
        return insights_list
    
    try:
        # Extract XML content
        xml_content = extract_xml_content(content)
        print(f"Extracted XML content: '{xml_content[:200] if xml_content else 'None'}{'...' if xml_content and len(xml_content) > 200 else ''}'")
        
        if xml_content:
            # Parse XML
            root = ET.fromstring(xml_content)
            print(f"XML root tag: {root.tag}")
            
            # Extract insights items
            insights_sections = root.findall('.//insights')
            print(f"Found {len(insights_sections)} insights sections")
            
            for insights_section in insights_sections:
                items = insights_section.findall('item')
                print(f"Found {len(items)} items in insights section")
                for item in items:
                    if item.text and item.text.strip():
                        insights_list.append(item.text.strip())
                        print(f"Added insight: {item.text.strip()}")
            
            # If root is insights directly
            if root.tag == 'insights':
                items = root.findall('item')
                print(f"Found {len(items)} items in root insights")
                for item in items:
                    if item.text and item.text.strip():
                        insights_list.append(item.text.strip())
                        print(f"Added insight: {item.text.strip()}")
            
            print(f"Total insights extracted: {len(insights_list)}")
            return insights_list
        
        # Fallback to text parsing
        print("XML parsing failed, trying text parsing...")
        return parse_insights_text_format(content)
        
    except Exception as e:
        print(f"❌ XML parsing error: {e}")
        # Fallback to text parsing
        return parse_insights_text_format(content)

def parse_insights_text_format(content: str) -> List[str]:
    """Fallback text parsing for insights when XML parsing fails"""
    insights_list = []
    
    print(f"🔧 Text parsing insights...")
    
    # Simple text parsing logic
    lines = content.split('\n')
    
    in_insights_section = False
    for line in lines:
        line = line.strip()
        
        # Check if we're entering insights section
        if '<insights>' in line.lower():
            in_insights_section = True
            continue
        elif '</insights>' in line.lower():
            in_insights_section = False
            continue
        
        # Extract items from insights section
        if in_insights_section:
            if line.startswith('<item>') and line.endswith('</item>'):
                item_text = line.replace('<item>', '').replace('</item>', '').strip()
                if item_text:
                    insights_list.append(item_text)
                    print(f"Text parsed insight: {item_text}")
        
        # Also look for general insight patterns
        elif line and any(keyword in line.lower() for keyword in ['insight', 'analysis', 'understanding', 'shows', 'demonstrates', 'indicates']):
            insights_list.append(line)
            print(f"Pattern matched insight: {line}")
    
    print(f"Text parsing found {len(insights_list)} insights")
    return insights_list

def extract_xml_content(content: str) -> str:
    """Extract XML content from LLM response"""
    try:
        # Look for XML tags in the content
        xml_patterns = [
            r'<update>.*?</update>',
            r'<memory>.*?</memory>',
            r'<analysis>.*?</analysis>',
            r'<insights>.*?</insights>'
        ]
        
        for pattern in xml_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                return matches[0]
        
        return ""
        
    except Exception as e:
        return ""

def parse_text_format(content: str) -> tuple[List[str], List[str]]:
    """Fallback text parsing when XML parsing fails"""
    profile_updates = []
    events_updates = []
    
    # Simple text parsing logic
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if 'profile' in line.lower() and ('update' in line.lower() or 'item' in line.lower()):
            current_section = 'profile'
        elif 'event' in line.lower() and ('update' in line.lower() or 'item' in line.lower()):
            current_section = 'events'
        elif line and current_section == 'profile':
            profile_updates.append(line)
        elif line and current_section == 'events':
            events_updates.append(line)
    
    return profile_updates, events_updates

def format_profile(profile_items: List[str]) -> str:
    """Format profile items for display"""
    if not profile_items:
        return "None"
    return "\n".join(f"- {item}" for item in profile_items)

def format_events(events: List[str]) -> str:
    """Format event items for display"""
    if not events:
        return "None"
    return "\n".join(f"- {event}" for event in events)

def format_conversation(conversation: List[Dict[str, str]]) -> str:
    """Format conversation for LLM input"""
    formatted_lines = []
    for msg in conversation:
        formatted_lines.append(f"{msg['speaker']}: {msg['text']}")
    return "\n".join(formatted_lines)

def initialize_memory_components(agent_id: str, user_id: str) -> Dict:
    """Initialize memory components for a user"""
    return {
        "agent_id": agent_id,
        "user_id": user_id,
        "profile_memory": [],
        "event_memory": [],
        "mind_memory": []
    }

def update_all_memory_components(conversation: List[Dict], session_time: str, llm_client: OpenAIClient, memory_state: Dict) -> Dict:
    """
    Update all three memory components using PersonaLab's pipeline approach
    """
    # Stage 1: Modification - analyze conversation and extract information
    profile_result = update_profile_memory(
        conversation, session_time, llm_client, 
        memory_state.get("profile_memory", [])
    )
    
    # Stage 2: Update - update profile and events based on modification
    event_result = update_event_memory(
        conversation, session_time, llm_client,
        memory_state.get("event_memory", []),
        memory_state.get("profile_memory", []),
        profile_result["profile_items"]
    )
    
    # Stage 3: Theory of Mind - psychological analysis
    mind_result = update_mind_memory(
        conversation, session_time, llm_client,
        profile_result["profile_items"],
        event_result["event_items"]
    )
    
    # Update memory state
    memory_state["profile_memory"].extend(profile_result["profile_items"])
    memory_state["event_memory"].extend(event_result["event_items"])
    memory_state["mind_memory"].extend(mind_result["mind_items"])
    
    return {
        "memory_state": memory_state,
        "session_updates": {
            "profile": profile_result,
            "event": event_result,
            "mind": mind_result
        }
    }

def main():
    """Main function to process conversations with PersonaLab-style memory updates"""
    
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    llm_client = OpenAIClient(api_key=api_key)
    
    # Load conversation data
    with open('data/locomo10.json', 'r') as f:
        data = json.load(f)
    
    # Process conversations with memory updates
    all_results = []
    final_profiles = {}
    
    for idx, d in enumerate(data):
        conversation = d['conversation']
        qa = d['qa']
        sample_id = d.get('sample_id', f'sample_{idx}')
        
        print(f"\n🔄 Processing sample {idx+1}/{len(data)}: {sample_id}")
        print("=" * 60)
        
        # Initialize memory for this user
        memory_state = initialize_memory_components(
            agent_id="locomo_agent",
            user_id=sample_id
        )
        
        # Process each session in the conversation
        session_results = []
        
        for i in range(100):
            print(f"Processing session {i}")
            session_key = f"session_{i}"
            if session_key not in conversation:
                continue
                
            session_time = conversation[f"session_{i}_date_time"]
            session = conversation[session_key]
            
            print(f"\n  📅 Processing Session {i} ({session_time})")
            
            # Update all memory components
            memory_update_result = update_all_memory_components(
                session, session_time, llm_client, memory_state
            )
            
            # Update memory state
            memory_state = memory_update_result["memory_state"]
            session_updates = memory_update_result["session_updates"]
            
            # Store session results
            session_results.append({
                "session_id": i,
                "session_time": session_time,
                "message_count": len(session),
                "updates": session_updates
            })
            
        
        # Create final user profile summary
        final_user_profile = {
            "sample_id": sample_id,
            "sample_index": idx,
            "total_sessions_processed": len(session_results),
            "final_memory_state": {
                "profile_memory": memory_state["profile_memory"],
                "event_memory": memory_state["event_memory"], 
                "mind_memory": memory_state["mind_memory"]
            },
            "memory_counts": {
                "profile_items": len(memory_state["profile_memory"]),
                "event_items": len(memory_state["event_memory"]),
                "mind_insights": len(memory_state["mind_memory"])
            },
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Save individual user profile
        profile_filename = f'memory/user_profile_{sample_id}.json'
        with open(profile_filename, 'w') as f:
            json.dump(final_user_profile, f, indent=2)
        
        print(f"\n💾 Saved user profile: {profile_filename}")
        print(f"📊 Final Memory Summary for {sample_id}:")
        print(f"   📝 Profile items: {len(memory_state['profile_memory'])}")
        print(f"   📅 Event items: {len(memory_state['event_memory'])}")
        print(f"   🧠 Mind insights: {len(memory_state['mind_memory'])}")
        
        # Store in final profiles collection
        final_profiles[sample_id] = final_user_profile
        
        # Store results for this sample
        sample_result = {
            "sample_id": sample_id,
            "sample_index": idx,
            "total_sessions": len(session_results),
            "sessions": session_results,
            "final_memory_state": memory_state,
            "final_user_profile": final_user_profile
        }
        all_results.append(sample_result)
    
    # Save consolidated results
    output_file = 'memory_pipeline_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Save all final profiles
    profiles_file = 'final_user_profiles.json'
    with open(profiles_file, 'w') as f:
        json.dump(final_profiles, f, indent=2)
    
    print(f"\n📁 Results saved:")
    print(f"   📄 Individual profiles: user_profile_[sample_id].json files")
    print(f"   📄 All profiles: {profiles_file}")
    print(f"   📄 Full results: {output_file}")
    
    # Print final summary
    total_sessions = sum(len(result["sessions"]) for result in all_results)
    total_profile_items = sum(len(result["final_memory_state"]["profile_memory"]) for result in all_results)
    total_event_items = sum(len(result["final_memory_state"]["event_memory"]) for result in all_results)
    total_mind_items = sum(len(result["final_memory_state"]["mind_memory"]) for result in all_results)
    
    print(f"\n📊 Final Processing Summary:")
    print(f"   👥 Users processed: {len(all_results)}")
    print(f"   💬 Total sessions: {total_sessions}")
    print(f"   📝 Total profile items: {total_profile_items}")
    print(f"   📅 Total event items: {total_event_items}")
    print(f"   🧠 Total mind insights: {total_mind_items}")
    print(f"   🎯 Total memory items: {total_profile_items + total_event_items + total_mind_items}")

if __name__ == "__main__":
    main()

        

   




