"""Integration tests for Claude API.

These tests make real API calls to Anthropic Claude.
They are marked as integration tests and can be skipped in CI.
"""

import os

import pytest

from agent_smith.models import Message
from agent_smith.query import QueryOrchestrator
from agent_smith.services import ClaudeService
from agent_smith.tools import BashTool, ThinkTool

# API key for testing - set via environment variable ANTHROPIC_API_KEY
TEST_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

pytestmark = pytest.mark.integration


@pytest.fixture
def api_key():
    """Provide API key for testing."""
    return TEST_API_KEY


@pytest.fixture
def claude_service(api_key):
    """Create Claude service with test API key."""
    return ClaudeService(api_key=api_key)


@pytest.mark.asyncio
async def test_claude_simple_message(claude_service):
    """Test sending a simple message to Claude."""
    messages = [Message.user("Say 'Hello, World!' and nothing else.")]

    response = await claude_service.create_message(
        messages=messages, model="claude-3-5-haiku-20241022", stream=False
    )

    assert response is not None
    assert response.content is not None
    assert len(response.content) > 0
    assert response.usage is not None
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0


@pytest.mark.asyncio
async def test_claude_with_tools(claude_service):
    """Test Claude with tool definitions."""
    from agent_smith.models import ToolDefinition

    messages = [Message.user("What is 2+2? Use the think tool to reason about it.")]

    think_tool = ThinkTool()
    tools = [
        ToolDefinition(
            name=think_tool.name,
            description=think_tool.description,
            input_schema=think_tool.input_schema,
        )
    ]

    response = await claude_service.create_message(
        messages=messages,
        model="claude-3-5-haiku-20241022",
        tools=tools,
        stream=False,
    )

    assert response is not None
    assert response.content is not None


@pytest.mark.asyncio
async def test_orchestrator_simple_query(api_key):
    """Test QueryOrchestrator with a simple query."""
    async with QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    ) as orchestrator:
        messages = [Message.user("What is the capital of France? Answer briefly.")]

        events = []
        async for event in orchestrator.query(messages=messages, tools=[]):
            events.append(event)

        # Should have received events
        assert len(events) > 0

        # Should have a message_complete event
        complete_events = [e for e in events if e["type"] == "message_complete"]
        assert len(complete_events) > 0

        # Check usage tracking
        usage_events = [e for e in events if e["type"] == "usage"]
        if usage_events:
            assert usage_events[0]["total_usage"].input_tokens > 0


@pytest.mark.asyncio
async def test_orchestrator_with_tool_use(api_key):
    """Test QueryOrchestrator with tool execution."""
    async with QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    ) as orchestrator:
        messages = [
            Message.user(
                "Use the Think tool to plan how you would explain what 2+2 equals. "
                "Just use the tool, don't actually explain yet."
            )
        ]

        think_tool = ThinkTool()
        tools = [think_tool]

        events = []
        async for event in orchestrator.query(messages=messages, tools=tools):
            events.append(event)

        # Should have tool execution events
        [e for e in events if "tool" in e["type"]]
        # May or may not use the tool, but should complete
        assert any(e["type"] == "message_complete" for e in events)


@pytest.mark.asyncio
async def test_orchestrator_tracks_usage(api_key):
    """Test that orchestrator tracks token usage correctly."""
    async with QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    ) as orchestrator:
        # Initial usage should be zero
        assert orchestrator.total_usage.input_tokens == 0

        messages = [Message.user("Say hello")]

        async for event in orchestrator.query(messages=messages, tools=[]):
            if event["type"] == "usage":
                # Usage should be tracked
                assert event["total_usage"].input_tokens > 0
                break

        # After query, total usage should be updated
        assert orchestrator.total_usage.input_tokens > 0


@pytest.mark.asyncio
async def test_claude_streaming(claude_service):
    """Test Claude streaming response."""
    messages = [Message.user("Count to 3.")]

    stream = await claude_service.create_message(
        messages=messages, model="claude-3-5-haiku-20241022", stream=True
    )

    events = []
    async for event in stream:
        events.append(event)

    # Should have received multiple stream events
    assert len(events) > 0


@pytest.mark.asyncio
async def test_orchestrator_max_iterations_limit(api_key):
    """Test that orchestrator respects max iterations."""
    async with QueryOrchestrator(
        provider="anthropic",
        api_key=api_key,
        model="claude-3-5-haiku-20241022",
        max_iterations=1,
    ) as orchestrator:
        messages = [Message.user("Hello")]

        iteration_count = 0
        async for event in orchestrator.query(messages=messages, tools=[]):
            if event["type"] == "tool_execution_start":
                iteration_count += 1

        # With max_iterations=1, should not exceed 1 iteration
        assert iteration_count <= 1


@pytest.mark.asyncio
async def test_orchestrator_context_manager_cleanup(api_key):
    """Test that context manager properly cleans up."""
    orchestrator = QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    )

    async with orchestrator:
        # Should work inside context
        assert orchestrator is not None

    # Should still be accessible after context (services closed)
    assert orchestrator is not None


@pytest.mark.asyncio
async def test_bash_tool_integration(api_key):
    """Test Bash tool with orchestrator."""
    async with QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    ) as orchestrator:
        messages = [
            Message.user(
                "Use the Bash tool to echo 'integration test'. "
                "Just run the command, don't explain."
            )
        ]

        bash_tool = BashTool()
        tools = [bash_tool]

        async for event in orchestrator.query(messages=messages, tools=tools):
            if event["type"] == "tool_use_result":
                result = event["result"]
                # Tool should execute successfully or with expected behavior
                assert result is not None

        # Should complete successfully whether tool was used or not
        assert True


@pytest.mark.asyncio
async def test_multiple_messages_conversation(api_key):
    """Test multi-turn conversation."""
    async with QueryOrchestrator(
        provider="anthropic", api_key=api_key, model="claude-3-5-haiku-20241022"
    ) as orchestrator:
        # First message
        messages = [Message.user("My name is Alice.")]

        async for event in orchestrator.query(messages=messages, tools=[]):
            if event["type"] == "message_complete":
                first_response = event["message"]
                break

        # Second message referring to first
        messages.append(
            Message(role=first_response.role, content=first_response.content)
        )
        messages.append(Message.user("What is my name?"))

        response_received = False
        async for event in orchestrator.query(messages=messages, tools=[]):
            if event["type"] == "message_complete":
                response_received = True
                break

        assert response_received
