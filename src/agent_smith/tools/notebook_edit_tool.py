"""Notebook edit tool for editing Jupyter notebooks."""

import json
from pathlib import Path
from typing import Any, Literal

from .base import BaseTool, ToolResult


class NotebookEditTool(BaseTool):
    """Tool for editing Jupyter notebook (.ipynb) files.

    Supports three edit modes:
    - replace: Replace cell source and clear outputs
    - insert: Insert new cell at index
    - delete: Delete cell at index
    """

    name = "EditNotebook"
    description = (
        "Edit a Jupyter notebook (.ipynb) file. "
        "Can replace cell content, insert new cells, or delete cells. "
        "Supports both code and markdown cells."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "notebook_path": {
                "type": "string",
                "description": "Absolute path to the Jupyter notebook file to edit",
            },
            "cell_number": {
                "type": "integer",
                "description": "Zero-based index of the cell to edit",
            },
            "new_source": {
                "type": "string",
                "description": "New source code for the cell",
            },
            "cell_type": {
                "type": "string",
                "enum": ["code", "markdown"],
                "description": "Cell type (required for insert mode, optional for replace)",
            },
            "edit_mode": {
                "type": "string",
                "enum": ["replace", "insert", "delete"],
                "description": "Edit mode: replace (default), insert, or delete",
            },
        },
        "required": ["notebook_path", "cell_number", "new_source"],
    }

    async def execute(
        self,
        notebook_path: str,
        cell_number: int,
        new_source: str,
        cell_type: Literal["code", "markdown"] | None = None,
        edit_mode: Literal["replace", "insert", "delete"] = "replace",
        **kwargs,
    ) -> ToolResult:
        """
        Edit a Jupyter notebook cell.

        Args:
            notebook_path: Path to .ipynb file
            cell_number: Zero-based cell index
            new_source: New cell source content
            cell_type: Cell type (required for insert)
            edit_mode: Edit mode (replace/insert/delete)

        Returns:
            ToolResult indicating success or failure
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
            try:
                notebook = json.loads(content)
            except json.JSONDecodeError as e:
                return ToolResult(
                    content=f"Invalid JSON in notebook file: {e}",
                    is_error=True,
                )

            # Validate cell number
            cells = notebook.get("cells", [])
            if cell_number < 0:
                return ToolResult(
                    content=f"Cell number must be non-negative, got: {cell_number}",
                    is_error=True,
                )

            # Perform edit based on mode
            if edit_mode == "replace":
                if cell_number >= len(cells):
                    return ToolResult(
                        content=f"Cell number {cell_number} out of range (notebook has {len(cells)} cells)",
                        is_error=True,
                    )

                # Replace cell
                target_cell = cells[cell_number]
                target_cell["source"] = new_source
                target_cell["execution_count"] = None
                target_cell["outputs"] = []

                # Optionally change cell type
                if cell_type and cell_type != target_cell.get("cell_type"):
                    target_cell["cell_type"] = cell_type

                result_msg = f"Replaced cell {cell_number}"

            elif edit_mode == "insert":
                if cell_number > len(cells):
                    return ToolResult(
                        content=f"Insert position {cell_number} out of range (max: {len(cells)})",
                        is_error=True,
                    )

                if not cell_type:
                    return ToolResult(
                        content="cell_type is required for insert mode",
                        is_error=True,
                    )

                # Create new cell
                new_cell: dict[str, Any] = {
                    "cell_type": cell_type,
                    "source": new_source,
                    "metadata": {},
                }

                # Code cells need outputs array
                if cell_type == "code":
                    new_cell["outputs"] = []
                    new_cell["execution_count"] = None

                # Insert cell at position
                cells.insert(cell_number, new_cell)

                result_msg = f"Inserted new {cell_type} cell at position {cell_number}"

            elif edit_mode == "delete":
                if cell_number >= len(cells):
                    return ToolResult(
                        content=f"Cell number {cell_number} out of range (notebook has {len(cells)} cells)",
                        is_error=True,
                    )

                # Delete cell
                deleted_cell = cells.pop(cell_number)
                result_msg = f"Deleted {deleted_cell.get('cell_type', 'unknown')} cell at position {cell_number}"

            else:
                return ToolResult(
                    content=f"Invalid edit_mode: {edit_mode}. Must be replace, insert, or delete",
                    is_error=True,
                )

            # Write notebook back to file
            notebook_json = json.dumps(notebook, indent=1, ensure_ascii=False)
            path.write_text(notebook_json, encoding="utf-8")

            return ToolResult(
                content=f"{result_msg}\nNotebook saved: {path}",
                is_error=False,
            )

        except PermissionError as e:
            return ToolResult(
                content=f"Permission denied editing notebook: {e}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error editing notebook: {e}",
                is_error=True,
            )

    def requires_permission(self) -> bool:
        """Notebook edit modifies files - requires permission."""
        return True
