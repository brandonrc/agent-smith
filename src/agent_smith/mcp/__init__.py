"""Model Context Protocol (MCP) integration for Agent Smith.

This module provides MCP client functionality to connect to external
MCP servers (GitLab, Jira, databases, etc.) and expose their tools
to the AI assistant.
"""

from .client import MCPClient
from .manager import MCPClientManager
from .discovery import register_mcp_tools
from .trust import TrustManager

__all__ = [
    "MCPClient",
    "MCPClientManager",
    "register_mcp_tools",
    "TrustManager",
]
