"""Main Textual application for Agent Smith."""

from textual.app import App
from textual.binding import Binding

from ..config import settings
from .help_screen import HelpScreen
from .repl import REPLScreen


class AgentSmithApp(App):
    """Agent Smith Terminal UI Application."""

    CSS = """
    Screen {
        background: $surface;
    }
    """

    TITLE = "Agent Smith 🤖"
    SUB_TITLE = "AI Coding Assistant"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("f1", "help", "Help"),
    ]

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ):
        """
        Initialize Agent Smith app.

        Args:
            provider: LLM provider to use
            model: Model name to use
        """
        super().__init__()
        self.provider = provider or settings.get("default_provider", "anthropic")
        self.model = model or settings.get("large_model")

    def on_mount(self) -> None:
        """Called when app starts."""
        # Push the REPL screen
        self.push_screen(REPLScreen(provider=self.provider, model=self.model))

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
