"""
Test script to demonstrate PII detection in conversations.
"""
import time
import threading
from src.a2a_conversation.config.settings import KafkaConfig, LLMConfig, AppConfig
from src.a2a_conversation.agents.conversational_agent import ConversationalAgent
from src.a2a_conversation.agents.pii_monitor_agent import PIIMonitorAgent
from src.a2a_conversation.utils.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


def create_test_personas():
    """Create test personas that might share PII."""
    alice_persona = (
        "You are Alice, a friendly person who sometimes overshares personal "
        "information. You're excited to chat but might accidentally mention "
        "sensitive details like phone numbers, addresses, or email addresses."
    )

    bob_persona = (
        "You are Bob, a casual conversationalist who asks questions and "
        "sometimes shares personal information without thinking twice."
    )

    return alice_persona, bob_persona


def main():
    """Run test with PII monitoring."""
    # Load configurations
    kafka_config = KafkaConfig.from_env()
    llm_config = LLMConfig.from_env()
    app_config = AppConfig.from_env()

    # Setup logging
    setup_logging(level=app_config.log_level)

    logger.info("=" * 80)
    logger.info("PII DETECTION TEST - A2A Conversation")
    logger.info("=" * 80)

    # Create test personas
    alice_persona, bob_persona = create_test_personas()

    # Create agents
    alice = ConversationalAgent(
        name="Alice",
        persona=alice_persona,
        kafka_config=kafka_config,
        llm_config=llm_config,
        listen_topic=kafka_config.bob_topic,
        send_topic=kafka_config.alice_topic,
        max_turns=5,  # Shorter test
    )

    bob = ConversationalAgent(
        name="Bob",
        persona=bob_persona,
        kafka_config=kafka_config,
        llm_config=llm_config,
        listen_topic=kafka_config.alice_topic,
        send_topic=kafka_config.bob_topic,
        max_turns=5,
    )

    # Create PII Monitor
    pii_monitor = PIIMonitorAgent(
        kafka_config=kafka_config,
        llm_config=llm_config,
        monitor_topics=[kafka_config.alice_topic, kafka_config.bob_topic],
    )

    # Start all agents
    logger.info("Starting PII Monitor...")
    pii_thread = threading.Thread(target=pii_monitor.run, daemon=True)
    pii_thread.start()

    logger.info("Starting Bob...")
    bob_thread = threading.Thread(target=bob.run, daemon=True)
    bob_thread.start()

    time.sleep(2)

    # Alice starts with a message that might lead to PII sharing
    initial_message = (
        "Hey! I just moved to a new apartment and I'm so excited! "
        "Want to exchange contact info so we can hang out?"
    )
    logger.info(f"Alice starting conversation: '{initial_message}'")

    alice_thread = threading.Thread(
        target=alice.start_conversation,
        args=(initial_message,),
        daemon=True,
    )
    alice_thread.start()

    # Wait for conversation to complete
    alice_thread.join()
    bob_thread.join()

    # Give PII monitor time to process final messages
    time.sleep(3)

    logger.info("=" * 80)
    logger.info("Test completed! Check logs above for PII violations.")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        raise
