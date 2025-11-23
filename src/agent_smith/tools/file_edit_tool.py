"""File editing tool with diff generation."""

import difflib
from pathlib import Path
from typing import Any

import aiofiles

from ..models import ToolResult
from .base import BaseTool


class FileEditTool(BaseTool):
    """Edit files using exact string replacement."""

    @property
    def name(self) -> str:
        return "Edit"

    @property
    def description(self) -> str:
        return """Perform exact string replacements in files.

CRITICAL RULES:
- You MUST use Read tool at least once before editing
- Preserve exact indentation as it appears AFTER line number prefix
- NEVER include line number prefixes in old_string or new_string
- The edit will FAIL if old_string is not unique in the file
- Use replace_all for renaming variables/strings throughout file

Usage:
1. Read the file first with Read tool
2. Copy the EXACT text you want to replace (after the line number + tab)
3. Provide the new text with same indentation structure
4. Tool will show a diff preview

Examples:
- Replace single occurrence:
  old_string: "def foo():\n    return 42"
  new_string: "def foo():\n    return 100"

- Replace all occurrences (rename):
  old_string: "old_name"
  new_string: "new_name"
  replace_all: true

Tips:
- Include surrounding context to make old_string unique
- Preserve indentation exactly as shown in Read output
- Use replace_all for variable renames"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to replace (must match exactly)",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences of old_string (default: false)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Edit a file.

        Args:
            file_path: Path to file
            old_string: Text to replace
            new_string: Replacement text
            replace_all: Replace all occurrences
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with diff showing changes
        """
        try:
            path = Path(file_path).resolve()

            # Check if file exists
            if not path.exists():
                return ToolResult.error(f"File not found: {file_path}")

            # Read current content
            async with aiofiles.open(path, encoding="utf-8") as f:
                original_content = await f.read()

            # Validate strings are different
            if old_string == new_string:
                return ToolResult.error("old_string and new_string must be different")

            # Check if old_string exists
            if old_string not in original_content:
                return ToolResult.error(
                    "old_string not found in file. Make sure you copied the exact text from the Read tool output."
                )

            # Count occurrences
            occurrence_count = original_content.count(old_string)

            # Check uniqueness if not replace_all
            if not replace_all and occurrence_count > 1:
                return ToolResult.error(
                    f"old_string appears {occurrence_count} times in the file. "
                    f"Either provide a longer string with more context to make it unique, "
                    f"or use replace_all=true to replace all occurrences."
                )

            # Perform replacement
            if replace_all:
                new_content = original_content.replace(old_string, new_string)
                replace_count = occurrence_count
            else:
                # Replace only first occurrence
                new_content = original_content.replace(old_string, new_string, 1)
                replace_count = 1

            # Generate diff
            diff = self._generate_diff(original_content, new_content, file_path)

            # Write file
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(new_content)

            # Success message
            result = f"Successfully replaced {replace_count} occurrence(s) in {file_path}\n\n"
            result += "Diff:\n"
            result += diff

            return ToolResult.success(result)

        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult.error(f"Failed to edit file: {str(e)}")

    def _generate_diff(self, original: str, modified: str, file_path: str) -> str:
        """Generate unified diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff)

    async def requires_permission(self, file_path: str, **kwargs: Any) -> bool:
        """
        FileEditTool requires permission.

        Args:
            file_path: Path being edited
            **kwargs: Additional arguments

        Returns:
            True (always requires permission)
        """
        return True
