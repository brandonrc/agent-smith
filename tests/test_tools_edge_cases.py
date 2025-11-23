"""Edge case tests for tool system."""

import tempfile
from pathlib import Path

import pytest

from agent_smith.tools import (
    BashTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
    ListTool,
    ToolRegistry,
)


@pytest.mark.asyncio
async def test_bash_tool_command_not_found():
    """Test bash tool with non-existent command."""
    tool = BashTool()
    result = await tool.execute(command="nonexistentcommand12345")
    # Should return error
    assert result.is_error is True


@pytest.mark.asyncio
async def test_bash_tool_syntax_error():
    """Test bash tool with syntax error."""
    tool = BashTool()
    result = await tool.execute(command="echo 'unclosed quote")
    # May or may not error depending on shell, but should not crash
    assert result is not None


@pytest.mark.asyncio
async def test_bash_tool_empty_command():
    """Test bash tool with empty command."""
    tool = BashTool()
    result = await tool.execute(command="")
    # Should handle gracefully
    assert result is not None


@pytest.mark.asyncio
async def test_file_read_nonexistent():
    """Test reading non-existent file."""
    tool = FileReadTool()
    result = await tool.execute(file_path="/tmp/nonexistent_file_xyz123.txt")
    assert result.is_error is True
    assert (
        "not found" in result.content.lower()
        or "no such file" in result.content.lower()
    )


@pytest.mark.asyncio
async def test_file_read_directory():
    """Test reading a directory instead of file."""
    tool = FileReadTool()
    result = await tool.execute(file_path="/tmp")
    assert result.is_error is True


@pytest.mark.asyncio
async def test_file_read_with_offset_and_limit():
    """Test file read with offset and limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")
        # Create file with multiple lines
        Path(file_path).write_text("line1\nline2\nline3\nline4\nline5\n")

        tool = FileReadTool()

        # Read with offset
        result = await tool.execute(file_path=file_path, offset=2, limit=2)
        assert result.is_error is False
        # Should contain line3 and line4
        assert "line3" in result.content or "line4" in result.content


@pytest.mark.asyncio
async def test_file_write_invalid_path():
    """Test writing to invalid path."""
    tool = FileWriteTool()
    result = await tool.execute(
        file_path="/invalid/path/that/doesnt/exist/file.txt", content="test"
    )
    assert result.is_error is True


@pytest.mark.asyncio
async def test_file_write_overwrites_existing():
    """Test that file write overwrites existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")

        tool = FileWriteTool()

        # Write first content
        await tool.execute(file_path=file_path, content="original")

        # Write second content (should overwrite)
        result = await tool.execute(file_path=file_path, content="new content")
        assert result.is_error is False

        # Verify content was overwritten
        assert Path(file_path).read_text() == "new content"


@pytest.mark.asyncio
async def test_file_edit_nonexistent_file():
    """Test editing non-existent file."""
    tool = FileEditTool()
    result = await tool.execute(
        file_path="/tmp/nonexistent.txt", old_string="old", new_string="new"
    )
    assert result.is_error is True


@pytest.mark.asyncio
async def test_file_edit_string_not_found():
    """Test editing when old_string doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")
        Path(file_path).write_text("Hello World")

        tool = FileEditTool()
        result = await tool.execute(
            file_path=file_path, old_string="NotFound", new_string="new"
        )
        assert result.is_error is True
        assert "not found" in result.content.lower()


@pytest.mark.asyncio
async def test_file_edit_duplicate_strings():
    """Test editing when old_string appears multiple times."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")
        Path(file_path).write_text("test test test")

        tool = FileEditTool()
        # Without replace_all, should error on duplicates
        result = await tool.execute(
            file_path=file_path, old_string="test", new_string="new", replace_all=False
        )
        assert result.is_error is True


@pytest.mark.asyncio
async def test_file_edit_replace_all():
    """Test replacing all occurrences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")
        Path(file_path).write_text("test test test")

        tool = FileEditTool()
        result = await tool.execute(
            file_path=file_path, old_string="test", new_string="new", replace_all=True
        )
        assert result.is_error is False

        # Verify all replaced
        content = Path(file_path).read_text()
        assert content == "new new new"


@pytest.mark.asyncio
async def test_glob_nonexistent_path():
    """Test glob on non-existent path."""
    tool = GlobTool()
    result = await tool.execute(pattern="*.py", path="/nonexistent/path/xyz")
    assert result.is_error is True


@pytest.mark.asyncio
async def test_glob_empty_pattern():
    """Test glob with empty pattern."""
    tool = GlobTool()
    result = await tool.execute(pattern="")
    # Should handle gracefully
    assert result is not None


@pytest.mark.asyncio
async def test_glob_no_matches():
    """Test glob when no files match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GlobTool()
        result = await tool.execute(pattern="*.nonexistent", path=tmpdir)
        assert result.is_error is False
        assert "No files found" in result.content or "0 files" in result.content


