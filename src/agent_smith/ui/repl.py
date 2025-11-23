"""REPL screen for interactive conversation."""

from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog

from ..config import get_api_key
from ..models import Message
from ..query import QueryOrchestrator
from ..tools import default_tools


class REPLScreen(Screen):
    """Interactive REPL for Agent Smith."""

    CSS = """
    REPLScreen {
        background: $surface;
    }

    #message-log {
        height: 1fr;
        background: $surface;
        border: solid $primary;
        margin: 1;
    }

    #input-container {
        height: auto;
        dock: bottom;
        background: $surface;
        padding: 1;
    }

    #user-input {
        width: 100%;
    }

    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+r", "reset", "Reset"),
    ]

    def __init__(self, provider: str, model: str):
        """
        Initialize REPL screen.

        Args:
            provider: LLM provider
            model: Model name
        """
        super().__init__()
        self.provider = provider
        self.model = model
        self.messages: list[Message] = []
        self.orchestrator: QueryOrchestrator | None = None
        self.input_history: list[str] = []
        self.history_index = 0
        self.total_cost = 0.0

    def compose(self) -> ComposeResult:
        """Compose the REPL UI."""
        yield Header()

        # Message log
        yield RichLog(
            id="message-log",
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )

        # Input container
        with Vertical(id="input-container"):
            yield Input(
                placeholder="Ask a question or type /help for commands...",
                id="user-input",
            )

        # Status bar
        with Horizontal(id="status-bar"):
            yield Footer()

    async def on_mount(self) -> None:
        """Called when screen is mounted."""
        log = self.query_one("#message-log", RichLog)

        # Check for API key
        api_key = get_api_key(self.provider)
        if not api_key:
            log.write(
                Panel(
                    f"[red]No API key found for {self.provider}[/red]\n\n"
                    f"Set it with: [cyan]smith config set {self.provider}_api_key YOUR_KEY[/cyan]\n"
                    f"Or environment variable: [cyan]SMITH_{self.provider.upper()}_API_KEY[/cyan]",
                    title="⚠️  API Key Required",
                    border_style="red",
                )
            )
            return

        # Welcome message
        log.write(
            Panel(
                f"[bold green]Agent Smith[/bold green] v0.1.0\n\n"
                f"Provider: [cyan]{self.provider}[/cyan]\n"
                f"Model: [cyan]{self.model}[/cyan]\n\n"
                f"Type your question or [bold]/help[/bold] for commands.\n"
                f"Press [bold]Ctrl+C[/bold] to quit.",
                title="🤖 Welcome to Agent Smith",
                border_style="green",
            )
        )

        # Initialize orchestrator
        self.orchestrator = QueryOrchestrator(
            provider=self.provider,
            model=self.model,
        )

        # Focus input
        self.query_one("#user-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()
        if not user_input:
            return

        # Clear input IMMEDIATELY
        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""

        # Add to history
        self.input_history.append(user_input)
        self.history_index = len(self.input_history)

        # Check for commands
        if user_input.startswith("/"):
            await self.handle_command(user_input)
            return

        # Display user message IMMEDIATELY (synchronous)
        log = self.query_one("#message-log", RichLog)
        log.write("")  # Empty line
        log.write(
            Panel(
                Markdown(user_input),
                title="[bold cyan]You[/bold cyan]",
                border_style="cyan",
            )
        )

        # Add to conversation
        self.messages.append(Message.user(user_input))

        # Start async processing (doesn't block UI)
        self.run_worker(self.process_llm_response(), exclusive=False)

    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        log = self.query_one("#message-log", RichLog)

        if command == "/help":
            log.write(
                Panel(
                    "[bold]Available Commands:[/bold]\n\n"
                    "/help - Show this help\n"
                    "/clear - Clear message history\n"
                    "/reset - Reset conversation\n"
                    "/model - Show current model\n"
                    "/cost - Show token usage and cost\n"
                    "/tools - List available tools\n"
                    "/export [filename] - Export conversation to file\n\n"
                    "[bold]Keyboard Shortcuts:[/bold]\n\n"
                    "Ctrl+C - Quit\n"
                    "Ctrl+L - Clear screen\n"
                    "Ctrl+R - Reset conversation",
                    title="Help",
                    border_style="blue",
                )
            )
        elif command == "/clear":
            log.clear()
            self.notify("Screen cleared")
        elif command == "/reset":
            self.messages = []
            if self.orchestrator:
                self.orchestrator.total_usage.input_tokens = 0
                self.orchestrator.total_usage.output_tokens = 0
            log.clear()
            self.notify("Conversation reset")
        elif command == "/model":
            log.write(f"Current model: [cyan]{self.model}[/cyan]")
        elif command == "/cost":
            if self.orchestrator:
                usage = self.orchestrator.total_usage
                total_tokens = usage.input_tokens + usage.output_tokens
                log.write(
                    Panel(
                        f"[bold]Token Usage:[/bold]\n\n"
                        f"Input tokens: {usage.input_tokens:,}\n"
                        f"Output tokens: {usage.output_tokens:,}\n"
                        f"Cache creation: {usage.cache_creation_input_tokens:,}\n"
                        f"Cache reads: {usage.cache_read_input_tokens:,}\n"
                        f"Total: {total_tokens:,}",
                        title="📊 Usage Statistics",
                        border_style="cyan",
                    )
                )
        elif command == "/tools":
            tools_list = "\n".join(
                f"- {tool.name}: {tool.description.split('.')[0]}"
                for tool in default_tools.list_tools()
            )
            log.write(
                Panel(
                    f"[bold]Available Tools ({len(default_tools)} total):[/bold]\n\n{tools_list}",
                    title="🔧 Tools",
                    border_style="cyan",
                )
            )
        elif command.startswith("/export"):
            # Parse filename
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                filename = parts[1]
            else:
                filename = "conversation.md"

            # Check if there are messages to export
            if not self.messages:
                log.write("[yellow]No messages to export[/yellow]")
                return

            # Export conversation
            try:
                export_path = Path(filename).expanduser()
                with open(export_path, "w") as f:
                    f.write("# Agent Smith Conversation\n\n")
                    f.write(f"Provider: {self.provider}\n")
                    f.write(f"Model: {self.model}\n\n")
                    f.write(f"Messages in conversation: {len(self.messages)}\n\n")
                    f.write("---\n\n")

                    for idx, msg in enumerate(self.messages, 1):
                        role = "User" if msg.role.value == "user" else "Assistant"
                        content = msg.get_text()
                        f.write(f"## Message {idx}: {role}\n\n")
                        f.write(f"{content}\n\n")
                        f.write("---\n\n")

                log.write(
                    f"[green]✓[/green] Exported {len(self.messages)} message(s) to: [cyan]{export_path}[/cyan]"
                )
            except Exception as e:
                log.write(f"[red]Error exporting conversation: {e}[/red]")
        else:
            log.write(f"[red]Unknown command: {command}[/red]")
            log.write("Type [cyan]/help[/cyan] for available commands")

    async def process_llm_response(self) -> None:
        """Process LLM response (called as background worker)."""
        log = self.query_one("#message-log", RichLog)

        if not self.orchestrator:
            log.write("[red]Orchestrator not initialized[/red]")
            return

        # Show thinking indicator
        log.write("")
        log.write("[dim]🤔 Thinking...[/dim]")

        try:
            # Get response
            response_text = []
            tool_uses = []

            async for event in self.orchestrator.query(
                messages=self.messages,
                system="You are a helpful AI coding assistant. Use tools to help the user with their tasks.",
                tools=default_tools.list_tools(),
            ):
                if event["type"] == "text_delta":
                    # Could show streaming text here in the future
                    pass

                elif event["type"] == "tool_execution_start":
                    count = event["count"]
                    log.write(f"[yellow]🔧 Using {count} tool(s)...[/yellow]")

                elif event["type"] == "tool_use_result":
                    tool_name = event["name"]
                    result = event["result"]
                    status = "✅" if not result.is_error else "❌"
                    tool_uses.append(f"{status} {tool_name}")
                    # Show real-time tool completion
                    log.write(f"[dim]  {status} {tool_name}[/dim]")

                elif event["type"] == "message_complete":
                    log.write("[dim]✨ Generating response...[/dim]")
                    message = event["message"]
                    # Extract text from content blocks
                    for block in message.content:
                        # Handle both dict and Pydantic model blocks
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                response_text.append(block["text"])
                        elif hasattr(block, "type") and block.type == "text":
                            response_text.append(block.text)

                    # Add to conversation
                    self.messages.append(message.to_message())

                elif event["type"] == "usage":
                    # Update in real-time
                    usage = event["total_usage"]
                    total = usage.input_tokens + usage.output_tokens
                    self.sub_title = f"Tokens: {total:,}"

            # Display response
            log.write("")  # Empty line

            # Show assistant response
            if response_text:
                log.write(
                    Panel(
                        Markdown("\n\n".join(response_text)),
                        title="[bold green]Agent Smith[/bold green]",
                        border_style="green",
                    )
                )
            else:
                log.write("[yellow]No response from assistant[/yellow]")

        except Exception as e:
            log.write(f"[red]Error: {str(e)}[/red]")

    def action_clear(self) -> None:
        """Clear the message log."""
        log = self.query_one("#message-log", RichLog)
        log.clear()
        self.notify("Screen cleared")

    def action_reset(self) -> None:
        """Reset the conversation."""
        self.messages = []
        if self.orchestrator:
            self.orchestrator.total_usage.input_tokens = 0
            self.orchestrator.total_usage.output_tokens = 0
        log = self.query_one("#message-log", RichLog)
        log.clear()
        self.notify("Conversation reset")

    async def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.orchestrator:
            await self.orchestrator.close()
