"""Fixed tests for tool system."""

import tempfile
from pathlib import Path

import pytest

from agent_smith.models import ToolResult
from agent_smith.tools import (
    BashTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    ThinkTool,
    ToolRegistry,
    default_tools,
)


def test_tool_registry_creation():
    """Test creating a tool registry."""
    registry = ToolRegistry()
    assert registry is not None
    assert isinstance(registry.list_tools(), list)


def test_tool_registry_registration():
    """Test registering tools."""
    registry = ToolRegistry()
    tool = BashTool()
    registry.register(tool)

    tools = registry.list_tools()
    assert len(tools) > 0
    assert any(t.name == "Bash" for t in tools)


def test_default_tools_loaded():
    """Test that default tools are loaded."""
    tools = default_tools.list_tools()
    assert len(tools) == 9  # We have 9 tools

    tool_names = [t.name for t in tools]
    assert "Bash" in tool_names
    assert "Read" in tool_names
    assert "Write" in tool_names


@pytest.mark.asyncio
async def test_bash_tool_simple_command():
    """Test executing a simple bash command."""
    tool = BashTool()
    result = await tool.execute(command="echo 'test'", description="Test echo")

    assert isinstance(result, ToolResult)
    assert result.is_error is False
    assert "test" in result.content


@pytest.mark.asyncio
async def test_file_write_and_read():
    """Test writing and reading a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")
        content = "Hello, World!"

        # Write file
        write_tool = FileWriteTool()
        write_result = await write_tool.execute(file_path=file_path, content=content)
        assert write_result.is_error is False

        # Read file
        read_tool = FileReadTool()
        read_result = await read_tool.execute(file_path=file_path)
        assert read_result.is_error is False
        assert content in read_result.content


@pytest.mark.asyncio
async def test_file_edit():
    """Test editing a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")

        # Create initial file
        write_tool = FileWriteTool()
        await write_tool.execute(file_path=file_path, content="Hello World")

        # Edit file
        edit_tool = FileEditTool()
        edit_result = await edit_tool.execute(
            file_path=file_path, old_string="World", new_string="Python"
        )
        assert edit_result.is_error is False

        # Verify edit
        read_tool = FileReadTool()
        read_result = await read_tool.execute(file_path=file_path)
        assert "Python" in read_result.content
        assert "World" not in read_result.content


@pytest.mark.asyncio
async def test_think_tool():
    """Test think tool for reasoning."""
    tool = ThinkTool()
    result = await tool.execute(thoughts="Planning the implementation...")

    assert result.is_error is False
    # ThinkTool returns a summary message, not the original thoughts
    assert isinstance(result.content, str)


@pytest.mark.asyncio
async def test_tool_input_schema():
    """Test that tools have proper input schemas."""
    tool = BashTool()
    schema = tool.input_schema

    assert "type" in schema
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "command" in schema["properties"]
