"""List tool for directory contents."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ..models import ToolResult
from .base import BaseTool


class ListTool(BaseTool):
    """List directory contents with detailed information."""

    def __init__(self, max_entries: int = 1000):
        """
        Initialize ListTool.

        Args:
            max_entries: Maximum number of entries to return
        """
        self.max_entries = max_entries

    @property
    def name(self) -> str:
        return "List"

    @property
    def description(self) -> str:
        return """List directory contents with metadata.

Shows files and directories with:
- Type (file/directory)
- Size (for files)
- Modification time
- Permissions

Options:
- Recursive listing
- Show hidden files
- Sort by name, size, or time
- Filter by pattern

Examples:
- List current directory: {"path": "."}
- List recursively: {"path": "src", "recursive": true}
- Show hidden files: {"path": ".", "show_hidden": true}
- Sort by size: {"path": ".", "sort_by": "size"}

Use this instead of 'ls' command for directory listings."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (defaults to current directory)",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List subdirectories recursively",
                    "default": False,
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files (starting with .)",
                    "default": False,
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["name", "size", "time"],
                    "description": "Sort entries by name, size, or modification time",
                    "default": "name",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        path: str = ".",
        recursive: bool = False,
        show_hidden: bool = False,
        sort_by: Literal["name", "size", "time"] = "name",
        **kwargs: Any,
    ) -> ToolResult:
        """
        List directory contents.

        Args:
            path: Directory path
            recursive: List recursively
            show_hidden: Show hidden files
            sort_by: Sort method
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with directory listing
        """
        try:
            dir_path = Path(path).resolve()

            # Validate path
            if not dir_path.exists():
                return ToolResult.error(f"Path not found: {path}")

            if not dir_path.is_dir():
                return ToolResult.error(
                    f"Path is not a directory: {path}. Use Read tool for files."
                )

            # Collect entries
            entries = []

            if recursive:
                # Recursive listing
                for item in dir_path.rglob("*"):
                    if not show_hidden and item.name.startswith("."):
                        continue
                    entries.append(item)
            else:
                # Non-recursive listing
                for item in dir_path.iterdir():
                    if not show_hidden and item.name.startswith("."):
                        continue
                    entries.append(item)

            # Check entry count
            if len(entries) > self.max_entries:
                return ToolResult.error(
                    f"Too many entries ({len(entries)}). "
                    f"Maximum is {self.max_entries}. "
                    f"Use a more specific path or enable filtering."
                )

            # Sort entries
            if sort_by == "name":
                entries.sort(key=lambda x: x.name.lower())
            elif sort_by == "size":
                entries.sort(key=lambda x: x.stat().st_size, reverse=True)
            elif sort_by == "time":
                entries.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Format output
            result = f"Listing: {dir_path}\n"
            result += f"Total entries: {len(entries)}\n\n"

            # Column headers
            result += f"{'Type':<4} {'Size':>10} {'Modified':<20} {'Name'}\n"
            result += "-" * 70 + "\n"

            for item in entries:
                try:
                    stat = item.stat()

                    # Type
                    if item.is_dir():
                        type_str = "DIR"
                    elif item.is_symlink():
                        type_str = "LINK"
                    else:
                        type_str = "FILE"

                    # Size
                    if item.is_file():
                        size_str = self._format_size(stat.st_size)
                    else:
                        size_str = "-"

                    # Modified time
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    time_str = mtime.strftime("%Y-%m-%d %H:%M:%S")

                    # Name (relative path if recursive)
                    if recursive:
                        try:
                            name = str(item.relative_to(dir_path))
                        except ValueError:
                            name = str(item)
                    else:
                        name = item.name

                    # Add directory indicator
                    if item.is_dir():
                        name += "/"

                    result += f"{type_str:<4} {size_str:>10} {time_str:<20} {name}\n"

                except (PermissionError, OSError):
                    # Skip entries we can't access
                    continue

            return ToolResult.success(result)

        except PermissionError:
            return ToolResult.error(f"Permission denied: {path}")
        except Exception as e:
            return ToolResult.error(f"Failed to list directory: {str(e)}")

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        ListTool doesn't require permission (read-only).

        Returns:
            False
        """
        return False
