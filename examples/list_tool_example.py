#!/usr/bin/env python3
"""Example demonstrating ListTool."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.tools import ListTool


async def main():
    """Demonstrate ListTool."""
    print("🤖 Agent Smith - List Tool Example\n")

    list_tool = ListTool()

    # 1. List current directory
    print("1️⃣  Listing current directory...")
    result = await list_tool.execute(path=".")
    print(result.content)
    print()

    # 2. List with different sorting
    print("2️⃣  Listing sorted by size...")
    result = await list_tool.execute(path=".", sort_by="size")
    print(result.content[:500])  # Show first 500 chars
    print()

    # 3. List Python files directory
    print("3️⃣  Listing src/agent_smith directory...")
    result = await list_tool.execute(path="src/agent_smith")
    print(result.content)
    print()

    # 4. Recursive listing
    print("4️⃣  Recursive listing of tools...")
    result = await list_tool.execute(
        path="src/agent_smith/tools", recursive=True, sort_by="name"
    )
    print(result.content)
    print()

    # 5. Show hidden files
    print("5️⃣  Listing with hidden files...")
    result = await list_tool.execute(path=".", show_hidden=True)
    print(result.content[:500])  # Show first 500 chars
    print()

    print("✅ All List tool operations completed!")


if __name__ == "__main__":
    asyncio.run(main())
