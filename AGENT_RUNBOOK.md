# Agent Data Langroid - Multi-Agent Operational Runbook

## Overview
This unified runbook governs all AI agents (Claude Code, Gemini CLI, Codex, and future agents) operating within the Agent Data Langroid environment. It establishes standardized operating procedures, environment isolation, and conflict resolution mechanisms.

## Architecture Principles

### 1. Environment Isolation
- Each agent maintains isolated runtime environments
- Environment variables are agent-specific and non-conflicting
- File-based configurations are segregated by agent namespace

### 2. Unified Bootstrap Process
- All agents use the same bootstrap verification (`CLI.POSTBOOT.250.sh`)
- Agent-specific initialization follows common validation
- Environment cleanup between agent switches

### 3. Standardized Tool Permissions
- All agents follow identical tool permission models
- Approval-based execution for destructive operations
- Audit trails for all agent actions

## Agent-Specific Configurations

### Claude Code Agent
**Configuration File:** `.agents/claude/runbook.md`
**Environment Variables:**
- `CLAUDE_CODE_PROJECT_ROOT` - Project root directory
- `CLAUDE_CODE_MODEL` - Preferred model version
- `CLAUDE_CODE_TOOLS` - Allowed tool set

**Startup Command:**
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export CLAUDE_CODE_PROJECT_ROOT="$(pwd)" && \
export CLAUDE_CODE_MODEL="claude-3-5-sonnet-20241022" && \
export CLAUDE_CODE_TOOLS="read_file,write_file,run_shell_command,search_file_content" && \
claude code --model "$CLAUDE_CODE_MODEL" --tools "$CLAUDE_CODE_TOOLS"
```

### Gemini CLI Agent
**Configuration File:** `.agents/gemini/runbook.md`
**Startup Script:** `.agents/gemini/start.sh`
**Environment Variables:**
- `GOOGLE_GENAI_USE_GCA` - Use Google Code Assist (not Vertex)
- `GEMINI_CLI_MODEL` - Preferred model version
- `GEMINI_CLI_TOOLS` - Allowed tool set

**Startup Command:**
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export GOOGLE_GENAI_USE_GCA=true && \
unset GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX GEMINI_TOOL_SANDBOX GEMINI_EXTENSIONS_SANDBOX && \
unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT && \
gemini -e none --extensions none --approval-mode auto_edit \
  --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
  -m gemini-2.5-pro
```

> **Canonical launch:** Run `.agents/gemini/start.sh` to execute the exact sequence above with environment validation, conflict cleanup, and post-session teardown.

### Codex Agent (Cursor Extension)
**Configuration File:** `.agents/codex/runbook.md`
**Environment Variables:**
- `CURSOR_CODEX_MODEL` - Preferred model version
- `CURSOR_CODEX_TOOLS` - Allowed tool set
- `CURSOR_CODEX_PROJECT` - Project context

**Startup Command:**
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export CURSOR_CODEX_MODEL="gpt-4" && \
export CURSOR_CODEX_TOOLS="read_file,write_file,run_shell_command" && \
export CURSOR_CODEX_PROJECT="$(pwd)" && \
cursor --codex --model "$CURSOR_CODEX_MODEL" --tools "$CURSOR_CODEX_TOOLS"
```

## Common Operating Constraints

### Branch Management
- **ALL agents**: Work ONLY on feature branches
- **NEVER** commit directly to `main` branch
- Use conventional commit messages
- Require PR review for all changes

### File Permissions
- **Respect `.gitignore`** - Never modify ignored files
- **Preserve lockfiles** - `package-lock.json`, `poetry.lock`, etc.
- **System files protection** - No modification of `~/.bashrc`, `~/.zshrc`, etc.

### Tool Usage Standards
- **Read operations**: Always allowed
- **Write operations**: Require approval for sensitive files
- **Shell commands**: Restricted to safe operations
- **Network access**: Limited to project-related domains

## Environment Conflict Resolution

### Variable Isolation
- Agent-specific environment variables use namespaced prefixes
- Automatic cleanup of conflicting variables between agent switches
- Validation of environment state before agent startup

### File-based Configuration
- Each agent has dedicated `.agents/{agent_name}/` directory
- Shared configurations stored in `.agents/shared/`
- No cross-agent file dependencies

### Process Management
- Agents run in isolated terminal sessions
- Environment variables reset between sessions
- No persistent state shared between agents

## Quality Assurance

### Pre-execution Validation
- Environment variable conflict detection
- Required dependency verification
- Network connectivity checks

### Post-execution Cleanup
- Environment variable sanitization
- Temporary file removal
- Session state reset

### Monitoring and Audit
- All agent actions logged with timestamps
- Performance metrics collection
- Error reporting with context

## Emergency Procedures

### Environment Corruption
1. Terminate all agent processes
2. Run environment cleanup: `source ~/.zshrc && ./CLI.POSTBOOT.250.sh`
3. Verify environment integrity
4. Restart target agent with clean state

### Configuration Conflicts
1. Identify conflicting configuration files
2. Move conflicting files to backup locations
3. Restore from known good configurations
4. Test agent functionality

### Bootstrap Failure
1. Check GitHub authentication status
2. Verify network connectivity
3. Reset local environment state
4. Re-run bootstrap process

## Future Agent Integration

### Onboarding Checklist
- [ ] Create `.agents/{new_agent}/` directory structure
- [ ] Define agent-specific environment variables
- [ ] Document startup procedures
- [ ] Test environment isolation
- [ ] Validate tool permissions
- [ ] Update monitoring configurations

### Compatibility Requirements
- Must support environment variable isolation
- Must respect branch management policies
- Must implement approval-based execution
- Must provide audit logging
- Must integrate with bootstrap validation

## Implementation Notes

### File Structure
```
.agents/
├── shared/
│   ├── bootstrap.sh
│   └── validation.sh
├── claude/
│   ├── runbook.md
│   └── config.env
├── gemini/
│   ├── runbook.md
│   └── config.env
└── codex/
    ├── runbook.md
    └── config.env
```

### Environment Management
- Use `.env` files for agent-specific configurations
- Implement environment switching scripts
- Provide validation utilities for environment state

### Tool Integration
- Develop shared validation utilities
- Create agent-agnostic monitoring tools
- Implement centralized audit logging

---

**Version:** 1.0
**Last Updated:** October 11, 2025
**Maintained by:** Agent Data Langroid Team
