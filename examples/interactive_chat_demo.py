#!/usr/bin/env python3
"""
PersonaLab Interactive Chat Demo
"""

import os
import sys

sys.path.append(".")

from dotenv import load_dotenv

from personalab import Persona
from personalab.llm import OpenAIClient

load_dotenv()


class InteractiveChatDemo:
    def __init__(self):
        self.persona = None
        self.user_id = None
        self.session_count = 0

    def setup(self):
        print("PersonaLab Interactive Chat Demo")
        print("=" * 40)
        # Check API config
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: Please set the OPENAI_API_KEY environment variable")
            return False
        # Get user info
        self.user_id = input("Your name: ").strip() or "User"
        personality = input("AI personality (press Enter for default): ").strip()
        if not personality:
            personality = f"You are a friendly and smart AI assistant, chatting with {self.user_id}."
        # Create Persona
        try:
            self.persona = Persona(
                agent_id="interactive_assistant",
                personality=personality,
                use_memory=True,
                use_memo=True,
                show_retrieval=False,
            )
            print(f"AI assistant created, ready to chat with {self.user_id}")
            return True
        except Exception as e:
            print(f"Failed to create AI assistant: {e}")
            return False

    def display_retrieved_conversations(self, user_input: str):
        """Display retrieved related historical conversations"""
        try:
            memo = self.persona._get_or_create_memo(self.user_id)
            if not memo:
                return

            similar_conversations = memo.search_similar_conversations(
                agent_id=self.persona.agent_id,
                query=user_input,
                limit=2,
                similarity_threshold=0.6,
            )

            if not similar_conversations:
                print("No related historical conversations found")
                return

            print(
                f"Found {len(similar_conversations)} related historical conversations:"
            )
            print("-" * 40)

            for i, conv_summary in enumerate(similar_conversations, 1):
                conversation = memo.db.get_conversation(conv_summary["conversation_id"])

                if conversation:
                    print(
                        f"Conversation {i} (Similarity: {conv_summary['similarity_score']:.3f})"
                    )
                    print(f"Time: {conversation.created_at.strftime('%m-%d %H:%M')}")

                    # Display conversation content
                    for msg in conversation.messages[:4]:  # Maximum 4 messages
                        role = "User" if msg.role == "user" else "AI"
                        content = (
                            msg.content[:100] + "..."
                            if len(msg.content) > 100
                            else msg.content
                        )
                        print(f"  {role}: {content}")

                    if len(conversation.messages) > 4:
                        print(
                            f"  ... and {len(conversation.messages) - 4} more messages"
                        )
                    print()

        except Exception as e:
            print(f"Failed to retrieve historical conversations: {e}")

    def display_memory(self):
        """Display memory status"""
        try:
            memory = self.persona.get_memory(self.user_id)

            print("\n=== Memory Status ===")
            print(f"Profile: {memory['profile'] or 'No profile'}")
            print(f"Events: {len(memory['events'])} events")
            if memory["events"]:
                for event in memory["events"][-3:]:  # Display recent 3 events
                    print(f"  - {event}")

            print(f"Mind: {len(memory['mind'])} insights")
            if memory["mind"]:
                for insight in memory["mind"][-2:]:  # Display recent 2 insights
                    print(f"  - {insight}")

        except Exception as e:
            print(f"Failed to retrieve memory: {e}")

    def chat_session(self):
        self.session_count += 1
        print(f"\n=== Session {self.session_count} ===")
        print(
            "Type 'exit' to end session, 'memory' to view memory, 'help' to view help\n"
        )

        message_count = 0

        while True:
            try:
                user_input = input(f"{self.user_id}: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    break
                elif user_input.lower() in ["memory", "mem"]:
                    self.display_memory()
                    continue
                elif user_input.lower() in ["help", "h"]:
                    print(
                        "Commands: Type directly | 'memory' to view memory | 'exit' to exit"
                    )
                    continue

                # Display related historical conversations
                self.display_retrieved_conversations(user_input)

                # AI conversation
                response = self.persona.chat(user_input, user_id=self.user_id)
                print(f"AI: {response}\n")

                message_count += 1

            except KeyboardInterrupt:
                print("\nExiting session...")
                break
            except Exception as e:
                print(f"Conversation error: {e}")

        # Update memory
        if message_count > 0:
            try:
                result = self.persona.endsession(self.user_id)
                print(f"Memory updated: {result}")
            except Exception as e:
                print(f"Failed to update memory: {e}")

        return message_count > 0

    def run(self):
        if not self.setup():
            return

        try:
            while True:
                had_conversation = self.chat_session()

                if had_conversation:
                    self.display_memory()

                choice = input("\nStart new session? (y/n): ").strip().lower()
                if choice in ["n", "no", "q"]:
                    break

        except KeyboardInterrupt:
            print("\nProgram exiting")

        finally:
            if self.persona:
                try:
                    self.persona.close()
                except:
                    pass

        print(f"Total {self.session_count} sessions, thank you for using!")


def main():
    demo = InteractiveChatDemo()
    demo.run()


if __name__ == "__main__":
    main()
