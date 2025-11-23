"""Query orchestration for LLM interactions with tool execution."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from .config import settings
from .models import (
    APIUsage,
    Message,
    MessageResponse,
    Tool,
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)
from .services import ClaudeService, OpenAIService


class QueryOrchestrator:
    """Orchestrates LLM queries with tool execution."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        max_iterations: int | None = None,
    ):
        """
        Initialize query orchestrator.

        Args:
            provider: LLM provider ('anthropic' or 'openai')
            model: Model name to use
            api_key: API key for the provider
            max_iterations: Maximum tool use iterations (default: 25)
        """
        self.provider = provider or settings.get("default_provider", "anthropic")
        self.model = model or settings.get("large_model")
        self.max_parallel_tools = settings.get("max_parallel_tools", 10)
        self.max_iterations = max_iterations or 25  # Prevent infinite loops

        # Initialize appropriate service
        if self.provider == "anthropic":
            self.service: ClaudeService | OpenAIService = ClaudeService(api_key)
        elif self.provider == "openai":
            self.service = OpenAIService(api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Track usage
        self.total_usage = APIUsage()

    async def query(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[Tool] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a query with tool support.

        This implements the agentic loop:
        1. Send message to LLM
        2. If LLM wants to use tools, execute them
        3. Send tool results back to LLM
        4. Repeat until LLM returns final answer

        Args:
            messages: Conversation history
            system: System prompt
            tools: Available tools
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Yields:
            Events during query execution:
            - {"type": "text_delta", "text": str}
            - {"type": "tool_use_start", "tool": str, "id": str}
            - {"type": "tool_use_result", "id": str, "result": ToolResult}
            - {"type": "message_complete", "message": MessageResponse}
            - {"type": "usage", "usage": APIUsage}
        """
        # Convert tools to definitions
        tool_definitions = None
        tool_map = {}
        if tools:
            tool_definitions = [ToolDefinition.from_tool(tool) for tool in tools]
            tool_map = {tool.name: tool for tool in tools}

        # Track conversation
        conversation = messages.copy()
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # Get response from LLM
            response = await self.service.create_message(
                messages=conversation,
                system=system,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tool_definitions,
                stream=False,
            )

            if not isinstance(response, MessageResponse):
                raise TypeError("Expected MessageResponse from non-streaming call")

            # Update usage
            usage = APIUsage.from_dict(response.usage)
            self.total_usage = self.total_usage.add(usage)

            yield {
                "type": "usage",
                "usage": usage,
                "total_usage": self.total_usage,
            }

            # Check for tool use
            tool_uses = self._extract_tool_uses(response)

            if not tool_uses:
                # No tool use, we're done
                yield {
                    "type": "message_complete",
                    "message": response,
                    "stop_reason": response.stop_reason,
                }
                break

            # Execute tools in parallel (up to max_parallel_tools)
            yield {"type": "tool_execution_start", "count": len(tool_uses)}

            tool_results = await self._execute_tools_parallel(
                tool_uses, tool_map, max_parallel=self.max_parallel_tools
            )

            # Yield tool results
            for tool_use, result in zip(tool_uses, tool_results):
                yield {
                    "type": "tool_use_result",
                    "id": tool_use.id,
                    "name": tool_use.name,
                    "result": result,
                }

            # Add assistant message and tool results to conversation
            conversation.append(response.to_message())

            # Add tool results as user message
            tool_result_blocks = [
                ToolResultBlock(
                    tool_use_id=tool_use.id,
                    content=result.content,
                    is_error=result.is_error,
                )
                for tool_use, result in zip(tool_uses, tool_results)
            ]

            conversation.append(Message.user(tool_result_blocks))  # type: ignore

            # Continue loop to get next response

        if iterations >= self.max_iterations:
            yield {
                "type": "error",
                "error": f"Max iterations ({self.max_iterations}) reached",
            }

    def _extract_tool_uses(self, response: MessageResponse) -> list[ToolUseBlock]:
        """Extract tool use blocks from response."""
        tool_uses = []
        for block in response.content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_uses.append(
                    ToolUseBlock(
                        id=block["id"],
                        name=block["name"],
                        input=block["input"],
                    )
                )
            elif isinstance(block, ToolUseBlock):
                tool_uses.append(block)
        return tool_uses

    async def _execute_tools_parallel(
        self,
        tool_uses: list[ToolUseBlock],
        tool_map: dict[str, Tool],
        max_parallel: int = 10,
    ) -> list[Any]:
        """Execute multiple tools in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_with_semaphore(tool_use: ToolUseBlock) -> Any:
            async with semaphore:
                return await self._execute_tool(tool_use, tool_map)

        tasks = [execute_with_semaphore(tool_use) for tool_use in tool_uses]
        return await asyncio.gather(*tasks)

    async def _execute_tool(
        self, tool_use: ToolUseBlock, tool_map: dict[str, Tool]
    ) -> Any:
        """Execute a single tool."""
        from .models import ToolResult

        tool = tool_map.get(tool_use.name)
        if not tool:
            return ToolResult.error(f"Unknown tool: {tool_use.name}")

        try:
            # Check permissions (TODO: implement permission UI)
            requires_permission = await tool.requires_permission(**tool_use.input)
            if requires_permission:
                # For now, just execute - permission UI will be added later
                pass

            # Execute tool
            result = await tool.execute(**tool_use.input)
            return result
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {str(e)}")

    async def close(self) -> None:
        """Close the service."""
        await self.service.close()

    async def __aenter__(self) -> "QueryOrchestrator":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


async def simple_query(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    system: str | None = None,
    tools: list[Tool] | None = None,
) -> str:
    """
    Simple helper for one-shot queries.

    Args:
        prompt: User prompt
        provider: LLM provider
        model: Model to use
        system: System prompt
        tools: Available tools

    Returns:
        Text response from LLM
    """
    async with QueryOrchestrator(provider=provider, model=model) as orchestrator:
        messages = [Message.user(prompt)]
        response_text = []

        async for event in orchestrator.query(
            messages=messages, system=system, tools=tools
        ):
            if event["type"] == "message_complete":
                message = event["message"]
                # Extract text from content
                for block in message.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        response_text.append(block["text"])

        return "\n".join(response_text)
