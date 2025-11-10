"""
PII monitoring agent that observes conversations and detects PII violations.
"""
import json
import time
from typing import List, Dict, Optional

from kafka import KafkaConsumer
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from ..config.settings import KafkaConfig, LLMConfig
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class PIIMonitorAgent:
    """Agent that monitors conversations for PII (Personally Identifiable Information) violations."""

    PII_CATEGORIES = [
        "Social Security Numbers",
        "Credit Card Numbers",
        "Email Addresses",
        "Phone Numbers",
        "Physical Addresses",
        "Driver's License Numbers",
        "Passport Numbers",
        "Medical Record Numbers",
        "Bank Account Numbers",
        "Date of Birth",
        "Full Names with sensitive context",
        "IP Addresses",
        "Biometric data",
    ]

    def __init__(
        self,
        kafka_config: KafkaConfig,
        llm_config: LLMConfig,
        monitor_topics: List[str],
    ):
        """
        Initialize PII monitoring agent.

        Args:
            kafka_config: Kafka configuration
            llm_config: LLM configuration
            monitor_topics: List of Kafka topics to monitor
        """
        self.name = "PII-Monitor"
        self.kafka_config = kafka_config
        self.llm_config = llm_config
        self.monitor_topics = monitor_topics

        logger.info(
            f"Initializing PII Monitor | Topics: {', '.join(monitor_topics)}"
        )

        # Initialize LangChain OpenAI LLM for PII detection
        self.llm = ChatOpenAI(
            model=llm_config.model,
            temperature=0.0,  # Use low temperature for consistent analysis
            api_key=llm_config.api_key,
            max_tokens=500,
        )

        # Setup Kafka consumer
        self._setup_kafka()

        # Track conversation history for context
        self.conversation_history: List[Dict] = []
        self.pii_violations: List[Dict] = []

        logger.info("PII Monitor initialized successfully")

    def _setup_kafka(self) -> None:
        """Initialize Kafka consumer to monitor topics."""
        logger.debug("Setting up Kafka consumer for PII monitoring")

        try:
            self.consumer = KafkaConsumer(
                *self.monitor_topics,
                bootstrap_servers=self.kafka_config.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                group_id="pii-monitor-group",
                enable_auto_commit=self.kafka_config.enable_auto_commit,
            )

            logger.debug("Kafka consumer setup complete for PII monitoring")

        except Exception as e:
            logger.error(f"Failed to setup Kafka for PII monitor: {e}")
            raise

    @traceable(
        name="check_for_pii",
        run_type="llm",
        tags=["pii-detection", "security", "compliance"],
        metadata={"agent_type": "pii_monitor"}
    )
    def check_for_pii(self, message: str, speaker: str) -> Optional[Dict]:
        """
        Use LLM to analyze message for PII violations.

        Args:
            message: The message to analyze
            speaker: The speaker who sent the message

        Returns:
            Dictionary with violation details if PII found, None otherwise
        """
        logger.debug(f"Analyzing message from {speaker} for PII")

        # Add trace metadata
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.metadata = {
                    "speaker": speaker,
                    "message_length": len(message),
                    "pii_categories_checked": len(self.PII_CATEGORIES),
                }
        except Exception:
            pass

        try:
            system_prompt = f"""You are a PII (Personally Identifiable Information) detection expert.

Analyze the following message for any PII violations. Consider these categories:
{', '.join(self.PII_CATEGORIES)}

Respond in JSON format with the following structure:
{{
    "has_pii": true/false,
    "pii_types": ["list", "of", "pii", "types", "found"],
    "severity": "low/medium/high",
    "details": "Brief explanation of what PII was found and why it's concerning",
    "recommendation": "What should be done about this violation"
}}

Be strict in your analysis. Even partial information that could be used to identify someone should be flagged.
If no PII is found, set has_pii to false and leave other fields empty."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Speaker: {speaker}\nMessage: {message}"),
            ]

            response = self.llm.invoke(messages)
            response_text = response.content.strip()

            # Parse JSON response
            # Handle markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result = json.loads(response_text)

            if result.get("has_pii", False):
                logger.warning(
                    f"PII VIOLATION DETECTED from {speaker}: {result.get('pii_types')}"
                )
                return {
                    "speaker": speaker,
                    "message": message,
                    "timestamp": time.time(),
                    **result,
                }

            logger.debug(f"No PII detected in message from {speaker}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error during PII analysis: {e}", exc_info=True)
            return None

    @traceable(
        name="process_message",
        tags=["kafka", "message-processing"],
    )
    def process_message(self, data: Dict) -> None:
        """
        Process incoming message and check for PII.

        Args:
            data: Message data from Kafka
        """
        message = data.get("message", "")
        speaker = data.get("speaker", "Unknown")
        turn_count = data.get("turn_count", 0)

        logger.info(f"Processing message from {speaker} (Turn {turn_count})")

        # Add trace metadata
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.metadata = {
                    "speaker": speaker,
                    "turn_count": turn_count,
                    "total_messages_monitored": len(self.conversation_history) + 1,
                    "total_violations_so_far": len(self.pii_violations),
                }
        except Exception:
            pass

        # Add to conversation history
        self.conversation_history.append(
            {
                "speaker": speaker,
                "message": message,
                "turn_count": turn_count,
                "timestamp": time.time(),
            }
        )

        # Check for PII
        violation = self.check_for_pii(message, speaker)

        if violation:
            self.pii_violations.append(violation)
            self._log_warning(violation)

    def _log_warning(self, violation: Dict) -> None:
        """
        Log a PII violation warning.

        Args:
            violation: Violation details
        """
        logger.warning("=" * 80)
        logger.warning("⚠️  PII VIOLATION DETECTED ⚠️")
        logger.warning("=" * 80)
        logger.warning(f"Speaker: {violation['speaker']}")
        logger.warning(f"Severity: {violation.get('severity', 'unknown').upper()}")
        logger.warning(f"PII Types: {', '.join(violation.get('pii_types', []))}")
        logger.warning(f"Details: {violation.get('details', 'N/A')}")
        logger.warning(f"Recommendation: {violation.get('recommendation', 'N/A')}")
        logger.warning(f"Message excerpt: {violation['message'][:100]}...")
        logger.warning("=" * 80)

    def run(self) -> None:
        """Run the PII monitor in continuous mode."""
        logger.info("PII Monitor starting continuous monitoring...")

        try:
            while True:
                messages = self.consumer.poll(
                    timeout_ms=self.kafka_config.consumer_timeout_ms
                )

                if messages:
                    for topic_partition, records in messages.items():
                        for record in records:
                            self.process_message(record.value)

        except KeyboardInterrupt:
            logger.info("PII Monitor stopped by user")
        except Exception as e:
            logger.error(f"Error in PII monitor: {e}", exc_info=True)
        finally:
            self.cleanup()

    def get_summary(self) -> Dict:
        """
        Get summary of PII violations detected.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_messages_monitored": len(self.conversation_history),
            "total_violations": len(self.pii_violations),
            "violations_by_severity": self._count_by_severity(),
            "violations_by_type": self._count_by_type(),
            "violations_by_speaker": self._count_by_speaker(),
        }

    def _count_by_severity(self) -> Dict[str, int]:
        """Count violations by severity level."""
        counts = {"low": 0, "medium": 0, "high": 0}
        for v in self.pii_violations:
            severity = v.get("severity", "medium")
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _count_by_type(self) -> Dict[str, int]:
        """Count violations by PII type."""
        counts = {}
        for v in self.pii_violations:
            for pii_type in v.get("pii_types", []):
                counts[pii_type] = counts.get(pii_type, 0) + 1
        return counts

    def _count_by_speaker(self) -> Dict[str, int]:
        """Count violations by speaker."""
        counts = {}
        for v in self.pii_violations:
            speaker = v.get("speaker", "Unknown")
            counts[speaker] = counts.get(speaker, 0) + 1
        return counts

    def cleanup(self) -> None:
        """Close Kafka connections and log summary."""
        logger.info("PII Monitor cleaning up...")

        # Log summary
        summary = self.get_summary()
        logger.info("=" * 80)
        logger.info("PII MONITORING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total messages monitored: {summary['total_messages_monitored']}")
        logger.info(f"Total PII violations: {summary['total_violations']}")

        if summary['total_violations'] > 0:
            logger.info("\nViolations by severity:")
            for severity, count in summary['violations_by_severity'].items():
                if count > 0:
                    logger.info(f"  {severity.upper()}: {count}")

            logger.info("\nViolations by type:")
            for pii_type, count in summary['violations_by_type'].items():
                logger.info(f"  {pii_type}: {count}")

            logger.info("\nViolations by speaker:")
            for speaker, count in summary['violations_by_speaker'].items():
                logger.info(f"  {speaker}: {count}")

        logger.info("=" * 80)

        try:
            self.consumer.close()
            logger.debug("Kafka consumer closed")
        except Exception as e:
            logger.error(f"Error during PII monitor cleanup: {e}")
