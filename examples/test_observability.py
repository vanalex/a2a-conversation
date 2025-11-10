"""
Example: Test LangSmith observability integration.

This script demonstrates how to verify your LangSmith setup and view traces.
"""
import os
from a2a_conversation.config.settings import LangSmithConfig
from a2a_conversation.utils.observability import (
    ConversationTracer,
    LANGSMITH_AVAILABLE,
    trace_conversation_method
)


def check_langsmith_config():
    """Check if LangSmith is properly configured."""
    print("=" * 60)
    print("LangSmith Configuration Check")
    print("=" * 60)

    # Check if LangSmith SDK is available
    print(f"LangSmith SDK installed: {LANGSMITH_AVAILABLE}")

    if not LANGSMITH_AVAILABLE:
        print("\n⚠️  LangSmith SDK not available")
        print("The agents will still work, but tracing will be disabled.")
        return False

    # Load configuration
    config = LangSmithConfig.from_env()

    print(f"\nTracing enabled: {config.tracing_enabled}")
    print(f"API key set: {'Yes' if config.api_key else 'No'}")
    print(f"Project: {config.project}")
    print(f"Endpoint: {config.endpoint}")

    if config.tracing_enabled and not config.api_key:
        print("\n⚠️  Tracing enabled but no API key set!")
        print("Set LANGCHAIN_API_KEY in your .env file")
        return False

    if config.tracing_enabled and config.api_key:
        print("\n✅ LangSmith is properly configured!")
        print(f"\nView your traces at: https://smith.langchain.com")
        return True

    print("\n💡 Tracing is disabled")
    print("To enable, set LANGCHAIN_TRACING_V2=true in .env")
    return False


@trace_conversation_method(
    name="example_traced_function",
    tags=["example", "test"]
)
def example_traced_function(message: str) -> dict:
    """Example function with tracing."""
    print(f"\nProcessing: {message}")
    return {
        "message": message,
        "length": len(message),
        "processed": True
    }


def test_tracer():
    """Test the ConversationTracer utility."""
    print("\n" + "=" * 60)
    print("Testing ConversationTracer")
    print("=" * 60)

    tracer = ConversationTracer(project_name="a2a-conversation-test")

    # Test conversation start logging
    print("\n1. Logging conversation start...")
    tracer.log_conversation_start(
        agent_name="TestAgent",
        role="test",
        max_turns=5,
        test_run=True
    )

    # Test turn metrics
    print("2. Logging turn metrics...")
    tracer.log_turn_metrics(
        agent_name="TestAgent",
        turn_count=1,
        message_length=100,
        response_time_ms=250.5,
        test_run=True
    )

    # Test PII detection logging
    print("3. Logging PII detection...")
    tracer.log_pii_detection(
        speaker="TestAgent",
        has_pii=False,
        pii_types=[],
        severity="low",
        message_length=100
    )

    # Test trace context manager
    print("4. Testing trace context manager...")
    with tracer.trace_operation(
        "test_operation",
        tags=["test", "demo"],
        test_run=True
    ) as outputs:
        outputs["result"] = "success"
        outputs["value"] = 42

    # Test conversation end
    print("5. Logging conversation end...")
    tracer.log_conversation_end(
        total_turns=5,
        total_messages=10,
        pii_violations=0,
        duration_seconds=12.5,
        test_run=True
    )

    print("\n✅ All tracer methods executed successfully!")


def test_decorator():
    """Test the tracing decorator."""
    print("\n" + "=" * 60)
    print("Testing Tracing Decorator")
    print("=" * 60)

    result = example_traced_function("Hello, LangSmith!")
    print(f"Result: {result}")

    print("\n✅ Decorator test completed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LangSmith Observability Test Suite")
    print("=" * 60)

    # Check configuration
    is_configured = check_langsmith_config()

    if not LANGSMITH_AVAILABLE:
        print("\n" + "=" * 60)
        print("⚠️  Cannot run tests - LangSmith SDK not available")
        print("All tracing code will gracefully degrade (no errors)")
        print("=" * 60)
        return

    # Run tests
    test_tracer()
    test_decorator()

    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)

    if is_configured:
        print("\n🎉 Check your traces at https://smith.langchain.com")
        print(f"Project: {os.getenv('LANGCHAIN_PROJECT', 'a2a-conversation-test')}")
    else:
        print("\n💡 Set up LangSmith to see traces:")
        print("1. Get API key from https://smith.langchain.com")
        print("2. Add to .env:")
        print("   LANGCHAIN_TRACING_V2=true")
        print("   LANGCHAIN_API_KEY=your-api-key")
        print("3. Run this script again!")


if __name__ == "__main__":
    main()
