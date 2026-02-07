# Context Pack: Web Frontend

> Load this pack for any UI/frontend task (WEB-XX tickets).

## Purpose
Architecture and patterns for the web frontend system.

## Prerequisites
- Context Pack: Governance (for No-Code-New rules)
- Understanding of Nuxt 3 + Agency OS

## Architecture Stack
| Layer | Technology | Notes |
|-------|-----------|-------|
| Framework | Nuxt 3 | SSR + SPA modes |
| UI Kit | Agency OS | Pre-built dashboard components |
| CMS | Directus | Headless CMS, REST + GraphQL API |
| Knowledge | Agent Data | RAG-powered knowledge base |

## Agency OS Components (USE THESE, DON'T REWRITE)
- **DocsTreeView** — Tree view for documents/knowledge
- **buildDocsTree** — Utility to build tree structure from flat docs list
- Components are in Agency OS package, imported via Nuxt modules

## Key Patterns

### /docs is the standard
- `/docs` route is the canonical document browsing interface
- Uses DocsTreeView + Agent Data API for content
- `/knowledge` was a clone of `/docs` — use `/docs` only

### No New Code Rule Applied to Frontend
- WEB-49 **deleted** KnowledgeTreeView because DocsTreeView already existed
- Before writing ANY new component, search Agency OS first
- If Agency OS has a component that's 80% right, use it with props/slots

### Directus Integration
- Directus SDK is used in Nuxt for data fetching
- Collections are accessed via Nuxt composables
- Admin operations go through Directus Flows, not custom API endpoints

## Directus Connection
| Environment | URL | Notes |
|-------------|-----|-------|
| Local | http://localhost:8055 | Docker compose |
| Cloud | (Directus Cloud or self-hosted) | Via environment variable |

## Agent Data API in Frontend
```javascript
// Fetching docs tree
const { data } = await useFetch('/api/docs/tree')

// Getting document content
const { data } = await useFetch('/api/docs/file', { params: { path: docPath } })
```

## Common Mistakes to Avoid
1. Writing a custom tree component — use DocsTreeView
2. Creating new API routes in Nuxt — use Directus or Agent Data API directly
3. Adding npm packages for features Directus already provides
4. Building custom auth — Directus handles authentication

## Current State
- DocsTreeView connected to Agent Data /api/docs/tree
- Knowledge base browsing works via /docs route
- Agency OS provides dashboard layout, navigation, and widgets

## Related Documents
- `docs/context-packs/agent-data.md` — Agent Data API reference
- `docs/context-packs/directus.md` — Directus configuration
- `docs/playbooks/assembly-task.md` — UI assembly checklist
