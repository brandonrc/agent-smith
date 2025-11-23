"""Content search tool using grep."""

import re
from pathlib import Path
from typing import Any, Literal

from ..models import ToolResult
from .base import BaseTool


class GrepTool(BaseTool):
    """Search file contents using patterns."""

    def __init__(self, max_results: int = 100):
        """
        Initialize GrepTool.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results

    @property
    def name(self) -> str:
        return "Grep"

    @property
    def description(self) -> str:
        return """Search file contents using regex patterns.

Features:
- Full regex support (e.g., "log.*Error", "function\\s+\\w+")
- Filter by file type or glob pattern
- Multiple output modes:
  - "files_with_matches": Show only file paths (default)
  - "content": Show matching lines with context
  - "count": Show match counts per file
- Case-insensitive search option
- Context lines (before/after matches)

Examples:
- Find error logs: {"pattern": "error", "output_mode": "content"}
- Find TODO comments: {"pattern": "TODO:", "glob": "**/*.py"}
- Case-insensitive: {"pattern": "warning", "case_insensitive": true}
- With context: {"pattern": "def main", "output_mode": "content", "context": 3}

DO NOT use bash grep/rg commands - use this tool instead."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (defaults to current directory)",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py', '**/*.ts')",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["files_with_matches", "content", "count"],
                    "description": "Output mode (default: files_with_matches)",
                    "default": "files_with_matches",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                    "default": False,
                },
                "context": {
                    "type": "integer",
                    "description": "Number of context lines to show before and after matches (only for content mode)",
                    "default": 0,
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        output_mode: Literal[
            "files_with_matches", "content", "count"
        ] = "files_with_matches",
        case_insensitive: bool = False,
        context: int = 0,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Search for pattern in files.

        Args:
            pattern: Regex pattern to search
            path: Path to search (file or directory)
            glob: Glob pattern to filter files
            output_mode: Output format
            case_insensitive: Case insensitive search
            context: Number of context lines
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with search results
        """
        try:
            search_path = Path(path) if path else Path.cwd()

            # Validate path exists
            if not search_path.exists():
                return ToolResult.error(f"Path not found: {path}")

            # Compile regex pattern
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult.error(f"Invalid regex pattern: {str(e)}")

            # Get files to search
            if search_path.is_file():
                files = [search_path]
            else:
                # Search directory
                glob_pattern = glob or "**/*"
                files = [f for f in search_path.glob(glob_pattern) if f.is_file()]

            # Search files
            results = []
            total_matches = 0

            for file_path in files:
                try:
                    # Skip binary files
                    if not self._is_text_file(file_path):
                        continue

                    # Read file
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()

                    # Find matches
                    matches = []
                    for line_num, line in enumerate(lines, start=1):
                        if regex.search(line):
                            matches.append((line_num, line))
                            total_matches += 1

                    if matches:
                        rel_path = self._get_relative_path(file_path)

                        if output_mode == "files_with_matches":
                            results.append(str(rel_path))
                        elif output_mode == "count":
                            results.append(f"{rel_path}: {len(matches)}")
                        elif output_mode == "content":
                            # Format with context
                            formatted = self._format_matches_with_context(
                                rel_path, lines, matches, context
                            )
                            results.append(formatted)

                except (UnicodeDecodeError, PermissionError):
                    # Skip files we can't read
                    continue

            # Check if too many results
            if len(results) > self.max_results:
                return ToolResult.error(
                    f"Too many matches ({len(results)} files). "
                    f"Maximum is {self.max_results}. "
                    f"Please use a more specific pattern or glob filter."
                )

            # Format output
            if not results:
                result = f"No matches found for pattern: {pattern}"
            else:
                if output_mode == "files_with_matches":
                    result = f"Found {len(results)} file(s) with matches:\n\n"
                    result += "\n".join(results)
                elif output_mode == "count":
                    result = f"Match counts ({total_matches} total):\n\n"
                    result += "\n".join(results)
                elif output_mode == "content":
                    result = f"Found {total_matches} match(es) in {len(results)} file(s):\n\n"
                    result += "\n\n".join(results)

            return ToolResult.success(result)

        except Exception as e:
            return ToolResult.error(f"Search failed: {str(e)}")

    def _is_text_file(self, path: Path) -> bool:
        """Check if file is likely a text file."""
        # Check extension
        text_extensions = {
            ".txt",
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".html",
            ".css",
            ".scss",
            ".sass",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".md",
            ".rst",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".conf",
            ".cfg",
        }
        if path.suffix.lower() in text_extensions:
            return True

        # Check for common binary extensions
        binary_extensions = {
            ".pyc",
            ".pyo",
            ".so",
            ".dylib",
            ".dll",
            ".exe",
            ".bin",
            ".dat",
            ".db",
            ".sqlite",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".wasm",
        }
        if path.suffix.lower() in binary_extensions:
            return False

        # Default to text for files without extension or unknown extensions
        return True

    def _get_relative_path(self, path: Path) -> Path:
        """Get relative path from current directory."""
        try:
            return path.relative_to(Path.cwd())
        except ValueError:
            return path

    def _format_matches_with_context(
        self,
        file_path: Path,
        lines: list[str],
        matches: list[tuple[int, str]],
        context: int,
    ) -> str:
        """Format matches with context lines."""
        result = [f"{file_path}:"]

        for line_num, _ in matches:
            # Calculate context range
            start = max(1, line_num - context)
            end = min(len(lines), line_num + context)

            # Add context lines
            for i in range(start - 1, end):
                line = lines[i]
                line_number = i + 1
                prefix = ">" if line_number == line_num else " "
                result.append(f"{prefix} {line_number:6d}: {line}")

            # Add separator between matches
            if context > 0:
                result.append("  ...")

        return "\n".join(result)

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        GrepTool doesn't require permission (read-only).

        Returns:
            False (no permission needed)
        """
        return False
