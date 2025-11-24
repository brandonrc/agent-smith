"""MCP Tool wrapper for integrating MCP server tools with Agent Smith."""

import logging
from typing import Any

from agent_smith.mcp.discovery import parse_mcp_tool_name
from agent_smith.mcp.manager import MCPClientManager
from agent_smith.models import ToolResult

from .base import BaseTool

logger = logging.getLogger(__name__)


class MCPTool(BaseTool):
    """Wraps an MCP server tool as an Agent Smith tool.

    This class provides a bridge between MCP servers and Agent Smith's
    tool system, allowing Claude to use tools from external MCP servers
    like GitLab, Jira, etc.
    """

    def __init__(
        self,
        manager: MCPClientManager,
        server_name: str,
        tool_definition: dict[str, Any],
    ):
        """Initialize MCP tool wrapper.

        Args:
            manager: MCP client manager instance
            server_name: Name of the MCP server providing this tool
            tool_definition: Tool definition from MCP server
        """
        self._manager = manager
        self._server_name = server_name
        self._tool_definition = tool_definition

        # Create unique tool name with server prefix
        self._name = f"mcp__{server_name}__{tool_definition['name']}"

        # Add server context to description
        base_description = tool_definition.get("description", "")
        self._description = f"[MCP:{server_name}] {base_description}"

        # Store input schema
        self._input_schema = tool_definition.get(
            "inputSchema", {"type": "object", "properties": {}}
        )

        logger.debug(f"Created MCP tool wrapper: {self._name}")

    @property
    def name(self) -> str:
        """Tool name in format: mcp__<server>__<tool>."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description with MCP server context."""
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool inputs from MCP server."""
        return self._input_schema

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the MCP tool.

        Args:
            **kwargs: Tool arguments as defined in input_schema

        Returns:
            ToolResult with the execution result
        """
        # Parse the tool name to get server and tool name
        parsed = parse_mcp_tool_name(self._name)
        if not parsed:
            return ToolResult.error(f"Invalid MCP tool name: {self._name}")

        server_name, tool_name = parsed

        try:
            logger.info(f"Executing MCP tool: {tool_name} on server: {server_name}")

            # Call the tool via the MCP manager
            result = await self._manager.call_tool(
                server=server_name, tool=tool_name, arguments=kwargs
            )

            # Check if the result indicates an error
            is_error = result.get("isError", False)
            content = result.get("content", "")

            if is_error:
                logger.warning(f"MCP tool {tool_name} returned error: {content}")
                return ToolResult.error(content)

            logger.debug(f"MCP tool {tool_name} executed successfully")
            return ToolResult.success(content)

        except ValueError as e:
            # Server not found or not registered
            error_msg = f"MCP server error: {str(e)}"
            logger.error(error_msg)
            return ToolResult.error(error_msg)

        except Exception as e:
            # Other execution errors
            error_msg = f"Failed to execute MCP tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return ToolResult.error(error_msg)

    async def requires_permission(self, **kwargs: Any) -> bool:
        """MCP tools don't require additional permission.

        Permission is already handled at the server level via the
        trust manager during server registration.

        Args:
            **kwargs: Tool input parameters

        Returns:
            False - permission handled at server level
        """
        return False

    @property
    def server_name(self) -> str:
        """Get the name of the MCP server providing this tool."""
        return self._server_name

    @property
    def original_tool_name(self) -> str:
        """Get the original tool name from the MCP server."""
        return self._tool_definition["name"]

    def __repr__(self) -> str:
        """String representation of MCPTool."""
        return (
            f"MCPTool(server={self._server_name!r}, "
            f"tool={self.original_tool_name!r})"
        )


def register_mcp_tools_with_registry(
    manager: MCPClientManager, registry
) -> int:
    """Register all MCP tools with the tool registry.

    Args:
        manager: MCP client manager with connected servers
        registry: Tool registry to register tools with

    Returns:
        Number of tools registered
    """
    all_tools = manager.get_all_tools()
    count = 0

    for server_name, tools in all_tools.items():
        for tool_def in tools:
            try:
                mcp_tool = MCPTool(manager, server_name, tool_def)
                registry.register(mcp_tool)
                count += 1
                logger.debug(f"Registered MCP tool: {mcp_tool.name}")
            except Exception as e:
                logger.error(
                    f"Failed to register MCP tool {tool_def.get('name')}: {e}"
                )

    logger.info(f"Registered {count} MCP tools with tool registry")
    return count


def unregister_mcp_tools_from_registry(
    manager: MCPClientManager, registry, server_name: str | None = None
) -> int:
    """Unregister MCP tools from the tool registry.

    Args:
        manager: MCP client manager
        registry: Tool registry to unregister tools from
        server_name: If provided, only unregister tools from this server

    Returns:
        Number of tools unregistered
    """
    count = 0

    # Get all registered tools
    all_tools = registry.list_tools()

    for tool in all_tools:
        if isinstance(tool, MCPTool):
            # If server_name is specified, only unregister that server's tools
            if server_name is None or tool.server_name == server_name:
                registry.unregister(tool.name)
                count += 1
                logger.debug(f"Unregistered MCP tool: {tool.name}")

    logger.info(f"Unregistered {count} MCP tools from tool registry")
    return count
