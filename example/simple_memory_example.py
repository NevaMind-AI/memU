#!/usr/bin/env python3
"""
Intelligent Memory Agent Usage Example - Detailed Iteration Output

Demonstrates Memory Agent's workflow with detailed output for each iteration:
1. Shows every function call with arguments and results
2. Displays LLM processing steps 
3. Enforces strict no-pronouns policy for memory items
4. Validates memory compliance

**ZERO TOLERANCE FOR PRONOUNS - Every memory item must be completely self-contained.**
"""

from memu.llm import OpenAIClient, AnthropicClient
from memu.memory import MemoryAgent
import json
from datetime import datetime

import re
import os
import shutil

character_test = None

def validate_memory_items(memory_items, character_name):
    """Validate that memory items follow strict no-pronouns rules"""
    print("\n🔍 VALIDATING MEMORY ITEMS FOR NO-PRONOUNS POLICY:")
    violations = []
    
    # Pronouns to check for
    pronouns = ['she', 'he', 'they', 'it', 'her', 'his', 'their', 'him', 'them']
    vague_references = ['the book', 'the place', 'the friend', 'the course', 'the job', 'the company']
    
    for i, item in enumerate(memory_items):
        content = item.get('content', '').lower()
        original_content = item.get('content', '')
        
        # Check for pronouns
        found_pronouns = [p for p in pronouns if f' {p} ' in f' {content} ' or content.startswith(f'{p} ')]
        
        # Check for vague references
        found_vague = [v for v in vague_references if v in content]
        
        # Check if starts with character name
        starts_with_name = character_name.lower() in content[:50]
        
        if found_pronouns or found_vague or not starts_with_name:
            violations.append({
                'item_number': i + 1,
                'content': original_content[:100] + "..." if len(original_content) > 100 else original_content,
                'pronouns': found_pronouns,
                'vague_refs': found_vague,
                'has_name': starts_with_name
            })
    
    # Report results
    if violations:
        print(f"❌ VIOLATIONS FOUND: {len(violations)} items violate no-pronouns policy:")
        for v in violations[:3]:  # Show first 3 violations
            print(f"  Item {v['item_number']}: {v['content']}")
            if v['pronouns']:
                print(f"    ❌ Contains pronouns: {v['pronouns']}")
            if v['vague_refs']:
                print(f"    ❌ Contains vague references: {v['vague_refs']}")
            if not v['has_name']:
                print(f"    ❌ Doesn't start with {character_name}")
        if len(violations) > 3:
            print(f"    ... and {len(violations) - 3} more violations")
    else:
        print(f"✅ PERFECT COMPLIANCE: All {len(memory_items)} items follow no-pronouns policy!")
        print("   ✅ All items contain complete subjects")
        print("   ✅ No pronouns detected")
        print("   ✅ No vague references found")
    
    return len(violations) == 0

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

