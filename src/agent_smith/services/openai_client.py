"""OpenAI API client."""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from ..config import get_api_key, settings
from ..models import APIUsage, ContentBlock, Message, MessageResponse, ToolDefinition


class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """
        Initialize OpenAI service.

        Args:
            api_key: OpenAI API key. If not provided, will be loaded from config.
            base_url: Base URL for API. If not provided, uses default.
        """
        self.api_key = api_key or get_api_key("openai")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set it with 'smith config set openai_api_key YOUR_KEY' "
                "or environment variable SMITH_OPENAI_API_KEY"
            )

        self.base_url = base_url or settings.get(
            "openai.base_url", "https://api.openai.com/v1"
        )
        self.timeout = settings.get("openai.timeout", 600.0)

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def create_message(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[ToolDefinition] | None = None,
        stream: bool = False,
    ) -> MessageResponse | AsyncIterator[ChatCompletionChunk]:
        """
        Create a message with OpenAI.

        Args:
            messages: List of messages in conversation
            model: Model name (defaults to settings)
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Available tools
            stream: Whether to stream response

        Returns:
            MessageResponse or async iterator of stream chunks
        """
        model = model or settings.get("large_model", "gpt-4o")
        max_tokens = max_tokens or settings.get("openai.max_tokens", 8192)
        temperature = temperature or settings.get("openai.temperature", 1.0)

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages, system)

        # Convert tools to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in tools
            ]

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        if stream:
            return self._stream_message(**kwargs)
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return self._convert_response(response)

    async def _stream_message(
        self, **kwargs: Any
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream message response."""
        kwargs["stream"] = True
        stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk

    def _convert_messages(
        self, messages: list[Message], system: str | None = None
    ) -> list[ChatCompletionMessageParam]:
        """Convert internal Message objects to OpenAI format."""
        result: list[ChatCompletionMessageParam] = []

        # Add system message if provided
        if system:
            result.append({"role": "system", "content": system})

        for msg in messages:
            openai_msg: ChatCompletionMessageParam

            if isinstance(msg.content, str):
                openai_msg = {
                    "role": msg.role.value,  # type: ignore
                    "content": msg.content,
                }
            else:
                # Convert content blocks to OpenAI format
                # OpenAI uses different structure for tool calls
                content_parts = []
                tool_calls = []

                for block in msg.content:
                    block_dict = (
                        block if isinstance(block, dict) else block.model_dump()
                    )

                    if block_dict["type"] == "text":
                        content_parts.append(block_dict["text"])
                    elif block_dict["type"] == "tool_use":
                        # OpenAI format for tool calls
                        tool_calls.append(
                            {
                                "id": block_dict["id"],
                                "type": "function",
                                "function": {
                                    "name": block_dict["name"],
                                    "arguments": str(block_dict["input"]),
                                },
                            }
                        )
                    elif block_dict["type"] == "tool_result":
                        # OpenAI format for tool results
                        result.append(
                            {
                                "role": "tool",
                                "tool_call_id": block_dict["tool_use_id"],
                                "content": (
                                    block_dict["content"]
                                    if isinstance(block_dict["content"], str)
                                    else str(block_dict["content"])
                                ),
                            }
                        )
                        continue

                if msg.role.value == "assistant" and tool_calls:
                    openai_msg = {
                        "role": "assistant",
                        "content": "\n".join(content_parts) if content_parts else None,
                        "tool_calls": tool_calls,  # type: ignore
                    }
                else:
                    openai_msg = {
                        "role": msg.role.value,  # type: ignore
                        "content": "\n".join(content_parts),
                    }

            result.append(openai_msg)

        return result

    def _convert_response(self, response: ChatCompletion) -> MessageResponse:
        """Convert OpenAI response to internal format."""
        choice = response.choices[0]
        message = choice.message

        # Convert content blocks
        content_blocks: list[ContentBlock] = []

        # Add text content
        if message.content:
            content_blocks.append({"type": "text", "text": message.content})  # type: ignore

        # Add tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                content_blocks.append(  # type: ignore
                    {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": tool_call.function.arguments,
                    }
                )

        # Extract usage
        usage = APIUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

        return MessageResponse(
            id=response.id,
            role="assistant",  # type: ignore
            content=content_blocks,  # type: ignore
            model=response.model,
            stop_reason=choice.finish_reason,
            usage=usage.model_dump(),
        )

    async def close(self) -> None:
        """Close the API client."""
        await self.client.close()

    async def __aenter__(self) -> "OpenAIService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
