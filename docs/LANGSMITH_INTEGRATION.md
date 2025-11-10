# LangSmith Integration - Technical Documentation

Complete technical documentation for the LangSmith observability integration in the A2A Conversation project.

## Architecture Overview

The LangSmith integration provides comprehensive observability across three main components:

1. **ConversationalAgent** - Traces LLM reasoning and message flow
2. **PIIMonitorAgent** - Traces PII detection and security compliance
3. **ObservabilityUtils** - Custom metrics and trace management

## Implementation Details

### 1. Configuration Layer

**File:** `src/a2a_conversation/config/settings.py`

```python
@dataclass
class LangSmithConfig:
    """LangSmith observability configuration."""
    tracing_enabled: bool = False
    endpoint: str = "https://api.smith.langchain.com"
    api_key: str = ""
    project: str = "a2a-conversation"

    def setup(self) -> None:
        """Set up LangSmith tracing environment variables."""
        if self.tracing_enabled and self.api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = self.endpoint
            os.environ["LANGCHAIN_API_KEY"] = self.api_key
            os.environ["LANGCHAIN_PROJECT"] = self.project
```

**Environment Variables:**
- `LANGCHAIN_TRACING_V2` - Enable/disable tracing
- `LANGCHAIN_API_KEY` - LangSmith API key
- `LANGCHAIN_PROJECT` - Project name for organizing traces
- `LANGCHAIN_ENDPOINT` - API endpoint (defaults to cloud)

### 2. Agent Instrumentation

#### ConversationalAgent Tracing

**File:** `src/a2a_conversation/agents/conversational_agent.py`

**Traced Methods:**

1. **listen_for_message**
   ```python
   @traceable(name="listen_for_message", tags=["kafka", "input"])
   def listen_for_message(self, state: ConversationState) -> ConversationState:
       # Traces Kafka message consumption
       # Captures: topic, message, turn_count, history
   ```

2. **reason_with_llm**
   ```python
   @traceable(
       name="reason_with_llm",
       tags=["llm", "reasoning"],
       metadata={"agent_type": "conversational"}
   )
   def reason_with_llm(self, state: ConversationState) -> ConversationState:
       # Traces LLM invocation with full context
       # Metadata: agent_name, turn_count, conversation_length
   ```

3. **send_response**
   ```python
   @traceable(name="send_response", tags=["kafka", "output"])
   def send_response(self, state: ConversationState) -> ConversationState:
       # Traces message publishing to Kafka
       # Captures: message, topic, updated state
   ```

4. **start_conversation / run**
   ```python
   @traceable(
       name="start_conversation",
       run_type="chain",
       tags=["agent", "conversation-starter"]
   )
   def start_conversation(self, initial_message: str) -> None:
       # Traces entire conversation lifecycle
       # Metadata: agent_name, role, initial_message
   ```

#### PIIMonitorAgent Tracing

**File:** `src/a2a_conversation/agents/pii_monitor_agent.py`

**Traced Methods:**

1. **check_for_pii**
   ```python
   @traceable(
       name="check_for_pii",
       run_type="llm",
       tags=["pii-detection", "security", "compliance"],
       metadata={"agent_type": "pii_monitor"}
   )
   def check_for_pii(self, message: str, speaker: str) -> Optional[Dict]:
       # Traces PII detection LLM call
       # Metadata: speaker, message_length, pii_categories_checked
   ```

2. **process_message**
   ```python
   @traceable(
       name="process_message",
       tags=["kafka", "message-processing"],
   )
   def process_message(self, data: Dict) -> None:
       # Traces message processing pipeline
       # Metadata: speaker, turn_count, total_messages, violations
   ```

### 3. Observability Utilities

**File:** `src/a2a_conversation/utils/observability.py`

#### ConversationTracer Class

High-level API for logging conversation metrics:

