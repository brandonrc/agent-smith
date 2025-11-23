"""File reading tool with caching."""

from pathlib import Path
from typing import Any

import aiofiles

from ..models import ToolResult
from .base import BaseTool


class FileReadTool(BaseTool):
    """Read files from the local filesystem."""

    def __init__(self, max_line_length: int = 2000):
        """
        Initialize FileReadTool.

        Args:
            max_line_length: Maximum length for lines (longer lines are truncated)
        """
        self.max_line_length = max_line_length

    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return """Read files from the local filesystem.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, reads up to 2000 lines from the beginning
- Can optionally specify line offset and limit for large files
- Lines longer than 2000 characters are truncated
- Results are formatted with line numbers (cat -n format)
- Can read any text file
- For binary files, returns error message

Examples:
- Read entire file: {"file_path": "/path/to/file.py"}
- Read specific range: {"file_path": "/path/to/file.py", "offset": 100, "limit": 50}

DO NOT use this tool to read directories - use Glob tool instead."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed). Only provide if file is too large.",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of lines to read. Only provide if file is too large.",
                    "default": 2000,
                },
            },
            "required": ["file_path"],
        }

    async def execute(
        self,
        file_path: str,
        offset: int = 1,
        limit: int = 2000,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Read a file.

        Args:
            file_path: Path to file
            offset: Line number to start from (1-indexed)
            limit: Number of lines to read
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with file contents
        """
        try:
            path = Path(file_path).resolve()

            # Check if file exists
            if not path.exists():
                return ToolResult.error(f"File not found: {file_path}")

            # Check if it's a directory
            if path.is_dir():
                return ToolResult.error(
                    f"Path is a directory: {file_path}. Use Glob tool to list directory contents."
                )

            # Read file
            try:
                async with aiofiles.open(path, encoding="utf-8") as f:
                    lines = await f.readlines()
            except UnicodeDecodeError:
                # Try reading as binary to detect file type
                return ToolResult.error(
                    f"Cannot read binary file: {file_path}. This appears to be a binary file."
                )

            # Apply offset and limit
            total_lines = len(lines)
            start_idx = max(0, offset - 1)  # Convert to 0-indexed
            end_idx = min(total_lines, start_idx + limit)

            selected_lines = lines[start_idx:end_idx]

            # Format with line numbers (cat -n style)
            formatted_lines = []
            for i, line in enumerate(selected_lines, start=offset):
                # Truncate long lines
                line = line.rstrip("\n")
                if len(line) > self.max_line_length:
                    line = line[: self.max_line_length] + "... [truncated]"

                # Format with line number (spaces + number + tab + content)
                formatted_lines.append(f"{i:6d}\t{line}")

            result = "\n".join(formatted_lines)

            # Add metadata if file was partially read
            if start_idx > 0 or end_idx < total_lines:
                header = f"[Showing lines {offset}-{end_idx} of {total_lines}]\n"
                result = header + result

            # Warn if file is empty
            if not result:
                result = "[File is empty]"

            return ToolResult.success(result)

        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult.error(f"Failed to read file: {str(e)}")

    async def requires_permission(self, file_path: str, **kwargs: Any) -> bool:
        """
        FileReadTool doesn't require permission (read-only).

        Args:
            file_path: Path being read
            **kwargs: Additional arguments

        Returns:
            False (no permission needed for reading)
        """
        return False
