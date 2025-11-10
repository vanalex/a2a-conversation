"""
Real-time Streamlit dashboard for monitoring A2A conversation flow and states.
"""
import json
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from kafka import KafkaConsumer
from typing import List, Dict
import threading
import time

from a2a_conversation.config.settings import KafkaConfig
from a2a_conversation.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConversationMonitor:
    """Monitor and visualize conversations in real-time."""

    def __init__(self, kafka_config: KafkaConfig):
        """Initialize the conversation monitor."""
        self.kafka_config = kafka_config
        self.messages: List[Dict] = []
        self.running = False
        self.consumer = None

    def start_monitoring(self, topics: List[str]) -> None:
        """Start monitoring Kafka topics."""
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.kafka_config.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                group_id="dashboard-monitor",
                enable_auto_commit=True,
            )
            self.running = True
            logger.info(f"Started monitoring topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            st.error(f"Failed to connect to Kafka: {e}")

    def fetch_messages(self, timeout_ms: int = 1000) -> List[Dict]:
        """Fetch new messages from Kafka."""
        if not self.consumer:
            return []

        new_messages = []
        records = self.consumer.poll(timeout_ms=timeout_ms)

        for topic_partition, messages in records.items():
            for record in messages:
                msg_data = record.value
                msg_data["topic"] = topic_partition.topic
                msg_data["partition"] = topic_partition.partition
                msg_data["offset"] = record.offset
                new_messages.append(msg_data)

        if new_messages:
            self.messages.extend(new_messages)
            logger.debug(f"Fetched {len(new_messages)} new messages")

        return new_messages

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Stopped monitoring")


def render_state_graph() -> None:
    """Render the LangGraph state graph visualization."""
    st.subheader("🔄 Conversation Flow Graph")

    # Mermaid diagram for the conversation flow
    mermaid_diagram = """
    graph TD
        A[Listen for Message] --> B[Reason with LLM]
        B --> C[Send Response]
        C --> D{Should Continue?}
        D -->|Continue| A
        D -->|End| E[End Conversation]

        style A fill:#e1f5ff
        style B fill:#fff9e1
        style C fill:#e8f5e9
        style D fill:#fce4ec
        style E fill:#f3e5f5
    """

    st.markdown(f"```mermaid\n{mermaid_diagram}\n```")

    # State information
    st.info("""
    **State Components:**
    - `conversation_history`: List of all messages
    - `current_message`: Current message being processed
    - `turn_count`: Number of conversation turns
    - `max_turns`: Maximum allowed turns
    - `agent_name`: Name of the agent
    """)


def render_conversation_timeline(messages: List[Dict]) -> None:
    """Render conversation timeline visualization."""
    st.subheader("💬 Conversation Timeline")

    if not messages:
        st.info("No messages yet. Waiting for conversation to start...")
        return

    # Create timeline visualization
    for i, msg in enumerate(messages):
        speaker = msg.get("speaker", "Unknown")
        message_text = msg.get("message", "")
        turn_count = msg.get("turn_count", 0)
        timestamp = msg.get("timestamp", time.time())
        topic = msg.get("topic", "")

        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%H:%M:%S")

        # Color based on speaker
        if speaker == "Alice":
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px 0;">
                <strong>🌊 {speaker}</strong> <em>(Turn {turn_count} @ {time_str})</em><br/>
                {message_text}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #f3e5f5; padding: 10px; border-radius: 5px; margin: 5px 0;">
                <strong>💻 {speaker}</strong> <em>(Turn {turn_count} @ {time_str})</em><br/>
                {message_text}
            </div>
            """, unsafe_allow_html=True)


def render_statistics(messages: List[Dict]) -> None:
    """Render conversation statistics."""
    st.subheader("📊 Statistics")

    if not messages:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Messages", len(messages))

    with col2:
        max_turn = max([msg.get("turn_count", 0) for msg in messages], default=0)
        st.metric("Current Turn", max_turn)

    with col3:
        alice_count = len([m for m in messages if m.get("speaker") == "Alice"])
        st.metric("Alice Messages", alice_count)

    with col4:
        bob_count = len([m for m in messages if m.get("speaker") == "Bob"])
        st.metric("Bob Messages", bob_count)

    # Message length chart
    if messages:
        fig = go.Figure()

        speakers = [msg.get("speaker", "Unknown") for msg in messages]
        lengths = [len(msg.get("message", "")) for msg in messages]
        turns = [msg.get("turn_count", 0) for msg in messages]

        colors = ["#2196F3" if s == "Alice" else "#9C27B0" for s in speakers]

        fig.add_trace(go.Bar(
            x=turns,
            y=lengths,
            marker_color=colors,
            text=speakers,
            hovertemplate="<b>%{text}</b><br>Turn: %{x}<br>Length: %{y}<extra></extra>"
        ))

        fig.update_layout(
            title="Message Length by Turn",
            xaxis_title="Turn Number",
            yaxis_title="Message Length (characters)",
            showlegend=False,
            height=300
        )

        st.plotly_chart(fig, use_container_width=True)


def render_conversation_history_table(messages: List[Dict]) -> None:
    """Render detailed conversation history."""
    st.subheader("📝 Detailed History")

    if not messages:
        return

    # Create expandable section for full history
    with st.expander("View Full Conversation History"):
        for msg in messages:
            conv_history = msg.get("conversation_history", [])
            if conv_history:
                st.json(conv_history)
                break


def main():
    """Main Streamlit dashboard."""
    st.set_page_config(
        page_title="A2A Conversation Monitor",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🤖 A2A Conversation Real-Time Monitor")
    st.markdown("Monitor agent-to-agent conversations and state flow")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        kafka_brokers = st.text_input(
            "Kafka Brokers",
            "localhost:9092",
            help="Comma-separated list of Kafka brokers"
        )

        alice_topic = st.text_input("Alice Topic", "alice-messages")
        bob_topic = st.text_input("Bob Topic", "bob-messages")

        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 10, 2)

        if st.button("Clear Messages"):
            if "monitor" in st.session_state:
                st.session_state.monitor.messages = []
            st.rerun()

    # Initialize monitor
    if "monitor" not in st.session_state:
        kafka_config = KafkaConfig(
            bootstrap_servers=kafka_brokers,
            alice_topic=alice_topic,
            bob_topic=bob_topic,
        )
        st.session_state.monitor = ConversationMonitor(kafka_config)
        st.session_state.monitor.start_monitoring([alice_topic, bob_topic])

    monitor = st.session_state.monitor

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📊 Live Dashboard", "🔄 State Graph", "📖 Documentation"])

    with tab1:
        # Fetch new messages
        monitor.fetch_messages(timeout_ms=500)

        # Render dashboard components
        render_statistics(monitor.messages)
        st.divider()
        render_conversation_timeline(monitor.messages)
        st.divider()
        render_conversation_history_table(monitor.messages)

    with tab2:
        render_state_graph()

    with tab3:
        st.markdown("""
        ## 📖 Dashboard Guide

        ### Features
        - **Real-time monitoring** of agent conversations via Kafka
        - **State graph visualization** showing conversation flow
        - **Timeline view** of all messages exchanged
        - **Statistics** on message counts and lengths

        ### How It Works
        1. Connects to Kafka topics (Alice and Bob)
        2. Listens for messages in real-time
        3. Visualizes conversation flow and statistics
        4. Displays full conversation history

        ### State Management
        Each message contains:
        - `speaker`: Agent name (Alice/Bob)
        - `message`: Message content
        - `conversation_history`: Full conversation context
        - `turn_count`: Current turn number
        - `timestamp`: Message timestamp

        ### Graph Nodes
        - **Listen**: Agent waits for incoming messages
        - **Reason**: LLM processes message and generates response
        - **Respond**: Agent sends response to Kafka
        - **Should Continue**: Checks if max turns reached
        """)

    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
