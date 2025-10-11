# Gemini CLI Agent - Operational Runbook

## Agent Identity
- **Name:** Gemini CLI
- **Type:** Google Gemini-based coding assistant
- **Version:** 2.5 Pro
- **Namespace:** GOOGLE_GENAI_*, GEMINI_CLI_*

## Startup Configuration

### Environment Variables
```bash
export GOOGLE_GENAI_USE_GCA=true
export GEMINI_CLI_MODEL="gemini-2.5-pro"
export GEMINI_CLI_TOOLS="run_shell_command,read_file,write_file,search_file_content,web_fetch"
export GEMINI_CLI_APPROVAL_MODE="auto_edit"
export GEMINI_CLI_EXTENSIONS="none"
```

### Startup Command
```bash
source ~/.zshrc && ./CLI.POSTBOOT.250.sh && \
export GOOGLE_GENAI_USE_GCA=true && \
unset GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX && \
unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT && \
unset GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT && \
gemini -e none --extensions none --approval-mode auto_edit \
  --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
  -m gemini-2.5-pro
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
- `web_fetch`: Limited to project-related domains

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
- Complete OAuth flow in browser when prompted
- Verify GOOGLE_GENAI_USE_GCA=true is set
- Check network connectivity

### Rate Limiting (429 Errors)
1. Verify `GOOGLE_GENAI_USE_GCA=true` is set
2. Wait and retry once
3. If persistent, report quota/account issues

### Environment Conflicts
- Ensure Google API keys are unset to avoid Vertex conflicts
- Clean up sandbox environment variables
- Validate GCA authentication

## Monitoring and Audit

### Activity Logging
- Log all file modifications with timestamps
- Record command executions
- Track approval decisions
- Monitor quota usage

### Performance Metrics
- Response time monitoring
- Success/failure rates
- Token usage tracking

## Integration Points

### With Other Agents
- No shared state with Claude/Codex
- Independent environment sessions
- Respect shared bootstrap validation
- Clean environment variable conflicts

### With CI/CD
- Comply with GitHub Actions workflows
- Respect branch protection rules
- Follow PR approval processes

## Emergency Procedures

### Session Corruption
1. Terminate Gemini CLI process
2. Reset environment: `source ~/.zshrc`
3. Unset conflicting Google environment variables
4. Re-run bootstrap: `./CLI.POSTBOOT.250.sh`
5. Restart with clean GCA configuration

### Authentication Failures
1. Clear browser cache/cookies if OAuth issues
2. Verify GCA access permissions
3. Check account quota status
4. Re-initiate OAuth flow

### Quota Exhaustion
1. Pause operations immediately
2. Report quota status
3. Switch to alternative agent if available
4. Wait for quota reset or upgrade

---

**Agent Version:** Gemini 2.5 Pro (GCA)
**Last Updated:** October 11, 2025
**Configuration Hash:** GEMINI_GCA_v1.0_20251011
