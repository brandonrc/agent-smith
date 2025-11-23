"""Bash command execution tool."""

import asyncio
from pathlib import Path
from typing import Any

from ..models import ToolResult
from .base import BaseTool


class BashTool(BaseTool):
    """Execute bash commands in a shell."""

    def __init__(self, working_dir: Path | None = None, timeout: float = 120.0):
        """
        Initialize BashTool.

        Args:
            working_dir: Working directory for commands (defaults to cwd)
            timeout: Default timeout in seconds
        """
        self.working_dir = working_dir or Path.cwd()
        self.default_timeout = timeout

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return """Execute bash commands in a persistent shell.

IMPORTANT: This tool is for terminal operations like git, npm, docker, etc.
DO NOT use it for file operations - use dedicated tools instead:
- Reading files: Use Read tool (not cat/head/tail)
- Editing files: Use Edit tool (not sed/awk)
- Writing files: Use Write tool (not echo/cat)
- Finding files: Use Glob tool (not find/ls)
- Searching content: Use Grep tool (not grep/rg)

Examples:
- git status
- npm install
- python script.py
- docker ps
- make build

The tool returns both stdout and stderr."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "description": {
                    "type": "string",
                    "description": "Clear, concise description of what this command does (5-10 words, active voice)",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds (default: 120)",
                    "default": 120.0,
                },
            },
            "required": ["command", "description"],
        }

    async def execute(
        self,
        command: str,
        description: str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Execute a bash command.

        Args:
            command: Command to execute
            description: Description of command
            timeout: Timeout in seconds
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with command output
        """
        timeout = timeout or self.default_timeout

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass
                return ToolResult.error(f"Command timed out after {timeout} seconds")

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Combine output
            output = stdout_text
            if stderr_text:
                output += f"\n{stderr_text}"

            # Check return code
            if process.returncode != 0:
                return ToolResult(
                    content=output
                    or f"Command failed with exit code {process.returncode}",
                    is_error=True,
                )

            return ToolResult.success(output or "(no output)")

        except Exception as e:
            return ToolResult.error(f"Command execution failed: {str(e)}")

    async def requires_permission(self, command: str, **kwargs: Any) -> bool:
        """
        Check if command requires permission.

        Dangerous patterns require user approval.

        Args:
            command: The command to check
            **kwargs: Additional arguments

        Returns:
            True if permission required
        """
        # List of dangerous patterns
        dangerous_patterns = [
            "rm -rf",
            "rm -fr",
            "dd if=",
            "mkfs",
            "> /dev/",
            "sudo ",
            "chmod 777",
            "chown ",
            "kill -9",
            "pkill",
            "killall",
            "reboot",
            "shutdown",
            "halt",
            "init 0",
            "init 6",
            ":(){:|:&};:",  # Fork bomb
            "format ",
            "fdisk",
            "parted",
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in command_lower:
                return True

        # Git commands that modify remote state
        if "git push" in command_lower and "--force" in command_lower:
            return True

        # Safe commands that don't need permission
        safe_prefixes = [
            "git status",
            "git diff",
            "git log",
            "ls ",
            "cat ",
            "echo ",
            "pwd",
            "which ",
            "npm list",
            "pip list",
            "python --version",
            "node --version",
        ]

        for prefix in safe_prefixes:
            if command_lower.startswith(prefix):
                return False

        # Default: require permission for most commands
        return True
