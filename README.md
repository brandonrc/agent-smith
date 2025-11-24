# Agent Smith - Python Implementation

Modern Python implementation of Agent Smith, a terminal-based AI coding assistant.

## Features

- 🤖 Multi-provider LLM support (Anthropic Claude, OpenAI GPT, AWS Bedrock, Google Vertex)
- 🖥️ Beautiful terminal UI with Textual
- 🔧 Extensible tool system (16+ built-in tools)
- 🔐 Secure credential management (OS keyring support)
- ⚙️ XDG-compliant configuration
- 🚀 Fast async I/O with asyncio
- 📝 Type-safe with Pydantic
- 🎯 **Model Context Protocol (MCP) support** - Connect to GitLab, Jira, databases, and more!

## Installation

### From PyPI (once published)

```bash
pip install agent-smith
```

### From Source (Development)

```bash
cd python
pip install -e ".[dev]"
```

## Quick Start

### 1. Install and Configure

```bash
# Install
pip install agent-smith

# Set API key
smith config set anthropic_api_key sk-ant-...

# Or use environment variable
export SMITH_ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Run Agent Smith

```bash
# Start interactive mode
smith

# Use with specific model
smith --model claude-opus-4-20250514

# Verbose mode
smith --verbose --debug
```

### 3. Configuration

Agent Smith follows XDG Base Directory specification:

**Linux/macOS:**
- Config: `~/.config/agent-smith/`
- Data: `~/.local/share/agent-smith/`
- Cache: `~/.cache/agent-smith/`
- Logs: `~/.local/state/agent-smith/`

**Windows:**
- Config: `%APPDATA%\agent-smith\`
- Data: `%LOCALAPPDATA%\agent-smith\`

### Configuration Files

**`~/.config/agent-smith/settings.toml`**
```toml
[default]
default_provider = "anthropic"
large_model = "claude-sonnet-4-5-20250929"
small_model = "claude-3-5-haiku-20241022"
show_cost = true
enable_prompt_caching = true
max_parallel_tools = 10
```

**`~/.config/agent-smith/.secrets.toml`** (gitignored)
```toml
[default]
anthropic_api_key = "sk-ant-..."
openai_api_key = "sk-..."
```

## Commands

```bash
# Configuration
smith config show              # Show current configuration
smith config set KEY VALUE     # Set configuration value
smith config edit              # Edit config in $EDITOR
smith config path              # Show config paths

# Model Selection
smith model select             # Interactive model selector
smith model list               # List available models

# MCP Server
smith mcp serve                # Run as MCP server for Claude Desktop

# Utilities
smith doctor                   # Run diagnostics
smith version                  # Show version
smith --help                   # Show help
```

## Environment Variables

All settings can be overridden with environment variables using `SMITH_` prefix:

```bash
export SMITH_DEFAULT_PROVIDER=openai
export SMITH_LARGE_MODEL=gpt-4o
export SMITH_VERBOSE=true
export SMITH_ANTHROPIC_API_KEY=sk-ant-...
export SMITH_OPENAI_API_KEY=sk-...
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/brandonrc/agent-smith.git
cd agent-smith/python

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent_smith --cov-report=html

# Run specific test
pytest tests/test_config.py -v
```

### Type Checking

```bash
mypy src/agent_smith
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/

# Lint with ruff
ruff check src/ tests/
```

## MCP (Model Context Protocol) Integration

Agent Smith supports MCP, allowing it to connect to external services and tools.

### What is MCP?

MCP is an open standard that enables AI applications to connect to external data sources and tools in a standardized way. Think of it like "USB-C for AI" - one protocol to connect to many services.

### Supported MCP Servers

Agent Smith can connect to any MCP-compatible server, including:

- **GitLab** - Manage repositories, merge requests, issues
- **Jira** - Create and manage tickets, projects, workflows
- **Filesystem** - Secure file operations in allowed directories
- **Databases** - PostgreSQL, MySQL, SQLite
- **And many more...**

### Quick Start with MCP

1. **Install Node.js** (required for most MCP servers):
```bash
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

2. **Configure MCP servers** in `~/.config/agent-smith/settings.toml`:
```toml
[mcp]
enabled = true

[mcp.servers.gitlab]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-gitlab"]
env = {
    GITLAB_TOKEN = "glpat-your-token-here",
    GITLAB_URL = "https://gitlab.com"
}
enabled = true
trusted = false  # Will prompt for approval on first use

[mcp.servers.jira]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-jira"]
env = {
    JIRA_URL = "https://your-company.atlassian.net",
    JIRA_EMAIL = "your-email@company.com",
    JIRA_API_TOKEN = "your-api-token"
}
enabled = true
trusted = false
```

3. **Start Agent Smith** - it will prompt you to approve each MCP server on first use

4. **Use MCP tools** - Claude can now use GitLab, Jira, etc.:
```
> "List my open GitLab merge requests"
> "Create a Jira ticket for this bug"
```

5. **Check MCP status** with `/mcp` command in the REPL

### MCP Commands

- `/mcp` - Show MCP server status and tool counts
- `/tools` - List all available tools (including MCP tools)

### Security

- **Server Approval** - First-time use requires explicit user approval
- **Trust Management** - Approved servers are tracked in `~/.local/share/agent-smith/mcp_trust.json`
- **Environment Isolation** - Each server runs in its own subprocess
- **Configuration Changes** - Reapproval required if server config changes

### Available MCP Servers

Find more MCP servers at: https://github.com/modelcontextprotocol/servers

## Architecture

```
src/agent_smith/
├── cli.py              # CLI entry point
├── config/             # Configuration management (dynaconf)
├── mcp/                # MCP integration
│   ├── client.py       # MCP client for single server
│   ├── manager.py      # Multi-server management
│   ├── discovery.py    # Tool discovery and registration
│   └── trust.py        # Security and approval system
├── models/             # Pydantic data models
├── ui/                 # Textual UI components
│   ├── app.py          # Main application
│   ├── repl.py         # Interactive REPL screen
│   └── help_screen.py  # Help screen
├── tools/              # Tool system (13+ tools)
│   ├── bash_tool.py
│   ├── file_read_tool.py
│   ├── file_write_tool.py
│   ├── file_edit_tool.py
│   ├── glob_tool.py
│   ├── grep_tool.py
│   ├── list_tool.py
│   ├── agent_tool.py
│   ├── think_tool.py
│   ├── mcp_tool.py     # MCP tool wrapper
│   └── ...
├── services/           # LLM API clients
│   ├── claude.py       # Anthropic Claude
│   └── openai.py       # OpenAI GPT
├── query.py            # Main query orchestration
└── mcp_integration.py  # MCP initialization
```
