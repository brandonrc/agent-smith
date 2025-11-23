"""Help screen for Agent Smith UI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static


class HelpScreen(Screen):
    """Display help information."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    #help-content {
        height: auto;
    }

    .help-section {
        margin: 1 0;
    }

    .help-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .help-item {
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("q", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Create help screen widgets."""
        with Container(id="help-container"):
            with VerticalScroll(id="help-content"):
                yield Static(self._get_help_text(), classes="help-section")
        yield Footer()

    def _get_help_text(self) -> str:
        """Get help text content."""
        return """[bold cyan]🤖 Agent Smith - Help[/bold cyan]

[bold]Keyboard Shortcuts:[/bold]
  Ctrl+C / Ctrl+D    Quit the application
  F1                 Show this help screen
  Up/Down            Navigate message history

[bold]Commands:[/bold]
  /help              Show this help screen
  /clear             Clear all messages
  /reset             Reset conversation (clear messages and usage)
  /model             Show current model and provider
  /model <name>      Switch to a different model
  /cost              Show token usage and cost estimate
  /tools             List all available tools

[bold]Features:[/bold]
  • Interactive REPL with AI coding assistant
  • Real-time tool execution and feedback
  • Markdown rendering for code and text
  • Token usage tracking
  • Multi-provider support (Anthropic, OpenAI)

[bold]Tools Available:[/bold]
  • Bash        - Execute shell commands
  • Read        - Read file contents
  • Write       - Write files
  • Edit        - Edit files with exact string replacement
  • Glob        - Find files by pattern
  • Grep        - Search file contents
  • List        - List directory contents
  • Agent       - Spawn sub-agents for complex tasks
  • Think       - Extended reasoning and planning

[bold]Configuration:[/bold]
  Config Dir:  ~/.config/agent-smith/
  Data Dir:    ~/.local/share/agent-smith/

  Use 'smith config show' to view settings
  Use 'smith config set <key> <value>' to update

[bold]Examples:[/bold]
  "List all Python files in src/"
  "Read and explain the main.py file"
  "Write a function to parse JSON"
  "Find all TODO comments in the project"
  "Refactor this code to use async/await"

[dim]Press ESC, Q, or Enter to close this help screen[/dim]
"""

    def action_dismiss(self) -> None:
        """Dismiss the help screen."""
        self.app.pop_screen()
