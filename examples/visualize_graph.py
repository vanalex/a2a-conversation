"""
Example: Visualize the conversation flow graph.

This script demonstrates how to visualize the LangGraph state machine
without requiring any external visualization tools.
"""
from a2a_conversation.config.settings import KafkaConfig, LLMConfig
from a2a_conversation.agents.conversational_agent import ConversationalAgent
from a2a_conversation.utils.visualization import visualize_graph, print_graph_structure


def main():
    """Demonstrate graph visualization."""
    print("Creating conversational agent...")

    # Load configurations
    kafka_config = KafkaConfig.from_env()
    llm_config = LLMConfig.from_env()

    # Create a sample agent
    agent = ConversationalAgent(
        name="Alice",
        persona="A curious marine biologist",
        kafka_config=kafka_config,
        llm_config=llm_config,
        listen_topic="bob-messages",
        send_topic="alice-messages",
        max_turns=10,
    )

    # Print text-based graph structure (always works, no dependencies)
    print_graph_structure(agent.graph)

    # Generate Mermaid diagram (text format, no dependencies)
    print("\nGenerating Mermaid diagram...")
    mermaid_file = visualize_graph(agent.graph, "conversation_graph.mmd", format="mermaid")

    if mermaid_file:
        print(f"\n✓ Mermaid diagram saved to: {mermaid_file}")
        print("\nYou can:")
        print("  1. View it at: https://mermaid.live/")
        print("  2. Use it in GitHub markdown (renders automatically)")
        print("  3. Use it in the Streamlit dashboard")

    # Cleanup
    agent.cleanup()

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