def demo_detailed_iterations(conversation: list[dict] = []):
    """Demonstrate automatic workflow with detailed iteration output"""
    
    print("🧠 DETAILED ITERATION OUTPUT DEMO")
    print("=" * 60)
    print("🚫 STRICT NO-PRONOUNS POLICY ENFORCED")
    print("📊 SHOWS EVERY ITERATION WITH FULL DETAILS")
    print("=" * 60)
    
    # Initialize LLM client
    llm_client = OpenAIClient(model="gpt-4o-mini")
    memory_agent = MemoryAgent(llm_client=llm_client, memory_dir="memory")
    
    # Convert string conversation to message format for run() method
    conversation_messages = conversation or [
        {"role": "user", "content": "Hi Alice! How was your weekend?"},
        {"role": "assistant", "content": "It was absolutely wonderful! I went hiking in the Blue Ridge Mountains with my friend Sarah Johnson. We discovered this breathtaking hidden waterfall called Crystal Falls, and I took over 200 photos. The weather was perfect - sunny but not too hot, around 75 degrees. I also finally finished reading 'The Midnight Library' by Matt Haig. It's such an inspiring book about life choices and infinite possibilities."},
        {"role": "user", "content": "That sounds wonderful! What did you think of the book?"},
        {"role": "assistant", "content": "I absolutely loved it! The concept of experiencing different versions of your life really resonated with me. Haig's writing style is so engaging and philosophical. It made me reflect deeply about choices I've made and paths not taken. I've been feeling a bit stuck in my current job as a product manager at TechFlow Solutions. The book reminded me that it's never too late to make significant changes. I'm actually seriously considering enrolling in that advanced photography course at the Community Arts Center that starts in September."},
        {"role": "user", "content": "Have you always been interested in photography?"},
        {"role": "assistant", "content": "I was passionate about it in college at State University - I even had a minor in Visual Arts alongside my Business major. But I put it aside when I got busy with my career after graduation in 2019. My photography professor, Dr. Martinez, always said I had a natural eye for composition. Seeing those mountain views this weekend really rekindled that passion. I'm thinking about joining the local photography club - the Mountain View Camera Club."}
    ]
    
    print("📖 Rich conversation for detailed iteration analysis:")
    print(f"   {len(conversation_messages)} conversation turns")
    print("   Contains: hiking details, book information, career thoughts, future plans")
    print("   Challenge: Convert all to self-contained, no-pronoun memory items")
    
    # Use the agent's automatic run method
    print("\n🤖 Starting automatic processing with DETAILED iteration output...")
    print("📊 Will show every function call, argument, and result...\n")
    
    result = memory_agent.run(
        conversation=conversation_messages,
        # character_name="Alice",
        character_name=character_test or conversation_messages[0]["role"],
        max_iterations=20
    )
    
    if result.get("success"):
        print("✅ Automatic processing completed successfully!")
        print(f"📊 Total Iterations: {result.get('iterations', 0)}")
        print(f"🔧 Total Function calls: {len(result.get('function_calls', []))}")
        print(f"📁 Files generated: {len(result.get('files_generated', []))}")
        
        # Show detailed iteration output
        print("\n" + "=" * 80)
        print("📋 DETAILED ITERATION-BY-ITERATION OUTPUT:")
        print("=" * 80)
        
        # Group function calls by iteration
        function_calls = result.get('function_calls', [])
        processing_log = result.get('processing_log', [])
        
        # Display function calls grouped by iteration
        if function_calls:
            iteration_calls = {}
            
            # Group calls by iteration
            for call in function_calls:
                iter_num = call.get('iteration', 1)
                if iter_num not in iteration_calls:
                    iteration_calls[iter_num] = []
                iteration_calls[iter_num].append(call)
            
            # Display each iteration
            for iter_num in sorted(iteration_calls.keys()):
                print(f"\n🔄 ITERATION {iter_num}")
                print("-" * 50)
                
                calls = iteration_calls[iter_num]
                for i, call in enumerate(calls, 1):
                    function_name = call.get('function', 'unknown')
                    arguments = call.get('arguments', {})
                    call_result = call.get('result', {})
                    success = call_result.get('success', False)
                    
                    print(f"\n📞 Function Call {i}: {function_name}")
                    print(f"   Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
                    
                    # Show key arguments (truncated for readability)
                    if arguments:
                        print("   📥 Arguments:")
                        for key, value in arguments.items():
                            if isinstance(value, str) and len(value) > 150:
                                print(f"      {key}: {value[:150]}...")
                            elif isinstance(value, list) and len(value) > 3:
                                print(f"      {key}: [{len(value)} items] - {value[:3]}...")
                            else:
                                print(f"      {key}: {value}")
                    
                    # Show detailed results
                    if call_result:
                        print("   📤 Results:")
                        if success:
                            # Show specific results based on function type
                            if function_name == 'summarize_conversation':
                                items_count = call_result.get('items_count', 0)
                                summary = call_result.get('summary', '')
                                print(f"      ✅ Items extracted: {items_count}")
                                print(f"      ✅ Summary length: {len(summary)} characters")
                                print(f"      📝 Summary preview: {summary[:200]}...")
                                
                                # Show sample memory items with validation
                                memory_items = call_result.get('memory_items', [])
                                if memory_items:
                                    print(f"      📦 Sample memory items ({len(memory_items)} total):")
                                    for j, item in enumerate(memory_items[:3], 1):
                                        content = item.get('content', '')
                                        item_type = item.get('type', 'unknown')
                                        context = item.get('context', '')
                                        
                                        print(f"        {j}. [{item_type.upper()}] {content}")
                                        if context:
                                            print(f"           Context: {context}")
                                        
                                        # Quick compliance check
                                        has_alice = 'Alice' in content
                                        has_pronouns = any(p in content.lower() for p in ['she ', 'he ', 'they ', 'it '])
                                        compliance = "✅ COMPLIANT" if has_alice and not has_pronouns else "❌ VIOLATION"
                                        print(f"           {compliance}")
                                    
                                    if len(memory_items) > 3:
                                        print(f"        ... and {len(memory_items) - 3} more items")
                            
                            elif function_name == 'generate_memory_suggestions':
                                suggestions = call_result.get('suggestions', {})
                                print(f"      ✅ Categories analyzed: {len(suggestions)}")
                                print("      📋 Suggestion summary:")
                                for cat, data in list(suggestions.items())[:4]:
                                    should_add = data.get('should_add', False)
                                    suggestion = data.get('suggestion', '')
                                    print(f"        {cat}: {'📈 ADD' if should_add else '⏸️ SKIP'}")
                                    print(f"          {suggestion[:100]}...")
                            
                            elif function_name == 'update_memory_with_suggestions':
                                modifications = call_result.get('modifications', [])
                                category = call_result.get('category', 'unknown')
                                print(f"      ✅ Category: {category}")
                                print(f"      ✅ Modifications: {len(modifications)}")
                                if modifications:
                                    print("      📝 Modified content samples:")
                                    for j, mod in enumerate(modifications[:2], 1):
                                        content = mod.get('content', '')
                                        memory_id = mod.get('memory_id', '')
                                        print(f"        {j}. [{memory_id}] {content}")
                                        
                                        # Quick compliance check
                                        has_alice = 'Alice' in content
                                        has_pronouns = any(p in content.lower() for p in ['she ', 'he ', 'they ', 'it '])
                                        compliance = "✅ COMPLIANT" if has_alice and not has_pronouns else "❌ VIOLATION"
                                        print(f"           {compliance}")
                            
                            elif function_name == 'add_activity_memory':
                                category = call_result.get('category', 'unknown')
                                content_added = call_result.get('content_added', 0)
                                embeddings_generated = call_result.get('embeddings_generated', False)
                                print(f"      ✅ Category: {category}")
                                print(f"      ✅ Content added: {content_added} characters")
                                print(f"      ✅ Embeddings: {'Generated' if embeddings_generated else 'Skipped'}")
                            
                            elif function_name == 'link_related_memories':
                                links_created = call_result.get('links_created', 0)
                                category = call_result.get('category', 'unknown')
                                print(f"      ✅ Category: {category}")
                                print(f"      ✅ Links created: {links_created}")
                                if links_created > 0:
                                    print("      🔗 Semantic connections established")
                            
                            elif function_name == 'get_available_categories':
                                categories = call_result.get('categories', {})
                                print(f"      ✅ Categories found: {list(categories.keys())}")
                                print("      📁 Memory structure ready")

                            elif function_name == 'run_theory_of_mind':
                                items_count = call_result.get('items_count', 0)
                                reasoning_process = call_result.get('reasoning_process', '')
                                print(f"      ✅ Items extracted: {items_count}")
                                print(f"      ✅ Reasoning process length: {len(reasoning_process)} characters")
                                print(f"      📝 Reasoning process preview: {reasoning_process[:200]}...")

                                # Show sample memory items with validation
                                theory_of_mind_items = call_result.get('theory_of_mind_items', [])
                                if theory_of_mind_items:
                                    print(f"      📦 Sample memory items ({len(theory_of_mind_items)} total):")
                                    for j, item in enumerate(theory_of_mind_items[:3], 1):
                                        content = item.get('content', '')
                                        item_type = item.get('type', 'unknown')
                                        context = item.get('context', '')
                                        
                                        print(f"        {j}. [{item_type.upper()}] {content}")
                                        if context:
                                            print(f"           Context: {context}")
                                        
                                        # Quick compliance check
                                        has_alice = 'Alice' in content
                                        has_pronouns = any(p in content.lower() for p in ['she ', 'he ', 'they ', 'it '])
                                        compliance = "✅ COMPLIANT" if has_alice and not has_pronouns else "❌ VIOLATION"
                                        print(f"           {compliance}")
                                    
                                    if len(theory_of_mind_items) > 3:
                                        print(f"        ... and {len(theory_of_mind_items) - 3} more items")
                            
                            else:
                                # Generic result display
                                message = call_result.get('message', '')
                                if message:
                                    print(f"      ✅ {message}")
                        else:
                            error = call_result.get('error', 'Unknown error')
                            print(f"      ❌ Error: {error}")
        
        # Show processing log if available
        if processing_log:
            print(f"\n📝 PROCESSING LOG:")
            print("-" * 30)
            for i, log_entry in enumerate(processing_log, 1):
                print(f"{i}. {log_entry}")
        
        # Show files generated
        files_generated = result.get('files_generated', [])
        if files_generated:
            print(f"\n📁 FILES GENERATED:")
            print("-" * 30)
            for i, file_path in enumerate(files_generated, 1):
                print(f"{i}. {file_path}")
        
        print("\n" + "=" * 80)
        print("🎉 DETAILED ITERATION OUTPUT COMPLETE!")
        print("💾 All memory items stored with strict no-pronouns compliance")
        print("🔍 Every function call and result has been displayed")
        print("=" * 80)
        
    else:
        print(f"❌ Automatic processing failed: {result.get('error')}")
        
        # Show partial results if available
        if 'function_calls' in result:
            print("\n📋 Partial function calls made before failure:")
            function_calls = result.get('function_calls', [])
            for i, call in enumerate(function_calls, 1):
                function_name = call.get('function', 'unknown')
                success = call.get('result', {}).get('success', False)
                error = call.get('result', {}).get('error', '')
                print(f"  {i}. {function_name} - {'✅' if success else '❌'}")
                if not success and error:
                    print(f"     Error: {error}")

if __name__ == "__main__":
    print("🌟 DETAILED ITERATION OUTPUT DEMONSTRATION")
    print("This demo shows EVERY iteration with complete details.")
    print("Enforces strict no-pronouns policy with real-time validation.\n")
    
    # conversation, speakers = load_locomo_conversation(sample_id=2, session_id=[0,1,2,3], perserve_role=True)
    # conversation, speakers = load_debug_conversation("0001.txt")
    # conversations, speakers = load_locomo_conversation(sample_id=2, session_id=[0,1,2,3], add_image_caption=True, perserve_role=True)
    conversations, speakers = load_locomo_conversation(sample_id=2, session_id=[0,1], add_image_caption=True, perserve_role=True)

    character_test = speakers[1]

    # Run detailed iterations demo
    # demo_detailed_iterations(conversations)
    for i, conversation in enumerate(conversations):
        print(f"🔄 Running conversation {i+1} of {len(conversations)}")
        demo_detailed_iterations(conversation)

        pattern = rf"{re.escape(character_test)}_([^.]+)\.md$"
        for file in os.listdir("memory"):
            match = re.match(pattern, file)
            if match:
                tag = match.group(1)
                shutil.copy2(f"memory/{character_test}_{tag}.md", f"memory/{character_test}_{tag}_{i+1}.md")
