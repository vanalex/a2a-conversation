# Visualization Guide

This document explains the three visualization options available for monitoring and understanding the A2A conversation flow.

## Quick Start

### ✅ Option 1: Built-in (Works Now - No Extra Setup)

```bash
uv run python examples/visualize_graph.py
```

This generates:
- Text-based graph structure (printed to console)
- Mermaid diagram file (`conversation_graph.mmd`)

**Output Example:**
```
============================================================
CONVERSATION FLOW GRAPH STRUCTURE
============================================================

Nodes:
  - listen
  - reason
  - respond

Edges:
  listen -> reason
  reason -> respond
  respond -> listen (conditional)
  respond -> END (conditional)

Entry Point:
  listen
============================================================
```

The Mermaid file can be viewed at https://mermaid.live/ or embedded in GitHub markdown.

---

## 🎨 Option 2: Real-Time Streamlit Dashboard (Requires Extra Install)

### Why Use This?
- Monitor live conversations as they happen
- See message flow between Alice and Bob in real-time
- View statistics and conversation history
- Interactive web interface

### Installation

```bash
# Note: May require Python 3.11-3.12 instead of 3.14
uv sync --extra dashboard
```

### Usage

1. Start your conversation agents:
   ```bash
   uv run python -m src.a2a_conversation.main
   ```

2. In a separate terminal, launch the dashboard:
   ```bash
   streamlit run src/a2a_conversation/dashboard.py
   ```

3. Open your browser to http://localhost:8501

### Features

**Live Dashboard Tab:**
- Real-time message timeline
- Color-coded by speaker (Alice = blue, Bob = purple)
- Message count and turn statistics
- Interactive charts showing message lengths

**State Graph Tab:**
- Mermaid visualization of the LangGraph workflow
- State component documentation
- Flow explanation

**Documentation Tab:**
- How-to guides
- Architecture overview

### Configuration

Use the sidebar to configure:
- Kafka broker address
- Topic names
- Auto-refresh interval

### Troubleshooting

**Problem:** `cmake` command not found during installation

**Solution:** Streamlit depends on `pyarrow` which needs cmake to build on Python 3.14:
```bash
# Install cmake
brew install cmake  # macOS
sudo apt install cmake  # Ubuntu

# Or use Python 3.11-3.12 which has pre-built wheels
pyenv install 3.12.0
pyenv local 3.12.0
```

---

## 📊 Option 3: Static PNG/SVG (Requires System Dependencies)

### Why Use This?
- Generate publication-quality diagrams
- Embed in presentations or documentation
- No need for web browser

### Installation

```bash
# Install system dependency
brew install graphviz  # macOS
sudo apt install graphviz graphviz-dev  # Ubuntu

# Install Python package
uv sync --extra viz
```

### Usage

```python
from a2a_conversation.agents.conversational_agent import ConversationalAgent
from a2a_conversation.utils.visualization import visualize_graph

# Create agent
alice = ConversationalAgent(...)

# Generate PNG
visualize_graph(alice.graph, "conversation_graph.png")

# Or SVG
visualize_graph(alice.graph, "conversation_graph.svg", format="svg")
```

---

## Comparison Table

| Feature | Built-in | Streamlit Dashboard | Static PNG/SVG |
|---------|----------|---------------------|----------------|
| **Setup Required** | None | Extra dependencies | System + Python deps |
| **Real-time Monitoring** | ❌ | ✅ | ❌ |
| **Works on Python 3.14** | ✅ | ⚠️ May need cmake | ⚠️ Requires graphviz |
| **Output Format** | Text + Mermaid | Web interface | PNG/SVG files |
| **Message History** | ❌ | ✅ | ❌ |
| **Statistics** | ❌ | ✅ | ❌ |
| **Best For** | Quick checks | Development/Debugging | Documentation |

---

## Recommended Workflow

1. **Development:** Use **Built-in** for quick graph structure checks
2. **Testing:** Use **Streamlit Dashboard** to monitor live conversations
3. **Documentation:** Use **Static PNG/SVG** for presentations and wikis

---

## Example: Complete Visualization Workflow

```bash
# 1. Check graph structure (no setup needed)
uv run python examples/visualize_graph.py

# 2. Start the agents
uv run python -m src.a2a_conversation.main

# 3. In another terminal, watch them chat (requires dashboard install)
uv sync --extra dashboard
streamlit run src/a2a_conversation/dashboard.py
```

---

## FAQ

**Q: Which option should I use?**
A: Start with the built-in visualization. Add the dashboard if you need real-time monitoring.

**Q: The dashboard won't install on Python 3.14?**
A: Use Python 3.11 or 3.12, or install cmake: `brew install cmake`

**Q: Can I use the Mermaid diagram in my README?**
A: Yes! GitHub automatically renders Mermaid in markdown:
```markdown
\`\`\`mermaid
graph TD
    A[Listen] --> B[Reason]
    B --> C[Respond]
    C --> D{Continue?}
    D -->|Yes| A
    D -->|No| E[End]
\`\`\`
```

**Q: Do I need all three options?**
A: No! The built-in visualization works out-of-the-box. The others are optional enhancements.
