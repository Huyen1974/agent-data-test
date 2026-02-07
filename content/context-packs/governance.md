# Context Pack: Governance

> Load this pack when working on any task to understand rules and constraints.

## Purpose
Provides the constitutional framework, laws, and principles governing all AI agent work in this system.

## Prerequisites
- Read and understand this entire document before starting any task
- These rules are NON-NEGOTIABLE

## Constitution Summary
The system operates under "Agents First" philosophy:
- **AI agents are primary workers**, humans are architects/reviewers
- **No new code** unless absolutely necessary — prefer existing tools, Agency OS components, Directus built-in features
- **Two-hat principle**: Agents wear "Builder hat" (do work) and "Reviewer hat" (verify work)
- All work must be **self-verifiable** — never report success without actual testing

## GC-LAW Key Rules

### GC-LAW 1.3: Single Service Account
- **ONE SA only**: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com`
- NEVER create new Service Accounts
- All Cloud Run deploys, GCS operations, and GCP API calls use this SA

### GC-LAW: No Code New
- Do NOT write new components when existing ones work
- Use Agency OS components as-is
- Use Directus built-in features (Flows, Permissions, API) before custom code
- If WEB-49 deleted KnowledgeTreeView, it was because DocsTreeView already existed

### GC-LAW: Hybrid Local/Cloud
- **Always maintain BOTH local and cloud endpoints**
- Local is priority (faster, cheaper) but NEVER remove cloud fallback
- Config must have: local URL + cloud URL + both API keys
- When local is down, auto-fallback to cloud

## Decision Process (Two-Hat / 2 Mu)
1. **Research** — Investigate before acting. Read actual code, not assumptions.
2. **Plan** — Propose approach, identify risks
3. **Execute** — Make changes using existing components
4. **Verify** — Test with real endpoints, not just "it should work"
5. **Report** — Document what was done, what was verified, what's next

## Stop Rules (Universal)
- Do NOT create new Service Accounts (GC-LAW 1.3)
- Do NOT delete cloud config when adding local config
- Do NOT guess — verify from actual code/config
- Do NOT write new UI components if Agency OS has one
- If infrastructure is broken beyond scope → REPORT, don't heroically fix
- Context Packs must stay under 500 lines each

## Hybrid Principle (Applies Everywhere)
```
Priority: Local SERVICES (fast, free) → Fallback: Cloud SERVICES (when local unavailable)
Cloud for DATA (Firestore, Qdrant, GCS) — ONE SOURCE shared by local + cloud.
NEVER only one path. NEVER delete one when adding the other.
```
This applies to: MCP config, Agent Data connections, all service connections, all future designs.
- Local and Cloud Run share the SAME Firestore (`github-chatgpt-ggcloud`)
- Config must have fallback: local → cloud for services
- Data is always centralized in cloud (Firestore/Qdrant/GCS)

## Related Documents
- `docs/foundation/constitution` — Full constitution text
- `docs/foundation/laws` — Complete GC-LAW reference
- `docs/playbooks/infrastructure-change.md` — Infrastructure change checklist
