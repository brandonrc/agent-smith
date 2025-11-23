"""Main CLI entry point for Agent Smith."""

import typer
from rich.console import Console
from rich.panel import Panel

from .config import AppPaths, get_api_key, set_api_key, settings

# Create Typer app
app = typer.Typer(
    name="smith",
    help="🤖 Agent Smith - Terminal-based AI coding assistant",
    no_args_is_help=False,
    rich_markup_mode="rich",
    add_completion=True,
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode",
    ),
    model_override: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override default model",
    ),
) -> None:
    """
    Agent Smith - Your AI coding assistant.

    Run without arguments to start interactive mode.
    Use subcommands for specific actions.
    """
    # Update settings from CLI args
    if verbose:
        settings.set("verbose", True)
    if debug:
        settings.set("debug", True)
        settings.set("log_level", "DEBUG")
    if model_override:
        settings.set("large_model", model_override)

    # If no subcommand, launch REPL
    if ctx.invoked_subcommand is None:
        launch_repl()


def launch_repl() -> None:
    """Launch the interactive REPL."""
    from .ui import AgentSmithApp

    # Check for API key
    provider = settings.get("default_provider", "anthropic")
    api_key = get_api_key(provider)

    if not api_key:
        console.print(
            Panel(
                f"[red]No API key found for {provider}[/red]\n\n"
                f"Set it with: [cyan]smith config set {provider}_api_key YOUR_KEY[/cyan]\n"
                f"Or set environment variable: [cyan]SMITH_{provider.upper()}_API_KEY[/cyan]",
                title="⚠️  API Key Required",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Launch Textual app
    model = settings.get("large_model")
    app = AgentSmithApp(provider=provider, model=model)
    app.run()


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__

    console.print(
        Panel(
            f"[bold]Agent Smith[/bold] v{__version__}\n"
            f"Python implementation\n\n"
            f"[dim]Paths:[/dim]\n"
            f"  Config: {AppPaths.CONFIG_DIR}\n"
            f"  Data: {AppPaths.DATA_DIR}\n"
            f"  Cache: {AppPaths.CACHE_DIR}\n"
            f"  Logs: {AppPaths.LOG_DIR}",
            title="ℹ️  Version Info",
            border_style="blue",
        )
    )


@app.command()
def config(
    action: str = typer.Argument(..., help="Action: show, set, get, edit, path, reset"),
    key: str | None = typer.Argument(None, help="Configuration key"),
    value: str | None = typer.Argument(None, help="Value to set"),
    keyring: bool = typer.Option(
        False, "--keyring", help="Store in system keyring (for API keys)"
    ),
) -> None:
    """Manage Agent Smith configuration."""
    from rich.table import Table

    if action == "show":
        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Show key settings (hide sensitive data)
        table.add_row("Default Provider", str(settings.default_provider))
        table.add_row("Large Model", str(settings.large_model))
        table.add_row("Small Model", str(settings.small_model))
        table.add_row("Max Parallel Tools", str(settings.max_parallel_tools))
        table.add_row("Show Cost", str(settings.show_cost))
        table.add_row("Prompt Caching", str(settings.enable_prompt_caching))
        table.add_row("Verbose", str(settings.verbose))
        table.add_row("Debug", str(settings.debug))

        # Show API key status (masked)
        for provider in ["anthropic", "openai"]:
            api_key = get_api_key(provider)
            status = "✅ Set" if api_key else "❌ Not set"
            table.add_row(f"{provider.title()} API Key", status)

        console.print(table)
        console.print(f"\n[dim]Config file: {AppPaths.SETTINGS_FILE}[/dim]")

    elif action == "set":
        if not key or not value:
            console.print("[red]Error: Both key and value required for 'set'[/red]")
            raise typer.Exit(1)

        # Handle API keys specially
        if key.endswith("_api_key"):
            provider = key.replace("_api_key", "")
            set_api_key(provider, value, use_keyring=keyring)
            console.print(f"[green]✓[/green] API key for {provider} set successfully")
            if keyring:
                console.print("[dim]Stored in system keyring[/dim]")
            else:
                console.print(f"[dim]Stored in {AppPaths.SECRETS_FILE}[/dim]")
        else:
            # Update regular setting
            settings.set(key, value)
            console.print(f"[green]✓[/green] {key} = {value}")

    elif action == "get":
        if not key:
            console.print("[red]Error: Key required for 'get'[/red]")
            raise typer.Exit(1)

        value = settings.get(key)
        if value is not None:
            # Mask API keys
            if "api_key" in key and value:
                value = f"{value[:8]}...{value[-4:]}"
            console.print(f"{key} = [green]{value}[/green]")
        else:
            console.print(f"[red]Key '{key}' not found[/red]")

    elif action == "edit":
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(AppPaths.SETTINGS_FILE)])

    elif action == "path":
        table = Table(title="Agent Smith Paths", show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="green")

        table.add_row("Config Directory", str(AppPaths.CONFIG_DIR))
        table.add_row("Data Directory", str(AppPaths.DATA_DIR))
        table.add_row("Cache Directory", str(AppPaths.CACHE_DIR))
        table.add_row("Log Directory", str(AppPaths.LOG_DIR))
        table.add_row("", "")
        table.add_row("Settings File", str(AppPaths.SETTINGS_FILE))
        table.add_row("Secrets File", str(AppPaths.SECRETS_FILE))
        table.add_row("Providers File", str(AppPaths.PROVIDERS_FILE))
        table.add_row("Log File", str(AppPaths.LOG_FILE))

        console.print(table)

    elif action == "reset":
        confirm = typer.confirm(
            "This will delete configuration files. Continue?", default=False
        )
        if confirm:
            for file in [
                AppPaths.SETTINGS_FILE,
                AppPaths.PROVIDERS_FILE,
                AppPaths.PERMISSIONS_FILE,
            ]:
                if file.exists():
                    file.unlink()

            console.print("[green]✓[/green] Configuration reset to defaults")
            console.print("[dim]API keys in .secrets.toml were preserved[/dim]")
        else:
            console.print("Cancelled")

    else:
        console.print(
            f"[red]Unknown action '{action}'. Use: show, set, get, edit, path, reset[/red]"
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