@pytest.mark.asyncio
async def test_grep_nonexistent_path():
    """Test grep on non-existent path."""
    tool = GrepTool()
    result = await tool.execute(pattern="test", path="/nonexistent/file.txt")
    assert result.is_error is True


@pytest.mark.asyncio
async def test_grep_no_matches():
    """Test grep when pattern doesn't match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("hello world")

        tool = GrepTool()
        result = await tool.execute(
            pattern="nonexistent", path=str(file_path), output_mode="content"
        )
        assert result.is_error is False
        assert "No matches found" in result.content or len(result.content.strip()) == 0


@pytest.mark.asyncio
async def test_grep_case_insensitive():
    """Test grep case insensitive search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("Hello World")

        tool = GrepTool()
        result = await tool.execute(
            pattern="hello",
            path=str(file_path),
            output_mode="content",
            case_insensitive=True,
        )
        assert result.is_error is False
        assert "Hello" in result.content


@pytest.mark.asyncio
async def test_list_nonexistent_path():
    """Test listing non-existent directory."""
    tool = ListTool()
    result = await tool.execute(path="/nonexistent/path")
    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_file_instead_of_directory():
    """Test listing a file instead of directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test")

        tool = ListTool()
        result = await tool.execute(path=str(file_path))
        assert result.is_error is True
        assert "not a directory" in result.content.lower()


@pytest.mark.asyncio
async def test_list_empty_directory():
    """Test listing empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = ListTool()
        result = await tool.execute(path=tmpdir)
        assert result.is_error is False
        assert "0" in result.content  # 0 entries


@pytest.mark.asyncio
async def test_list_hidden_files():
    """Test listing with hidden files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create hidden file
        Path(tmpdir, ".hidden").write_text("test")
        Path(tmpdir, "visible.txt").write_text("test")

        tool = ListTool()

        # Without show_hidden
        result = await tool.execute(path=tmpdir, show_hidden=False)
        assert ".hidden" not in result.content

        # With show_hidden
        result = await tool.execute(path=tmpdir, show_hidden=True)
        assert ".hidden" in result.content


@pytest.mark.asyncio
async def test_list_sort_by_size():
    """Test listing sorted by size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "small.txt").write_text("x")
        Path(tmpdir, "large.txt").write_text("x" * 1000)

        tool = ListTool()
        result = await tool.execute(path=tmpdir, sort_by="size")
        assert result.is_error is False
        # Large file should appear first (descending order)
        assert result.content.index("large.txt") < result.content.index("small.txt")


@pytest.mark.asyncio
async def test_list_recursive():
    """Test recursive directory listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested structure
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        Path(tmpdir, "file1.txt").write_text("test")
        Path(subdir, "file2.txt").write_text("test")

        tool = ListTool()
        result = await tool.execute(path=tmpdir, recursive=True)
        assert result.is_error is False
        assert "file1.txt" in result.content
        assert "file2.txt" in result.content or "subdir" in result.content


def test_tool_registry_unregister():
    """Test unregistering a tool."""
    registry = ToolRegistry()
    tool = BashTool()
    registry.register(tool)

    assert "Bash" in registry
    registry.unregister("Bash")
    assert "Bash" not in registry


def test_tool_registry_get():
    """Test getting a tool from registry."""
    registry = ToolRegistry()
    tool = BashTool()
    registry.register(tool)

    retrieved = registry.get("Bash")
    assert retrieved is not None
    assert retrieved.name == "Bash"


def test_tool_registry_get_nonexistent():
    """Test getting non-existent tool."""
    registry = ToolRegistry()
    retrieved = registry.get("NonExistent")
    assert retrieved is None


def test_tool_registry_length():
    """Test tool registry length."""
    registry = ToolRegistry()
    assert len(registry) == 0

    registry.register(BashTool())
    assert len(registry) == 1

    registry.register(FileReadTool())
    assert len(registry) == 2


def test_tool_repr():
    """Test tool __repr__ method."""
    tool = BashTool()
    repr_str = repr(tool)
    assert "BashTool" in repr_str
    assert "Bash" in repr_str
