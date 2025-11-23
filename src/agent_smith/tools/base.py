"""Base classes for tools."""

from abc import ABC, abstractmethod
from typing import Any

from ..models import ToolResult


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool inputs."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given inputs."""
        pass

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        Check if tool requires user permission.

        Override this in tools that perform dangerous operations.

        Args:
            **kwargs: Tool input parameters

        Returns:
            True if permission is required, False otherwise
        """
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        Unregister a tool.

        Args:
            name: Name of tool to unregister
        """
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """
        Get list of all registered tools.

        Returns:
            List of tool instances
        """
        return list(self._tools.values())

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry({len(self)} tools: {list(self._tools.keys())})"
