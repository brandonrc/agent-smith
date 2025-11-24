"""MCP Client implementation for connecting to a single MCP server."""

import asyncio
import json
import logging
import os
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Manages connection to a single MCP server via stdio.

    This class handles:
    - Starting the MCP server process
    - Initializing the connection
    - Discovering available tools and prompts
    - Executing tool calls
    - Graceful shutdown
    """

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
    ):
        """Initialize MCP client.

        Args:
            name: Unique identifier for this server
            command: Command to execute (e.g., "npx")
            args: Command arguments (e.g., ["-y", "@modelcontextprotocol/server-gitlab"])
            env: Environment variables for the server process
        """
        self.name = name
        self.command = command
        self.args = args
        self.env = {**os.environ, **(env or {})}

        self.session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._tools_cache: list[dict[str, Any]] = []
        self._prompts_cache: list[dict[str, Any]] = []
        self._connected = False

    async def start(self) -> None:
        """Start the MCP server and establish connection."""
        try:
            logger.info(f"Starting MCP server: {self.name}")

            # Create server parameters
            server_params = StdioServerParameters(
                command=self.command, args=self.args, env=self.env
            )

            # Connect to the server
            self._read_stream, self._write_stream = await stdio_client(server_params)

            # Create session
            self.session = ClientSession(self._read_stream, self._write_stream)

            # Initialize the session
            await self.session.__aenter__()

            # Initialize the connection
            await self.session.initialize()

            self._connected = True
            logger.info(f"Successfully connected to MCP server: {self.name}")

        except Exception as e:
            logger.error(f"Failed to start MCP server {self.name}: {e}")
            await self.shutdown()
            raise

    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover available tools from the MCP server.

        Returns:
            List of tool definitions with name, description, and input schema
        """
        if not self.session:
            raise RuntimeError(f"MCP client {self.name} not connected")

        try:
            result = await self.session.list_tools()
            self._tools_cache = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema,
                }
                for tool in result.tools
            ]
            logger.info(
                f"Discovered {len(self._tools_cache)} tools from {self.name}"
            )
            return self._tools_cache

        except Exception as e:
            logger.error(f"Failed to list tools from {self.name}: {e}")
            return []

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError(f"MCP client {self.name} not connected")

        try:
            logger.debug(f"Calling tool {tool_name} on {self.name}")
            result = await self.session.call_tool(tool_name, arguments)

            # Extract content from result
            content_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    content_parts.append(item.text)
                elif hasattr(item, "data"):
                    content_parts.append(str(item.data))

            return {
                "content": "\n".join(content_parts),
                "isError": result.isError if hasattr(result, "isError") else False,
            }

        except Exception as e:
            logger.error(f"Tool call failed for {tool_name} on {self.name}: {e}")
            return {"content": f"Error: {str(e)}", "isError": True}

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Discover available prompts from the MCP server.

        Returns:
            List of prompt definitions
        """
        if not self.session:
            raise RuntimeError(f"MCP client {self.name} not connected")

        try:
            result = await self.session.list_prompts()
            self._prompts_cache = [
                {
                    "name": prompt.name,
                    "description": prompt.description or "",
                    "arguments": [
                        {
                            "name": arg.name,
                            "description": arg.description or "",
                            "required": arg.required,
                        }
                        for arg in (prompt.arguments or [])
                    ],
                }
                for prompt in result.prompts
            ]
            logger.info(
                f"Discovered {len(self._prompts_cache)} prompts from {self.name}"
            )
            return self._prompts_cache

        except Exception as e:
            logger.error(f"Failed to list prompts from {self.name}: {e}")
            return []

    async def get_prompt(
        self, prompt_name: str, arguments: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Execute a prompt on the MCP server.

        Args:
            prompt_name: Name of the prompt
            arguments: Prompt arguments

        Returns:
            Prompt result
        """
        if not self.session:
            raise RuntimeError(f"MCP client {self.name} not connected")

        try:
            result = await self.session.get_prompt(prompt_name, arguments or {})
            return {
                "description": result.description or "",
                "messages": [
                    {"role": msg.role, "content": str(msg.content)}
                    for msg in result.messages
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_name} from {self.name}: {e}")
            return {"description": "", "messages": []}

    async def shutdown(self) -> None:
        """Gracefully shut down the MCP server connection."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None

            self._connected = False
            logger.info(f"Shut down MCP server: {self.name}")

        except Exception as e:
            logger.error(f"Error shutting down MCP server {self.name}: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connected and self.session is not None

    def get_cached_tools(self) -> list[dict[str, Any]]:
        """Get cached tools without making a network call."""
        return self._tools_cache

    def get_cached_prompts(self) -> list[dict[str, Any]]:
        """Get cached prompts without making a network call."""
        return self._prompts_cache
