# LangSmith Observability Guide

Complete guide to monitoring and debugging your A2A conversation agents with LangSmith.

## Table of Contents
- [Quick Start](#quick-start)
- [What Gets Traced](#what-gets-traced)
- [Trace Structure](#trace-structure)
- [Best Practices](#best-practices)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Get LangSmith API Key

1. Sign up at [smith.langchain.com](https://smith.langchain.com)
2. Navigate to Settings → API Keys
3. Create a new API key

### 2. Configure Environment

Add to your `.env` file:

```env
# Enable tracing
LANGCHAIN_TRACING_V2=true

# Your API key from LangSmith
LANGCHAIN_API_KEY=lsv2_pt_...

# Project name (creates automatically if doesn't exist)
LANGCHAIN_PROJECT=a2a-conversation

# Optional: LangSmith endpoint (defaults to cloud)
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 3. Run Your Agents

```bash
uv run python -m src.a2a_conversation.main
```

### 4. View Traces

Open [smith.langchain.com](https://smith.langchain.com) and navigate to your project!

---

## What Gets Traced

### Conversational Agent Operations

#### 1. **listen_for_message**
- **Type:** Kafka input operation
- **Tags:** `kafka`, `input`
- **Captures:**
  - Message received from Kafka
  - Topic name
  - Turn count
  - Conversation history

#### 2. **reason_with_llm**
- **Type:** LLM reasoning operation
- **Tags:** `llm`, `reasoning`
- **Captures:**
  - Full prompt sent to LLM
  - System message (persona)
  - Conversation context
  - LLM response
  - Token usage
  - Latency
- **Metadata:**
  - Agent name
  - Turn count
  - Conversation history length

#### 3. **send_response**
- **Type:** Kafka output operation
- **Tags:** `kafka`, `output`
- **Captures:**
  - Message sent to Kafka
  - Topic name
  - Turn count increment
  - Updated conversation history

#### 4. **start_conversation / run_agent**
- **Type:** Chain operation
- **Tags:** `agent`, `conversation-starter` or `listener`
- **Captures:**
  - Full conversation lifecycle
  - Initial message
  - All turns
  - Final state
- **Metadata:**
  - Agent name
  - Role (initiator/listener)
  - Max turns

### PII Monitor Agent Operations

#### 1. **check_for_pii**
- **Type:** LLM analysis operation
- **Tags:** `pii-detection`, `security`, `compliance`
- **Captures:**
  - Message analyzed
  - PII detection prompt
  - LLM analysis response
  - Detection results (has_pii, types, severity)
  - Token usage
- **Metadata:**
  - Speaker name
  - Message length
  - Number of PII categories checked

#### 2. **process_message**
- **Type:** Message processing operation
- **Tags:** `kafka`, `message-processing`
- **Captures:**
  - Message processing pipeline
  - PII check results
  - Violation logging
- **Metadata:**
  - Speaker
  - Turn count
  - Total messages monitored
  - Total violations so far

---

## Trace Structure

### Example: Full Conversation Trace Hierarchy

```
start_conversation (Alice)
├── reason_with_llm
│   └── ChatOpenAI.invoke
│       ├── Input: system + user messages
│       └── Output: generated response
├── send_response
│   └── Kafka publish
├── listen_for_message
│   └── Kafka poll
├── reason_with_llm
│   └── ChatOpenAI.invoke
├── send_response
└── ... (repeats until max_turns)
```

### Example: PII Monitor Trace

```
process_message
├── check_for_pii
│   └── ChatOpenAI.invoke (PII detection)
│       ├── Input: PII detection prompt + message
│       └── Output: JSON with PII analysis
└── _log_warning (if violation found)
```

---

## Best Practices

### 1. Use Meaningful Project Names

Organize traces by environment or experiment:

```env
# Development
LANGCHAIN_PROJECT=a2a-conversation-dev

# Staging
LANGCHAIN_PROJECT=a2a-conversation-staging

# Production
LANGCHAIN_PROJECT=a2a-conversation-prod

# Experiments
LANGCHAIN_PROJECT=a2a-conversation-experiment-gpt4o
```

### 2. Add Custom Tags

Use the observability utility to add custom tags:

```python
from a2a_conversation.utils.observability import trace_conversation_method

@trace_conversation_method(
    name="custom_operation",
    tags=["custom", "experiment", "v2"]
)
def my_custom_method(self, state):
    # Your code
    pass
```

### 3. Monitor Key Metrics

Track these metrics in LangSmith:

- **Latency:** Time for each LLM call
- **Token Usage:** Costs per conversation
- **PII Violations:** Security compliance
- **Turn Distribution:** Conversation patterns
- **Error Rates:** Failed operations

### 4. Set Up Alerts

In LangSmith dashboard:
1. Navigate to your project
2. Click "Monitoring" → "Alerts"
3. Create alerts for:
   - High latency (> 3s)
   - High token usage (> 2000 tokens/turn)
   - PII violations detected
   - Error rate spikes

### 5. Use Datasets for Testing

Create test datasets in LangSmith:

```python
from langsmith import Client

client = Client()

# Create dataset
dataset = client.create_dataset("conversation-test-cases")

# Add examples
client.create_examples(
    dataset_id=dataset.id,
    inputs=[
        {"initial_message": "Tell me about the ocean"},
        {"initial_message": "What's your favorite food?"},
    ],
    outputs=[
        {"expected_turns": 10, "expected_pii_violations": 0},
        {"expected_turns": 10, "expected_pii_violations": 0},
    ]
)
```

---

## Advanced Features

### Custom Metrics Logging

```python
from a2a_conversation.utils.observability import ConversationTracer

tracer = ConversationTracer(project_name="a2a-conversation")

# Log conversation start
tracer.log_conversation_start(
    agent_name="Alice",
    role="initiator",
    max_turns=10,
    experiment_id="exp_123",
    model_version="gpt-4"
)

# Log turn metrics
tracer.log_turn_metrics(
    agent_name="Alice",
    turn_count=5,
    message_length=128,
    response_time_ms=450.2,
    tokens_used=256
)

# Log PII detection
tracer.log_pii_detection(
    speaker="Bob",
    has_pii=True,
    pii_types=["Email Address"],
    severity="medium",
    message_length=150
)

# Log conversation end
tracer.log_conversation_end(
    total_turns=10,
    total_messages=20,
    pii_violations=1,
    duration_seconds=45.3,
    success=True
)
```

### Trace Context Manager

```python
with tracer.trace_operation(
    "analyze_sentiment",
    tags=["analysis", "sentiment"],
    agent="Alice",
    turn=5
) as outputs:
    # Perform analysis
    sentiment = analyze_message(message)
    outputs["sentiment"] = sentiment
    outputs["confidence"] = 0.95
```

### Adding Feedback

```python
from a2a_conversation.utils.observability import add_conversation_feedback

# After reviewing a conversation
add_conversation_feedback(
    run_id="abc123",
    score=0.9,
    comment="Great natural conversation flow",
    reviewer="human",
    quality_aspects={
        "coherence": 0.95,
        "engagement": 0.85,
        "safety": 1.0
    }
)
```

---

## Trace Analysis Examples

### 1. Find Slow LLM Calls

In LangSmith:
1. Go to your project
2. Filter by `run_type:llm`
3. Sort by latency (descending)
4. Identify patterns in slow calls

### 2. Analyze PII Violations

Filter traces:
- Tags: `pii-detection`
- Metadata: `has_pii:true`
- Group by: `severity`

### 3. Compare Agent Performance

Create comparison view:
- Filter by `agent:Alice` vs `agent:Bob`
- Compare:
  - Average response time
  - Token usage
  - Message quality (via feedback)

### 4. Debug Failed Conversations

1. Filter by status: `error`
2. Examine trace tree for failure point
3. View full inputs/outputs at failure
4. Check error messages and stack traces

---

## Integration with Streamlit Dashboard

The Streamlit dashboard can be enhanced with LangSmith data:

```python
from langsmith import Client

client = Client()

# Get recent runs
runs = client.list_runs(
    project_name="a2a-conversation",
    limit=100
)

# Display in dashboard
for run in runs:
    st.write(f"Run: {run.name}")
    st.write(f"Latency: {run.latency}ms")
    st.write(f"Tokens: {run.total_tokens}")
```

---

## Troubleshooting

### Traces Not Appearing

**Problem:** No traces show up in LangSmith

**Solutions:**
1. Verify API key is correct:
   ```bash
   echo $LANGCHAIN_API_KEY
   ```

2. Check tracing is enabled:
   ```bash
   echo $LANGCHAIN_TRACING_V2  # Should be "true"
   ```

3. Verify project name:
   ```bash
   echo $LANGCHAIN_PROJECT
   ```

4. Check logs for connection errors:
   ```bash
   grep -i "langsmith\|tracing" logs/a2a_conversation.log
   ```

### High Latency

**Problem:** Traces show high latency

**Solutions:**
1. Check LangSmith endpoint latency
2. Verify network connection
3. Consider local tracing mode (see below)

### Rate Limits

**Problem:** Rate limit errors from LangSmith

**Solutions:**
1. Upgrade LangSmith plan
2. Reduce trace frequency
3. Use sampling:
   ```python
   import random

   # Only trace 10% of operations
   if random.random() < 0.1:
       with tracer.trace_operation(...):
           # operation
   ```

### Local Development Mode

For development without external dependencies:

```env
LANGCHAIN_TRACING_V2=false
```

All tracing decorators gracefully degrade - code still works without LangSmith.

---

## Resources

- **LangSmith Docs:** https://docs.smith.langchain.com
- **API Reference:** https://api.python.langchain.com/en/latest/langsmith/langsmith.html
- **Best Practices:** https://docs.smith.langchain.com/tracing/faq
- **Community:** https://github.com/langchain-ai/langsmith-sdk

---

## Next Steps

1. ✅ Set up LangSmith API key
2. ✅ Run conversations and view traces
3. 📊 Create custom dashboards
4. 🔔 Set up monitoring alerts
5. 📈 Build evaluation datasets
6. 🎯 Optimize based on insights

Happy tracing! 🚀
