# Claude Code Agent Memory

## OBJECTIVE
Run Claude Code CLI for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results.

## STARTUP
Use .agents/claude/start.sh for canonical validated launch sequence.

## OPERATIONAL PROCESS
Ask → Read → Cite → Act:
1. Ask: Clarify requirements and constraints
2. Read: Analyze codebase using read_file, search, and tools
3. Cite: Explain reasoning with specific references to code
4. Act: Execute changes with verification

## CONSTITUTION
See docs/constitution/Claude.md for complete operational guidelines and allowed-tools configuration.
