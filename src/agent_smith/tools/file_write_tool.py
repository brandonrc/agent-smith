"""File writing tool."""

from pathlib import Path
from typing import Any

import aiofiles

from ..models import ToolResult
from .base import BaseTool


class FileWriteTool(BaseTool):
    """Write files to the local filesystem."""

    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return """Write files to the local filesystem.

IMPORTANT:
- This tool will OVERWRITE existing files
- ALWAYS prefer editing existing files using the Edit tool
- NEVER write files unless explicitly required
- If file exists, you MUST use Read tool first to check contents
- Only create new files when specifically requested

Usage:
- file_path must be absolute path
- content is the full file content to write
- Creates parent directories if needed
- Sets appropriate file permissions

Examples:
- Create new file: {"file_path": "/path/to/new_file.py", "content": "print('hello')"}

DO NOT use this for:
- Editing existing files (use Edit tool)
- Documentation files unless explicitly requested
- README files unless explicitly requested"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write (must be absolute, not relative)",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(
        self,
        file_path: str,
        content: str,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Write a file.

        Args:
            file_path: Path to file
            content: Content to write
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with success/failure
        """
        try:
            path = Path(file_path).resolve()

            # Check if file already exists
            file_exists = path.exists()

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)

            # Success message
            action = "Updated" if file_exists else "Created"
            line_count = content.count("\n") + 1
            char_count = len(content)

            result = f"{action} {file_path}\n"
            result += f"Lines: {line_count}, Characters: {char_count}"

            return ToolResult.success(result)

        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult.error(f"Failed to write file: {str(e)}")

    async def requires_permission(
        self, file_path: str, content: str, **kwargs: Any
    ) -> bool:
        """
        FileWriteTool requires permission.

        Args:
            file_path: Path being written
            content: Content being written
            **kwargs: Additional arguments

        Returns:
            True (always requires permission)
        """
        # Always require permission for file writes
        return True
