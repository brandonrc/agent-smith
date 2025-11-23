"""Message models for LLM communication."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"


class TextBlock(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str


class ImageBlock(BaseModel):
    """Image content block."""

    type: Literal["image"] = "image"
    source: dict[str, Any]


class ToolUseBlock(BaseModel):
    """Tool use block from assistant."""

    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    """Tool result block from user."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | list[dict[str, Any]]
    is_error: bool = False


# Union of all content block types
ContentBlock = TextBlock | ImageBlock | ToolUseBlock | ToolResultBlock


class Message(BaseModel):
    """Message in conversation."""

    role: MessageRole
    content: str | list[ContentBlock]

    def get_text(self) -> str:
        """Extract text content from message."""
        if isinstance(self.content, str):
            return self.content

        texts = []
        for block in self.content:
            if isinstance(block, TextBlock):
                texts.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))

        return "\n".join(texts)

    def get_tool_uses(self) -> list[ToolUseBlock]:
        """Extract tool use blocks from message."""
        if isinstance(self.content, str):
            return []

        tools = []
        for block in self.content:
            if isinstance(block, ToolUseBlock):
                tools.append(block)
            elif isinstance(block, dict) and block.get("type") == "tool_use":
                tools.append(
                    ToolUseBlock(
                        id=block["id"],
                        name=block["name"],
                        input=block["input"],
                    )
                )

        return tools

    def has_tool_use(self) -> bool:
        """Check if message contains tool use."""
        return len(self.get_tool_uses()) > 0

    @classmethod
    def user(cls, content: str | list[ContentBlock]) -> "Message":
        """Create user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str | list[ContentBlock]) -> "Message":
        """Create assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)


class StreamEvent(BaseModel):
    """Streaming event from LLM."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Response from LLM API."""

    id: str
    role: MessageRole
    content: list[ContentBlock]
    model: str
    stop_reason: str | None = None
    stop_sequence: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)

    def to_message(self) -> Message:
        """Convert to Message object."""
        return Message(role=self.role, content=self.content)
