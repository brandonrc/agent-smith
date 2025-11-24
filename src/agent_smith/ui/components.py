"""Reusable UI components for Agent Smith.

This module provides rich, styled components for displaying various
types of content in the terminal UI.
"""

from typing import Any

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


class CodeBlock(Static):
    """Widget for displaying syntax-highlighted code blocks.

    Automatically detects language and applies appropriate highlighting.
    """

    def __init__(
        self,
        code: str,
        language: str = "python",
        theme: str = "monokai",
        line_numbers: bool = True,
        **kwargs: Any,
    ):
        """Initialize code block.

        Args:
            code: The code to display
            language: Programming language for syntax highlighting
            theme: Color theme (monokai, github-dark, etc.)
            line_numbers: Whether to show line numbers
            **kwargs: Additional Static widget arguments
        """
        super().__init__(**kwargs)
        self.code = code
        self.language = language
        self.theme = theme
        self.line_numbers = line_numbers

    def render(self) -> RenderableType:
        """Render the code block with syntax highlighting."""
        return Syntax(
            self.code,
            self.language,
            theme=self.theme,
            line_numbers=self.line_numbers,
            word_wrap=False,
        )


class DiffViewer(Static):
    """Widget for displaying git-style diffs with color coding.

    Highlights additions in green, deletions in red.
    """

    def __init__(self, diff_text: str, **kwargs: Any):
        """Initialize diff viewer.

        Args:
            diff_text: The diff text to display
            **kwargs: Additional Static widget arguments
        """
        super().__init__(**kwargs)
        self.diff_text = diff_text

    def render(self) -> RenderableType:
        """Render the diff with syntax highlighting."""
        return Syntax(
            self.diff_text,
            "diff",
            theme="monokai",
            line_numbers=False,
            word_wrap=False,
        )


