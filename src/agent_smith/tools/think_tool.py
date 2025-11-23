"""Think tool for extended reasoning."""

from typing import Any

from ..models import ToolResult
from .base import BaseTool


class ThinkTool(BaseTool):
    """Enable extended thinking for complex problem-solving."""

    @property
    def name(self) -> str:
        return "Think"

    @property
    def description(self) -> str:
        return """Enable extended thinking for complex reasoning tasks.

Use this tool when you need to:
- Work through a complex problem step-by-step
- Analyze multiple options and trade-offs
- Plan a multi-step approach
- Reason about architecture or design decisions
- Think through edge cases and implications

The thinking process is private and helps you reason better before
providing your final response to the user.

Examples:
- "How should I refactor this authentication system?"
- "What are the pros/cons of different database choices?"
- "How can I optimize this algorithm?"

Usage:
Simply provide your thoughts in the 'thoughts' parameter. The content
is processed and helps inform your response, but the user only sees
your final answer.

Note: This is for your internal reasoning. After thinking, provide
your actual response in a normal message."""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "thoughts": {
                    "type": "string",
                    "description": "Your extended reasoning and thought process",
                },
            },
            "required": ["thoughts"],
        }

    async def execute(
        self,
        thoughts: str,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Process extended thinking.

        Args:
            thoughts: The reasoning content
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult acknowledging the thinking
        """
        # Calculate some basic stats
        word_count = len(thoughts.split())
        line_count = len(thoughts.splitlines())

        result = (
            f"Extended thinking recorded ({word_count} words, {line_count} lines).\n"
        )
        result += "Proceed with your response based on this reasoning."

        return ToolResult.success(result)

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        ThinkTool doesn't require permission (internal reasoning).

        Returns:
            False
        """
        return False
