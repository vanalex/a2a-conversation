"""
Utility functions for conversation management.
"""
from typing import List, Dict
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def print_conversation_summary(history: List[Dict]) -> None:
    """
    Print a formatted summary of the conversation.

    Args:
        history: List of conversation messages with speaker and message keys
    """
    logger.info("Generating conversation summary")

    print(f"\n{'=' * 60}")
    print(f"📜 CONVERSATION SUMMARY")
    print(f"{'=' * 60}")

    for msg in history:
        speaker = msg.get("speaker", "Unknown")
        text = msg.get("message", "")
        print(f"\n{speaker}: {text}")

    print(f"\n{'=' * 60}\n")

    logger.debug(f"Conversation summary completed ({len(history)} messages)")