```python
class ConversationTracer:
    """Utility class for tracing conversation metrics and events."""

    def __init__(self, project_name: str = "a2a-conversation"):
        self.client = Client() if LANGSMITH_AVAILABLE else None

    def log_conversation_start(self, agent_name, role, max_turns, **metadata):
        """Log conversation initialization"""

    def log_turn_metrics(self, agent_name, turn_count, message_length,
                         response_time_ms, **metadata):
        """Log per-turn performance metrics"""

    def log_pii_detection(self, speaker, has_pii, pii_types, severity,
                          message_length):
        """Log PII detection results"""

    def log_conversation_end(self, total_turns, total_messages,
                            pii_violations, duration_seconds, **metadata):
        """Log conversation summary"""

    @contextmanager
    def trace_operation(self, operation_name, tags=None, **metadata):
        """Context manager for custom operation tracing"""
```

#### Helper Functions

```python
def get_trace_url(run_id: str) -> Optional[str]:
    """Get LangSmith URL for a trace"""

def add_conversation_feedback(run_id, score, comment=None, **metadata):
    """Add human feedback to traces"""

def trace_conversation_method(name=None, tags=None, **trace_kwargs):
    """Decorator for tracing custom methods"""
```

### 4. Main Application Integration

**File:** `src/a2a_conversation/main.py`

```python
def main() -> None:
    # Load configurations
    langsmith_config = LangSmithConfig.from_env()

    # Setup LangSmith observability
    langsmith_config.setup()

    # Log status
    if langsmith_config.tracing_enabled and langsmith_config.api_key:
        logger.info(f"LangSmith tracing: ENABLED")
        logger.info(f"View traces at: https://smith.langchain.com")
    else:
        logger.info("LangSmith tracing: DISABLED")
```

## Trace Data Structure

### Trace Hierarchy Example

```
RUN: start_conversation (Alice)
├── METADATA
│   ├── agent_name: "Alice"
│   ├── role: "initiator"
│   └── initial_message: "I just got back..."
│
├── SPAN: reason_with_llm
│   ├── METADATA
│   │   ├── agent_name: "Alice"
│   │   ├── turn_count: 0
│   │   └── conversation_length: 0
│   │
│   └── LLM: ChatOpenAI.invoke
│       ├── INPUT
│       │   ├── System: "You are Alice..."
│       │   └── Human: "Recent conversation..."
│       │
│       ├── OUTPUT
│       │   └── "That sounds amazing! What did..."
│       │
│       └── METADATA
│           ├── model: "gpt-4"
│           ├── temperature: 0.8
│           ├── total_tokens: 256
│           └── latency_ms: 450.2
│
├── SPAN: send_response
│   └── OUTPUT: Kafka publish success
│
├── SPAN: listen_for_message
│   └── INPUT: Message from Bob
│
└── ... (continues for all turns)
```

### Metadata Captured

**Per Agent Run:**
- `agent_name`: Agent identifier (Alice/Bob/PII-Monitor)
- `role`: Agent role (initiator/listener/monitor)
- `turn_count`: Current conversation turn
- `max_turns`: Maximum allowed turns
- `conversation_length`: Number of messages in history

**Per LLM Call:**
- `model`: LLM model name
- `temperature`: Model temperature setting
- `total_tokens`: Token usage
- `prompt_tokens`: Input tokens
- `completion_tokens`: Output tokens
- `latency_ms`: Response time in milliseconds

**Per PII Check:**
- `speaker`: Message speaker
- `message_length`: Characters in message
- `pii_categories_checked`: Number of PII types checked
- `has_pii`: Boolean detection result
- `pii_types`: List of detected PII types
- `severity`: Violation severity (low/medium/high)

## Performance Considerations

### Overhead

**Minimal Performance Impact:**
- LangSmith tracing adds ~10-20ms per traced operation
- Async background uploading prevents blocking
- Graceful degradation if LangSmith unavailable

