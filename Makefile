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

.PHONY: agents-constitution-check

agents-constitution-check: ## Verify constitution content matches source exactly (read-only)
	@echo "🔍 Verifying constitution equivalence..."
	@bash scripts/verify-constitution-equivalence.sh
