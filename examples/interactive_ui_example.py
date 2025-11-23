#!/usr/bin/env python3
"""Example demonstrating the interactive Textual UI.

This example shows how to launch the Agent Smith terminal UI.
The UI provides:
- Interactive REPL with message history
- Real-time tool execution display
- Token usage tracking
- Command system (/help, /clear, /reset, /model, /cost, /tools)
- Keyboard shortcuts (Ctrl+C to quit, F1 for help)

Usage:
    python examples/interactive_ui_example.py

Or use the CLI directly:
    smith                    # Launch interactive UI
    agent-smith             # Alternative command
    smith --model gpt-4     # Override model
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.config import get_api_key
from agent_smith.ui import AgentSmithApp


def main():
    """Launch the Agent Smith interactive UI."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print("\nSet it with: smith config set anthropic_api_key YOUR_KEY")
        print("Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY")
        return

    print("🤖 Launching Agent Smith Interactive UI...")
    print("\nKeyboard shortcuts:")
    print("  Ctrl+C / Ctrl+D - Quit")
    print("  F1 - Help")
    print("\nCommands:")
    print("  /help   - Show help")
    print("  /clear  - Clear messages")
    print("  /reset  - Reset conversation")
    print("  /model  - Show current model")
    print("  /cost   - Show token usage")
    print("  /tools  - List available tools")
    print("\nStarting app...")
    print("-" * 60)

    # Launch the Textual app
    app = AgentSmithApp(provider="anthropic")
    app.run()


if __name__ == "__main__":
    main()
