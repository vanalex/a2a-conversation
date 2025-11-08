"""
A2A Conversation Agents - LangGraph AI agents communicating via Kafka.
"""
__version__ = "0.1.0"

from .agents.conversational_agent import ConversationalAgent
from .config.settings import KafkaConfig, LLMConfig, AppConfig

__all__ = [
    "ConversationalAgent",
    "KafkaConfig",
    "LLMConfig",
    "AppConfig",
]
