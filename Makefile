postboot:
	@bash ./CLI.POSTBOOT.250.sh

agents-preflight:
	@echo "🔍 Running agent preflight checks..."
	@echo "Checking Gemini sandbox guards..."
	@grep -q "GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX GEMINI_TOOL_SANDBOX GEMINI_EXTENSIONS_SANDBOX" .agents/gemini/start.sh || (echo "❌ Missing sandbox guards in Gemini launcher"; exit 1)
	@grep -q "GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX GEMINI_TOOL_SANDBOX GEMINI_EXTENSIONS_SANDBOX" .agents/gemini/runbook.md || (echo "❌ Missing sandbox guards in Gemini runbook"; exit 1)
	@echo "✅ Gemini sandbox guards verified"
	@echo "Checking Claude flag consistency..."
	@grep -q "\\-\\-allowed-tools" .agents/claude/start.sh || (echo "❌ Claude launcher missing --allowed-tools"; exit 1)
	@grep -q "\\-\\-allowed-tools" .agents/claude/runbook.md || (echo "❌ Claude runbook missing --allowed-tools"; exit 1)
	@! grep -q "\\-\\-tools" .agents/claude/start.sh || (echo "❌ Incorrect --tools in Claude launcher"; exit 1)
	@! grep -q "\\-\\-tools" .agents/claude/runbook.md || (echo "❌ Incorrect --tools in Claude runbook"; exit 1)
	@echo "✅ Claude flag consistency verified"
	@echo "Checking overview consistency..."
	@grep -A 20 "### Claude Code Agent" AGENT_RUNBOOK.md | grep -q "\\-\\-allowed-tools" || (echo "❌ Overview Claude section missing --allowed-tools"; exit 1)
	@grep -A 20 "### Gemini CLI Agent" AGENT_RUNBOOK.md | grep -q "GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX GEMINI_TOOL_SANDBOX GEMINI_EXTENSIONS_SANDBOX" || (echo "❌ Overview Gemini section missing sandbox guards"; exit 1)
	@echo "✅ Overview consistency verified"
	@echo "Checking .agents directory..."
	@! grep -q "^\\.agents/" .gitignore || (echo "❌ .agents/ directory ignored"; exit 1)
	@echo "✅ .agents directory not ignored"
	@echo "Checking CLI availability..."
	@gemini --version || echo "ℹ️  Gemini CLI not available locally"
	@claude --version || echo "ℹ️  Claude CLI not available locally"
	@echo "✅ Agent preflight checks passed!"

.PHONY: sync-constitution sync-constitution-dry sync-constitution-check test-constitution constitution-verify

sync-constitution:      ## Apply constitution updates to all agent runbooks
	@echo "🔄 Syncing constitution to agent runbooks..."
	@bash scripts/sync-constitution.sh

sync-constitution-dry:  ## Preview constitution changes (dry-run)
	@echo "🔍 Previewing constitution sync..."
	@bash scripts/sync-constitution.sh --dry-run

sync-constitution-check: ## Check if constitution is in sync (CI gate)
	@echo "🔍 Checking constitution sync status..."
	@bash scripts/sync-constitution.sh --check

test-constitution: ## Run constitution sync tests
	@echo "🧪 Running constitution sync tests..."
	@bash scripts/tests/test-constitution-sync.sh

constitution-verify: ## Verify constitution content matches source exactly
	@echo "🔍 Verifying constitution equivalence..."
	@bash scripts/verify-constitution-equivalence.sh
