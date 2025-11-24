"""REPL screen for interactive conversation."""

from pathlib import Path

from rich.panel import Panel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog

from ..config import get_api_key
from ..mcp_integration import get_mcp_status, initialize_mcp, shutdown_mcp
from ..models import Message
from ..query import QueryOrchestrator
from ..tools import default_tools
from .components import (
    format_cost_info,
    format_error,
    format_tool_result,
    format_tool_use,
)
from .message_renderer import message_renderer


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

        # Initialize MCP (Model Context Protocol) servers
        log.write("[dim]Initializing MCP servers...[/dim]")
        try:
            await initialize_mcp(auto_approve=False)
            mcp_status = get_mcp_status()
            if mcp_status["initialized"] and mcp_status["tools_count"] > 0:
                log.write(
                    f"[green]✓[/green] MCP initialized: {len(mcp_status['servers'])} server(s), {mcp_status['tools_count']} tool(s)"
                )
        except Exception as e:
            log.write(f"[yellow]⚠️  MCP initialization skipped: {e}[/yellow]")

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
        log.write(message_renderer.render_user_message(user_input))

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
                    "/help - Show this help message\n"
                    "/clear - Clear screen (keeps conversation)\n"
                    "/reset - Reset conversation and clear history\n"
                    "/model [name] - Show or change current model\n"
                    "/cost - Show detailed token usage and estimated costs\n"
                    "/tools - List all available tools\n"
                    "/mcp - Show MCP server status\n"
                    "/doctor - Run system diagnostics\n"
                    "/export [filename] - Export conversation to file\n"
                    "/review [PR#] - Code review mode for pull requests\n"
                    "/pr-comments [PR#] - Fetch and analyze PR comments\n\n"
                    "[bold]Examples:[/bold]\n\n"
                    "/model - Show current model\n"
                    "/model claude-3-5-haiku-20241022 - Switch to Haiku\n"
                    "/mcp - View connected MCP servers\n"
                    "/review 123 - Review PR #123\n"
                    "/pr-comments - Get comments from current PR\n"
                    "/export my-chat.md - Save conversation\n\n"
                    "[bold]Keyboard Shortcuts:[/bold]\n\n"
                    "Ctrl+C - Quit application\n"
                    "Ctrl+L - Clear screen\n"
                    "Ctrl+R - Reset conversation",
                    title="📚 Help",
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
        elif command.startswith("/model"):
            # Parse model name
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                # Change model
                new_model = parts[1]
                old_model = self.model
                self.model = new_model

                # Reinitialize orchestrator with new model
                if self.orchestrator:
                    self.orchestrator.model = new_model

                log.write(
                    f"[green]✓[/green] Model changed from [cyan]{old_model}[/cyan] to [cyan]{new_model}[/cyan]"
                )
                self.notify(f"Model: {new_model}")
            else:
                # Show current model
                log.write(
                    Panel(
                        f"[bold]Current Configuration:[/bold]\n\n"
                        f"Provider: [cyan]{self.provider}[/cyan]\n"
                        f"Model: [cyan]{self.model}[/cyan]\n\n"
                        f"[bold]Available Models (Anthropic):[/bold]\n"
                        f"- claude-sonnet-4-5-20250929 (Sonnet 4.5 - Latest)\n"
                        f"- claude-3-5-sonnet-20241022 (Sonnet 3.5)\n"
                        f"- claude-3-5-haiku-20241022 (Haiku - Fast & Cheap)\n"
                        f"- claude-3-opus-20240229 (Opus - Most Capable)\n\n"
                        f"[dim]Use /model <name> to switch models[/dim]",
                        title="🤖 Model Configuration",
                        border_style="cyan",
                    )
                )
        elif command == "/cost":
            if self.orchestrator:
                usage = self.orchestrator.total_usage
                log.write(
                    format_cost_info(
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        cache_creation_tokens=usage.cache_creation_input_tokens,
                        cache_read_tokens=usage.cache_read_input_tokens,
                        model=self.model,
                    )
                )
            else:
                log.write("[yellow]No usage data available yet[/yellow]")
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
        elif command == "/mcp":
            # Show MCP server status
            mcp_status = get_mcp_status()

            if not mcp_status["initialized"]:
                log.write(
                    Panel(
                        "[yellow]MCP is not initialized.[/yellow]\n\n"
                        "MCP (Model Context Protocol) allows Agent Smith to connect to\n"
                        "external services like GitLab, Jira, databases, and more.\n\n"
                        "[bold]To configure MCP servers:[/bold]\n"
                        "1. Edit settings.toml in your config directory\n"
                        "2. Add MCP server configurations\n"
                        "3. Restart Agent Smith\n\n"
                        "[dim]See documentation for examples[/dim]",
                        title="📡 MCP Status",
                        border_style="yellow",
                    )
                )
            else:
                servers = mcp_status["servers"]
                server_status = mcp_status["server_status"]

                status_lines = []
                for server_name in servers:
                    info = server_status.get(server_name, {})
                    connected = info.get("connected", False)
                    tools_count = info.get("tools_count", 0)
                    prompts_count = info.get("prompts_count", 0)

                    status_icon = "🟢" if connected else "🔴"
                    status_lines.append(f"{status_icon} [bold]{server_name}[/bold]")
                    status_lines.append(
                        f"   Tools: {tools_count}, Prompts: {prompts_count}"
                    )

                status_text = "\n".join(status_lines)

                log.write(
                    Panel(
                        f"[bold]MCP Servers ({len(servers)} registered):[/bold]\n\n"
                        f"{status_text}\n\n"
                        f"[bold cyan]Total: {mcp_status['tools_count']} tools, "
                        f"{mcp_status['prompts_count']} prompts[/bold cyan]",
                        title="📡 MCP Status",
                        border_style="green",
                    )
                )
        elif command == "/doctor":
            # Run system diagnostics
            import sys

            from platformdirs import user_config_dir

            issues = []
            checks = []

            # Check Python version
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            if sys.version_info >= (3, 11):
                checks.append(f"✅ Python {py_version} (OK)")
            else:
                checks.append(f"❌ Python {py_version} (Need 3.11+)")
                issues.append("Python version too old")

            # Check API keys
            api_key = get_api_key(self.provider)
            if api_key:
                checks.append(f"✅ {self.provider.capitalize()} API key configured")
            else:
                checks.append(f"❌ {self.provider.capitalize()} API key not found")
                issues.append(
                    f"Set API key with: smith config set {self.provider}_api_key YOUR_KEY"
                )

            # Check config directory
            config_dir = Path(user_config_dir("agent-smith"))
            if config_dir.exists():
                checks.append(f"✅ Config directory: {config_dir}")
            else:
                checks.append(f"⚠️  Config directory missing: {config_dir}")

            # Check tools
            tool_count = len(default_tools.list_tools())
            checks.append(f"✅ {tool_count} tools registered")

            # Check orchestrator
            if self.orchestrator:
                checks.append("✅ Query orchestrator initialized")
                checks.append(f"✅ Current model: {self.model}")
            else:
                checks.append("❌ Query orchestrator not initialized")
                issues.append("Orchestrator initialization failed")

            # Check memory directory
            memory_dir = config_dir / "memory"
            if memory_dir.exists():
                memory_files = len(list(memory_dir.rglob("*")))
                checks.append(f"✅ Memory directory: {memory_files} file(s)")
            else:
                checks.append("ℹ️  Memory directory not created yet")

            # Build report
            status = (
                "✅ All systems operational"
                if not issues
                else f"⚠️  {len(issues)} issue(s) found"
            )
            report = f"[bold]{status}[/bold]\n\n"
            report += "\n".join(checks)

            if issues:
                report += "\n\n[bold red]Issues:[/bold red]\n"
                report += "\n".join(f"• {issue}" for issue in issues)

            log.write(
                Panel(
                    report,
                    title="🏥 System Diagnostics",
                    border_style="green" if not issues else "yellow",
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
        elif command.startswith("/review"):
            # Code review mode
            parts = command.split(maxsplit=1)
            pr_number = parts[1] if len(parts) > 1 else ""

            # Create review prompt
            review_prompt = f"""You are an expert code reviewer. Follow these steps:

1. If no PR number is provided, use Bash("gh pr list") to show open PRs
2. If a PR number is provided, use Bash("gh pr view {pr_number}") to get PR details
3. Use Bash("gh pr diff {pr_number}") to get the diff
4. Analyze the changes and provide a thorough code review that includes:
   - Overview of what the PR does
   - Analysis of code quality and style
   - Specific suggestions for improvements
   - Any potential issues or risks

Keep your review concise but thorough. Focus on:
- Code correctness
- Following project conventions
- Performance implications
- Test coverage
- Security considerations

Format your review with clear sections and bullet points.

PR number: {pr_number if pr_number else "(to be determined)"}"""

            # Add as user message and process
            log.write("")
            log.write("[bold cyan]Starting code review mode...[/bold cyan]")
            log.write("")

            # Add to conversation
            self.messages.append(Message.user(review_prompt))

            # Start async processing
            self.run_worker(self.process_llm_response(), exclusive=False)

        elif command.startswith("/pr-comments"):
            # PR comments analysis mode
            parts = command.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""

            # Create PR comments prompt
            pr_comments_prompt = f"""You are an AI assistant integrated into a git-based version control system. Your task is to fetch and display comments from a GitHub pull request.

Follow these steps:

1. Use Bash("gh pr view --json number,headRepository") to get the PR number and repository info
2. Use Bash to run gh api commands to get PR-level and review comments:
   - gh api /repos/{{owner}}/{{repo}}/issues/{{number}}/comments for PR-level comments
   - gh api /repos/{{owner}}/{{repo}}/pulls/{{number}}/comments for review comments
3. Parse and format all comments in a readable way
4. Return ONLY the formatted comments, with no additional text

Format the comments as:

## Comments

[For each comment thread:]
- @author file.ts#line:
  ```diff
  [diff_hunk from the API response]
  ```
  > quoted comment text

  [any replies indented]

If there are no comments, return "No comments found."

Remember:
1. Only show the actual comments, no explanatory text
2. Include both PR-level and code review comments
3. Preserve the threading/nesting of comment replies
4. Show the file and line number context for code review comments
5. Use jq to parse the JSON responses from the GitHub API

{f"Additional user input: {args}" if args else ""}"""

            # Add as user message and process
            log.write("")
            log.write("[bold cyan]Fetching PR comments...[/bold cyan]")
            log.write("")

            # Add to conversation
            self.messages.append(Message.user(pr_comments_prompt))

            # Start async processing
            self.run_worker(self.process_llm_response(), exclusive=False)

        else:
            log.write(f"[red]Unknown command: {command}[/red]")
            log.write("Type [cyan]/help[/cyan] for available commands")

    async def process_llm_response(self) -> None:
        """Process LLM response (called as background worker)."""
        log = self.query_one("#message-log", RichLog)

        if not self.orchestrator:
            log.write(format_error("Orchestrator not initialized"))
            return

        # Show thinking indicator
        log.write("")
        log.write("[dim]🤔 Thinking...[/dim]")

        try:
            # Get response
            response_text = []
            streaming_text = []
            current_tool_uses = []

            async for event in self.orchestrator.query(
                messages=self.messages,
                system="You are a helpful AI coding assistant. Use tools to help the user with their tasks.",
                tools=default_tools.list_tools(),
            ):
                if event["type"] == "text_delta":
                    # Accumulate streaming text
                    delta = event["delta"]
                    streaming_text.append(delta)
                    # For now, we accumulate and display at the end
                    # Real-time streaming would require Live() context

                elif event["type"] == "tool_use":
                    # Show tool use with formatted display
                    tool_name = event["name"]
                    arguments = event.get("arguments", {})
                    log.write(format_tool_use(tool_name, arguments))
                    current_tool_uses.append((tool_name, arguments))

                elif event["type"] == "tool_execution_start":
                    count = event["count"]
                    log.write(f"[yellow]🔧 Executing {count} tool(s)...[/yellow]")

                elif event["type"] == "tool_use_result":
                    tool_name = event["name"]
                    result = event["result"]
                    # Show formatted tool result
                    log.write(
                        format_tool_result(
                            tool_name=tool_name,
                            result=(
                                result.content
                                if hasattr(result, "content")
                                else str(result)
                            ),
                            is_error=(
                                result.is_error
                                if hasattr(result, "is_error")
                                else False
                            ),
                        )
                    )

                elif event["type"] == "message_complete":
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

            # Show assistant response with enhanced rendering
            if response_text:
                full_response = "\n\n".join(response_text)
                log.write(message_renderer.render_assistant_message(full_response))
            else:
                log.write("[yellow]No text response from assistant[/yellow]")

        except Exception as e:
            log.write(format_error(f"Error processing response: {str(e)}"))

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

        # Shutdown MCP servers
        await shutdown_mcp()
