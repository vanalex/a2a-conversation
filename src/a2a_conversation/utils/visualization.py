"""
Visualization utilities for LangGraph state graphs and conversation flow.
"""
from pathlib import Path
from typing import Optional
from langgraph.graph import StateGraph
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def visualize_graph(
    graph: StateGraph,
    output_path: str = "conversation_graph.png",
    format: str = "png"
) -> Optional[Path]:
    """
    Visualize a LangGraph StateGraph.

    Args:
        graph: The compiled LangGraph StateGraph to visualize
        output_path: Path where to save the visualization
        format: Output format ('png', 'svg', 'mermaid')

    Returns:
        Path to the saved visualization file, or None if failed
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "mermaid":
            # Generate Mermaid diagram
            mermaid_code = graph.get_graph().draw_mermaid()
            output_file = output_file.with_suffix(".mmd")
            output_file.write_text(mermaid_code)
            logger.info(f"Mermaid diagram saved to: {output_file}")
            print(f"\nMermaid diagram saved to: {output_file}")
            print("\nMermaid Code:")
            print(mermaid_code)
        else:
            # Generate PNG/SVG using pygraphviz
            try:
                png_data = graph.get_graph().draw_mermaid_png()
                output_file = output_file.with_suffix(f".{format}")
                output_file.write_bytes(png_data)
                logger.info(f"Graph visualization saved to: {output_file}")
                print(f"\nGraph visualization saved to: {output_file}")
            except Exception as e:
                logger.error(f"PNG/SVG generation requires pygraphviz: {e}")
                print(f"\nError: PNG/SVG format requires pygraphviz")
                print("Install with: brew install graphviz && uv sync --extra viz")
                print("\nTip: Use format='mermaid' for text-based diagrams (no dependencies needed)")
                return None

        return output_file

    except Exception as e:
        logger.error(f"Failed to visualize graph: {e}", exc_info=True)
        return None


def print_graph_structure(graph: StateGraph) -> None:
    """
    Print the graph structure as text.

    Args:
        graph: The compiled LangGraph StateGraph
    """
    try:
        print("\n" + "=" * 60)
        print("CONVERSATION FLOW GRAPH STRUCTURE")
        print("=" * 60)

        graph_obj = graph.get_graph()

        print("\nNodes:")
        for node in graph_obj.nodes:
            print(f"  - {node}")

        print("\nEdges:")
        for edge in graph_obj.edges:
            print(f"  {edge.source} -> {edge.target}")

        print("\n" + "=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Failed to print graph structure: {e}", exc_info=True)
