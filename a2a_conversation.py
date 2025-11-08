"""
LangGraph AI Conversation Agents with Apache Kafka 4.0
Two AI agents engage in natural conversation using LLMs for reasoning.
Messages are passed through Kafka topics.
"""

from typing import TypedDict, Annotated, List, Dict
from langgraph.graph import StateGraph, END
from kafka import KafkaProducer, KafkaConsumer
import json
import time
import threading
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
load_dotenv()

# State definition for conversational agents
class ConversationState(TypedDict):
    conversation_history: List[Dict[str, str]]
    current_message: str
    turn_count: int
    max_turns: int
    agent_name: str


@dataclass
class KafkaConfig:
    bootstrap_servers: list[str]
    alice_topic: str = "alice-messages"
    bob_topic: str = "bob-messages"


class ConversationalAgent:
    """AI agent that uses LLM to reason and respond in conversations"""

    def __init__(
            self,
            name: str,
            persona: str,
            kafka_config: KafkaConfig,
            listen_topic: str,
            send_topic: str,
            max_turns: int = 10,
            api_key: str = None
    ):
        self.name = name
        self.persona = persona
        self.kafka_config = kafka_config
        self.listen_topic = listen_topic
        self.send_topic = send_topic
        self.max_turns = max_turns

        # Initialize LangChain OpenAI LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.8,
            api_key=api_key or os.environ.get("OPENAI_API_KEY")
        )

        # Kafka setup
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_config.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.consumer = KafkaConsumer(
            listen_topic,
            bootstrap_servers=kafka_config.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id=f'{name}-group',
            enable_auto_commit=True
        )

        self.graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph workflow for conversational agent"""
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("listen", self.listen_for_message)
        workflow.add_node("reason", self.reason_with_llm)
        workflow.add_node("respond", self.send_response)

        # Define edges
        workflow.set_entry_point("listen")
        workflow.add_edge("listen", "reason")
        workflow.add_edge("reason", "respond")
        workflow.add_conditional_edges(
            "respond",
            self.should_continue,
            {
                "continue": "listen",
                "end": END
            }
        )

        return workflow.compile()

    def listen_for_message(self, state: ConversationState) -> ConversationState:
        """Listen for incoming messages from Kafka"""
        print(f"\n👂 {self.name} - Listening on {self.listen_topic}...")

        # Poll for messages
        messages = self.consumer.poll(timeout_ms=30000)

        if messages:
            for topic_partition, records in messages.items():
                for record in records:
                    data = record.value
                    state["current_message"] = data["message"]
                    state["turn_count"] = data["turn_count"]
                    state["conversation_history"] = data["conversation_history"]

                    print(f"📨 {self.name} - Received: \"{state['current_message']}\"")
                    break
                break

        return state

    def reason_with_llm(self, state: ConversationState) -> ConversationState:
        """Use LLM to reason about the conversation and generate response"""
        print(f"🤔 {self.name} - Reasoning with LLM...")

        # Build conversation context
        context = self._build_context(state)

        # Call LangChain OpenAI
        try:
            messages = [
                SystemMessage(content=f"""You are {self.name}. {self.persona}

