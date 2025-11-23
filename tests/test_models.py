"""Tests for Pydantic models."""


from agent_smith.models import (
    ImageBlock,
    Message,
    MessageRole,
    TextBlock,
    ToolResult,
    ToolResultBlock,
    ToolUseBlock,
)


def test_message_role_enum():
    """Test MessageRole enum."""
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"


def test_text_block_creation():
    """Test creating a TextBlock."""
    block = TextBlock(text="Hello, world!")
    assert block.type == "text"
    assert block.text == "Hello, world!"


def test_image_block_creation():
    """Test creating an ImageBlock."""
    source = {"type": "base64", "data": "abcd1234"}
    block = ImageBlock(source=source)
    assert block.type == "image"
    assert block.source == source


def test_tool_use_block_creation():
    """Test creating a ToolUseBlock."""
    block = ToolUseBlock(id="tool_123", name="bash", input={"command": "ls"})
    assert block.type == "tool_use"
    assert block.id == "tool_123"
    assert block.name == "bash"
    assert block.input == {"command": "ls"}


def test_tool_result_block_creation():
    """Test creating a ToolResultBlock."""
    block = ToolResultBlock(tool_use_id="tool_123", content="output", is_error=False)
    assert block.type == "tool_result"
    assert block.tool_use_id == "tool_123"
    assert block.content == "output"
    assert block.is_error is False


def test_message_with_string_content():
    """Test creating a Message with string content."""
    msg = Message(role=MessageRole.USER, content="Hello!")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello!"


def test_message_with_block_content():
    """Test creating a Message with block content."""
    blocks = [TextBlock(text="Hello"), TextBlock(text="World")]
    msg = Message(role=MessageRole.ASSISTANT, content=blocks)
    assert msg.role == MessageRole.ASSISTANT
    assert len(msg.content) == 2


def test_message_user_helper():
    """Test Message.user() helper method."""
    msg = Message.user("Test message")
    assert msg.role == MessageRole.USER
    assert msg.content == "Test message"


def test_message_assistant_helper():
    """Test Message.assistant() helper method."""
    msg = Message.assistant("Response")
    assert msg.role == MessageRole.ASSISTANT
    assert msg.content == "Response"


def test_message_get_text_with_string():
    """Test get_text() with string content."""
    msg = Message.user("Plain text")
    assert msg.get_text() == "Plain text"


def test_message_get_text_with_blocks():
    """Test get_text() with block content."""
    blocks = [TextBlock(text="Hello "), TextBlock(text="World")]
    msg = Message(role=MessageRole.ASSISTANT, content=blocks)
    text = msg.get_text()
    assert "Hello " in text
    assert "World" in text


def test_tool_result_success():
    """Test creating a success ToolResult."""
    result = ToolResult.success("Command output")
    assert result.is_error is False
    assert result.content == "Command output"


def test_tool_result_error():
    """Test creating an error ToolResult."""
    result = ToolResult.error("Error message")
    assert result.is_error is True
    assert result.content == "Error message"


def test_tool_result_validation():
    """Test ToolResult validation."""
    # Should accept boolean for is_error
    result = ToolResult(content="test", is_error=True)
    assert result.is_error is True

    # Should default to False
    result = ToolResult(content="test")
    assert result.is_error is False
