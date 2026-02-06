# Playbook: Assembly Task (UI/Frontend)

> Use this playbook for any WEB-XX task that involves UI assembly or frontend changes.

## Before Starting

### Load Context Packs
- [ ] `governance` — Rules and constraints
- [ ] `web-frontend` — Architecture and components
- [ ] `current-sprint` — What's happening now

### Pre-flight Checks
- [ ] Read the ticket requirements completely
- [ ] Search Agency OS components for existing solutions
- [ ] Confirm: Is new code ACTUALLY needed? (Usually NO)
- [ ] Check Directus for existing data structures
- [ ] Verify local dev environment is running (`dot-ai-start`)

## During Task

### Step 1: Research
- [ ] Identify which Agency OS components to use
- [ ] Read the source code of those components
- [ ] Check if props/slots can customize behavior enough
- [ ] If component doesn't exist in Agency OS, check Nuxt ecosystem

### Step 2: Plan
- [ ] List files that will be modified (NOT created)
- [ ] Identify data source: Directus collection or Agent Data API?
- [ ] Draft approach using existing components only
- [ ] If new code is needed, document WHY existing won't work

### Step 3: Execute
- [ ] Modify existing files (prefer edit over create)
- [ ] Use Agency OS components via imports
- [ ] Connect to data source (Directus SDK or Agent Data fetch)
- [ ] Keep changes minimal — no cleanup of surrounding code

### Step 4: Verify (MANDATORY)
- [ ] Run local dev server and visually verify
- [ ] Test all user interactions (click, navigate, form submit)
- [ ] Check mobile responsiveness if applicable
- [ ] Verify no console errors
- [ ] Test with real data, not mock data

## After Task

### Documentation
- [ ] Write session report: `docs/operations/sessions/web-XX-report.md`
- [ ] Upload report to Agent Data via `upload_document` tool
- [ ] Update `docs/context-packs/current-sprint.md` if sprint status changed

### Cleanup
- [ ] Remove any test data created during development
- [ ] Verify no temporary files were committed
- [ ] Check that no new npm packages were added unnecessarily

## Red Flags (STOP and reconsider)
- "I need to create a new component" → Check Agency OS first
- "I need a new API endpoint" → Check Directus/Agent Data APIs
- "I need to install a new package" → Is there a built-in way?
- "I need to modify the database schema" → Use Directus admin
