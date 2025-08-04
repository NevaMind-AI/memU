#!/usr/bin/env python3
"""
Quick Memory Agent Test with Locomo Data

Fast test script that processes the first few sessions to quickly validate
the memory agent workflow and show real-time action results.
"""

import sys
import os
import json
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime
import uuid

import traceback

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not found. Install with: pip install python-dotenv")
    # Manual .env loading
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
        print("✅ Manually loaded environment variables from .env file")

# Add the parent directory to the path so we can import memu
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from memu.memory.memory_agent import MemoryAgent
from memu.llm.openai_client import OpenAIClient
from memu.llm.azure_openai_client import AzureOpenAIClient
from memu.llm.base import BaseLLMClient, LLMResponse


class LLMLoggingWrapper:
    """LLM Client wrapper that logs all input/output to files"""

    def __init__(self, llm_client: BaseLLMClient, log_dir: str, character_name: str):
        self.llm_client = llm_client
        self.log_dir = Path(log_dir)
        self.character_name = character_name
        self.call_counter = 0

        # Create character-specific log directory
        self.character_log_dir = self.log_dir / f"{character_name}_llm_logs"
        self.character_log_dir.mkdir(parents=True, exist_ok=True)

        # Create main log file for this character
        self.main_log_file = (
            self.character_log_dir / f"{character_name}_llm_interactions.log"
        )

        # Initialize log
        with open(self.main_log_file, "w", encoding="utf-8") as f:
            f.write(f"=== LLM INTERACTION LOG FOR {character_name} ===\n")
            f.write(f"Started at: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

    def chat_completion(
        self, messages, model=None, temperature=0.7, max_tokens=12000, **kwargs
    ):
        """Wrapper around chat_completion with logging"""
        self.call_counter += 1
        call_id = (
            f"{self.character_name}_{self.call_counter:03d}_{uuid.uuid4().hex[:8]}"
        )

        # Log the input
        self._log_interaction(
            call_id,
            "INPUT",
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "kwargs": kwargs,
            },
        )

        # Make the actual LLM call
        start_time = time.time()
        try:
            response = self.llm_client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            duration = time.time() - start_time

            # Log the output
            self._log_interaction(
                call_id,
                "OUTPUT",
                {
                    "success": response.success,
                    "content": response.content,
                    "usage": response.usage,
                    "model": response.model,
                    "error": response.error,
                    "tool_calls": response.tool_calls,
                    "duration_seconds": round(duration, 3),
                },
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log the error
            self._log_interaction(
                call_id,
                "ERROR",
                {"error": str(e), "duration_seconds": round(duration, 3)},
            )

            # Re-raise the exception
            raise

    def _serialize_any_object(self, obj):
        """Recursively serialize any object to JSON-compatible format"""
        try:
            # Try direct JSON serialization first
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            pass

        # Handle None
        if obj is None:
            return None

        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle lists
        if isinstance(obj, (list, tuple)):
            return [self._serialize_any_object(item) for item in obj]

        # Handle dictionaries
        if isinstance(obj, dict):
            return {str(k): self._serialize_any_object(v) for k, v in obj.items()}

        # Handle Pydantic models
        if hasattr(obj, "model_dump"):
            try:
                return obj.model_dump()
            except Exception:
                pass

        if hasattr(obj, "dict"):
            try:
                return obj.dict()
            except Exception:
                pass

        # Handle objects with __dict__
        if hasattr(obj, "__dict__"):
            try:
                return {
                    str(k): self._serialize_any_object(v)
                    for k, v in obj.__dict__.items()
                }
            except Exception:
                pass

        # Handle tool calls specifically
        if hasattr(obj, "id") and hasattr(obj, "type"):
            result = {
                "id": getattr(obj, "id", None),
                "type": getattr(obj, "type", None),
            }

            if hasattr(obj, "function"):
                func = obj.function
                result["function"] = {
                    "name": getattr(func, "name", None),
                    "arguments": getattr(func, "arguments", None),
                }

            return result

        # Final fallback: convert to string
        return {"serialized_as_string": True, "type": str(type(obj)), "value": str(obj)}

    def _serialize_tool_calls(self, tool_calls):
        """Convert tool calls to JSON-serializable format"""
        if not tool_calls:
            return None

        return self._serialize_any_object(tool_calls)

    def _log_interaction(self, call_id: str, interaction_type: str, data: dict):
        """Log a single interaction to both main log and individual file"""
        timestamp = datetime.now().isoformat()

        # Create individual interaction log file
        interaction_file = (
            self.character_log_dir / f"{call_id}_{interaction_type.lower()}.json"
        )

        # Serialize all data to ensure JSON compatibility
        log_data = self._serialize_any_object(data)

        # Prepare log entry
        log_entry = {
            "call_id": call_id,
            "character": self.character_name,
            "timestamp": timestamp,
            "type": interaction_type,
            "data": log_data,
        }

        # Write to individual JSON file
        try:
            with open(interaction_file, "w", encoding="utf-8") as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # This should rarely happen now with comprehensive serialization
            print(f"⚠️ Warning: Failed to serialize log data for {call_id}: {e}")

            # Create minimal safe log entry
            safe_entry = {
                "call_id": call_id,
                "character": self.character_name,
                "timestamp": timestamp,
                "type": interaction_type,
                "serialization_error": str(e),
                "original_data_type": str(type(data)),
                "data": {
                    "summary": "Serialization failed - see main log for details",
                    "success": (
                        str(data.get("success"))
                        if isinstance(data, dict)
                        else "unknown"
                    ),
                },
            }

            try:
                with open(interaction_file, "w", encoding="utf-8") as f:
                    json.dump(safe_entry, f, indent=2, ensure_ascii=False)
            except Exception as e2:
                # If even this fails, write a simple text file
                with open(
                    interaction_file.with_suffix(".txt"), "w", encoding="utf-8"
                ) as f:
                    f.write(f"Failed to serialize log data: {e}\n")
                    f.write(f"Secondary error: {e2}\n")
                    f.write(f"Call ID: {call_id}\n")
                    f.write(f"Type: {interaction_type}\n")
                    f.write(f"Data type: {type(data)}\n")

        # Append to main log file
        with open(self.main_log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] {interaction_type} - Call ID: {call_id}\n")
            f.write("-" * 60 + "\n")

            if interaction_type == "INPUT":
                f.write(f"Model: {data.get('model', 'default')}\n")
                f.write(f"Temperature: {data.get('temperature', 0.7)}\n")
                f.write(f"Max Tokens: {data.get('max_tokens', 1000)}\n")
                f.write("Messages:\n")
                for i, msg in enumerate(data.get("messages", []), 1):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    f.write(f"  {i}. [{role.upper()}]: {content}\n")

            elif interaction_type == "OUTPUT":
                f.write(f"Success: {data.get('success', False)}\n")
                f.write(f"Model: {data.get('model', 'unknown')}\n")
                f.write(f"Duration: {data.get('duration_seconds', 0)}s\n")

                if data.get("usage"):
                    usage = data["usage"]
                    f.write(f"Usage: {usage}\n")

                if data.get("tool_calls"):
                    f.write(f"Tool calls: {len(data['tool_calls'])} functions called\n")

                content = data.get("content", "")
                if content:
                    f.write(f"Response:\n{content}\n")

                if data.get("error"):
                    f.write(f"Error: {data['error']}\n")

            elif interaction_type == "ERROR":
                f.write(f"Error: {data.get('error', 'Unknown error')}\n")
                f.write(f"Duration: {data.get('duration_seconds', 0)}s\n")

            f.write("=" * 80 + "\n")

    def simple_chat(self, prompt: str, **kwargs) -> str:
        """Wrapper around simple_chat with logging"""
        messages = [{"role": "user", "content": prompt}]
        response = self.chat_completion(messages, **kwargs)
        return response.content if response.success else f"Error: {response.error}"

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped client"""
        return getattr(self.llm_client, name)


def create_llm_client(log_dir: str = None, character_name: str = "default"):
    """Create LLM client based on environment configuration with optional logging"""
    provider = os.environ.get("LLM_PROVIDER", "azure").lower()

    if provider == "azure":
        # Check Azure configuration
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

        if not api_key or api_key == "your_azure_openai_api_key_here":
            raise ValueError("Azure OpenAI API key not configured")
        if not endpoint or endpoint == "https://your-resource-name.openai.azure.com/":
            raise ValueError("Azure OpenAI endpoint not configured")

        print(f"✅ Using Azure OpenAI: {endpoint}")
        client = AzureOpenAIClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            deployment_name=deployment,
            api_version=api_version,
        )

    elif provider == "openai":
        # Check OpenAI configuration
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("OpenAI API key not configured")
        print(f"✅ Using OpenAI: {api_key[:12]}...")
        client = OpenAIClient()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'openai' or 'azure'")

    # Wrap with logging if log_dir is provided
    if log_dir:
        print(f"🔍 Enabling LLM logging for character: {character_name}")
        return LLMLoggingWrapper(client, log_dir, character_name)
    else:
        return client


class LocomoDataLoader:
    """Locomo data loader for quick testing"""

    def __init__(self, data_path="./data/locomo10.json"):
        self.data_path = data_path
        self.data = None
        self.load_data()

    def load_data(self):
        """Load locomo data from JSON file"""
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"✅ Loaded {len(self.data)} samples from locomo data")
        except Exception as e:
            print(f"❌ Failed to load locomo data: {e}")
            self.data = []

    def get_sample(self, index=0):
        """Get a specific sample from the data"""
        if not self.data or index >= len(self.data):
            return None
        return self.data[index]

    def get_characters(self, sample):
        """Extract character names from a sample"""
        if not sample or "conversation" not in sample:
            return []

        characters = set()
        conversation = sample["conversation"]

        # First try to get speakers from speaker_a and speaker_b fields
        if "speaker_a" in conversation:
            characters.add(conversation["speaker_a"])
        if "speaker_b" in conversation:
            characters.add(conversation["speaker_b"])

        # Also extract from all session dialogues
        for session_key in conversation:
            if session_key.startswith("session_") and not session_key.endswith(
                "_date_time"
            ):
                session_data = conversation[session_key]
                if isinstance(session_data, list):
                    for dialog in session_data:
                        if isinstance(dialog, dict) and "speaker" in dialog:
                            speaker = dialog["speaker"]
                            if speaker and speaker.strip():
                                characters.add(speaker.strip())

        # Remove any empty strings
        characters.discard("")
        return list(characters)

    def get_all_sessions(self, sample):
        """Get all available session numbers"""
        if not sample or "conversation" not in sample:
            return []

        sessions = []
        for key in sample["conversation"]:
            if key.startswith("session_") and not key.endswith("_date_time"):
                session_num = int(key.split("_")[1])
                sessions.append(session_num)

        return sorted(sessions)

    def get_session_conversations(self, sample, session_num=1):
        """Get conversations from a specific session"""
        session_key = f"session_{session_num}"
        if (
            not sample
            or "conversation" not in sample
            or session_key not in sample["conversation"]
        ):
            print(f"⚠️ Warning: No data found for {session_key}")
            return []

        conversations = sample["conversation"][session_key]

        # Debug: Check the structure of conversations
        if conversations and len(conversations) > 0:
            first_conv = conversations[0]
            print(
                f"📊 Session {session_num} structure - first conversation keys: {list(first_conv.keys()) if isinstance(first_conv, dict) else 'Not a dict'}"
            )

            # Validate expected fields
            if isinstance(first_conv, dict):
                has_speaker = "speaker" in first_conv
                has_text = "text" in first_conv
                print(f"   Has 'speaker' field: {has_speaker}")
                print(f"   Has 'text' field: {has_text}")

                if not has_speaker or not has_text:
                    print(f"   Available fields: {list(first_conv.keys())}")

        return conversations

    def get_session_date(self, sample, session_num=1):
        """Get session date"""
        session_date_key = f"session_{session_num}_date_time"
        if not sample or "conversation" not in sample:
            return "2025-01-15"

        return sample["conversation"].get(session_date_key, "2025-01-15")

    def format_session_as_conversation(self, conversations):
        """Format entire session as a single conversation text"""
        if not conversations:
            return ""

        session_text = ""
        for dialog in conversations:
            session_text += f"{dialog['speaker']}: {dialog['text']}\n"

        return session_text.strip()


def display_function_results(function_calls):
    """Display function call results in a formatted way"""
    print(f"\n🔧 FUNCTION CALLS EXECUTED ({len(function_calls)} total):")
    print("=" * 60)

    for i, func_call in enumerate(function_calls, 1):
        func_name = func_call.get("function_name", "unknown")
        func_result = func_call.get("result", {})
        success = func_result.get("success", False)
        status = "✅" if success else "❌"

        print(f"\n{i:2d}. {status} {func_name.upper()}")

        if success:
            # Show specific results based on function type
            if func_name == "add_activity_memory":
                items_added = func_result.get("memory_items_added", 0)
                character = func_result.get("character_name", "N/A")
                print(f"     Character: {character}")
                print(f"     Memory items added: {items_added}")

            elif func_name == "run_theory_of_mind":
                character = func_result.get("character_name", "N/A")
                items_added = func_result.get("theory_of_mind_items_added", 0)
                print(f"     Character: {character}")
                print(f"     ToM items added: {items_added}")

            elif func_name == "generate_memory_suggestions":
                suggestions = func_result.get("suggestions", {})
                print(f"     Suggestions for {len(suggestions)} categories:")
                for cat, suggestion in list(suggestions.items())[:3]:
                    print(f"       • {cat}: {repr(suggestion)[:80]}...")

            elif func_name == "update_memory_with_suggestions":
                modifications = func_result.get("new_memory_items", [])
                category = func_result.get("category", "unknown")
                print(f"     Category: {category}")
                print(f"     Modifications: {len(modifications)}")
                for mod in modifications[:2]:
                    memory_id = mod.get("memory_id", "N/A")
                    content = mod.get("content", "")[:80]
                    print(f"       [{memory_id}] {content}...")
                if len(modifications) > 2:
                    print(f"       ... and {len(modifications) - 2} more")

            elif func_name == "link_related_memories":
                links_added = func_result.get("total_items_linked", 0)
                category = func_result.get("category", "unknown")
                print(f"     Category: {category}")
                print(f"     Links added: {links_added}")

            elif func_name == "cluster_memories":
                updated_clusters = func_result.get("updated_clusters", [])
                new_clusters = func_result.get("new_clusters", [])
                print(f"     Updated clusters: {updated_clusters}")
                print(f"     New clusters: {new_clusters}")

        else:
            error = func_result.get("error", "Unknown error")
            print(f"     Error: {error}")


def quick_memory_test():
    """Run quick memory processing test with first few sessions"""

    print("🚀 QUICK MEMORY AGENT TEST WITH LOCOMO DATA")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().strftime('%H:%M:%S')}")

    # Check LLM provider configuration
    provider = os.environ.get("LLM_PROVIDER", "azure").lower()
    print(f"🔧 LLM Provider: {provider.upper()}")

    # Setup directories
    memory_dir = "./memory"
    llm_logs_dir = "./llm_logs"
    print(f"📁 Using memory directory: {memory_dir}")
    print(f"📝 Using LLM logs directory: {llm_logs_dir}")

    # Create directories
    Path(memory_dir).mkdir(exist_ok=True)
    Path(llm_logs_dir).mkdir(exist_ok=True)

    # Load data
    data_loader = LocomoDataLoader()
    sample = data_loader.get_sample(0)

    if not sample:
        print("❌ No locomo data available")
        return

    # Debug: Show structure of loaded data
    print(f"\n🔍 DEBUG: Locomo data structure analysis")
    print(f"   Sample keys: {list(sample.keys())}")
    if "conversation" in sample:
        conv_keys = list(sample["conversation"].keys())
        print(f"   Conversation keys: {conv_keys[:10]}")  # Show first 10 keys

        # Check the first session
        for key in conv_keys:
            if key.startswith("session_") and not key.endswith("_date_time"):
                first_session_data = sample["conversation"][key]
                if first_session_data:
                    print(
                        f"   First session ({key}) has {len(first_session_data)} items"
                    )
                    if len(first_session_data) > 0:
                        first_item = first_session_data[0]
                        print(f"   First item type: {type(first_item)}")
                        if isinstance(first_item, dict):
                            print(f"   First item keys: {list(first_item.keys())}")
                            for k, v in list(first_item.items())[:3]:
                                print(f"      {k}: {repr(v)[:100]}")
                break

    # Get characters and sessions
    characters = data_loader.get_characters(sample)
    sessions = data_loader.get_all_sessions(sample)

    print(f"📊 Available characters: {characters}")
    print(f"📊 Testing first 3 sessions from {len(sessions)} available")

    try:
        # Test with first character and first 3 sessions
        test_character = characters[0]
        test_sessions = sessions[:3]

        print(f"\n🎯 PROCESSING CHARACTER: {test_character}")
        print(f"🎯 TESTING SESSIONS: {test_sessions}")

        # Create LLM client with logging for this character
        try:
            llm_client = create_llm_client(
                log_dir=llm_logs_dir, character_name=test_character
            )
            print("✅ LLM client with logging initialized successfully")
        except ValueError as e:
            print(f"❌ LLM configuration error: {e}")
            print("📝 Please configure your .env file properly")
            return

        # Create memory agent
        memory_agent = MemoryAgent(
            llm_client=llm_client, memory_dir=memory_dir, enable_embeddings=True
        )
        print("✅ Memory agent initialized successfully")

        for session_idx, session_num in enumerate(test_sessions, 1):
            print(f"\n{'='*80}")
            print(f"📅 SESSION {session_num} ({session_idx}/{len(test_sessions)})")
            print(f"{'='*80}")

            # Get session data
            conversations = data_loader.get_session_conversations(sample, session_num)
            if not conversations:
                print(f"⚠️ No conversations in session {session_num}")
                continue

            print(f"📊 Raw conversations loaded: {len(conversations)} items")

            # Check character participation
            character_dialogues = []
            for d in conversations:
                if isinstance(d, dict) and "speaker" in d:
                    if d["speaker"] == test_character:
                        character_dialogues.append(d)

            if not character_dialogues:
                print(f"⚠️ {test_character} not in session {session_num}")
                # Show available speakers in this session for debugging
                available_speakers = set()
                for d in conversations:
                    if isinstance(d, dict) and "speaker" in d:
                        available_speakers.add(d["speaker"])
                print(
                    f"   Available speakers in session {session_num}: {list(available_speakers)}"
                )
                continue

            session_date = data_loader.get_session_date(sample, session_num)
            session_text = data_loader.format_session_as_conversation(conversations)

            print(f"📅 Date: {session_date}")
            print(f"📊 Total dialogues: {len(conversations)}")
            print(f"👤 {test_character} dialogues: {len(character_dialogues)}")

            # Show session preview
            print(f"\n📝 SESSION PREVIEW:")
            for i, dialog in enumerate(conversations[:3], 1):
                speaker_emoji = "👤" if dialog["speaker"] == test_character else "👥"
                print(
                    f"  {i}. {speaker_emoji} {dialog['speaker']}: {dialog['text'][:70]}..."
                )
            if len(conversations) > 3:
                print(f"      ... and {len(conversations) - 3} more dialogues")

            try:
                # Process with memory agent
                print(f"\n🚀 Starting Memory Agent workflow...")
                start_time = time.time()

                # Debug: Check raw conversation data quality
                print(f"\n🔍 DEBUG: Checking conversation data quality...")
                empty_speakers = 0
                empty_texts = 0
                valid_dialogues = 0

                for i, dialog in enumerate(conversations[:5]):  # Check first 5
                    speaker = dialog.get("speaker", "")
                    text = dialog.get("text", "")
                    print(
                        f"   Dialog {i+1}: speaker='{speaker}', text='{text[:50]}{'...' if len(text) > 50 else ''}'"
                    )

                    if not speaker or speaker.strip() == "":
                        empty_speakers += 1
                    if not text or text.strip() == "":
                        empty_texts += 1
                    if speaker and text and speaker.strip() and text.strip():
                        valid_dialogues += 1

                print(f"   Total dialogues: {len(conversations)}")
                print(f"   Empty speakers: {empty_speakers}")
                print(f"   Empty texts: {empty_texts}")
                print(f"   Valid dialogues: {valid_dialogues}")

                # Convert conversations to the format expected by memory agent
                conversation_list = []
                for dialog in conversations:
                    # Ensure dialog is a dictionary
                    if not isinstance(dialog, dict):
                        print(f"   Skipping non-dict dialog: {type(dialog)} = {dialog}")
                        continue

                    speaker = (
                        dialog.get("speaker", "").strip()
                        if dialog.get("speaker")
                        else ""
                    )
                    text = dialog.get("text", "").strip() if dialog.get("text") else ""

                    # Skip completely empty dialogues
                    if not speaker and not text:
                        continue

                    # Use fallback values for missing data
                    if not speaker:
                        speaker = "Unknown"
                    if not text:
                        text = "[No message content]"

                    conversation_list.append({"role": speaker, "content": text})

                print(
                    f"   Processed dialogues for memory agent: {len(conversation_list)}"
                )

                # Only proceed if we have valid conversations
                if not conversation_list:
                    print(f"⚠️ No valid conversations found in session {session_num}")
                    continue

                result = memory_agent.run(
                    conversation=conversation_list,
                    character_name=test_character,
                    max_iterations=12,
                )

                processing_time = time.time() - start_time

                # Display results
                print(f"\n⏱️  Processing completed in {processing_time:.2f} seconds")
                print(f"✅ Success: {result.get('success', False)}")
                print(f"🔄 Iterations: {result.get('iterations', 0)}")

                if result.get("success"):
                    function_calls = result.get("function_calls", [])
                    display_function_results(function_calls)

                    # Show memory files status
                    print(f"\n📁 MEMORY FILES STATUS:")
                    for category in ["activity", "profile", "event"]:
                        memory_file = os.path.join(
                            memory_dir, f"{test_character}_{category}.md"
                        )
                        if os.path.exists(memory_file):
                            size = os.path.getsize(memory_file)
                            with open(memory_file, "r", encoding="utf-8") as f:
                                content = f.read()
                            items = len(
                                [
                                    line
                                    for line in content.split("\n")
                                    if line.strip().startswith("[")
                                ]
                            )
                            print(f"   📄 {category}: {size} bytes, {items} items")
                        else:
                            print(f"   ⚪ {category}: not created")
                else:
                    print(
                        f"❌ Processing failed: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                print(f"❌ Exception during session {session_num}: {e}")
                traceback.print_exc()

            # Brief pause between sessions
            if session_idx < len(test_sessions):
                print("\n⏳ Waiting 1 second before next session...")
                time.sleep(1)

        # Show final memory state
        print(f"\n{'='*80}")
        print(f"📊 FINAL MEMORY STATE FOR {test_character}")
        print(f"{'='*80}")

        total_memory_size = 0
        total_items = 0

        for category in ["activity", "profile", "event"]:
            memory_file = os.path.join(memory_dir, f"{test_character}_{category}.md")
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    content = f.read()

                size = len(content)
                items = len(
                    [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith("[")
                    ]
                )
                total_memory_size += size
                total_items += items

                print(f"\n📄 {category.upper()} MEMORY:")
                print(f"   Size: {size} characters")
                print(f"   Items: {items}")

                # Show sample items
                memory_lines = [
                    line for line in content.split("\n") if line.strip().startswith("[")
                ]
                if memory_lines:
                    print(f"   Sample items:")
                    for i, line in enumerate(memory_lines[:3], 1):
                        item_id = line.split("]")[0] + "]" if "]" in line else "N/A"
                        item_content = (
                            line[line.find("]") + 1 :].strip()[:60]
                            if "]" in line
                            else line[:60]
                        )
                        print(f"     {i}. {item_id} {item_content}...")

                    if len(memory_lines) > 3:
                        print(f"     ... and {len(memory_lines) - 3} more items")
            else:
                print(f"\n📄 {category.upper()} MEMORY: Not created")

        print(f"\n📊 TOTAL MEMORY GENERATED:")
        print(f"   Total size: {total_memory_size} characters")
        print(f"   Total items: {total_items}")
        print(f"   Sessions processed: {len(test_sessions)}")

        # Show LLM logging summary
        print(f"\n📝 LLM LOGGING SUMMARY:")
        character_log_dir = Path(llm_logs_dir) / f"{test_character}_llm_logs"
        if character_log_dir.exists():
            log_files = list(character_log_dir.glob("*.json"))
            main_log = character_log_dir / f"{test_character}_llm_interactions.log"

            print(f"   Log directory: {character_log_dir}")
            print(f"   Individual interaction files: {len(log_files)}")
            print(f"   Main log file: {main_log.name}")

            if main_log.exists():
                log_size = main_log.stat().st_size
                print(f"   Main log size: {log_size} bytes")

            # Count INPUT/OUTPUT/ERROR files
            input_files = len([f for f in log_files if f.name.endswith("_input.json")])
            output_files = len(
                [f for f in log_files if f.name.endswith("_output.json")]
            )
            error_files = len([f for f in log_files if f.name.endswith("_error.json")])

            print(f"   LLM calls made: {input_files}")
            print(f"   Successful responses: {output_files}")
            print(f"   Errors: {error_files}")

            # Show some example log files
            if log_files:
                print(f"   Example log files:")
                for i, log_file in enumerate(sorted(log_files)[:5], 1):
                    print(f"     {i}. {log_file.name}")
                if len(log_files) > 5:
                    print(f"     ... and {len(log_files) - 5} more files")
        else:
            print(f"   ⚠️ No LLM logs found for {test_character}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()

    finally:
        # Keep both memory files and LLM logs
        print(f"\n💾 Memory files preserved in: {memory_dir}")
        print(f"📝 LLM logs preserved in: {llm_logs_dir}")

    print(f"\n✅ Quick test completed!")
    print(f"🕒 Finished at: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    quick_memory_test()
