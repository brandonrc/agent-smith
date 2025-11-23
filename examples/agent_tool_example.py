#!/usr/bin/env python3
"""Example demonstrating AgentTool (sub-agents)."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.config import get_api_key
from agent_smith.tools import AgentTool


async def main():
    """Demonstrate AgentTool."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print(
            "\nSet it with: smith config set anthropic_api_key YOUR_KEY\n"
            "Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY"
        )
        return

    print("🤖 Agent Smith - Agent Tool Example\n")
    print("Spawning a sub-agent to analyze the project...\n")

    agent_tool = AgentTool()

    # Spawn a sub-agent to perform a complex task
    result = await agent_tool.execute(
        description="Analyze Python project",
        prompt="""Analyze this Python project and provide a summary:

1. Find all Python files in the src/agent_smith directory
2. Count how many tools are implemented
3. Search for any TODO or FIXME comments
4. Provide a brief summary of what you found

Use the appropriate tools (Glob, Grep, Read) to gather this information.
Be thorough and provide specific details.""",
    )

    if result.is_error:
        print(f"❌ Agent failed: {result.content}")
    else:
        print("✅ Agent completed task!\n")
        print("=" * 60)
        print(result.content)
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