class ProgressIndicator:
    """Context manager for showing progress during long operations.

    Provides a rich progress bar with spinner for visual feedback.
    """

    def __init__(self, description: str = "Processing..."):
        """Initialize progress indicator.

        Args:
            description: Text to display next to progress indicator
        """
        self.description = description
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        )
        self.task_id = None

    def __enter__(self):
        """Start showing progress."""
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop showing progress."""
        if self.task_id is not None:
            self.progress.stop()
        return False

    def update(self, description: str | None = None, completed: int | None = None):
        """Update progress indicator.

        Args:
            description: New description text
            completed: Number of completed items
        """
        if self.task_id is not None:
            update_kwargs = {}
            if description:
                update_kwargs["description"] = description
            if completed is not None:
                update_kwargs["completed"] = completed
            self.progress.update(self.task_id, **update_kwargs)


def format_tool_use(tool_name: str, arguments: dict[str, Any]) -> Panel:
    """Format a tool use message for display.

    Args:
        tool_name: Name of the tool being used
        arguments: Tool arguments

    Returns:
        Formatted Panel for display
    """
    # Create a table for arguments
    if arguments:
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Argument", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in arguments.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            table.add_row(key, value_str)

        content = Group(
            Text(f"🔧 Using tool: {tool_name}", style="bold blue"),
            Text(""),
            table,
        )
    else:
        content = Text(f"🔧 Using tool: {tool_name}", style="bold blue")

    return Panel(
        content,
        title="Tool Use",
        border_style="blue",
        padding=(0, 1),
    )


def format_tool_result(
    tool_name: str,
    result: str,
    is_error: bool = False,
) -> Panel:
    """Format a tool result message for display.

    Args:
        tool_name: Name of the tool
        result: Result text
        is_error: Whether this is an error result

    Returns:
        Formatted Panel for display
    """
    # Determine if result looks like code
    is_code = "\n" in result and (
        result.strip().startswith("{")
        or result.strip().startswith("[")
        or "def " in result
        or "class " in result
        or "import " in result
    )

    if is_code and not is_error:
        # Display as code with syntax highlighting
        content = Syntax(
            result,
            "python",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )
    else:
        # Display as text
        style = "red" if is_error else "green"
        content = Text(result, style=style)

    status_icon = "❌" if is_error else "✅"
    title = f"{status_icon} {tool_name} Result"
    border_style = "red" if is_error else "green"

    return Panel(
        content,
        title=title,
        border_style=border_style,
        padding=(0, 1),
    )


def format_thinking(text: str) -> Panel:
    """Format a thinking/reasoning message for display.

    Args:
        text: Thinking text

    Returns:
        Formatted Panel for display
    """
    return Panel(
        Text(text, style="dim italic"),
        title="💭 Thinking",
        border_style="dim blue",
        padding=(0, 1),
    )


def format_error(error_message: str, title: str = "Error") -> Panel:
    """Format an error message for display.

    Args:
        error_message: Error message text
        title: Panel title

    Returns:
        Formatted Panel for display
    """
    return Panel(
        Text(error_message, style="bold red"),
        title=f"⚠️  {title}",
        border_style="red",
        padding=(0, 1),
    )


def format_success(message: str, title: str = "Success") -> Panel:
    """Format a success message for display.

    Args:
        message: Success message text
        title: Panel title

    Returns:
        Formatted Panel for display
    """
    return Panel(
        Text(message, style="bold green"),
        title=f"✅ {title}",
        border_style="green",
        padding=(0, 1),
    )


def format_info(message: str, title: str = "Info") -> Panel:
    """Format an informational message for display.

    Args:
        message: Info message text
        title: Panel title

    Returns:
        Formatted Panel for display
    """
    return Panel(
        Text(message, style="cyan"),
        title=f"ℹ️  {title}",
        border_style="cyan",
        padding=(0, 1),
    )


def format_code_with_language(code: str, language: str) -> Syntax:
    """Format code with specific language highlighting.

    Args:
        code: Code text
        language: Programming language

    Returns:
        Syntax-highlighted renderable
    """
    return Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=False,
    )


def format_markdown(text: str) -> Markdown:
    """Format markdown text for display.

    Args:
        text: Markdown text

    Returns:
        Rendered markdown
    """
    return Markdown(text, code_theme="monokai", inline_code_theme="monokai")


def format_table(
    headers: list[str],
    rows: list[list[str]],
    title: str | None = None,
) -> Table:
    """Format a data table for display.

    Args:
        headers: Column headers
        rows: Table rows
        title: Optional table title

    Returns:
        Formatted Table
    """
    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*row)

    return table


def format_cost_info(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    model: str = "claude-sonnet-4-5",
) -> Panel:
    """Format token usage and cost information.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Cache creation tokens
        cache_read_tokens: Cache read tokens
        model: Model name for pricing

    Returns:
        Formatted Panel with cost breakdown
    """
    # Pricing for Sonnet 4.5 (per million tokens)
    prices = {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    }

    # Calculate costs
    input_cost = input_tokens * prices["input"] / 1_000_000
    output_cost = output_tokens * prices["output"] / 1_000_000
    cache_write_cost = cache_creation_tokens * prices["cache_write"] / 1_000_000
    cache_read_cost = cache_read_tokens * prices["cache_read"] / 1_000_000
    total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

    # Create table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow", justify="right")

    table.add_row("Input tokens", f"{input_tokens:,}")
    table.add_row("Output tokens", f"{output_tokens:,}")
    if cache_creation_tokens > 0:
        table.add_row("Cache creation", f"{cache_creation_tokens:,}")
    if cache_read_tokens > 0:
        table.add_row("Cache reads", f"{cache_read_tokens:,}")
    table.add_row("", "")
    table.add_row("Input cost", f"${input_cost:.4f}")
    table.add_row("Output cost", f"${output_cost:.4f}")
    if cache_write_cost > 0:
        table.add_row("Cache write cost", f"${cache_write_cost:.4f}")
    if cache_read_cost > 0:
        table.add_row("Cache read cost", f"${cache_read_cost:.4f}")
    table.add_row("", "")
    table.add_row(
        "[bold]Total Cost[/bold]", f"[bold green]${total_cost:.4f}[/bold green]"
    )

    return Panel(
        table,
        title=f"📊 Usage & Cost ({model})",
        border_style="cyan",
        padding=(0, 1),
    )


def format_stream_chunk(text: str, is_complete: bool = False) -> Text:
    """Format a streaming text chunk for display.

    Args:
        text: Text chunk
        is_complete: Whether this is the final chunk

    Returns:
        Formatted Text object
    """
    style = "green" if is_complete else "white"
    return Text(text, style=style)
