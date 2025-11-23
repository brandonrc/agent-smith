#!/usr/bin/env python3
"""Example demonstrating advanced tools (Agent, Think, List)."""
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
    """Demonstrate advanced tools."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print(
            "\nSet it with: smith config set anthropic_api_key YOUR_KEY\n"
            "Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY"
        )
        return

    print("🤖 Agent Smith - Advanced Tools Example\n")
    print("=" * 60)
    print("Testing: AgentTool, ThinkTool, ListTool")
    print("=" * 60)
    print()

    # Create orchestrator with all tools
    async with QueryOrchestrator(provider="anthropic") as orchestrator:
        # Example query that demonstrates advanced tools
        messages = [
            Message.user(
                """Please help me analyze this Python project:

1. First, use the Think tool to plan your approach
2. Use the List tool to see the project structure
3. Use the Agent tool to spawn a sub-agent that will:
   - Find all Python files
   - Search for any TODO or FIXME comments
   - Summarize what needs attention

Be systematic and show your thought process."""
            )
        ]

        print("User: Analyze this project using advanced tools...\n")

        current_iteration = 0

        async for event in orchestrator.query(
            messages=messages,
            system="You are a helpful coding assistant. Use tools to complete tasks efficiently. "
            "Use Think tool for planning, List tool for directory info, and Agent tool for complex subtasks.",
            tools=default_tools.list_tools(),
        ):
            if event["type"] == "tool_execution_start":
                current_iteration += 1
                print(
                    f"\n🔧 Iteration {current_iteration}: Executing {event['count']} tool(s)..."
                )

            elif event["type"] == "tool_use_result":
                tool_name = event["name"]
                result = event["result"]
                status = "✅" if not result.is_error else "❌"

                print(f"{status} {tool_name}")

                # Show preview of result
                if not result.is_error:
                    content = result.content
                    if len(content) > 200:
                        preview = content[:200] + "..."
                    else:
                        preview = content
                    print(f"   Preview: {preview}")
                else:
                    print(f"   Error: {result.content}")

            elif event["type"] == "message_complete":
                message = event["message"]
                print("\n" + "=" * 60)
                print("Claude's Response:")
                print("=" * 60)
                for block in message.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        print(block["text"])
                print("=" * 60)

            elif event["type"] == "usage":
                total_usage = event["total_usage"]
                print(
                    f"\n📊 Total Tokens: {total_usage.input_tokens + total_usage.output_tokens} "
                    f"(in: {total_usage.input_tokens}, out: {total_usage.output_tokens})"
                )


if __name__ == "__main__":
    asyncio.run(main())
