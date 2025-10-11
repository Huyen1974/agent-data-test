# Codex Agent - Operational Runbook

## Agent Identity
- **Name:** Codex
- **Type:** Cursor-integrated coding assistant
- **Version:** Latest stable
- **Namespace:** CURSOR_CODEX_*

## Startup Configuration

### Environment Variables
```bash
export CURSOR_CODEX_MODEL="gpt-4"
export CURSOR_CODEX_TOOLS="read_file,write_file,run_shell_command"
export CURSOR_CODEX_PROJECT="$(pwd)"
export CURSOR_CODEX_APPROVAL_MODE="auto_edit"
```

### Startup Command
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export CURSOR_CODEX_MODEL="gpt-4" && \
export CURSOR_CODEX_TOOLS="read_file,write_file,run_shell_command" && \
export CURSOR_CODEX_PROJECT="$(pwd)" && \
export CURSOR_CODEX_APPROVAL_MODE="auto_edit" && \
cursor --codex --model "$CURSOR_CODEX_MODEL" --tools "$CURSOR_CODEX_TOOLS" --approval-mode "$CURSOR_CODEX_APPROVAL_MODE"
```

## Operational Constraints

### File Permissions
- ✅ Read all project files
- ⚠️ Write requires approval for: `*.lock`, `*.json`, configuration files
- ❌ Never modify: `.gitignore`, system dotfiles, CI configurations

### Branch Management
- Work only on feature branches
- Never commit to `main` directly
- Require pull request review
- Use conventional commits

### Tool Restrictions
- `run_shell_command`: Safe operations only, no destructive commands
- `grep`: Allowed for code analysis
- `run_terminal_cmd`: Requires approval for multi-step operations

## Quality Standards

### Code Quality
- Follow existing code style and conventions
- Respect `.pre-commit-config.yaml`
- Maintain test coverage
- Update documentation

### Testing Requirements
- Run relevant tests before committing
- Ensure CI passes on feature branch
- Validate functionality with smoke tests

## Error Handling

### Authentication Issues
- Verify Cursor authentication
- Check extension permissions
- Validate API key configuration

### Rate Limiting
- Respect API quotas
- Implement intelligent retry logic
- Report quota exhaustion

### Environment Conflicts
- Isolate Cursor-specific environment variables
- Clean up after session completion
- Validate Cursor extension state

## Monitoring and Audit

### Activity Logging
- Log all file modifications with timestamps
- Record command executions
- Track approval decisions

### Performance Metrics
- Response time monitoring
- Success/failure rates
- Resource usage tracking

## Integration Points

### With Other Agents
- No shared state with Claude/Gemini
- Independent environment sessions
- Respect shared bootstrap validation

### With CI/CD
- Comply with GitHub Actions workflows
- Respect branch protection rules
- Follow PR approval processes

### With Cursor IDE
- Integrate with Cursor's native features
- Respect Cursor's file watching
- Utilize Cursor's built-in tools

## Emergency Procedures

### Session Corruption
1. Terminate Cursor Codex process
2. Restart Cursor IDE
3. Reset extension state
4. Re-run bootstrap: `./CLI.POSTBOOT.250.sh`
5. Restart with clean configuration

### Extension Issues
1. Verify Cursor extension is installed and enabled
2. Check extension permissions
3. Update extension if needed
4. Restart Cursor IDE

### File Conflicts
1. Identify modified files
2. Create backup of changes
3. Restore from git if needed
4. Reapply changes carefully

---

**Agent Version:** Cursor Codex Extension
**Last Updated:** October 11, 2025
**Configuration Hash:** CODEX_v1.0_20251011
