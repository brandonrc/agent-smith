#!/usr/bin/env python3
"""Example demonstrating all Agent Smith tools."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.config import get_api_key
from agent_smith.models import Message
from agent_smith.query import QueryOrchestrator
from agent_smith.tools import default_tools


async def main():
    """Demonstrate all tools."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print(
            "\nSet it with: smith config set anthropic_api_key YOUR_KEY\n"
            "Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY"
        )
        return

    print("🤖 Agent Smith - All Tools Example\n")
    print("=" * 60)
    print("Available tools:")
    for tool in default_tools.list_tools():
        print(f"  - {tool.name}: {tool.description.split('.')[0]}")
    print("=" * 60)
    print()

    # Create orchestrator with all default tools
    async with QueryOrchestrator(provider="anthropic") as orchestrator:
        # Example query that uses multiple tools
        messages = [
            Message.user(
                """Please analyze this Python project:

1. Find all Python files (use Glob tool)
2. Search for any TODO comments (use Grep tool)
3. Read the pyproject.toml file (use Read tool)
4. Show me the project structure

Be thorough and use the appropriate tools for each task."""
            )
        ]

        print("User: Analyze this Python project...\n")

        async for event in orchestrator.query(
            messages=messages,
            system="You are a helpful coding assistant. Use the appropriate tools for each task.",
            tools=default_tools.list_tools(),
        ):
            if event["type"] == "tool_execution_start":
                print(f"\n🔧 Executing {event['count']} tool(s)...")

            elif event["type"] == "tool_use_result":
                tool_name = event["name"]
                result = event["result"]
                status = "✅" if not result.is_error else "❌"

                print(f"{status} {tool_name}")
                if result.is_error:
                    print(f"   Error: {result.content}")

            elif event["type"] == "message_complete":
                message = event["message"]
                # Extract text
                print("\n" + "=" * 60)
                print("Claude's Response:")
                print("=" * 60)
                for block in message.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        print(block["text"])
                print("=" * 60)

            elif event["type"] == "usage":
                usage = event["total_usage"]
                print(
                    f"\n📊 Total Tokens: {usage.input_tokens + usage.output_tokens} "
                    f"(in: {usage.input_tokens}, out: {usage.output_tokens})"
                )


if __name__ == "__main__":
    asyncio.run(main())
