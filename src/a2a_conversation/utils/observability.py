"""
LangSmith observability utilities for A2A conversation agents.
"""
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import time

try:
    from langsmith import Client, traceable
    from langsmith.run_helpers import get_current_run_tree, trace
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class ConversationTracer:
    """Utility class for tracing conversation metrics and events."""

    def __init__(self, project_name: str = "a2a-conversation"):
        """
        Initialize the conversation tracer.

        Args:
            project_name: LangSmith project name
        """
        self.project_name = project_name
        self.client = None

        if LANGSMITH_AVAILABLE:
            try:
                self.client = Client()
                logger.info(f"LangSmith client initialized for project: {project_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {e}")

    def log_conversation_start(
        self,
        agent_name: str,
        role: str,
        max_turns: int,
        **metadata: Any
    ) -> None:
        """
        Log the start of a conversation.

        Args:
            agent_name: Name of the agent
            role: Role (initiator/listener)
            max_turns: Maximum conversation turns
            **metadata: Additional metadata to log
        """
        if not self.client:
            return

        try:
            self.client.create_run(
                name=f"conversation_start_{agent_name}",
                run_type="chain",
                inputs={"role": role, "max_turns": max_turns},
                project_name=self.project_name,
                tags=["conversation-start", agent_name.lower()],
                extra={"metadata": {"agent_name": agent_name, "role": role, **metadata}},
            )
        except Exception as e:
            logger.debug(f"Failed to log conversation start: {e}")

    def log_turn_metrics(
        self,
        agent_name: str,
        turn_count: int,
        message_length: int,
        response_time_ms: float,
        **metadata: Any
    ) -> None:
        """
        Log metrics for a conversation turn.

        Args:
            agent_name: Name of the agent
            turn_count: Current turn number
            message_length: Length of the message
            response_time_ms: Response time in milliseconds
            **metadata: Additional metadata
        """
        if not self.client:
            return

        try:
            self.client.create_run(
                name=f"turn_{agent_name}_{turn_count}",
                run_type="chain",
                inputs={
                    "turn_count": turn_count,
                    "message_length": message_length,
                },
                outputs={"response_time_ms": response_time_ms},
                project_name=self.project_name,
                tags=["turn-metrics", agent_name.lower()],
                extra={
                    "metadata": {
                        "agent_name": agent_name,
                        "turn_count": turn_count,
                        **metadata,
                    }
                },
            )
        except Exception as e:
            logger.debug(f"Failed to log turn metrics: {e}")

    def log_pii_detection(
        self,
        speaker: str,
        has_pii: bool,
        pii_types: List[str],
        severity: str,
        message_length: int,
    ) -> None:
        """
        Log PII detection results.

        Args:
            speaker: Speaker name
            has_pii: Whether PII was detected
            pii_types: Types of PII found
            severity: Severity level
            message_length: Length of analyzed message
        """
        if not self.client:
            return

        try:
            self.client.create_run(
                name=f"pii_check_{speaker}",
                run_type="chain",
                inputs={"speaker": speaker, "message_length": message_length},
                outputs={
                    "has_pii": has_pii,
                    "pii_types": pii_types,
                    "severity": severity,
                },
                project_name=self.project_name,
                tags=["pii-detection", severity if has_pii else "clean"],
                extra={
                    "metadata": {
                        "speaker": speaker,
                        "has_pii": has_pii,
                        "pii_types": pii_types,
                        "severity": severity,
                    }
                },
            )
        except Exception as e:
            logger.debug(f"Failed to log PII detection: {e}")

    def log_conversation_end(
        self,
        total_turns: int,
        total_messages: int,
        pii_violations: int,
        duration_seconds: float,
        **metadata: Any
    ) -> None:
        """
        Log conversation end summary.

        Args:
            total_turns: Total turns in conversation
            total_messages: Total messages exchanged
            pii_violations: Number of PII violations
            duration_seconds: Total conversation duration
            **metadata: Additional metadata
        """
        if not self.client:
            return

        try:
            self.client.create_run(
                name="conversation_end",
                run_type="chain",
                inputs={
                    "total_turns": total_turns,
                    "total_messages": total_messages,
                },
                outputs={
                    "duration_seconds": duration_seconds,
                    "pii_violations": pii_violations,
                },
                project_name=self.project_name,
                tags=["conversation-end", "summary"],
                extra={
                    "metadata": {
                        "total_turns": total_turns,
                        "total_messages": total_messages,
                        "pii_violations": pii_violations,
                        "duration_seconds": duration_seconds,
                        **metadata,
                    }
                },
            )
        except Exception as e:
            logger.debug(f"Failed to log conversation end: {e}")

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        tags: Optional[List[str]] = None,
        **metadata: Any
    ):
        """
        Context manager for tracing an operation.

        Args:
            operation_name: Name of the operation
            tags: Optional tags for the operation
            **metadata: Additional metadata

        Yields:
            Dictionary to store outputs
        """
        start_time = time.time()
        outputs = {}

        try:
            yield outputs
        finally:
            duration_ms = (time.time() - start_time) * 1000

            if self.client:
                try:
                    self.client.create_run(
                        name=operation_name,
                        run_type="chain",
                        inputs=metadata,
                        outputs={**outputs, "duration_ms": duration_ms},
                        project_name=self.project_name,
                        tags=tags or [],
                        extra={"metadata": metadata},
                    )
                except Exception as e:
                    logger.debug(f"Failed to trace operation {operation_name}: {e}")


def get_trace_url(run_id: str) -> Optional[str]:
    """
    Get the LangSmith URL for a trace.

    Args:
        run_id: The run ID

    Returns:
        URL to view the trace, or None if not available
    """
    if not LANGSMITH_AVAILABLE:
        return None

    return f"https://smith.langchain.com/o/default/projects/p/default/runs/{run_id}"


def add_conversation_feedback(
    run_id: str,
    score: float,
    comment: Optional[str] = None,
    **metadata: Any
) -> bool:
    """
    Add feedback to a conversation trace.

    Args:
        run_id: The run ID to add feedback to
        score: Score (0.0 to 1.0)
        comment: Optional comment
        **metadata: Additional metadata

    Returns:
        True if successful, False otherwise
    """
    if not LANGSMITH_AVAILABLE:
        return False

    try:
        client = Client()
        client.create_feedback(
            run_id=run_id,
            key="conversation_quality",
            score=score,
            comment=comment,
            **metadata,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add feedback: {e}")
        return False


# Decorator for easy tracing
def trace_conversation_method(
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    **trace_kwargs: Any
):
    """
    Decorator for tracing conversation methods.

    Args:
        name: Optional custom name for the trace
        tags: Optional tags for the trace
        **trace_kwargs: Additional kwargs for traceable

    Returns:
        Decorated function
    """
    if not LANGSMITH_AVAILABLE:
        # Return pass-through decorator if LangSmith not available
        def decorator(func):
            return func
        return decorator

    return traceable(
        name=name,
        tags=tags or [],
        **trace_kwargs
    )