You are having a natural conversation. Respond authentically to what the other person said.
Keep responses conversational (2-4 sentences). Show personality and emotion.
DO NOT use greetings like "hi" or "hello" unless it's the very first message.
Continue the conversation naturally based on what was just said."""),
                HumanMessage(content=context)
            ]

            response = self.llm.invoke(messages)
            response_text = response.content
            state["current_message"] = response_text

            print(f"💭 {self.name} - Generated response: \"{response_text}\"")

        except Exception as e:
            print(f"❌ {self.name} - LLM Error: {e}")
            state["current_message"] = "I'm having trouble thinking right now..."

        return state

    def _build_context(self, state: ConversationState) -> str:
        """Build conversation context for LLM"""
        context_parts = []

        if state["conversation_history"]:
            context_parts.append("Recent conversation:")
            for msg in state["conversation_history"][-6:]:  # Last 3 exchanges
                speaker = msg["speaker"]
                text = msg["message"]
                context_parts.append(f"{speaker}: {text}")

        context_parts.append(f"\nThe other person just said: \"{state['current_message']}\"")
        context_parts.append(f"\nRespond as {self.name}:")

        return "\n".join(context_parts)

    def send_response(self, state: ConversationState) -> ConversationState:
        """Send response to Kafka"""

        # Add to conversation history
        state["conversation_history"].append({
            "speaker": self.name,
            "message": state["current_message"],
            "timestamp": time.time()
        })

        state["turn_count"] += 1

        print(f"📤 {self.name} - Turn {state['turn_count']}: \"{state['current_message']}\"")

        # Send to Kafka
        self.producer.send(
            self.send_topic,
            {
                "message": state["current_message"],
                "conversation_history": state["conversation_history"],
                "turn_count": state["turn_count"],
                "speaker": self.name,
                "timestamp": time.time()
            }
        )
        self.producer.flush()

        return state

    def should_continue(self, state: ConversationState) -> str:
        """Decide whether to continue conversation"""
        if state["turn_count"] >= state["max_turns"]:
            print(f"🏁 {self.name} - Reached max turns ({state['max_turns']})")
            return "end"
        return "continue"

    def start_conversation(self, initial_message: str):
        """Start the conversation with an initial message"""
        print(f"🚀 {self.name} - Starting conversation...")

        initial_state = {
            "conversation_history": [],
            "current_message": initial_message,
            "turn_count": 0,
            "max_turns": self.max_turns,
            "agent_name": self.name
        }

        # Use LLM to generate first message
        initial_state = self.reason_with_llm(initial_state)
        initial_state = self.send_response(initial_state)

        # Continue with normal flow
        initial_state["current_message"] = ""
        result = self.graph.invoke(initial_state)

        print(f"🎯 {self.name} - Conversation ended")
        self.cleanup()

    def run(self):
        """Run agent in listening mode"""
        print(f"🚀 {self.name} - Starting in listening mode...")

        initial_state = {
            "conversation_history": [],
            "current_message": "",
            "turn_count": 0,
            "max_turns": self.max_turns,
            "agent_name": self.name
        }

        result = self.graph.invoke(initial_state)
        print(f"🎯 {self.name} - Conversation ended")
        self.cleanup()

    def cleanup(self):
        """Close Kafka connections"""
        self.producer.close()
        self.consumer.close()


def print_conversation_summary(agent_name: str, history: List[Dict]):
    """Print a formatted summary of the conversation"""
    print(f"\n{'=' * 60}")
    print(f"📜 CONVERSATION SUMMARY")
    print(f"{'=' * 60}")
    for msg in history:
        speaker = msg["speaker"]
        text = msg["message"]
        print(f"\n{speaker}: {text}")
    print(f"\n{'=' * 60}\n")


def main():
    """Main function to run conversational agents"""

    # Kafka configuration
    kafka_config = KafkaConfig(
        bootstrap_servers=['localhost:9092']
    )

    max_turns = 12  # Total turns in conversation

    # Define agent personas
    alice_persona = """You are Alice, a curious and enthusiastic marine biologist who loves discovering new things about ocean life. 
You're optimistic, ask thoughtful questions, and share fascinating facts about the sea."""

    bob_persona = """You are Bob, a philosophical software engineer who enjoys pondering big questions about technology and life.
You're thoughtful, sometimes skeptical, but always respectful and interested in others' perspectives."""

    # Create agents
    alice = ConversationalAgent(
        name="Alice",
        persona=alice_persona,
        kafka_config=kafka_config,
        listen_topic=kafka_config.bob_topic,
        send_topic=kafka_config.alice_topic,
        max_turns=max_turns
    )

    bob = ConversationalAgent(
        name="Bob",
        persona=bob_persona,
        kafka_config=kafka_config,
        listen_topic=kafka_config.alice_topic,
        send_topic=kafka_config.bob_topic,
        max_turns=max_turns
    )

    # Start Bob in listening mode
    bob_thread = threading.Thread(target=bob.run, daemon=True)
    bob_thread.start()

    # Give Bob time to start listening
    time.sleep(3)

    # Alice starts the conversation
    alice_thread = threading.Thread(
        target=alice.start_conversation,
        args=("I just got back from an amazing dive where I saw bioluminescent plankton!",),
        daemon=True
    )
    alice_thread.start()

    # Wait for conversation to complete
    alice_thread.join()
    bob_thread.join()

    print("\n✨ Conversation completed!")


if __name__ == "__main__":
    """
    Prerequisites:
    1. Install dependencies: 
       pip install langgraph kafka-python langchain-openai

    2. Set your OpenAI API key:
       export OPENAI_API_KEY='your-api-key-here'

    3. Start Kafka:
       docker run -d -p 9092:9092 apache/kafka:latest

    4. Run the script:
       python conversation_agents.py
    """

    main()