"""Notebook read tool for reading Jupyter notebooks."""

import json
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult


class NotebookReadTool(BaseTool):
    """Tool for reading Jupyter notebook (.ipynb) files.

    Reads and parses Jupyter notebooks, extracting cells, outputs, and metadata.
    """

    name = "ReadNotebook"
    description = (
        "Read a Jupyter notebook (.ipynb) file. "
        "Returns the notebook cells with their source code, outputs, and metadata. "
        "Useful for analyzing or understanding existing notebooks."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "notebook_path": {
                "type": "string",
                "description": "Absolute path to the Jupyter notebook file to read",
            }
        },
        "required": ["notebook_path"],
    }

    def _process_output(self, output: dict[str, Any]) -> str:
        """
        Process a single notebook output.

        Args:
            output: Output dictionary from notebook cell

        Returns:
            Formatted output string
        """
        output_type = output.get("output_type", "")

        if output_type == "stream":
            # Stream output (stdout/stderr)
            text = output.get("text", "")
            if isinstance(text, list):
                text = "".join(text)
            return text[:1000]  # Truncate to prevent token overflow

        elif output_type in ("execute_result", "display_data"):
            # Execution result or displayed data
            data = output.get("data", {})
            if "text/plain" in data:
                text = data["text/plain"]
                if isinstance(text, list):
                    text = "".join(text)
                return text[:1000]
            elif "text/html" in data:
                return "[HTML output]"
            elif "image/png" in data or "image/jpeg" in data:
                return "[Image output]"
            return "[Display data]"

        elif output_type == "error":
            # Error output
            ename = output.get("ename", "Error")
            evalue = output.get("evalue", "")
            traceback = output.get("traceback", [])
            if isinstance(traceback, list):
                traceback_str = "\n".join(traceback[:5])  # Limit traceback lines
            else:
                traceback_str = str(traceback)
            return f"{ename}: {evalue}\n{traceback_str}"

        return "[Unknown output type]"

    def _format_cell(self, cell: dict[str, Any], index: int, language: str) -> str:
        """
        Format a notebook cell for display.

        Args:
            cell: Cell dictionary from notebook
            index: Cell index
            language: Programming language

        Returns:
            Formatted cell string
        """
        cell_type = cell.get("cell_type", "unknown")
        source = cell.get("source", "")

        # Source can be string or list of strings
        if isinstance(source, list):
            source = "".join(source)

        # Build cell output
        lines = [f"## Cell {index} ({cell_type})"]

        if cell_type == "code":
            execution_count = cell.get("execution_count")
            if execution_count is not None:
                lines.append(f"Execution count: {execution_count}")
            lines.append(f"\n```{language}")
            lines.append(source)
            lines.append("```")

            # Process outputs
            outputs = cell.get("outputs", [])
            if outputs:
                lines.append("\n### Outputs:")
                for output in outputs:
                    output_text = self._process_output(output)
                    if output_text:
                        lines.append(f"```\n{output_text}\n```")

        elif cell_type == "markdown":
            lines.append(f"\n{source}")

        return "\n".join(lines)

    async def execute(self, notebook_path: str, **kwargs) -> ToolResult:
        """
        Read a Jupyter notebook file.

        Args:
            notebook_path: Path to .ipynb file

        Returns:
            ToolResult with formatted notebook contents
        """
        try:
            path = Path(notebook_path).expanduser().resolve()

            # Validate file exists
            if not path.exists():
                return ToolResult(
                    content=f"Notebook file does not exist: {notebook_path}",
                    is_error=True,
                )

            # Validate file extension
            if path.suffix != ".ipynb":
                return ToolResult(
                    content=f"File is not a Jupyter notebook (.ipynb): {path.suffix}",
                    is_error=True,
                )

            # Read and parse notebook
            content = path.read_text(encoding="utf-8")
            notebook = json.loads(content)

            # Extract metadata
            metadata = notebook.get("metadata", {})
            language_info = metadata.get("language_info", {})
            language = language_info.get("name", "python")

            # Process cells
            cells = notebook.get("cells", [])
            if not cells:
                return ToolResult(
                    content="Notebook has no cells",
                    is_error=False,
                )

            # Format notebook
            output_lines = [
                f"# Notebook: {path.name}",
                f"Language: {language}",
                f"Total cells: {len(cells)}",
                "\n---\n",
            ]

            for index, cell in enumerate(cells):
                formatted_cell = self._format_cell(cell, index, language)
                output_lines.append(formatted_cell)
                output_lines.append("\n---\n")

            return ToolResult(
                content="\n".join(output_lines),
                is_error=False,
            )

        except json.JSONDecodeError as e:
            return ToolResult(
                content=f"Invalid JSON in notebook file: {e}",
                is_error=True,
            )
        except PermissionError as e:
            return ToolResult(
                content=f"Permission denied reading notebook: {e}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error reading notebook: {e}",
                is_error=True,
            )

    def requires_permission(self) -> bool:
        """Notebook read is safe - doesn't require explicit permission."""
        return False
