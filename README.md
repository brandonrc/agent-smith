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
- 🎯 Model Context Protocol (MCP) support

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

## Architecture

```
src/agent_smith/
├── cli.py              # CLI entry point
├── config/             # Configuration management (dynaconf)
├── models/             # Pydantic data models
├── ui/                 # Textual UI components
│   ├── app.py          # Main application
│   ├── repl.py         # Interactive REPL screen
│   └── help_screen.py  # Help screen
├── tools/              # Tool system (9 tools)
│   ├── bash_tool.py
│   ├── file_read_tool.py
│   ├── file_write_tool.py
│   ├── file_edit_tool.py
│   ├── glob_tool.py
│   ├── grep_tool.py
│   ├── list_tool.py
│   ├── agent_tool.py
│   └── think_tool.py
├── services/           # LLM API clients
│   ├── claude.py       # Anthropic Claude
│   └── openai.py       # OpenAI GPT
└── query.py            # Main query orchestration
```
