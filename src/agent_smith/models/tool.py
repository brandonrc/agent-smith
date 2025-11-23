"""Tool-related models."""

from typing import Any, Protocol

from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base class for tool inputs."""

    pass


class ToolResult(BaseModel):
    """Result from tool execution."""

    content: str | list[dict[str, Any]]
    is_error: bool = False

    @classmethod
    def success(cls, content: str | list[dict[str, Any]]) -> "ToolResult":
        """Create success result."""
        return cls(content=content, is_error=False)

    @classmethod
    def error(cls, error_message: str) -> "ToolResult":
        """Create error result."""
        return cls(content=error_message, is_error=True)


class Tool(Protocol):
    """Protocol for tool implementations."""

    @property
    def name(self) -> str:
        """Tool name for LLM."""
        ...

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool inputs."""
        ...

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given inputs."""
        ...

    async def requires_permission(self, **kwargs: Any) -> bool:
        """Check if tool requires user permission."""
        return False


class ToolDefinition(BaseModel):
    """Tool definition for LLM API."""

    name: str
    description: str
    input_schema: dict[str, Any]

    @classmethod
    def from_tool(cls, tool: Tool) -> "ToolDefinition":
        """Create definition from tool instance."""
        return cls(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
        )
