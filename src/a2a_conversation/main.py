"""
Main entry point for A2A Conversation Agents.

LangGraph AI Conversation Agents with Apache Kafka 4.0
Two AI agents engage in natural conversation using LLMs for reasoning.
Messages are passed through Kafka topics.
"""
import time
import threading

from .config.settings import KafkaConfig, LLMConfig, AppConfig
from .agents.conversational_agent import ConversationalAgent
from .utils.logging_config import setup_logging, get_logger
from .utils.conversation import print_conversation_summary

# Initialize logger
logger = get_logger(__name__)


def create_agent_personas() -> tuple[str, str]:
    """
    Define agent personas.

    Returns:
        Tuple of (alice_persona, bob_persona)
    """
    alice_persona = (
        "You are Alice, a curious and enthusiastic marine biologist who loves "
        "discovering new things about ocean life. You're optimistic, ask thoughtful "
        "questions, and share fascinating facts about the sea."
    )

    bob_persona = (
        "You are Bob, a philosophical software engineer who enjoys pondering big "
        "questions about technology and life. You're thoughtful, sometimes skeptical, "
        "but always respectful and interested in others' perspectives."
    )

    return alice_persona, bob_persona


def main() -> None:
    """Main function to run conversational agents."""

    # Load configurations
    kafka_config = KafkaConfig.from_env()
    llm_config = LLMConfig.from_env()
    app_config = AppConfig.from_env()

    # Setup logging
    setup_logging(
        level=app_config.log_level,
        log_file=app_config.log_file,
    )

    logger.info("=" * 60)
    logger.info("Starting A2A Conversation Agents")
    logger.info("=" * 60)
    logger.info(f"Kafka brokers: {kafka_config.bootstrap_servers}")
    logger.info(f"LLM model: {llm_config.model}")
    logger.info(f"Max turns: {app_config.max_turns}")
    logger.info("=" * 60)

    # Define agent personas
    alice_persona, bob_persona = create_agent_personas()

    # Create agents
    logger.info("Creating Alice agent...")
    alice = ConversationalAgent(
        name="Alice",
        persona=alice_persona,
        kafka_config=kafka_config,
        llm_config=llm_config,
        listen_topic=kafka_config.bob_topic,
        send_topic=kafka_config.alice_topic,
        max_turns=app_config.max_turns,
    )

    logger.info("Creating Bob agent...")
    bob = ConversationalAgent(
        name="Bob",
        persona=bob_persona,
        kafka_config=kafka_config,
        llm_config=llm_config,
        listen_topic=kafka_config.alice_topic,
        send_topic=kafka_config.bob_topic,
        max_turns=app_config.max_turns,
    )

    # Start Bob in listening mode
    logger.info("Starting Bob in listening mode...")
    bob_thread = threading.Thread(target=bob.run, daemon=True)
    bob_thread.start()

    # Give Bob time to start listening
    logger.info(f"Waiting {app_config.startup_delay_seconds}s for Bob to initialize...")
    time.sleep(app_config.startup_delay_seconds)

    # Alice starts the conversation
    initial_message = "I just got back from an amazing dive where I saw bioluminescent plankton!"
    logger.info(f"Alice starting conversation with: '{initial_message}'")

    alice_thread = threading.Thread(
        target=alice.start_conversation,
        args=(initial_message,),
        daemon=True,
    )
    alice_thread.start()

    # Wait for conversation to complete
    logger.info("Waiting for conversation to complete...")
    alice_thread.join()
    bob_thread.join()

    logger.info("=" * 60)
    logger.info("Conversation completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    """
    Prerequisites:
    1. Install dependencies:
       uv sync
       # or
       pip install langgraph kafka-python langchain-openai python-dotenv

    2. Set your OpenAI API key in .env file:
       OPENAI_API_KEY=your-api-key-here

    3. Start Kafka:
       docker run -d -p 9092:9092 apache/kafka:latest

    4. Run the application:
       python -m src.a2a_conversation.main
       # or
       uv run python -m src.a2a_conversation.main
    """
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise
