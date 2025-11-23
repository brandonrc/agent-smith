#!/usr/bin/env python3
"""Example of using tools with Agent Smith."""
import asyncio
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.config import get_api_key
from agent_smith.models import Message, ToolResult
from agent_smith.query import QueryOrchestrator


# Example tool: Calculator
class CalculatorTool:
    """Simple calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform basic arithmetic operations (add, subtract, multiply, divide)"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The arithmetic operation to perform",
                },
                "a": {
                    "type": "number",
                    "description": "First number",
                },
                "b": {
                    "type": "number",
                    "description": "Second number",
                },
            },
            "required": ["operation", "a", "b"],
        }

    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        """Execute the calculation."""
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return ToolResult.error("Cannot divide by zero")
                result = a / b
            else:
                return ToolResult.error(f"Unknown operation: {operation}")

            return ToolResult.success(f"Result: {a} {operation} {b} = {result}")
        except Exception as e:
            return ToolResult.error(f"Calculation failed: {str(e)}")

    async def requires_permission(self, **kwargs: Any) -> bool:
        """Calculator doesn't need permission."""
        return False


async def main():
    """Run tool example."""
    # Check if API key is configured
    api_key = get_api_key("anthropic")
    if not api_key:
        print("❌ No Anthropic API key found!")
        print(
            "\nSet it with: smith config set anthropic_api_key YOUR_KEY\n"
            "Or: export SMITH_ANTHROPIC_API_KEY=YOUR_KEY"
        )
        return

    print("🤖 Agent Smith - Tool Usage Example\n")
    print("Asking Claude to use the calculator tool...\n")

    # Create calculator tool
    calculator = CalculatorTool()

    # Create orchestrator
    async with QueryOrchestrator(provider="anthropic") as orchestrator:
        messages = [
            Message.user(
                "What is 42 multiplied by 17? Use the calculator tool to compute it."
            )
        ]

        print("User: What is 42 multiplied by 17?\n")

        async for event in orchestrator.query(
            messages=messages,
            system="You are a helpful assistant. Always use the calculator tool for math operations.",
            tools=[calculator],
        ):
            if event["type"] == "tool_execution_start":
                print(f"🔧 Executing {event['count']} tool(s)...")

            elif event["type"] == "tool_use_result":
                print(f"  ✓ {event['name']}: {event['result'].content}")

            elif event["type"] == "message_complete":
                message = event["message"]
                # Extract text
                for block in message.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        print(f"\nClaude: {block['text']}\n")

            elif event["type"] == "usage":
                usage = event["usage"]
                print(
                    f"[Tokens: input={usage.input_tokens}, output={usage.output_tokens}]"
                )


if __name__ == "__main__":
    asyncio.run(main())
