# Claude Code Agent - Operational Runbook

## Agent Identity
- **Name:** Claude Code
- **Type:** Anthropic Claude-based coding assistant
- **Version:** Latest stable
- **Namespace:** CLAUDE_CODE_*

## Startup Configuration

### Environment Variables
```bash
export CLAUDE_CODE_PROJECT_ROOT="$(pwd)"
export CLAUDE_CODE_MODEL="claude-3-5-sonnet-20241022"
export CLAUDE_CODE_TOOLS="read_file,write_file,run_shell_command,search_file_content"
export CLAUDE_CODE_APPROVAL_MODE="auto_edit"
```

### Startup Command
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export CLAUDE_CODE_PROJECT_ROOT="$(pwd)" && \
export CLAUDE_CODE_MODEL="claude-3-5-sonnet-20241022" && \
export CLAUDE_CODE_TOOLS="read_file,write_file,run_shell_command,search_file_content" && \
export CLAUDE_CODE_APPROVAL_MODE="auto_edit" && \
claude code --model "$CLAUDE_CODE_MODEL" --tools "$CLAUDE_CODE_TOOLS" --approval-mode "$CLAUDE_CODE_APPROVAL_MODE"
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
- Verify Anthropic API key configuration
- Check network connectivity
- Retry with exponential backoff

### Rate Limiting
- Respect API quotas
- Implement intelligent retry logic
- Report quota exhaustion

### Environment Conflicts
- Isolate environment variables
- Clean up after session completion
- Validate environment state

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
- No shared state with Gemini/Codex
- Independent environment sessions
- Respect shared bootstrap validation

### With CI/CD
- Comply with GitHub Actions workflows
- Respect branch protection rules
- Follow PR approval processes

## Emergency Procedures

### Session Corruption
1. Terminate Claude Code process
2. Reset environment: `source ~/.zshrc`
3. Re-run bootstrap: `./CLI.POSTBOOT.250.sh`
4. Restart with clean configuration

### File Conflicts
1. Identify modified files
2. Create backup of changes
3. Restore from git if needed
4. Reapply changes carefully

---

**Agent Version:** Claude 3.5 Sonnet
**Last Updated:** October 11, 2025
**Configuration Hash:** CLAUDE_v1.0_20251011