**Token Usage:**
- No additional tokens consumed
- Traces don't affect LLM calls
- Metadata-only overhead

### Best Practices

1. **Use Appropriate Sampling in Production**
   ```python
   import random

   # Trace 10% of conversations
   if random.random() < 0.1:
       # Enable tracing for this conversation
       os.environ["LANGCHAIN_TRACING_V2"] = "true"
   ```

2. **Batch Metrics Logging**
   ```python
   # Log multiple metrics at conversation end
   # Rather than per-turn logging
   ```

3. **Use Tags for Filtering**
   ```python
   # Tag by experiment, version, environment
   @traceable(tags=["experiment-v2", "gpt-4", "production"])
   ```

## Error Handling

All tracing code includes graceful error handling:

```python
try:
    run_tree = get_current_run_tree()
    if run_tree:
        run_tree.metadata = {...}
except Exception:
    pass  # Tracing not enabled or available
```

**Benefits:**
- Application continues if LangSmith unavailable
- No crashes from tracing errors
- Optional dependency pattern

## Testing

### Unit Tests

**File:** `examples/test_observability.py`

```bash
# Test observability configuration and utilities
uv run python examples/test_observability.py
```

**Tests:**
1. Configuration check
2. Tracer utility methods
3. Decorator functionality
4. Graceful degradation

### Integration Tests

```bash
# Run agents with tracing enabled
LANGCHAIN_TRACING_V2=true uv run python -m src.a2a_conversation.main

# Verify traces at https://smith.langchain.com
```

## Troubleshooting

### Common Issues

**1. Traces Not Appearing**

Check:
```bash
# Verify environment variables
echo $LANGCHAIN_TRACING_V2
echo $LANGCHAIN_API_KEY
echo $LANGCHAIN_PROJECT

# Check logs
grep -i langsmith logs/a2a_conversation.log
```

**2. Import Errors**

LangSmith SDK is required:
```bash
# Verify installation
uv pip list | grep langsmith

# Should show: langsmith==0.x.x
```

**3. Authentication Errors**

Verify API key:
```python
from langsmith import Client
client = Client()  # Should not raise error
```

## Monitoring Dashboard

### Key Metrics to Track

1. **Performance Metrics**
   - Average LLM latency per agent
   - Token usage per conversation
   - Messages per second throughput

2. **Quality Metrics**
   - Conversation completion rate
   - Average conversation length
   - User feedback scores

3. **Security Metrics**
   - PII violations per 1000 messages
   - Violation severity distribution
   - Speaker violation patterns

4. **Cost Metrics**
   - Total tokens per day/week/month
   - Cost per conversation
   - Model usage distribution

### Creating Custom Dashboards

In LangSmith web UI:
1. Navigate to project
2. Click "Dashboards" → "New Dashboard"
3. Add widgets for key metrics
4. Share with team

## Future Enhancements

Potential improvements:

1. **Automatic Feedback Collection**
   ```python
   # Auto-score conversations based on metrics
   if no_pii_violations and avg_response_time < 1000:
       score = 1.0
   ```

2. **A/B Testing Integration**
   ```python
   # Tag traces by experiment variant
   @traceable(tags=[f"variant-{variant_id}"])
   ```

3. **Custom Metrics**
   ```python
   # Track domain-specific metrics
   tracer.log_domain_metric(
       metric_name="conversation_coherence",
       value=0.95
   )
   ```

4. **Real-time Alerts**
   - High latency detection
   - PII violation alerts
   - Error rate monitoring

## References

- **LangSmith Documentation:** https://docs.smith.langchain.com
- **Python SDK:** https://github.com/langchain-ai/langsmith-sdk
- **Tracing Guide:** https://docs.smith.langchain.com/tracing
- **Best Practices:** https://docs.smith.langchain.com/tracing/faq

---

**Last Updated:** 2025-11-10
**Version:** 1.0.0
**Maintainer:** A2A Conversation Team
