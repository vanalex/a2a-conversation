"""
State definitions for conversational agents.
"""
from typing import TypedDict, List, Dict


class ConversationState(TypedDict):
    """State for conversational agents in LangGraph."""
    conversation_history: List[Dict[str, str]]
    current_message: str
    turn_count: int
    max_turns: int
    agent_name: str
