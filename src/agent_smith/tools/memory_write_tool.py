"""Memory write tool for persistent memory storage."""

from pathlib import Path

from platformdirs import user_config_dir

from .base import BaseTool, ToolResult


class MemoryWriteTool(BaseTool):
    """Tool for writing to persistent memory storage.

    Memory files are stored in ~/.config/agent-smith/memory/ and can be used
    to persist information across conversations.
    """

    name = "Write"
    description = (
        "Write to persistent memory storage. "
        "Memory files are stored in the agent's memory directory and persist across conversations. "
        "Creates parent directories automatically if they don't exist. "
        "Overwrites existing files with the same path."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the memory file to write (relative to memory directory)",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the memory file",
            },
        },
        "required": ["file_path", "content"],
    }

    def __init__(self):
        """Initialize memory write tool."""
        super().__init__()
        # Use same base directory structure as config
        self.memory_dir = Path(user_config_dir("agent-smith")) / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        """
        Write to persistent memory storage.

        Args:
            file_path: Relative path to memory file
            content: Content to write

        Returns:
            ToolResult indicating success or failure
        """
        try:
            full_path = self.memory_dir / file_path

            # Security: Prevent directory traversal
            if not str(full_path.resolve()).startswith(str(self.memory_dir.resolve())):
                return ToolResult(
                    content="Invalid memory file path - path traversal not allowed",
                    is_error=True,
                )

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            full_path.write_text(content, encoding="utf-8")

            return ToolResult(
                content=f"Successfully saved to memory: {file_path}",
                is_error=False,
            )

        except PermissionError as e:
            return ToolResult(
                content=f"Permission denied writing to memory: {e}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error writing to memory: {e}",
                is_error=True,
            )

    def requires_permission(self) -> bool:
        """Memory write modifies system state - requires permission."""
        return True
