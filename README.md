# A2A Conversation

Ever wondered what happens if you put two LLMs on a message bus and leave them unsupervised? This repo. This happens.

Alice (a curious marine biologist) and Bob (a philosophical software engineer) chat with each other through Apache Kafka, guided by a tiny LangGraph workflow and powered by OpenAI. It’s like walkie‑talkies for nerdy AIs.


## Features (a.k.a. Why is this fun?)
- Two independent agents that talk to each other through Kafka topics
- Small, readable LangGraph state machine: listen → reason → respond → (maybe) continue
- **PII Monitor Agent**: Real-time observer that detects personally identifiable information violations
- **Real-time Visualization**: Streamlit dashboard and LangGraph graph visualization
- **LangSmith Observability**: Full tracing and monitoring with LangSmith for LLMOps
- Pluggable personas for delightful chaos
- Bounded conversations via `max_turns` so your GPUs (and patience) survive
- Production-grade structured logging (no more `print()` statements)
- Environment-based configuration with sensible defaults
- Modular architecture for easy extension


## How it works (high‑level)
1. Each agent has a Kafka `consumer` (to listen) and a `producer` (to reply).
2. Both agents run the same three‑step graph:
   - listen: pull the latest message from their topic
   - reason: build context and ask the LLM what to say next
   - respond: publish to the other agent’s topic and increment the turn counter
3. The conversation ends when `turn_count >= max_turns`.

Code to peek at: `src/a2a_conversation/` package with modular components.


## Requirements
- Python 3.11+ recommended
  - Note: `pyproject.toml` currently says `>=3.14`. If you don’t have a time machine, 3.11–3.12 works fine with the listed libs. Adjust if needed.
- A running Kafka broker at `localhost:9092`
- An OpenAI API key (`OPENAI_API_KEY`)


## Installation

With uv (fast, nice, recommended):

```bash
# if you have uv installed
uv sync
```


## Configuration
Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.8
LLM_MAX_TOKENS=500
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ALICE_TOPIC=alice-messages
KAFKA_BOB_TOPIC=bob-messages
MAX_TURNS=12
LOG_LEVEL=INFO
LOG_FILE=logs/a2a_conversation.log
```

All settings have sensible defaults and can be configured via environment variables.


## Running the demo

### Option 1: Docker Compose (Recommended for Production)
Run everything with a single command:

```bash
# Make sure your .env file has OPENAI_API_KEY set
docker-compose up
```

This starts both Kafka and the application in containers with health checks and proper networking.

To run in detached mode:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f a2a-conversation
```

Stop everything:
```bash
docker-compose down
```

### Option 2: Local Development
First, start Kafka:

```bash
docker run -d --name kafka -p 9092:9092 apache/kafka:latest
```

Then run the application locally:

```bash
# Using Python
python -m src.a2a_conversation.main

# Or with uv
uv run python -m src.a2a_conversation.main
```

### What you'll see:
- Bob boots into listening mode, subscribes to `alice-messages`.
- Alice generates the first message via the LLM, publishes to `bob-messages`.
- The two take turns until `max_turns` is hit.
- Structured logs with timestamps, log levels, and context (console + file).

Default topics (from the code):
- Alice sends on: `alice-messages`, listens on: `bob-messages`
- Bob sends on: `bob-messages`, listens on: `alice-messages`


## Visualization

The project includes three visualization options with different dependency requirements:

### Option 1: Built-in Text Visualization (No Extra Dependencies)

Generate Mermaid diagrams and view text-based graph structure:

```bash
uv run python examples/visualize_graph.py
```

