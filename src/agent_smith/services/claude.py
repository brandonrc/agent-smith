"""Anthropic Claude API client."""

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import (
    Message as AnthropicMessage,
)
from anthropic.types import (
    MessageStreamEvent,
)

from ..config import get_api_key, settings
from ..models import APIUsage, ContentBlock, Message, MessageResponse, ToolDefinition


class ClaudeService:
    """Service for interacting with Anthropic Claude API."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key. If not provided, will be loaded from config.
        """
        self.api_key = api_key or get_api_key("anthropic")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set it with 'smith config set anthropic_api_key YOUR_KEY' "
                "or environment variable SMITH_ANTHROPIC_API_KEY"
            )

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.base_url = settings.get("anthropic.base_url", "https://api.anthropic.com")
        self.api_version = settings.get("anthropic.api_version", "2023-06-01")
        self.timeout = settings.get("anthropic.timeout", 600.0)

    async def create_message(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[ToolDefinition] | None = None,
        stream: bool = False,
    ) -> MessageResponse | AsyncIterator[MessageStreamEvent]:
        """
        Create a message with Claude.

        Args:
            messages: List of messages in conversation
            model: Model name (defaults to settings)
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Available tools
            stream: Whether to stream response

        Returns:
            MessageResponse or async iterator of stream events
        """
        model = model or settings.get("large_model", "claude-sonnet-4-5-20250929")
        max_tokens = max_tokens or settings.get("anthropic.max_tokens", 8192)
        temperature = temperature or settings.get("anthropic.temperature", 1.0)

        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages(messages)

        # Convert tools to Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in tools
            ]

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            kwargs["system"] = system

        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        if stream:
            return self._stream_message(**kwargs)
        else:
            response = await self.client.messages.create(**kwargs)
            return self._convert_response(response)

    async def _stream_message(self, **kwargs: Any) -> AsyncIterator[MessageStreamEvent]:
        """Stream message response."""
        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                yield event

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert internal Message objects to Anthropic format."""
        result = []
        for msg in messages:
            anthropic_msg: dict[str, Any] = {"role": msg.role.value}

            if isinstance(msg.content, str):
                anthropic_msg["content"] = msg.content
            else:
                # Convert content blocks
                content_blocks = []
                for block in msg.content:
                    if isinstance(block, dict):
                        content_blocks.append(block)
                    else:
                        content_blocks.append(block.model_dump())
                anthropic_msg["content"] = content_blocks

            result.append(anthropic_msg)

        return result

    def _convert_response(self, response: AnthropicMessage) -> MessageResponse:
        """Convert Anthropic response to internal format."""
        # Convert content blocks
        content_blocks: list[ContentBlock] = []
        for block in response.content:
            block_dict = {
                "type": block.type,
            }

            if hasattr(block, "text"):
                block_dict["text"] = block.text
            elif hasattr(block, "id"):  # ToolUseBlock
                block_dict["id"] = block.id
                block_dict["name"] = block.name
                block_dict["input"] = block.input

            content_blocks.append(block_dict)  # type: ignore

        # Extract usage
        usage = APIUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
            cache_read_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            ),
        )

        return MessageResponse(
            id=response.id,
            role="assistant",  # type: ignore
            content=content_blocks,  # type: ignore
            model=response.model,
            stop_reason=response.stop_reason,
            stop_sequence=response.stop_sequence,
            usage=usage.model_dump(),
        )

    async def count_tokens(self, text: str, model: str | None = None) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for
            model: Model to use for counting

        Returns:
            Number of tokens
        """
        model = model or settings.get("large_model", "claude-sonnet-4-5-20250929")

        # Use Anthropic's token counting
        # Note: This is an approximation - actual API might differ
        result = await self.client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )

        return result.input_tokens

    async def close(self) -> None:
        """Close the API client."""
        await self.client.close()

    async def __aenter__(self) -> "ClaudeService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
