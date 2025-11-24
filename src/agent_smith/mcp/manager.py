"""MCP Client Manager for managing multiple MCP server connections."""

import asyncio
import logging
from typing import Any, Optional

from .client import MCPClient

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Manages multiple MCP server connections.

    This class handles:
    - Registering and starting multiple MCP servers
    - Routing tool calls to the appropriate server
    - Managing server lifecycle
    - Aggregating tools from all servers
    """

    def __init__(self):
        """Initialize the MCP client manager."""
        self.clients: dict[str, MCPClient] = {}
        self._server_tools: dict[str, list[dict[str, Any]]] = {}
        self._server_prompts: dict[str, list[dict[str, Any]]] = {}

    async def register_server(
        self,
        name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> MCPClient:
        """Register and start an MCP server.

        Args:
            name: Unique identifier for the server
            command: Command to execute (e.g., "npx")
            args: Command arguments
            env: Environment variables

        Returns:
            The initialized MCP client

        Raises:
            RuntimeError: If server fails to start
        """
        if name in self.clients:
            logger.warning(f"MCP server {name} already registered")
            return self.clients[name]

        try:
            client = MCPClient(name, command, args, env)
            await client.start()

            # Discover tools and prompts
            tools = await client.list_tools()
            prompts = await client.list_prompts()

            # Cache the discoveries
            self._server_tools[name] = tools
            self._server_prompts[name] = prompts

            self.clients[name] = client

            logger.info(
                f"Registered MCP server '{name}': {len(tools)} tools, {len(prompts)} prompts"
            )
            return client

        except Exception as e:
            logger.error(f"Failed to register MCP server {name}: {e}")
            raise

    async def unregister_server(self, name: str) -> None:
        """Unregister and shut down an MCP server.

        Args:
            name: Server name to unregister
        """
        if name not in self.clients:
            logger.warning(f"MCP server {name} not found")
            return

        try:
            client = self.clients[name]
            await client.shutdown()

            del self.clients[name]
            self._server_tools.pop(name, None)
            self._server_prompts.pop(name, None)

            logger.info(f"Unregistered MCP server: {name}")

        except Exception as e:
            logger.error(f"Error unregistering MCP server {name}: {e}")

    async def call_tool(
        self, server: str, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on a specific MCP server.

        Args:
            server: Server name
            tool: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If server is not registered
            RuntimeError: If tool call fails
        """
        if server not in self.clients:
            raise ValueError(f"MCP server not registered: {server}")

        client = self.clients[server]

        if not client.is_connected:
            raise RuntimeError(f"MCP server {server} is not connected")

        return await client.call_tool(tool, arguments)

    async def get_prompt(
        self, server: str, prompt: str, arguments: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Get a prompt from a specific MCP server.

        Args:
            server: Server name
            prompt: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result

        Raises:
            ValueError: If server is not registered
        """
        if server not in self.clients:
            raise ValueError(f"MCP server not registered: {server}")

        client = self.clients[server]
        return await client.get_prompt(prompt, arguments or {})

    def get_all_tools(self) -> dict[str, list[dict[str, Any]]]:
        """Get all tools from all registered servers.

        Returns:
            Dictionary mapping server names to their tool lists
        """
        return self._server_tools.copy()

    def get_all_prompts(self) -> dict[str, list[dict[str, Any]]]:
        """Get all prompts from all registered servers.

        Returns:
            Dictionary mapping server names to their prompt lists
        """
        return self._server_prompts.copy()

    def get_server_tools(self, server: str) -> list[dict[str, Any]]:
        """Get tools from a specific server.

        Args:
            server: Server name

        Returns:
            List of tool definitions, or empty list if server not found
        """
        return self._server_tools.get(server, [])

    def get_server_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all registered servers.

        Returns:
            Dictionary mapping server names to their status info
        """
        status = {}
        for name, client in self.clients.items():
            status[name] = {
                "connected": client.is_connected,
                "tools_count": len(self._server_tools.get(name, [])),
                "prompts_count": len(self._server_prompts.get(name, [])),
            }
        return status

    async def reload_server(self, name: str) -> None:
        """Reload a specific MCP server (restart and rediscover).

        Args:
            name: Server name to reload
        """
        if name not in self.clients:
            raise ValueError(f"MCP server not registered: {name}")

        # Get the current client config
        old_client = self.clients[name]
        command = old_client.command
        args = old_client.args
        env = old_client.env

        # Unregister and restart
        await self.unregister_server(name)
        await self.register_server(name, command, args, env)

        logger.info(f"Reloaded MCP server: {name}")

    async def reload_all(self) -> None:
        """Reload all MCP servers."""
        server_names = list(self.clients.keys())
        for name in server_names:
            try:
                await self.reload_server(name)
            except Exception as e:
                logger.error(f"Failed to reload server {name}: {e}")

    async def shutdown_all(self) -> None:
        """Shut down all MCP servers."""
        logger.info("Shutting down all MCP servers...")

        # Shutdown all clients
        shutdown_tasks = [
            client.shutdown() for client in self.clients.values()
        ]
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        # Clear all state
        self.clients.clear()
        self._server_tools.clear()
        self._server_prompts.clear()

        logger.info("All MCP servers shut down")

    def list_servers(self) -> list[str]:
        """Get list of registered server names.

        Returns:
            List of server names
        """
        return list(self.clients.keys())

    def has_server(self, name: str) -> bool:
        """Check if a server is registered.

        Args:
            name: Server name

        Returns:
            True if server is registered
        """
        return name in self.clients

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get a specific MCP client by name.

        Args:
            name: Server name

        Returns:
            MCPClient instance or None if not found
        """
        return self.clients.get(name)
