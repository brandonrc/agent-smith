#!/usr/bin/env python3
"""Example demonstrating file operation tools."""
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.tools import (
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
)


async def main():
    """Demonstrate file operations."""
    print("🤖 Agent Smith - File Operations Example\n")

    # Create temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp(prefix="agent_smith_test_"))
    print(f"📁 Working in: {temp_dir}\n")

    try:
        # Initialize tools
        read_tool = FileReadTool()
        write_tool = FileWriteTool()
        edit_tool = FileEditTool()
        glob_tool = GlobTool()
        grep_tool = GrepTool()

        # 1. Create a test file
        print("1️⃣  Creating test file...")
        test_file = temp_dir / "example.py"
        content = """def hello():
    print("Hello, World!")

def add(a, b):
    # TODO: Add input validation
    return a + b

def main():
    hello()
    result = add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
        result = await write_tool.execute(file_path=str(test_file), content=content)
        print(f"   {result.content}\n")

        # 2. Read the file
        print("2️⃣  Reading file...")
        result = await read_tool.execute(file_path=str(test_file))
        print(f"   Lines read:\n{result.content[:200]}...\n")

        # 3. Search for files
        print("3️⃣  Finding Python files...")
        result = await glob_tool.execute(pattern="**/*.py", path=str(temp_dir))
        print(f"   {result.content}\n")

        # 4. Search for TODO comments
        print("4️⃣  Searching for TODO comments...")
        result = await grep_tool.execute(
            pattern="TODO",
            path=str(temp_dir),
            output_mode="content",
            context=1,
        )
        print(f"   {result.content}\n")

        # 5. Edit the file
        print("5️⃣  Editing file (replacing TODO)...")
        result = await edit_tool.execute(
            file_path=str(test_file),
            old_string="    # TODO: Add input validation",
            new_string="    # Input validation added\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\n        raise TypeError('Arguments must be numbers')",
        )
        print(f"   {result.content}\n")

        # 6. Read edited file
        print("6️⃣  Reading edited file...")
        result = await read_tool.execute(file_path=str(test_file))
        print(f"   Updated content:\n{result.content}\n")

        print("✅ All file operations completed successfully!")

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up {temp_dir}")
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    asyncio.run(main())
