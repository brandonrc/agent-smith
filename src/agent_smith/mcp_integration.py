"""MCP integration initialization for Agent Smith.

This module handles the initialization of MCP servers and registration
of MCP tools with the tool registry.
"""

import asyncio
import logging
from pathlib import Path

from agent_smith.config import AppPaths, settings
from agent_smith.mcp.discovery import register_mcp_tools
from agent_smith.mcp.manager import MCPClientManager
from agent_smith.mcp.trust import TrustManager
from agent_smith.tools import default_tools
from agent_smith.tools.mcp_tool import register_mcp_tools_with_registry

logger = logging.getLogger(__name__)

# Global MCP manager instance
_mcp_manager: MCPClientManager | None = None
_trust_manager: TrustManager | None = None


def get_mcp_manager() -> MCPClientManager | None:
    """Get the global MCP client manager instance.

    Returns:
        MCPClientManager instance or None if not initialized
    """
    return _mcp_manager


def get_trust_manager() -> TrustManager | None:
    """Get the global trust manager instance.

    Returns:
        TrustManager instance or None if not initialized
    """
    return _trust_manager


async def initialize_mcp(auto_approve: bool = False) -> tuple[MCPClientManager, TrustManager]:
    """Initialize MCP system.

    This function:
    1. Creates MCP client manager
    2. Creates trust manager
    3. Discovers and starts configured MCP servers
    4. Registers MCP tools with the tool registry

    Args:
        auto_approve: If True, automatically approve all servers (for testing)

    Returns:
        Tuple of (mcp_manager, trust_manager)
    """
    global _mcp_manager, _trust_manager

    logger.info("Initializing MCP system...")

    try:
        # Create MCP client manager
        _mcp_manager = MCPClientManager()

        # Create trust manager
        trust_file = AppPaths.DATA_DIR / "mcp_trust.json"
        _trust_manager = TrustManager(trust_file)

        # Check if MCP is enabled
        if not settings.get("mcp.enabled", True):
            logger.info("MCP is disabled in settings")
            return _mcp_manager, _trust_manager

        # Register MCP servers and discover tools
        registered_count = await register_mcp_tools(
            _mcp_manager, _trust_manager, auto_approve=auto_approve
        )

        if registered_count > 0:
            # Register MCP tools with the tool registry
            tools_count = register_mcp_tools_with_registry(_mcp_manager, default_tools)
            logger.info(f"MCP initialization complete: {tools_count} tools available")
        else:
            logger.info("No MCP servers were registered")

        return _mcp_manager, _trust_manager

    except Exception as e:
        logger.error(f"Failed to initialize MCP: {e}")
        # Return empty managers rather than failing completely
        if _mcp_manager is None:
            _mcp_manager = MCPClientManager()
        if _trust_manager is None:
            _trust_manager = TrustManager(AppPaths.DATA_DIR / "mcp_trust.json")
        return _mcp_manager, _trust_manager


async def shutdown_mcp() -> None:
    """Shut down all MCP servers and clean up resources."""
    global _mcp_manager

    if _mcp_manager:
        logger.info("Shutting down MCP servers...")
        try:
            await _mcp_manager.shutdown_all()
            logger.info("MCP shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down MCP: {e}")

    _mcp_manager = None


def is_mcp_initialized() -> bool:
    """Check if MCP has been initialized.

    Returns:
        True if MCP manager exists and has servers
    """
    return _mcp_manager is not None and len(_mcp_manager.list_servers()) > 0


def get_mcp_status() -> dict[str, any]:
    """Get current MCP system status.

    Returns:
        Dictionary with MCP status information
    """
    if not _mcp_manager:
        return {
            "initialized": False,
            "servers": [],
            "tools_count": 0,
        }

    server_status = _mcp_manager.get_server_status()

    return {
        "initialized": True,
        "servers": _mcp_manager.list_servers(),
        "server_status": server_status,
        "tools_count": sum(s["tools_count"] for s in server_status.values()),
        "prompts_count": sum(s["prompts_count"] for s in server_status.values()),
    }


# Convenience function for sync context (e.g., CLI commands)
def initialize_mcp_sync(auto_approve: bool = False) -> tuple[MCPClientManager, TrustManager]:
    """Synchronous wrapper for MCP initialization.

    Args:
        auto_approve: If True, automatically approve all servers

    Returns:
        Tuple of (mcp_manager, trust_manager)
    """
    return asyncio.run(initialize_mcp(auto_approve=auto_approve))


def shutdown_mcp_sync() -> None:
    """Synchronous wrapper for MCP shutdown."""
    asyncio.run(shutdown_mcp())
