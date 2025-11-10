"""
Configuration settings for A2A Conversation agents.
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class KafkaConfig:
    """Kafka broker configuration."""
    bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    alice_topic: str = "alice-messages"
    bob_topic: str = "bob-messages"
    consumer_timeout_ms: int = 30000
    enable_auto_commit: bool = True

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Create configuration from environment variables."""
        servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        return cls(
            bootstrap_servers=servers.split(","),
            alice_topic=os.getenv("KAFKA_ALICE_TOPIC", "alice-messages"),
            bob_topic=os.getenv("KAFKA_BOB_TOPIC", "bob-messages"),
            consumer_timeout_ms=int(os.getenv("KAFKA_CONSUMER_TIMEOUT_MS", "30000")),
        )


@dataclass
class LLMConfig:
    """LLM configuration."""
    model: str = "gpt-4"
    temperature: float = 0.8
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    max_tokens: int = 500

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create configuration from environment variables."""
        return cls(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.8")),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500")),
        )


@dataclass
class LangSmithConfig:
    """LangSmith observability configuration."""
    tracing_enabled: bool = False
    endpoint: str = "https://api.smith.langchain.com"
    api_key: str = ""
    project: str = "a2a-conversation"

    @classmethod
    def from_env(cls) -> "LangSmithConfig":
        """Create configuration from environment variables."""
        tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        return cls(
            tracing_enabled=tracing,
            endpoint=os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
            api_key=os.getenv("LANGCHAIN_API_KEY", ""),
            project=os.getenv("LANGCHAIN_PROJECT", "a2a-conversation"),
        )

    def setup(self) -> None:
        """Set up LangSmith tracing environment variables."""
        if self.tracing_enabled and self.api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = self.endpoint
            os.environ["LANGCHAIN_API_KEY"] = self.api_key
            os.environ["LANGCHAIN_PROJECT"] = self.project


@dataclass
class AppConfig:
    """Application configuration."""
    max_turns: int = 12
    startup_delay_seconds: int = 3
    log_level: str = "INFO"
    log_file: str = "logs/a2a_conversation.log"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls(
            max_turns=int(os.getenv("MAX_TURNS", "12")),
            startup_delay_seconds=int(os.getenv("STARTUP_DELAY_SECONDS", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/a2a_conversation.log"),
        )
