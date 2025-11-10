"""
Conversational AI agent using LangGraph and Kafka for message passing.
"""
import json
import time
from typing import Optional
from contextlib import contextmanager

from kafka import KafkaProducer, KafkaConsumer
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from ..config.settings import KafkaConfig, LLMConfig
from ..utils.logging_config import get_logger
from .conversation_state import ConversationState

logger = get_logger(__name__)


class ConversationalAgent:
    """AI agent that uses LLM to reason and respond in conversations via Kafka."""

    def __init__(
        self,
        name: str,
        persona: str,
        kafka_config: KafkaConfig,
        llm_config: LLMConfig,
        listen_topic: str,
        send_topic: str,
        max_turns: int = 10,
    ):
        """
        Initialize conversational agent.

        Args:
            name: Agent name
            persona: Agent personality description
            kafka_config: Kafka configuration
            llm_config: LLM configuration
            listen_topic: Kafka topic to listen on
            send_topic: Kafka topic to send messages to
            max_turns: Maximum conversation turns
        """
        self.name = name
        self.persona = persona
        self.kafka_config = kafka_config
        self.llm_config = llm_config
        self.listen_topic = listen_topic
        self.send_topic = send_topic
        self.max_turns = max_turns

        logger.info(
            f"Initializing agent '{name}' | Listen: {listen_topic} | Send: {send_topic}"
        )

        # Initialize LangChain OpenAI LLM
        self.llm = ChatOpenAI(
            model=llm_config.model,
            temperature=llm_config.temperature,
            api_key=llm_config.api_key,
            max_tokens=llm_config.max_tokens,
        )

        # Kafka setup
        self._setup_kafka()

        # Build LangGraph workflow
        self.graph = self._build_graph()

        logger.info(f"Agent '{name}' initialized successfully")

    def _setup_kafka(self) -> None:
        """Initialize Kafka producer and consumer."""
        logger.debug(f"Setting up Kafka for agent '{self.name}'")

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_config.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            self.consumer = KafkaConsumer(
                self.listen_topic,
                bootstrap_servers=self.kafka_config.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                group_id=f"{self.name}-group",
                enable_auto_commit=self.kafka_config.enable_auto_commit,
            )

            logger.debug(f"Kafka setup complete for agent '{self.name}'")

        except Exception as e:
            logger.error(f"Failed to setup Kafka for agent '{self.name}': {e}")
            raise

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for conversational agent."""
        logger.debug(f"Building LangGraph workflow for agent '{self.name}'")

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
            {"continue": "listen", "end": END},
        )

        return workflow.compile()

    @traceable(name="listen_for_message", tags=["kafka", "input"])
    def listen_for_message(self, state: ConversationState) -> ConversationState:
        """
        Listen for incoming messages from Kafka.

        Args:
            state: Current conversation state

        Returns:
            Updated conversation state
        """
        logger.info(f"Agent '{self.name}' listening on topic '{self.listen_topic}'")

        # Poll for messages
        messages = self.consumer.poll(timeout_ms=self.kafka_config.consumer_timeout_ms)

        if messages:
            for topic_partition, records in messages.items():
                for record in records:
                    data = record.value
                    state["current_message"] = data["message"]
                    state["turn_count"] = data["turn_count"]
                    state["conversation_history"] = data["conversation_history"]

                    logger.info(
                        f"Agent '{self.name}' received message: \"{state['current_message'][:100]}...\""
                    )
                    break
                break
        else:
            logger.warning(f"Agent '{self.name}' received no messages (timeout)")

        return state

    @traceable(
        name="reason_with_llm",
        tags=["llm", "reasoning"],
        metadata={"agent_type": "conversational"}
    )
    def reason_with_llm(self, state: ConversationState) -> ConversationState:
        """
        Use LLM to reason about the conversation and generate response.

        Args:
            state: Current conversation state

        Returns:
            Updated conversation state with generated response
        """
        logger.info(f"Agent '{self.name}' reasoning with LLM")

        # Add metadata to trace
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.metadata = {
                    "agent_name": self.name,
                    "turn_count": state.get("turn_count", 0),
                    "conversation_length": len(state.get("conversation_history", [])),
                }
        except Exception:
            pass  # Tracing not enabled or available

        # Build conversation context
        context = self._build_context(state)

        try:
            messages = [
                SystemMessage(
                    content=f"""You are {self.name}. {self.persona}

