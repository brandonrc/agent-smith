# MCP Implementation Plan

**Date:** 2025-11-24
**Goal:** Enable GitLab and Jira integration via Model Context Protocol

---

## Overview

MCP (Model Context Protocol) allows Agent Smith to connect to external services like GitLab and Jira through standardized server plugins.

**User Requirements:**
- GitLab integration (repos, MRs, issues)
- Jira integration (tickets, projects, workflows)

---

## Phase 1: MCP Client Foundation (Week 1)

### 1.1 Core MCP Client
**File:** `src/agent_smith/mcp/client.py`

**Responsibilities:**
- Start/stop MCP server processes
- Maintain stdio connections
- Handle JSON-RPC communication
- Tool discovery from servers

**Key Classes:**
```python
class MCPClient:
    """Manages connection to a single MCP server."""
    - start_server(command, args, env)
    - initialize()
    - list_tools()
    - call_tool(name, arguments)
    - shutdown()

class MCPClientManager:
    """Manages multiple MCP clients."""
    - register_server(name, config)
    - discover_tools()
    - route_tool_call(tool_name, arguments)
    - shutdown_all()
```

---

### 1.2 MCP Configuration
**File:** `src/agent_smith/config/mcp.py`

**Config Format:** (in `settings.toml`)
```toml
[mcp.servers.gitlab]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-gitlab"]
env = { GITLAB_TOKEN = "glpat-xxx", GITLAB_URL = "https://gitlab.com" }
enabled = true
trusted = false  # Requires approval

[mcp.servers.jira]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-jira"]
env = { JIRA_URL = "https://company.atlassian.net", JIRA_TOKEN = "xxx" }
enabled = true
trusted = false
```

---

### 1.3 MCPTool Wrapper
**File:** `src/agent_smith/tools/mcp_tool.py`

**Design:**
```python
class MCPTool(BaseTool):
    """
    Dynamic tool that wraps MCP server tools.

    One MCPTool instance per discovered MCP tool.
    Routes calls to appropriate MCP server.
    """

    def __init__(self, server_name: str, tool_definition: Tool):
        self.server_name = server_name
        self.mcp_tool = tool_definition
        self.name = f"{server_name}_{tool_definition.name}"
        self.description = tool_definition.description
        self.input_schema = tool_definition.inputSchema

    async def execute(self, **kwargs):
        # Route to MCP client manager
        return await mcp_manager.call_tool(
            server=self.server_name,
            tool=self.mcp_tool.name,
            arguments=kwargs
        )
```

---

## Phase 2: Server Discovery & Registration (Week 1-2)

### 2.1 Dynamic Tool Discovery

**Workflow:**
1. Agent Smith starts up
2. Read MCP server config from `settings.toml`
3. For each enabled server:
   - Start server process (subprocess)
   - Initialize MCP connection (stdio)
   - Call `tools/list` to discover tools
   - Create MCPTool wrapper for each tool
   - Register with ToolRegistry

**Code Location:** `src/agent_smith/mcp/discovery.py`

---

### 2.2 Tool Registration

```python
# On startup:
async def register_mcp_tools():
    mcp_manager = MCPClientManager()

    # Load config
    servers = settings.get("mcp.servers", {})

    for name, config in servers.items():
        if not config.get("enabled", False):
            continue

        # Start server
        client = await mcp_manager.start_server(
            name=name,
            command=config["command"],
            args=config["args"],
            env=config.get("env", {})
        )

        # Discover tools
        tools = await client.list_tools()

        # Register each tool
        for tool in tools:
            mcp_tool = MCPTool(server_name=name, tool_definition=tool)
            default_tools.register(mcp_tool)
```

---

## Phase 3: Security & Approval (Week 2)

### 3.1 Server Trust System

**File:** `src/agent_smith/mcp/trust.py`

**Features:**
- First-time approval prompt for new servers
- Store trust decisions in config
- Warn on configuration changes
- Sandbox server processes (future)

**UI Flow:**
```
User starts Agent Smith
→ New MCP server detected: gitlab
→ [APPROVAL DIALOG]

   🔒 MCP Server Approval Required

   Server: gitlab
   Command: npx @modelcontextprotocol/server-gitlab

   This server will have access to:
   - GitLab API (read/write)
   - Environment: GITLAB_TOKEN

   Tools provided:
   - create_merge_request
   - list_issues
   - get_file_contents
   ... (15 more)

   [Trust & Start] [Deny] [View Config]

→ User approves
→ Server starts and tools become available
```

---

### 3.2 Approval Dialog (Textual UI)

**File:** `src/agent_smith/ui/mcp_approval_dialog.py`

```python
class MCPApprovalDialog(Screen):
    """Modal dialog for MCP server approval."""

    def compose(self):
        yield Container(
            Static("🔒 MCP Server Approval Required"),
            Static(f"Server: {self.server_name}"),
            Static(f"Command: {self.command}"),
            # ... server details
            Button("Trust & Start", id="approve"),
            Button("Deny", id="deny"),
        )
```

---

## Phase 4: Integration with Agent Smith (Week 2-3)

### 4.1 Startup Integration

**File:** `src/agent_smith/cli.py`

```python
@app.callback()
def main(...):
    # Initialize MCP on startup
    if settings.get("mcp.enabled", True):
        asyncio.run(register_mcp_tools())
```

---

### 4.2 REPL Integration

**Add commands:**
- `/mcp` - Show connected MCP servers
- `/mcp list` - List all MCP tools
- `/mcp reload` - Reload MCP servers
- `/mcp trust <server>` - Trust a server
- `/mcp untrust <server>` - Untrust a server

