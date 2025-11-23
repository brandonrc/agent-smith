#!/usr/bin/env python3
"""Simple example of using Agent Smith query."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.config import get_api_key
from agent_smith.query import simple_query


async def main():
    """Run a simple query."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print(
            "\nSet it with: smith config set anthropic_api_key YOUR_KEY\n"
            "Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY"
        )
        return

    print("🤖 Agent Smith - Simple Query Example\n")
    print("Asking Claude a question...\n")

    # Simple query
    response = await simple_query(
        prompt="What is the capital of France? Answer in one sentence.",
        provider="anthropic",
        system="You are a helpful assistant. Be concise.",
    )

    print(f"Claude: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
