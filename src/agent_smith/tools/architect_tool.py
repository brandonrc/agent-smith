"""Architect Tool for high-level technical planning and architecture design.

This tool creates detailed implementation plans by analyzing requirements
and breaking them down into actionable steps. It uses a subset of read-only
tools to explore the codebase before generating the plan.
"""

import logging
from typing import Any

from agent_smith.models import Message, ToolResult
from agent_smith.query import QueryOrchestrator

from .base import BaseTool

logger = logging.getLogger(__name__)

ARCHITECT_SYSTEM_PROMPT = """You are an expert software architect. Your role is to analyze technical requirements and produce clear, actionable implementation plans.
These plans will then be carried out by a junior software engineer so you need to be specific and detailed. However do not actually write the code, just explain the plan.

Follow these steps for each request:
1. Carefully analyze requirements to identify core functionality and constraints
2. Define clear technical approach with specific technologies and patterns
3. Break down implementation into concrete, actionable steps at the appropriate level of abstraction

Keep responses focused, specific and actionable.

IMPORTANT: Do not ask the user if you should implement the changes at the end. Just provide the plan as described above.
IMPORTANT: Do not attempt to write the code or use any string modification tools. Just provide the plan."""

DESCRIPTION = """Your go-to tool for any technical or coding task. Analyzes requirements and breaks them down into clear, actionable implementation steps. Use this whenever you need help planning how to implement a feature, solve a technical problem, or structure your code."""


class ArchitectTool(BaseTool):
    """Tool for generating detailed technical implementation plans.

    This tool creates a separate LLM context with limited read-only tools
    to explore the codebase and generate comprehensive implementation plans.
    It prevents the architect from making changes, only analyzing and planning.
    """

    def __init__(self):
        """Initialize the Architect tool."""
        self._name = "Architect"
        self._description = DESCRIPTION

        # Define allowed exploration tools (read-only filesystem tools)
        self._allowed_tools = [
            "Bash",
            "List",
            "FileRead",
            "Glob",
            "Grep",
        ]

    @property
    def name(self) -> str:
        """Tool name for LLM."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool inputs."""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The technical request or coding task to analyze",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context from previous conversation or system state",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, prompt: str, context: str | None = None, **kwargs: Any) -> ToolResult:
        """Execute the architect tool to generate an implementation plan.

        This creates a new LLM query context with only read-only tools,
        allowing the architect to explore the codebase without making changes.

        Args:
            prompt: The technical request or coding task to analyze
            context: Optional additional context
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResult containing the implementation plan
        """
        try:
            logger.info("Architect tool: Starting implementation plan generation")

            # Construct the full prompt with context if provided
            full_prompt = prompt
            if context:
                full_prompt = f"<context>{context}</context>\n\n{prompt}"

            # Create a message for the architect
            architect_message = Message.user(full_prompt)

            # Import here to avoid circular imports
            from agent_smith.config import settings
            from agent_smith.tools import default_tools

            # Get the current provider and model from settings
            provider = settings.get("default_provider", "anthropic")
            model = settings.get("large_model")

            # Create a new orchestrator for the architect's context
            orchestrator = QueryOrchestrator(provider=provider, model=model)

            # Filter to only read-only exploration tools
            allowed_tools = [
                tool
                for tool in default_tools.list_tools()
                if tool.name in self._allowed_tools
            ]

            logger.debug(
                f"Architect tool: Using {len(allowed_tools)} read-only tools: {[t.name for t in allowed_tools]}"
            )

            # Execute the query with the architect system prompt
            messages = [architect_message]
            system_prompt = ARCHITECT_SYSTEM_PROMPT

            # Collect the response
            response_parts = []

            async for event in orchestrator.query(
                messages=messages,
                system=system_prompt,
                tools=allowed_tools,
            ):
                if event["type"] == "message_complete":
                    message = event["message"]
                    # Extract text from content blocks
                    for block in message.content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                response_parts.append(block["text"])
                        elif hasattr(block, "type") and block.type == "text":
                            response_parts.append(block.text)

            # Combine all response parts
            plan = "\n\n".join(response_parts)

            if not plan:
                logger.warning("Architect tool: No plan generated")
                return ToolResult.error("Failed to generate implementation plan")

            logger.info("Architect tool: Successfully generated implementation plan")
            return ToolResult.success(plan)

        except Exception as e:
            logger.error(f"Architect tool: Error generating plan: {e}")
            return ToolResult.error(f"Failed to generate implementation plan: {str(e)}")

    async def requires_permission(self, **kwargs: Any) -> bool:
        """Architect tool doesn't require permission (read-only).

        Returns:
            False - no permission needed for read-only planning
        """
        return False

    def __repr__(self) -> str:
        """String representation of ArchitectTool."""
        return f"ArchitectTool(name={self.name!r})"