You are having a natural conversation. Respond authentically to what the other person said.
Keep responses conversational (2-4 sentences). Show personality and emotion.
DO NOT use greetings like "hi" or "hello" unless it's the very first message.
Continue the conversation naturally based on what was just said."""
                ),
                HumanMessage(content=context),
            ]

            response = self.llm.invoke(messages)
            response_text = response.content
            state["current_message"] = response_text

            logger.info(
                f"Agent '{self.name}' generated response: \"{response_text[:100]}...\""
            )
            logger.debug(f"Full response: {response_text}")

        except Exception as e:
            logger.error(f"LLM error for agent '{self.name}': {e}", exc_info=True)
            state["current_message"] = "I'm having trouble thinking right now..."

        return state

    def _build_context(self, state: ConversationState) -> str:
        """
        Build conversation context for LLM.

        Args:
            state: Current conversation state

        Returns:
            Formatted context string
        """
        context_parts = []

        if state["conversation_history"]:
            context_parts.append("Recent conversation:")
            for msg in state["conversation_history"][-6:]:  # Last 3 exchanges
                speaker = msg["speaker"]
                text = msg["message"]
                context_parts.append(f"{speaker}: {text}")

        context_parts.append(
            f"\nThe other person just said: \"{state['current_message']}\""
        )
        context_parts.append(f"\nRespond as {self.name}:")

        return "\n".join(context_parts)

    @traceable(name="send_response", tags=["kafka", "output"])
    def send_response(self, state: ConversationState) -> ConversationState:
        """
        Send response to Kafka.

        Args:
            state: Current conversation state

        Returns:
            Updated conversation state
        """
        # Add to conversation history
        state["conversation_history"].append(
            {
                "speaker": self.name,
                "message": state["current_message"],
                "timestamp": time.time(),
            }
        )

        state["turn_count"] += 1

        logger.info(
            f"Agent '{self.name}' sending message (Turn {state['turn_count']}): "
            f"\"{state['current_message'][:100]}...\""
        )

        # Send to Kafka
        try:
            self.producer.send(
                self.send_topic,
                {
                    "message": state["current_message"],
                    "conversation_history": state["conversation_history"],
                    "turn_count": state["turn_count"],
                    "speaker": self.name,
                    "timestamp": time.time(),
                },
            )
            self.producer.flush()
            logger.debug(f"Message sent successfully to topic '{self.send_topic}'")

        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}", exc_info=True)

        return state

    def should_continue(self, state: ConversationState) -> str:
        """
        Decide whether to continue conversation.

        Args:
            state: Current conversation state

        Returns:
            'continue' or 'end'
        """
        if state["turn_count"] >= state["max_turns"]:
            logger.info(
                f"Agent '{self.name}' reached max turns ({state['max_turns']}), ending conversation"
            )
            return "end"

        logger.debug(
            f"Agent '{self.name}' continuing conversation "
            f"(Turn {state['turn_count']}/{state['max_turns']})"
        )
        return "continue"

    @traceable(
        name="start_conversation",
        run_type="chain",
        tags=["agent", "conversation-starter"]
    )
    def start_conversation(self, initial_message: str) -> None:
        """
        Start the conversation with an initial message.

        Args:
            initial_message: Initial message to start conversation
        """
        logger.info(f"Agent '{self.name}' starting conversation")

        # Add trace metadata
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.metadata = {
                    "agent_name": self.name,
                    "role": "initiator",
                    "initial_message": initial_message[:100],
                }
        except Exception:
            pass

        initial_state = {
            "conversation_history": [],
            "current_message": initial_message,
            "turn_count": 0,
            "max_turns": self.max_turns,
            "agent_name": self.name,
        }

        # Use LLM to generate first message
        initial_state = self.reason_with_llm(initial_state)
        initial_state = self.send_response(initial_state)

        # Continue with normal flow
        initial_state["current_message"] = ""
        result = self.graph.invoke(initial_state)

        logger.info(f"Agent '{self.name}' conversation ended")
        self.cleanup()

    @traceable(
        name="run_agent",
        run_type="chain",
        tags=["agent", "listener"]
    )
    def run(self) -> None:
        """Run agent in listening mode."""
        logger.info(f"Agent '{self.name}' starting in listening mode")

        # Add trace metadata
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.metadata = {
                    "agent_name": self.name,
                    "role": "listener",
                    "max_turns": self.max_turns,
                }
        except Exception:
            pass

        initial_state = {
            "conversation_history": [],
            "current_message": "",
            "turn_count": 0,
            "max_turns": self.max_turns,
            "agent_name": self.name,
        }

        result = self.graph.invoke(initial_state)
        logger.info(f"Agent '{self.name}' conversation ended")
        self.cleanup()

    def cleanup(self) -> None:
        """Close Kafka connections."""
        logger.info(f"Agent '{self.name}' cleaning up resources")

        try:
            self.producer.close()
            self.consumer.close()
            logger.debug(f"Kafka connections closed for agent '{self.name}'")
        except Exception as e:
            logger.error(f"Error during cleanup for agent '{self.name}': {e}")
