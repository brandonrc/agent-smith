"""Memory read tool for persistent memory storage."""

from pathlib import Path

from platformdirs import user_config_dir

from .base import BaseTool, ToolResult


class MemoryReadTool(BaseTool):
    """Tool for reading from persistent memory storage.

    Memory files are stored in ~/.config/agent-smith/memory/ and can be used
    to persist information across conversations.
    """

    name = "Read"
    description = (
        "Read from persistent memory storage. "
        "Memory files are stored in the agent's memory directory and persist across conversations. "
        "If no file_path is provided, returns the index file and a list of all memory files. "
        "If file_path is provided, returns the contents of that specific file."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Optional path to a specific memory file to read (relative to memory directory)",
            }
        },
    }

    def __init__(self):
        """Initialize memory read tool."""
        super().__init__()
        # Use same base directory structure as config
        self.memory_dir = Path(user_config_dir("agent-smith")) / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, file_path: str | None = None, **kwargs) -> ToolResult:
        """
        Read from persistent memory storage.

        Args:
            file_path: Optional relative path to specific memory file

        Returns:
            ToolResult with file contents or directory listing
        """
        try:
            # If a specific file is requested
            if file_path:
                full_path = self.memory_dir / file_path

                # Security: Prevent directory traversal
                if not str(full_path.resolve()).startswith(
                    str(self.memory_dir.resolve())
                ):
                    return ToolResult(
                        content="Invalid memory file path - path traversal not allowed",
                        is_error=True,
                    )

                # Check if file exists
                if not full_path.exists():
                    return ToolResult(
                        content=f"Memory file does not exist: {file_path}",
                        is_error=True,
                    )

                if not full_path.is_file():
                    return ToolResult(
                        content=f"Path is not a file: {file_path}",
                        is_error=True,
                    )

                # Read and return file contents
                content = full_path.read_text(encoding="utf-8")
                return ToolResult(content=content, is_error=False)

            # No file specified - return index and file list
            index_path = self.memory_dir / "index.md"
            if index_path.exists():
                index_content = index_path.read_text(encoding="utf-8")
            else:
                index_content = ""

            # Get recursive file listing
            files = []
            for path in self.memory_dir.rglob("*"):
                if path.is_file():
                    # Get relative path from memory_dir
                    rel_path = path.relative_to(self.memory_dir)
                    files.append(f"- {rel_path}")

            files_list = (
                "\n".join(sorted(files)) if files else "No files in memory directory"
            )

            # Format output
            content = f"""Here are the contents of the root memory file, `{index_path}`:
```
{index_content}
```

Files in the memory directory:
{files_list}"""

            return ToolResult(content=content, is_error=False)

        except PermissionError as e:
            return ToolResult(
                content=f"Permission denied reading memory: {e}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error reading memory: {e}",
                is_error=True,
            )

    def requires_permission(self) -> bool:
        """Memory read is safe - doesn't require explicit permission."""
        return False
