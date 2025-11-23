"""File pattern matching tool using glob."""

from pathlib import Path
from typing import Any

from ..models import ToolResult
from .base import BaseTool


class GlobTool(BaseTool):
    """Fast file pattern matching tool."""

    def __init__(self, max_results: int = 1000):
        """
        Initialize GlobTool.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results

    @property
    def name(self) -> str:
        return "Glob"

    @property
    def description(self) -> str:
        return """Fast file pattern matching using glob patterns.

Supports glob patterns like:
- "**/*.js" - All JavaScript files recursively
- "src/**/*.ts" - All TypeScript files in src
- "*.py" - Python files in current directory
- "test_*.py" - Test files matching pattern

Returns matching file paths sorted by modification time (newest first).

Examples:
- Find all Python files: {"pattern": "**/*.py"}
- Find in specific directory: {"pattern": "src/**/*.ts", "path": "src"}
- Find test files: {"pattern": "test_*.py"}

Use this when you need to:
- Find files by name patterns
- List directory contents
- Search for specific file types

DO NOT use bash find/ls commands - use this tool instead."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against (e.g., '**/*.py', 'src/**/*.ts')",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in (defaults to current directory)",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        pattern: str,
        path: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Find files matching pattern.

        Args:
            pattern: Glob pattern
            path: Directory to search (defaults to cwd)
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with list of matching files
        """
        try:
            search_path = Path(path) if path else Path.cwd()

            # Validate path exists
            if not search_path.exists():
                return ToolResult.error(f"Directory not found: {path}")

            if not search_path.is_dir():
                return ToolResult.error(f"Path is not a directory: {path}")

            # Search for matches
            matches = []
            for file_path in search_path.glob(pattern):
                if file_path.is_file():
                    # Get relative path for cleaner output
                    try:
                        rel_path = file_path.relative_to(Path.cwd())
                    except ValueError:
                        rel_path = file_path

                    matches.append((file_path, str(rel_path)))

            # Limit results
            if len(matches) > self.max_results:
                return ToolResult.error(
                    f"Too many matches ({len(matches)}). "
                    f"Maximum is {self.max_results}. "
                    f"Please use a more specific pattern."
                )

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)

            # Format output
            if not matches:
                result = f"No files found matching pattern: {pattern}"
            else:
                result = f"Found {len(matches)} file(s) matching '{pattern}':\n\n"
                for _, rel_path in matches:
                    result += f"{rel_path}\n"

            return ToolResult.success(result.rstrip())

        except Exception as e:
            return ToolResult.error(f"Failed to search files: {str(e)}")

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        GlobTool doesn't require permission (read-only).

        Returns:
            False (no permission needed)
        """
        return False
