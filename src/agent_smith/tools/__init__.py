"""Tool implementations for Agent Smith."""

from .agent_tool import AgentTool
from .base import BaseTool, ToolRegistry
from .bash_tool import BashTool
from .file_edit_tool import FileEditTool
from .file_read_tool import FileReadTool
from .file_write_tool import FileWriteTool
from .glob_tool import GlobTool
from .grep_tool import GrepTool
from .list_tool import ListTool
from .memory_read_tool import MemoryReadTool
from .memory_write_tool import MemoryWriteTool
from .notebook_edit_tool import NotebookEditTool
from .notebook_read_tool import NotebookReadTool
from .think_tool import ThinkTool

# Default tool registry
default_tools = ToolRegistry()
default_tools.register(BashTool())
default_tools.register(FileReadTool())
default_tools.register(FileWriteTool())
default_tools.register(FileEditTool())
default_tools.register(GlobTool())
default_tools.register(GrepTool())
default_tools.register(ListTool())
default_tools.register(MemoryReadTool())
default_tools.register(MemoryWriteTool())
default_tools.register(NotebookReadTool())
default_tools.register(NotebookEditTool())
default_tools.register(AgentTool())
default_tools.register(ThinkTool())

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "BashTool",
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "GlobTool",
    "GrepTool",
    "ListTool",
    "MemoryReadTool",
    "MemoryWriteTool",
    "NotebookReadTool",
    "NotebookEditTool",
    "AgentTool",
    "ThinkTool",
    "default_tools",
]
