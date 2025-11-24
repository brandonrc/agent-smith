"""Advanced message rendering for different content types.

This module provides intelligent rendering of various message types
including text, code, tool use, errors, and more.
"""

import re
from typing import Any

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from .components import format_tool_result, format_tool_use


class MessageRenderer:
    """Handles rendering of different message types with appropriate styling."""

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": [r"def ", r"class ", r"import ", r"from .+ import"],
        "javascript": [r"function ", r"const ", r"let ", r"var ", r"=>"],
        "typescript": [r"interface ", r"type ", r"enum ", r": string", r": number"],
        "rust": [r"fn ", r"impl ", r"pub ", r"mut ", r"let mut"],
        "go": [r"func ", r"package ", r"import \(", r":="],
        "java": [r"public class", r"private ", r"protected ", r"@Override"],
        "cpp": [r"#include", r"std::", r"template<", r"namespace"],
        "c": [r"#include", r"int main", r"void ", r"struct "],
        "shell": [r"#!/bin/bash", r"#!/bin/sh", r"\$\(", r"export "],
        "sql": [r"SELECT ", r"INSERT ", r"UPDATE ", r"DELETE ", r"CREATE TABLE"],
        "json": [r"^\s*\{", r"^\s*\[", r'":\s*"', r'":\s*\d+'],
        "yaml": [r"^[a-z_]+:", r"^\s+-\s+", r"^---"],
        "markdown": [r"^#+\s+", r"^\*\*", r"^-\s+", r"^\d+\."],
        "diff": [r"^diff --git", r"^\+\+\+", r"^---", r"^@@"],
    }

    def __init__(self):
        """Initialize message renderer."""
        pass

    def detect_language(self, code: str) -> str:
        """Detect programming language from code content.

        Args:
            code: Code text to analyze

        Returns:
            Detected language name or 'text' if unknown
        """
        code_lines = code.split("\n")

        # Check for explicit language markers in markdown
        if code.strip().startswith("```"):
            first_line = code_lines[0].strip()
            if len(first_line) > 3:
                lang = first_line[3:].strip()
                if lang:
                    return lang

        # Try to detect language by patterns
        scores = {}
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[lang] = score

        if scores:
            # Return language with highest score
            return max(scores.items(), key=lambda x: x[1])[0]

        return "text"

    def extract_code_blocks(self, text: str) -> list[tuple[str, str, str]]:
        """Extract code blocks from markdown text.

        Args:
            text: Text containing markdown code blocks

        Returns:
            List of (before_text, code, language) tuples
        """
        # Pattern for markdown code blocks
        pattern = r"```(\w+)?\n(.*?)```"
        matches = list(re.finditer(pattern, text, re.DOTALL))

        if not matches:
            return []

        blocks = []
        last_end = 0

        for match in matches:
            before_text = text[last_end : match.start()].strip()
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append((before_text, code, language))
            last_end = match.end()

        # Add remaining text if any
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                blocks.append((remaining, "", ""))

        return blocks

    def render_message(
        self,
        content: str,
        role: str = "assistant",
        message_type: str = "text",
    ) -> RenderableType:
        """Render a message with appropriate styling.

        Args:
            content: Message content
            role: Message role (user/assistant)
            message_type: Type of message (text/code/error/tool_use/etc)

        Returns:
            Renderable object for display
        """
        if message_type == "error":
            return self.render_error(content)
        elif message_type == "code":
            return self.render_code(content)
        elif message_type == "diff":
            return self.render_diff(content)
        elif message_type == "tool_use":
            return self.render_tool_use(content)
        elif message_type == "tool_result":
            return self.render_tool_result(content)
        else:
            return self.render_text(content, role)

    def render_text(self, text: str, role: str = "assistant") -> RenderableType:
        """Render plain text or markdown with code block extraction.

        Args:
            text: Text content
            role: Message role

        Returns:
            Renderable object
        """
        # Check if text contains code blocks
        code_blocks = self.extract_code_blocks(text)

        if code_blocks:
            # Render text and code blocks separately
            renderables = []

            for before_text, code, language in code_blocks:
                if before_text:
                    renderables.append(Markdown(before_text, code_theme="monokai"))

                if code:
                    detected_lang = (
                        language if language != "text" else self.detect_language(code)
                    )
                    renderables.append(
                        Syntax(
                            code,
                            detected_lang,
                            theme="monokai",
                            line_numbers=True,
                            word_wrap=False,
                        )
                    )

            return Group(*renderables) if len(renderables) > 1 else renderables[0]
        else:
            # Check if entire content looks like code
            if self._looks_like_code(text):
                language = self.detect_language(text)
                return Syntax(
                    text,
                    language,
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=False,
                )
            else:
                # Render as markdown
                return Markdown(text, code_theme="monokai", inline_code_theme="monokai")

    def render_code(self, code: str, language: str | None = None) -> Syntax:
        """Render code with syntax highlighting.

        Args:
            code: Code text
            language: Programming language (auto-detect if None)

        Returns:
            Syntax-highlighted code
        """
        if language is None:
            language = self.detect_language(code)

        return Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=False,
        )

    def render_diff(self, diff_text: str) -> Syntax:
        """Render a diff with appropriate highlighting.

        Args:
            diff_text: Diff content

        Returns:
            Syntax-highlighted diff
        """
        return Syntax(
            diff_text,
            "diff",
            theme="monokai",
            line_numbers=False,
            word_wrap=False,
        )

    def render_error(self, error_text: str) -> Panel:
        """Render an error message.

        Args:
            error_text: Error message

        Returns:
            Styled error panel
        """
        return Panel(
            Text(error_text, style="bold red"),
            title="⚠️  Error",
            border_style="red",
            padding=(0, 1),
        )

    def render_tool_use(self, tool_data: dict[str, Any]) -> Panel:
        """Render a tool use message.

        Args:
            tool_data: Tool use data with name and arguments

        Returns:
            Formatted tool use panel
        """
        tool_name = tool_data.get("name", "Unknown")
        arguments = tool_data.get("arguments", {})
        return format_tool_use(tool_name, arguments)

    def render_tool_result(self, result_data: dict[str, Any]) -> Panel:
        """Render a tool result message.

        Args:
            result_data: Tool result data

        Returns:
            Formatted tool result panel
        """
        tool_name = result_data.get("tool_name", "Unknown")
        result = result_data.get("result", "")
        is_error = result_data.get("is_error", False)
        return format_tool_result(tool_name, result, is_error)

    def render_streaming_text(self, text: str) -> Text:
        """Render streaming text chunk.

        Args:
            text: Text chunk

        Returns:
            Styled text
        """
        return Text(text, style="white")

    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code rather than prose.

        Args:
            text: Text to analyze

        Returns:
            True if text appears to be code
        """
        # Heuristics for code detection
        indicators = [
            len(text.split("\n")) > 3,  # Multiple lines
            "{" in text and "}" in text,  # Braces
            "def " in text or "function " in text,  # Function definitions
            "import " in text or "#include" in text,  # Imports
            "class " in text or "interface " in text,  # Class definitions
            text.count(";") > 2,  # Multiple semicolons
            re.search(r"^\s{4,}", text, re.MULTILINE) is not None,  # Deep indentation
        ]

        # If multiple indicators are true, likely code
        return sum(indicators) >= 3

    def render_assistant_message(self, content: str) -> Panel:
        """Render a complete assistant message with panel.

        Args:
            content: Message content

        Returns:
            Styled panel with assistant message
        """
        rendered_content = self.render_text(content, "assistant")

        return Panel(
            rendered_content,
            title="[bold green]Agent Smith[/bold green]",
            border_style="green",
            padding=(0, 1),
        )

    def render_user_message(self, content: str) -> Panel:
        """Render a complete user message with panel.

        Args:
            content: Message content

        Returns:
            Styled panel with user message
        """
        rendered_content = Markdown(content, code_theme="monokai")

        return Panel(
            rendered_content,
            title="[bold cyan]You[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        )


# Global renderer instance
message_renderer = MessageRenderer()


def format_diff_viewer(diff_text: str) -> Syntax:
    """Convenience function for diff rendering.

    Args:
        diff_text: Diff content

    Returns:
        Rendered diff
    """
    return message_renderer.render_diff(diff_text)
