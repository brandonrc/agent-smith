"""Trust management system for MCP servers."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TrustManager:
    """Manages trust decisions for MCP servers.

    This class handles:
    - Loading and saving trust decisions
    - Prompting users for approval
    - Tracking trusted servers
    """

    def __init__(self, trust_file: Path):
        """Initialize trust manager.

        Args:
            trust_file: Path to the trust decisions file
        """
        self.trust_file = trust_file
        self.trusted_servers: dict[str, dict[str, Any]] = {}
        self._load_trust_decisions()

    def _load_trust_decisions(self) -> None:
        """Load trust decisions from file."""
        try:
            if self.trust_file.exists():
                with open(self.trust_file, "r") as f:
                    self.trusted_servers = json.load(f)
                logger.info(
                    f"Loaded trust decisions for {len(self.trusted_servers)} servers"
                )
            else:
                logger.info("No existing trust decisions found")
                self.trusted_servers = {}
        except Exception as e:
            logger.error(f"Failed to load trust decisions: {e}")
            self.trusted_servers = {}

    def _save_trust_decisions(self) -> None:
        """Save trust decisions to file."""
        try:
            self.trust_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.trust_file, "w") as f:
                json.dump(self.trusted_servers, f, indent=2)
            logger.info("Saved trust decisions")
        except Exception as e:
            logger.error(f"Failed to save trust decisions: {e}")

    def is_trusted(self, server_name: str) -> bool:
        """Check if a server is trusted.

        Args:
            server_name: Name of the server

        Returns:
            True if the server is trusted
        """
        return server_name in self.trusted_servers

    def trust_server(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env_keys: list[str],
    ) -> None:
        """Mark a server as trusted.

        Args:
            server_name: Name of the server
            command: Server command
            args: Command arguments
            env_keys: Environment variable keys (not values)
        """
        self.trusted_servers[server_name] = {
            "command": command,
            "args": args,
            "env_keys": env_keys,
        }
        self._save_trust_decisions()
        logger.info(f"Marked server as trusted: {server_name}")

    def untrust_server(self, server_name: str) -> None:
        """Remove trust for a server.

        Args:
            server_name: Name of the server
        """
        if server_name in self.trusted_servers:
            del self.trusted_servers[server_name]
            self._save_trust_decisions()
            logger.info(f"Removed trust for server: {server_name}")

    def get_trusted_servers(self) -> list[str]:
        """Get list of all trusted server names.

        Returns:
            List of trusted server names
        """
        return list(self.trusted_servers.keys())

    def get_server_info(self, server_name: str) -> dict[str, Any] | None:
        """Get stored information about a trusted server.

        Args:
            server_name: Name of the server

        Returns:
            Server information dict or None if not found
        """
        return self.trusted_servers.get(server_name)

    def has_config_changed(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env_keys: list[str],
    ) -> bool:
        """Check if server configuration has changed since it was trusted.

        Args:
            server_name: Name of the server
            command: Current server command
            args: Current command arguments
            env_keys: Current environment variable keys

        Returns:
            True if configuration has changed
        """
        if server_name not in self.trusted_servers:
            return True

        stored = self.trusted_servers[server_name]
        return (
            stored.get("command") != command
            or stored.get("args") != args
            or set(stored.get("env_keys", [])) != set(env_keys)
        )

    async def request_approval(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env_keys: list[str],
        auto_approve: bool = False,
    ) -> bool:
        """Request user approval for a server.

        Args:
            server_name: Name of the server
            command: Server command
            args: Command arguments
            env_keys: Environment variable keys
            auto_approve: If True, automatically approve (for testing)

        Returns:
            True if user approved, False otherwise
        """
        if auto_approve:
            self.trust_server(server_name, command, args, env_keys)
            return True

        # Check if already trusted and config hasn't changed
        if self.is_trusted(server_name):
            if not self.has_config_changed(server_name, command, args, env_keys):
                logger.info(f"Server {server_name} already trusted")
                return True
            else:
                logger.warning(
                    f"Configuration changed for {server_name}, re-requesting approval"
                )

        # Display approval prompt
        print("\n" + "=" * 60)
        print("🔒 MCP SERVER APPROVAL REQUIRED")
        print("=" * 60)
        print(f"\nServer Name: {server_name}")
        print(f"Command:     {command} {' '.join(args)}")
        print(f"Environment: {', '.join(env_keys) if env_keys else 'None'}")
        print("\nThis server will be able to:")
        print("  • Execute commands and scripts")
        print("  • Access the specified environment variables")
        print("  • Communicate with external services")
        print("\n⚠️  Only approve servers from trusted sources!")
        print("=" * 60)

        # Get user input
        while True:
            response = input(
                "\nDo you trust this server? [y]es/[n]o/[v]iew details: "
            ).lower()

            if response in ["y", "yes"]:
                self.trust_server(server_name, command, args, env_keys)
                print(f"✓ Server '{server_name}' approved and trusted.\n")
                return True

            elif response in ["n", "no"]:
                print(f"✗ Server '{server_name}' denied.\n")
                return False

            elif response in ["v", "view"]:
                print("\nDetailed Information:")
                print(f"  Command: {command}")
                print(f"  Arguments: {args}")
                print(f"  Environment Keys: {env_keys}")
                continue

            else:
                print("Invalid input. Please enter 'y', 'n', or 'v'.")

    def clear_all_trust(self) -> None:
        """Remove trust for all servers."""
        self.trusted_servers.clear()
        self._save_trust_decisions()
        logger.info("Cleared all trust decisions")

    def export_trust_decisions(self, export_path: Path) -> None:
        """Export trust decisions to a file.

        Args:
            export_path: Path to export to
        """
        try:
            with open(export_path, "w") as f:
                json.dump(self.trusted_servers, f, indent=2)
            logger.info(f"Exported trust decisions to {export_path}")
        except Exception as e:
            logger.error(f"Failed to export trust decisions: {e}")

    def import_trust_decisions(self, import_path: Path) -> None:
        """Import trust decisions from a file.

        Args:
            import_path: Path to import from
        """
        try:
            with open(import_path, "r") as f:
                imported = json.load(f)
            self.trusted_servers.update(imported)
            self._save_trust_decisions()
            logger.info(f"Imported trust decisions from {import_path}")
        except Exception as e:
            logger.error(f"Failed to import trust decisions: {e}")
