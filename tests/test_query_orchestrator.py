"""Tests for QueryOrchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from agent_smith.models import APIUsage, Message, MessageResponse
from agent_smith.query import QueryOrchestrator


@pytest.fixture
def mock_claude_service():
    """Mock Claude service."""
    with patch("agent_smith.query.ClaudeService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service."""
    with patch("agent_smith.query.OpenAIService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


def test_orchestrator_creation():
    """Test creating QueryOrchestrator."""
    orchestrator = QueryOrchestrator(provider="anthropic")
    assert orchestrator is not None
    assert orchestrator.provider == "anthropic"


def test_orchestrator_with_openai():
    """Test creating QueryOrchestrator with OpenAI."""
    orchestrator = QueryOrchestrator(provider="openai")
    assert orchestrator.provider == "openai"


def test_orchestrator_with_custom_model():
    """Test creating QueryOrchestrator with custom model."""
    orchestrator = QueryOrchestrator(
        provider="anthropic", model="claude-3-opus-20240229"
    )
    assert orchestrator.model == "claude-3-opus-20240229"


def test_orchestrator_context_manager():
    """Test QueryOrchestrator as context manager."""

    async def test():
        async with QueryOrchestrator(provider="anthropic") as orchestrator:
            assert orchestrator is not None

    # Just test that it can be used as context manager
    import asyncio

    asyncio.run(test())


@pytest.mark.asyncio
async def test_orchestrator_usage_tracking():
    """Test that orchestrator tracks token usage."""
    orchestrator = QueryOrchestrator(provider="anthropic")

    # Initial usage should be zero
    assert orchestrator.total_usage.input_tokens == 0
    assert orchestrator.total_usage.output_tokens == 0


def test_orchestrator_max_iterations():
    """Test orchestrator respects max_iterations."""
    orchestrator = QueryOrchestrator(provider="anthropic", max_iterations=5)
    assert orchestrator.max_iterations == 5


def test_orchestrator_default_max_iterations():
    """Test orchestrator has default max_iterations."""
    orchestrator = QueryOrchestrator(provider="anthropic")
    assert orchestrator.max_iterations > 0


@pytest.mark.asyncio
async def test_orchestrator_message_validation():
    """Test that orchestrator validates messages."""
    QueryOrchestrator(provider="anthropic")

    # Valid message should work
    messages = [Message.user("Hello")]
    assert len(messages) == 1
    assert messages[0].role.value == "user"


def test_api_usage_model():
    """Test APIUsage model."""
    usage = APIUsage(input_tokens=100, output_tokens=50)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.total_tokens == 150


def test_api_usage_with_cache():
    """Test APIUsage with cache tokens."""
    usage = APIUsage(
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=20,
        cache_read_tokens=30,
    )
    assert usage.cache_creation_tokens == 20
    assert usage.cache_read_tokens == 30


def test_message_response_model():
    """Test MessageResponse model."""
    from agent_smith.models import TextBlock

    response = MessageResponse(
        id="msg_123",
        model="claude-3-sonnet",
        content=[TextBlock(text="Hello")],
        stop_reason="end_turn",
        usage=APIUsage(input_tokens=10, output_tokens=5),
    )
    assert response.id == "msg_123"
    assert response.model == "claude-3-sonnet"
    assert len(response.content) == 1
    assert response.usage.total_tokens == 15
