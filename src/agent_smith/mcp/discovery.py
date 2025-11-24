"""MCP tool discovery and registration."""

import logging
from pathlib import Path

from agent_smith.config.mcp import MCPServerConfig, load_mcp_config
from agent_smith.config.settings import settings

from .manager import MCPClientManager
from .trust import TrustManager

logger = logging.getLogger(__name__)


async def register_mcp_tools(
    manager: MCPClientManager,
    trust_manager: TrustManager,
    auto_approve: bool = False,
) -> int:
    """Discover and register all configured MCP servers and their tools.

    This function:
    1. Loads MCP server configurations
    2. Checks trust status for each server
    3. Requests approval for untrusted servers
    4. Starts approved servers
    5. Discovers tools from each server

    Args:
        manager: MCP client manager instance
        trust_manager: Trust manager instance
        auto_approve: If True, automatically approve all servers (for testing)

    Returns:
        Number of servers successfully registered
    """
    # Load MCP configurations
    server_configs = load_mcp_config(settings)

    if not server_configs:
        logger.info("No MCP servers configured")
        return 0

    logger.info(f"Found {len(server_configs)} MCP server(s) in configuration")

    registered_count = 0

    # Process each server
    for name, config in server_configs.items():
        try:
            # Skip disabled servers
            if not config.enabled:
                logger.info(f"Skipping disabled MCP server: {name}")
                continue

            # Check trust status
            if not trust_manager.is_trusted(name) or trust_manager.has_config_changed(
                name, config.command, config.args, config.env_keys
            ):
                # Request approval
                approved = await trust_manager.request_approval(
                    server_name=name,
                    command=config.command,
                    args=config.args,
                    env_keys=config.env_keys,
                    auto_approve=auto_approve or config.trusted,
                )

                if not approved:
                    logger.info(f"User denied approval for MCP server: {name}")
                    continue

            # Register the server
            logger.info(f"Registering MCP server: {name}")
            await manager.register_server(
                name=name, command=config.command, args=config.args, env=config.env
            )

            registered_count += 1
            logger.info(f"Successfully registered MCP server: {name}")

        except Exception as e:
            logger.error(f"Failed to register MCP server '{name}': {e}")
            continue

    # Log summary
    if registered_count > 0:
        status = manager.get_server_status()
        total_tools = sum(s["tools_count"] for s in status.values())
        total_prompts = sum(s["prompts_count"] for s in status.values())

        logger.info(
            f"MCP initialization complete: {registered_count} server(s), "
            f"{total_tools} tool(s), {total_prompts} prompt(s)"
        )
    else:
        logger.warning("No MCP servers were registered")

    return registered_count


def get_mcp_tools_for_claude(manager: MCPClientManager) -> list[dict]:
    """Convert MCP tools to Claude-compatible tool definitions.

    Args:
        manager: MCP client manager

    Returns:
        List of tool definitions in Claude's format
    """
    claude_tools = []

    all_tools = manager.get_all_tools()

    for server_name, tools in all_tools.items():
        for tool in tools:
            # Create a unique tool name by prefixing with server name
            unique_name = f"mcp__{server_name}__{tool['name']}"

            # Convert to Claude's tool format
            claude_tool = {
                "name": unique_name,
                "description": (
                    f"[MCP:{server_name}] {tool.get('description', '')}"
                ),
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}}),
            }

            claude_tools.append(claude_tool)

    logger.debug(f"Converted {len(claude_tools)} MCP tools to Claude format")
    return claude_tools


def parse_mcp_tool_name(tool_name: str) -> tuple[str, str] | None:
    """Parse an MCP tool name to extract server and tool name.

    Args:
        tool_name: Tool name in format "mcp__<server>__<tool>"

    Returns:
        Tuple of (server_name, tool_name) or None if not an MCP tool
    """
    if not tool_name.startswith("mcp__"):
        return None

    parts = tool_name[5:].split("__", 1)
    if len(parts) != 2:
        return None

    return parts[0], parts[1]


async def reload_mcp_server(
    manager: MCPClientManager,
    trust_manager: TrustManager,
    server_name: str,
) -> bool:
    """Reload a specific MCP server.

    Args:
        manager: MCP client manager
        trust_manager: Trust manager
        server_name: Name of server to reload

    Returns:
        True if reload was successful
    """
    try:
        # Check if server exists
        if not manager.has_server(server_name):
            logger.error(f"Server not found: {server_name}")
            return False

        # Get current configuration
        server_configs = load_mcp_config(settings)
        if server_name not in server_configs:
            logger.error(f"Server configuration not found: {server_name}")
            return False

        config = server_configs[server_name]

        # Shutdown old server
        await manager.unregister_server(server_name)

        # Check trust
        if not trust_manager.is_trusted(server_name):
            approved = await trust_manager.request_approval(
                server_name=server_name,
                command=config.command,
                args=config.args,
                env_keys=config.env_keys,
            )
            if not approved:
                return False

        # Start new server
        await manager.register_server(
            name=server_name,
            command=config.command,
            args=config.args,
            env=config.env,
        )

        logger.info(f"Successfully reloaded MCP server: {server_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to reload MCP server '{server_name}': {e}")
        return False


def get_mcp_status_summary(manager: MCPClientManager) -> str:
    """Get a human-readable summary of MCP server status.

    Args:
        manager: MCP client manager

    Returns:
        Formatted status string
    """
    status = manager.get_server_status()

    if not status:
        return "No MCP servers registered"

    lines = ["MCP Server Status:", ""]

    for server_name, info in status.items():
        connection_status = "🟢 Connected" if info["connected"] else "🔴 Disconnected"
        lines.append(f"  • {server_name}: {connection_status}")
        lines.append(f"    Tools: {info['tools_count']}, Prompts: {info['prompts_count']}")

    return "\n".join(lines)


def list_available_tools(manager: MCPClientManager) -> str:
    """Get a human-readable list of all available MCP tools.

    Args:
        manager: MCP client manager

    Returns:
        Formatted tools list
    """
    all_tools = manager.get_all_tools()

    if not all_tools:
        return "No MCP tools available"

    lines = ["Available MCP Tools:", ""]

    for server_name, tools in all_tools.items():
        lines.append(f"  {server_name} ({len(tools)} tools):")
        for tool in tools:
            lines.append(f"    • {tool['name']}: {tool.get('description', 'No description')}")
        lines.append("")

    return "\n".join(lines)
