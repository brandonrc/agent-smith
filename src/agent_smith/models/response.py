"""Response models for LLM API interactions."""

from typing import Any

from pydantic import BaseModel, Field

from .message import ContentBlock, Message, MessageRole


class APIUsage(BaseModel):
    """API usage tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "APIUsage":
        """Create APIUsage from dictionary."""
        if data is None:
            return cls()
        # Handle both dict and Pydantic model
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        return cls(**data)

    def add(self, other: "APIUsage") -> "APIUsage":
        """Add two APIUsage objects together."""
        return APIUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens
            + other.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )


class MessageResponse(BaseModel):
    """Response from LLM API."""

    id: str
    model: str
    content: list[ContentBlock]
    stop_reason: str | None = None
    usage: APIUsage | None = None

    def to_message(self) -> Message:
        """Convert to Message object."""
        return Message(role=MessageRole.ASSISTANT, content=self.content)


class ToolDefinition(BaseModel):
    """Tool definition for LLM."""

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_tool(cls, tool: Any) -> "ToolDefinition":
        """Create ToolDefinition from a tool instance."""
        return cls(
            name=tool.name, description=tool.description, input_schema=tool.input_schema
        )
