# Context Pack: Directus

> Load this pack for any task involving Directus CMS integration.

## Purpose
Reference for Directus CMS configuration, collections, and integration patterns.

## Prerequisites
- Directus instance running (local Docker or cloud)
- Admin token for write operations

## Connection
| Environment | URL | Auth |
|-------------|-----|------|
| Local | `http://localhost:8055` | Admin token in .env |
| Cloud | Via environment variable | Admin token in Secret Manager |

## Role in Architecture
Directus serves as the **headless CMS** layer:
- Manages structured content (collections, fields, relations)
- Provides REST + GraphQL APIs out of the box
- Handles authentication and permissions
- Flows engine for automation (NO custom code needed)
- File storage and asset management

## Key Principle: Use Directus Built-in First
Before writing custom code, check if Directus provides:
- **Flows** — Automation, webhooks, scheduled tasks
- **Permissions** — Role-based access control
- **API** — REST/GraphQL endpoints for any collection
- **Webhooks** — Event notifications
- **Extensions** — Only if built-in features are insufficient

## Collections (Key)
Directus collections contain structured data. The exact schema depends on the current Directus instance configuration. Common patterns:
- Content collections for web pages
- Configuration collections for app settings
- Relationship collections linking entities

## SDK Usage in Nuxt
```javascript
// Using Directus SDK in Nuxt composable
import { createDirectus, rest, readItems } from '@directus/sdk';

const directus = createDirectus('http://localhost:8055').with(rest());

// Fetch items from a collection
const items = await directus.request(readItems('collection_name'));
```

## Flows (Automation)
Directus Flows replace custom backend logic:
- **Trigger**: On item create/update/delete, schedule, webhook
- **Operations**: Send email, run script, call API, transform data
- Use Flows instead of writing Cloud Functions when possible

## Integration with Agent Data
- Directus manages structured content
- Agent Data manages unstructured knowledge (docs, RAG)
- Frontend queries both: Directus for structured data, Agent Data for knowledge search
- No duplication — each system owns its domain

## Common Mistakes
1. Writing a custom API when Directus REST API already exposes the collection
2. Building auth from scratch — Directus has built-in auth with roles
3. Creating Cloud Functions for CRUD — use Directus Flows instead
4. Manually managing file uploads — Directus has file storage built in

## Admin Operations
```bash
# Access admin panel
open http://localhost:8055/admin

# API examples
curl http://localhost:8055/items/collection_name \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Related Documents
- `docs/context-packs/web-frontend.md` — Frontend integration patterns
- `docs/context-packs/governance.md` — No-code-new principle
