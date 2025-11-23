"""Agent tool for spawning sub-agents to handle complex tasks."""

from typing import Any

from ..config import settings
from ..models import Message, ToolResult
from ..query import QueryOrchestrator
from .base import BaseTool


class AgentTool(BaseTool):
    """Launch sub-agents to handle complex, multi-step tasks autonomously."""

    def __init__(self, max_iterations: int = 15):
        """
        Initialize AgentTool.

        Args:
            max_iterations: Maximum iterations for sub-agent
        """
        self.max_iterations = max_iterations

    @property
    def name(self) -> str:
        return "Task"

    @property
    def description(self) -> str:
        return """Launch a specialized agent to handle complex, multi-step tasks autonomously.

Use this tool when:
- Task requires multiple steps or iterations
- Need to search/analyze without knowing exact file paths
- Want autonomous problem-solving for a subtask
- Task is complex and self-contained

The agent has access to all tools and can work independently.

Examples:
- "Find all authentication-related code and summarize the flow"
- "Search for error handling patterns and suggest improvements"
- "Analyze the test coverage and identify gaps"

IMPORTANT:
- Provide clear, detailed task description
- Agent will report back with findings
- Agent cannot see your conversation context
- Use for significant subtasks, not simple operations

When NOT to use:
- For specific file paths (use Read/Edit directly)
- For simple single-tool operations (use tool directly)
- For conversational responses (respond directly)"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short (3-5 word) description of the task",
                },
                "prompt": {
                    "type": "string",
                    "description": "Detailed task for the agent to perform autonomously. Include exactly what information to return.",
                },
            },
            "required": ["description", "prompt"],
        }

    async def execute(
        self,
        description: str,
        prompt: str,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Launch a sub-agent.

        Args:
            description: Short task description
            prompt: Detailed task prompt
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult with agent's findings
        """
        try:
            # Import here to avoid circular dependency
            from ..tools import default_tools

            # Create sub-agent with same provider
            provider = settings.get("default_provider", "anthropic")

            async with QueryOrchestrator(provider=provider) as agent:
                # Set max iterations for sub-agent
                agent.max_iterations = self.max_iterations

                messages = [Message.user(prompt)]

                # Collect all responses
                response_texts = []
                tool_executions = []

                async for event in agent.query(
                    messages=messages,
                    system="You are a helpful AI assistant tasked with completing a specific objective. "
                    "Use the available tools to gather information and complete the task. "
                    "Be thorough and autonomous. Report your findings clearly.",
                    tools=default_tools.list_tools(),
                ):
                    if event["type"] == "tool_use_result":
                        tool_executions.append(
                            f"- {event['name']}: {'✓' if not event['result'].is_error else '✗'}"
                        )

                    elif event["type"] == "message_complete":
                        message = event["message"]
                        # Extract text from content
                        for block in message.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                response_texts.append(block["text"])

                # Format result
                result = f"[Sub-agent: {description}]\n\n"

                if tool_executions:
                    result += "Tools used:\n" + "\n".join(tool_executions) + "\n\n"

                result += "Findings:\n"
                result += "\n\n".join(response_texts)

                return ToolResult.success(result)

        except Exception as e:
            return ToolResult.error(f"Sub-agent failed: {str(e)}")

    async def requires_permission(self, **kwargs: Any) -> bool:
        """
        AgentTool doesn't require permission (sub-agent uses same permissions).

        Returns:
            False
        """
        return False