This creates a `conversation_graph.mmd` file you can:
- View at [mermaid.live](https://mermaid.live/)
- Embed in GitHub markdown (renders automatically)
- Use in documentation

### Option 2: Real-Time Streamlit Dashboard (Optional)

First, install the optional dashboard dependencies:
```bash
uv sync --extra dashboard
# or with pip
pip install -e ".[dashboard]"
```

Then launch the interactive dashboard to monitor conversations in real-time:

```bash
streamlit run src/a2a_conversation/dashboard.py
```

Features:
- **Live conversation timeline** with color-coded messages
- **Statistics dashboard** showing message counts and lengths
- **State graph visualization** of the LangGraph workflow
- **Auto-refresh** to see new messages as they arrive
- **Full conversation history** with detailed state information

The dashboard will open in your browser at `http://localhost:8501`

**Note:** On Python 3.14, you may need cmake to build pyarrow (a Streamlit dependency). Consider using Python 3.11-3.12 for the dashboard.

### Option 3: Static PNG/SVG Visualization (Optional)
Generate a static visualization of the LangGraph state machine:

```python
from a2a_conversation.agents.conversational_agent import ConversationalAgent
from a2a_conversation.utils.visualization import visualize_graph, print_graph_structure

# After creating an agent
alice = ConversationalAgent(...)

# Generate PNG visualization
visualize_graph(alice.graph, "conversation_graph.png")

# Or generate Mermaid diagram
visualize_graph(alice.graph, "conversation_graph.mmd", format="mermaid")

# Print text structure
print_graph_structure(alice.graph)
```

**Prerequisites for static PNG/SVG visualization (optional):**
```bash
# Install system dependency first
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz graphviz-dev

# Then install the optional Python package
uv pip install -e ".[viz]"
# or with pip
pip install -e ".[viz]"
```

Note: The Streamlit dashboard works without `pygraphviz` - it uses Mermaid diagrams instead!

## LangSmith Observability

This project includes comprehensive LangSmith integration for production-grade observability and LLMOps.

### Setup

1. Get your LangSmith API key from [smith.langchain.com](https://smith.langchain.com)

2. Add to your `.env`:
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your-langsmith-api-key-here
   LANGCHAIN_PROJECT=a2a-conversation
   ```

3. Run your agents - tracing happens automatically!

### What's Traced

**Conversational Agents:**
- `listen_for_message`: Kafka message consumption with timing
- `reason_with_llm`: LLM reasoning with context, turn count, and conversation history
- `send_response`: Message publishing with metadata
- `start_conversation` / `run_agent`: Full conversation lifecycle

**PII Monitor Agent:**
- `check_for_pii`: PII detection analysis with categories checked
- `process_message`: Message processing pipeline with violation counts

**Trace Metadata Includes:**
- Agent names and roles (initiator/listener)
- Turn counts and conversation length
- Message lengths and response times
- PII detection results (types, severity, violations)
- Conversation history context

### Viewing Traces

Once enabled, view your traces at: **https://smith.langchain.com**

You'll see:
- **Full conversation flows** with timing breakdowns
- **LLM calls** with prompts, completions, and token usage
- **Agent decision paths** through the LangGraph state machine
- **PII detection results** with security insights
- **Performance metrics** for each conversation turn

### Advanced Usage

```python
from a2a_conversation.utils.observability import ConversationTracer

tracer = ConversationTracer(project_name="my-custom-project")

# Log custom metrics
tracer.log_turn_metrics(
    agent_name="Alice",
    turn_count=5,
    message_length=128,
    response_time_ms=450.2
)

# Trace custom operations
with tracer.trace_operation("custom_operation", tags=["analysis"]) as outputs:
    # Your code here
    outputs["result"] = "success"
```

### Benefits

- **Debug faster**: See exactly what your agents are thinking and saying
- **Optimize performance**: Identify slow LLM calls and bottlenecks
- **Monitor quality**: Track PII violations and conversation health
- **Collaborate**: Share traces with your team
- **Analyze patterns**: Use LangSmith's analytics to understand agent behavior

### Disabling Tracing

Set `LANGCHAIN_TRACING_V2=false` in your `.env` or remove the variable entirely.

## Tuning knobs
All configuration is via environment variables (see `.env.example`):
- `MAX_TURNS`: how long they chat before touching grass
- `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`: control the LLM behavior
- `KAFKA_BOOTSTRAP_SERVERS`: point to your Kafka cluster
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`: LangSmith observability settings
- Personas: edit `src/a2a_conversation/main.py` → `create_agent_personas()` (pirates? pastry chefs? pirate pastry chefs?)


## Troubleshooting
- "ModuleNotFoundError: langgraph/langchain-openai/kafka-python" → dependencies not installed; run `uv sync` or `pip install`.
- "NoBrokersAvailable" → Kafka isn't up or not on `localhost:9092`. Start Docker container or configure `KAFKA_BOOTSTRAP_SERVERS`.
- "OpenAI Authentication Error" → set `OPENAI_API_KEY` in `.env`.
- Messages not flowing? Ensure both topics are implicitly created by the first `send` (Kafka does this by default in many setups) or pre-create them.
- Python version woes: if 3.14 jokes stop being funny, use 3.11–3.12.
- Check logs: Console output and `logs/a2a_conversation.log` (configurable via `LOG_FILE`).


## FAQ
- Why Kafka for two agents? 
  - Because real systems scale, and because it’s fun. You can split agents across machines, add more listeners, or log every message like a responsible adult.
- Do I need LangGraph? 
  - You don’t need it the way you don’t need seatbelts. It keeps the flow explicit and debuggable.
- Can I change the model provider?
  - Yes. Swap out `ChatOpenAI` for your favorite `langchain`-compatible chat model.


## Contributing
PRs welcome. If your change causes Alice and Bob to discuss the heat death of the universe for 10,000 turns, please also include snacks.


## License
This project is offered as-is with many emojis and few guarantees. Use responsibly and hydrate frequently.