"""MCP configuration loader and models."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dynaconf import Dynaconf

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server.

    Attributes:
        name: Unique identifier for the server
        type: Connection type ("stdio" or "sse")
        command: Command to execute
        args: Command arguments
        env: Environment variables for the server
        enabled: Whether the server should be started
        trusted: Whether the server has been approved by user
        url: Server URL (for SSE-based servers)
    """

    name: str
    type: str
    command: str
    args: list[str]
    env: dict[str, str]
    enabled: bool
    trusted: bool
    url: str | None = None

    @property
    def env_keys(self) -> list[str]:
        """Get list of environment variable keys (without values)."""
        return list(self.env.keys())


def load_mcp_config(settings: Dynaconf) -> dict[str, MCPServerConfig]:
    """Load MCP server configurations from settings.

    Args:
        settings: Dynaconf settings instance

    Returns:
        Dictionary mapping server names to their configurations
    """
    mcp_servers = {}

    try:
        # Check if MCP is enabled globally
        if not settings.get("mcp.enabled", True):
            logger.info("MCP is disabled in settings")
            return mcp_servers

        # Load server configurations
        servers_config = settings.get("mcp.servers", {})

        if not servers_config:
            logger.info("No MCP servers configured")
            return mcp_servers

        # Parse each server configuration
        for name, server_cfg in servers_config.items():
            try:
                # Validate required fields
                if not isinstance(server_cfg, dict):
                    logger.warning(f"Invalid config for MCP server '{name}': not a dict")
                    continue

                if "command" not in server_cfg or "args" not in server_cfg:
                    logger.warning(
                        f"MCP server '{name}' missing required fields (command, args)"
                    )
                    continue

                # Create server config
                config = MCPServerConfig(
                    name=name,
                    type=server_cfg.get("type", "stdio"),
                    command=server_cfg["command"],
                    args=server_cfg["args"],
                    env=server_cfg.get("env", {}),
                    enabled=server_cfg.get("enabled", True),
                    trusted=server_cfg.get("trusted", False),
                    url=server_cfg.get("url"),
                )

                mcp_servers[name] = config
                logger.debug(f"Loaded MCP server config: {name}")

            except Exception as e:
                logger.error(f"Failed to parse MCP server config for '{name}': {e}")
                continue

        logger.info(f"Loaded {len(mcp_servers)} MCP server configurations")

    except Exception as e:
        logger.error(f"Failed to load MCP configurations: {e}")

    return mcp_servers


def get_example_config() -> dict[str, Any]:
    """Get an example MCP configuration for documentation.

    Returns:
        Example configuration dictionary
    """
    return {
        "mcp": {
            "enabled": True,
            "servers": {
                "gitlab": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-gitlab"],
                    "env": {
                        "GITLAB_TOKEN": "glpat-your-token-here",
                        "GITLAB_URL": "https://gitlab.com",
                    },
                    "enabled": True,
                    "trusted": False,
                },
                "jira": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-jira"],
                    "env": {
                        "JIRA_URL": "https://your-company.atlassian.net",
                        "JIRA_EMAIL": "your-email@company.com",
                        "JIRA_API_TOKEN": "your-api-token",
                    },
                    "enabled": True,
                    "trusted": False,
                },
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"],
                    "env": {},
                    "enabled": False,
                    "trusted": False,
                },
            },
        }
    }


def create_example_config_file(output_path: Path) -> None:
    """Create an example MCP configuration file.

    Args:
        output_path: Path to write the example config
    """
    import toml

    example = get_example_config()

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            toml.dump(example, f)
        logger.info(f"Created example MCP config at {output_path}")
    except Exception as e:
        logger.error(f"Failed to create example config: {e}")


def validate_server_config(config: MCPServerConfig) -> tuple[bool, str]:
    """Validate an MCP server configuration.

    Args:
        config: Server configuration to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if not config.name:
        return False, "Server name is required"

    if not config.command:
        return False, f"Command is required for server '{config.name}'"

    if not isinstance(config.args, list):
        return False, f"Args must be a list for server '{config.name}'"

    # Validate type
    if config.type not in ["stdio", "sse"]:
        return False, f"Invalid type '{config.type}' for server '{config.name}'"

    # SSE servers require URL
    if config.type == "sse" and not config.url:
        return False, f"SSE server '{config.name}' requires a URL"

    # Validate env is dict
    if not isinstance(config.env, dict):
        return False, f"Env must be a dictionary for server '{config.name}'"

    return True, ""


def print_server_config(config: MCPServerConfig) -> None:
    """Pretty-print a server configuration.

    Args:
        config: Server configuration to print
    """
    print(f"\nMCP Server: {config.name}")
    print(f"  Type:      {config.type}")
    print(f"  Command:   {config.command} {' '.join(config.args)}")
    print(f"  Enabled:   {config.enabled}")
    print(f"  Trusted:   {config.trusted}")

    if config.env:
        print(f"  Environment Variables:")
        for key in config.env.keys():
            print(f"    - {key}")

    if config.url:
        print(f"  URL:       {config.url}")