---

## MCP Server Installation Guide

### GitLab MCP Server

```bash
# Install globally (recommended)
npm install -g @modelcontextprotocol/server-gitlab

# Or use with npx (no install)
# Agent Smith will run: npx -y @modelcontextprotocol/server-gitlab
```

**Configuration:**
```toml
[mcp.servers.gitlab]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-gitlab"]
env = { GITLAB_TOKEN = "glpat-your-token", GITLAB_URL = "https://gitlab.com" }
enabled = true
```

**Get GitLab Token:**
1. Go to GitLab → Settings → Access Tokens
2. Create token with scopes: `api`, `read_repository`, `write_repository`
3. Add to config

---

### Jira MCP Server

```bash
# Install
npm install -g @modelcontextprotocol/server-jira
```

**Configuration:**
```toml
[mcp.servers.jira]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-jira"]
env = {
    JIRA_URL = "https://your-company.atlassian.net",
    JIRA_EMAIL = "your-email@company.com",
    JIRA_API_TOKEN = "your-api-token"
}
enabled = true
```

**Get Jira Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Add to config

---

## Technical Architecture

### Process Model

```
┌─────────────────────────────┐
│   Agent Smith (Python)      │
│                             │
│  ┌─────────────────────┐   │
│  │ MCPClientManager    │   │
│  │                     │   │
│  │  ┌──────────────┐  │   │
│  │  │ GitLab Client│  │   │
│  │  └──────┬───────┘  │   │
│  │         │           │   │
│  │  ┌──────▼───────┐  │   │
│  │  │ Jira Client  │  │   │
│  │  └──────────────┘  │   │
│  └─────────────────────┘   │
└──────────┬──────────────────┘
           │ stdio
    ┌──────┴───────┬─────────┐
    │              │         │
┌───▼────────┐ ┌──▼──────┐  │
│ GitLab MCP │ │ Jira MCP│  │
│ Server     │ │ Server  │  │
│ (Node.js)  │ │(Node.js)│  │
└────────────┘ └─────────┘  │
```

### Communication Flow

```
User: "Create a Jira ticket"
  ↓
Claude API (with tools)
  ↓
Agent Smith Query Orchestrator
  ↓
Tool: mcp_jira_create_issue
  ↓
MCPClientManager.call_tool()
  ↓
Jira MCPClient
  ↓
JSON-RPC over stdio
  ↓
Jira MCP Server (Node.js)
  ↓
Jira REST API
  ↓
Result back to Claude
```

---

## Dependencies

### Add to pyproject.toml

```toml
dependencies = [
    # ... existing deps
    "mcp>=1.22.0",  # Model Context Protocol SDK
]
```

### External Requirements

**Node.js & npm** (for MCP servers):
```bash
# Check if installed:
node --version  # Need v18+
npm --version

# Install if missing (macOS):
brew install node

# Install if missing (Linux):
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## Implementation Checklist

### Week 1: Foundation
- [x] Install MCP SDK
- [ ] Create `src/agent_smith/mcp/` package
- [ ] Implement MCPClient class
- [ ] Implement MCPClientManager
- [ ] Implement MCPTool wrapper
- [ ] Add MCP configuration structure
- [ ] Test with simple echo server

### Week 2: Integration
- [ ] Implement server discovery
- [ ] Dynamic tool registration
- [ ] Add `/mcp` commands to REPL
- [ ] Implement trust/approval system
- [ ] Create approval dialog UI
- [ ] Handle server crashes/restarts

### Week 3: GitLab & Jira
- [ ] Install GitLab MCP server
- [ ] Configure GitLab integration
- [ ] Test GitLab workflows
- [ ] Install Jira MCP server
- [ ] Configure Jira integration
- [ ] Test Jira workflows
- [ ] Documentation & examples

---

## Testing Strategy

### Unit Tests
- MCPClient initialization
- Tool discovery
- Tool call routing
- Error handling

### Integration Tests
- Start/stop servers
- Tool execution
- Multi-server management

### E2E Tests (Manual)
1. Start Agent Smith
2. Approve GitLab server
3. Ask: "List my open merge requests"
4. Verify correct API call
5. Ask: "Create a Jira ticket for bug X"
6. Verify ticket created

---

## Known Challenges

1. **Process Management**
   - Need robust subprocess handling
   - Handle server crashes gracefully
   - Clean shutdown on exit

2. **Error Handling**
   - Server fails to start
   - Network issues
   - Invalid credentials
   - API rate limits

3. **Security**
   - Tokens in config (use environment variables)
   - Untrusted server code
   - Sandboxing (future: containers)

4. **Performance**
   - Server startup time (~2-3 seconds)
   - Keep servers warm between requests
   - Connection pooling

---

## Success Metrics

### Functional
- ✅ Can connect to GitLab MCP server
- ✅ Can list GitLab merge requests
- ✅ Can create Jira tickets
- ✅ Servers survive Agent Smith restarts

### User Experience
- ✅ Setup takes < 5 minutes
- ✅ Clear approval prompts
- ✅ Helpful error messages
- ✅ Fast response times (< 3s)

---

## Future Enhancements

1. **More MCP Servers**
   - GitHub
   - Slack
   - Databases (PostgreSQL, MySQL)
   - Google Drive
   - AWS services

2. **Advanced Features**
   - Server marketplace/discovery
   - Automatic updates
   - Docker-based sandboxing
   - Server health monitoring
   - Retry logic with backoff

3. **Developer Tools**
   - MCP server template generator
   - Testing utilities
   - Debug mode for MCP communication

---

*This is a living document - will be updated as implementation progresses*
