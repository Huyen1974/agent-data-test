#!/usr/bin/env python3
"""
MCP Server for Directus (stdio transport).
Provides CRUD access to Directus collections, schema inspection,
and flow management — all via the Directus REST API.

Auth: email/password login → Bearer token (auto-refreshes on 401).

Usage:
    python directus_stdio_server.py           # run as MCP stdio server
    python directus_stdio_server.py --test    # quick connectivity check
"""

import asyncio
import json
import logging
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("mcp-directus")

# --- Config ---
DIRECTUS_URL = os.getenv("DIRECTUS_URL", "https://directus.incomexsaigoncorp.vn")
DIRECTUS_STATIC_TOKEN = os.getenv("DIRECTUS_STATIC_TOKEN", "")

# Load credentials from file (preferred) or env vars (fallback)
_creds_file = os.getenv("DIRECTUS_CREDENTIALS_FILE", "")
DIRECTUS_EMAIL = os.getenv("DIRECTUS_EMAIL", "")
DIRECTUS_PASSWORD = os.getenv("DIRECTUS_PASSWORD", "")

if _creds_file and os.path.isfile(_creds_file):
    try:
        with open(_creds_file) as f:
            _creds = json.load(f)
        # credentials.local.json has profiles[].username/password and directusUrl
        _profiles = _creds.get("profiles", [])
        if _profiles:
            _default_name = _creds.get("defaultProfile", "")
            _profile = next(
                (p for p in _profiles if p.get("name") == _default_name),
                _profiles[0],
            )
            if not DIRECTUS_EMAIL:
                DIRECTUS_EMAIL = _profile.get("username", "")
            if not DIRECTUS_PASSWORD:
                DIRECTUS_PASSWORD = _profile.get("password", "")
        # staticToken takes precedence if present
        _st = _creds.get("staticToken", "")
        if _st and not DIRECTUS_STATIC_TOKEN:
            DIRECTUS_STATIC_TOKEN = _st
        logger.info("Loaded credentials from %s", _creds_file)
    except Exception as e:
        logger.warning("Failed to load credentials file: %s", e)

if not DIRECTUS_EMAIL:
    DIRECTUS_EMAIL = "admin@example.com"

# Collection whitelist (empty = allow all)
_whitelist_raw = os.getenv("DIRECTUS_COLLECTION_WHITELIST", "")
COLLECTION_WHITELIST: set[str] = (
    {c.strip() for c in _whitelist_raw.split(",") if c.strip()}
    if _whitelist_raw
    else set()
)

TIMEOUT = float(os.getenv("DIRECTUS_TIMEOUT", "30"))

# --- Token management ---
_access_token: str = ""
_refresh_token: str = ""


def _check_collection(collection: str) -> str | None:
    """Return an error message if collection is not whitelisted, else None."""
    if COLLECTION_WHITELIST and collection not in COLLECTION_WHITELIST:
        allowed = ", ".join(sorted(COLLECTION_WHITELIST))
        return f"Collection '{collection}' is not in the whitelist. Allowed: {allowed}"
    return None


async def _login(client: httpx.AsyncClient) -> bool:
    """Authenticate and store tokens. Returns True on success."""
    global _access_token, _refresh_token

    if DIRECTUS_STATIC_TOKEN:
        _access_token = DIRECTUS_STATIC_TOKEN
        return True

    if not DIRECTUS_PASSWORD:
        logger.error("No DIRECTUS_PASSWORD or DIRECTUS_STATIC_TOKEN set")
        return False

    try:
        resp = await client.post(
            f"{DIRECTUS_URL}/auth/login",
            json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            _access_token = data.get("access_token", "")
            _refresh_token = data.get("refresh_token", "")
            if _access_token:
                logger.info("Directus login OK")
                return True
        logger.error("Login failed: HTTP %s — %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Login error: %s", e)
    return False


async def _ensure_token(client: httpx.AsyncClient) -> dict[str, str]:
    """Return auth headers, refreshing/logging in if needed."""
    global _access_token, _refresh_token

    if _access_token:
        return {"Authorization": f"Bearer {_access_token}"}

    # Try refresh first
    if _refresh_token:
        try:
            resp = await client.post(
                f"{DIRECTUS_URL}/auth/refresh",
                json={"refresh_token": _refresh_token, "mode": "json"},
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                _access_token = data.get("access_token", "")
                _refresh_token = data.get("refresh_token", _refresh_token)
                if _access_token:
                    return {"Authorization": f"Bearer {_access_token}"}
        except Exception:
            pass

    # Fall back to full login
    if await _login(client):
        return {"Authorization": f"Bearer {_access_token}"}

    return {}


async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    """Make an authenticated request, retrying once on 401."""
    global _access_token

    headers = await _ensure_token(client)
    merged = {**headers, **kwargs.pop("headers", {})}

    resp = await client.request(
        method,
        f"{DIRECTUS_URL}{path}",
        headers=merged,
        timeout=kwargs.pop("timeout", TIMEOUT),
        **kwargs,
    )

    # On 401, clear token and retry once
    if resp.status_code == 401:
        _access_token = ""
        headers = await _ensure_token(client)
        if headers:
            merged.update(headers)
            resp = await client.request(
                method,
                f"{DIRECTUS_URL}{path}",
                headers=merged,
                timeout=TIMEOUT,
                **kwargs,
            )

    return resp


def _error(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {msg}")]


def _format_items(items: list[dict], collection: str, limit: int) -> str:
    """Format a list of items for display."""
    if not items:
        return f"No items found in '{collection}'."
    lines = [f"Items in '{collection}' ({len(items)} returned, limit={limit}):\n"]
    for item in items:
        item_id = item.get("id", "?")
        # Try common name fields
        label = (
            item.get("name")
            or item.get("title")
            or item.get("label")
            or item.get("slug")
            or ""
        )
        summary = f"  #{item_id}"
        if label:
            summary += f" — {label}"
        # Show status if present
        status = item.get("status")
        if status:
            summary += f" [{status}]"
        lines.append(summary)
    return "\n".join(lines)


# --- MCP server ---
server = Server("directus")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # --- READ ---
        Tool(
            name="directus_health",
            description="Check Directus server health status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="directus_list_collections",
            description="List all available Directus collections (tables).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="directus_get_schema",
            description="Get fields/schema for a Directus collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name, e.g. 'tasks'",
                    },
                },
                "required": ["collection"],
            },
        ),
        Tool(
            name="directus_get_items",
            description="List items from a Directus collection with optional filtering and sorting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name, e.g. 'tasks'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return (default 25)",
                        "default": 25,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of items to skip",
                        "default": 0,
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort field, prefix with - for descending. E.g. '-date_created'",
                    },
                    "filter": {
                        "type": "object",
                        "description": "Directus filter object, e.g. {\"status\": {\"_eq\": \"active\"}}",
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated fields to return. E.g. 'id,name,status'",
                    },
                    "search": {
                        "type": "string",
                        "description": "Full-text search query",
                    },
                },
                "required": ["collection"],
            },
        ),
        Tool(
            name="directus_get_item",
            description="Get a single item by ID from a Directus collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "id": {
                        "type": ["string", "integer"],
                        "description": "Item ID",
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated fields to return",
                    },
                },
                "required": ["collection", "id"],
            },
        ),
        # --- WRITE ---
        Tool(
            name="directus_create_item",
            description="Create a new item in a Directus collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "data": {
                        "type": "object",
                        "description": "Item data as JSON object",
                    },
                },
                "required": ["collection", "data"],
            },
        ),
        Tool(
            name="directus_update_item",
            description="Update an existing item in a Directus collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "id": {
                        "type": ["string", "integer"],
                        "description": "Item ID to update",
                    },
                    "data": {
                        "type": "object",
                        "description": "Fields to update as JSON object",
                    },
                },
                "required": ["collection", "id", "data"],
            },
        ),
        Tool(
            name="directus_delete_item",
            description="Delete an item from a Directus collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "id": {
                        "type": ["string", "integer"],
                        "description": "Item ID to delete",
                    },
                },
                "required": ["collection", "id"],
            },
        ),
        # --- WORKFLOWS ---
        Tool(
            name="directus_list_flows",
            description="List Directus automation flows.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="directus_trigger_flow",
            description="Manually trigger a Directus flow by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {
                        "type": "string",
                        "description": "Flow UUID to trigger",
                    },
                    "data": {
                        "type": "object",
                        "description": "Optional payload to send to the flow",
                    },
                },
                "required": ["flow_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # --- directus_health ---
            if name == "directus_health":
                resp = await client.get(
                    f"{DIRECTUS_URL}/server/health", timeout=TIMEOUT
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Directus health: {data.get('status', 'unknown')}\nURL: {DIRECTUS_URL}",
                        )
                    ]
                return _error(f"Health check failed: HTTP {resp.status_code}")

            # --- directus_list_collections ---
            elif name == "directus_list_collections":
                resp = await _request(client, "GET", "/collections")
                if resp.status_code == 200:
                    collections = resp.json().get("data", [])
                    # Filter out system collections for cleaner output
                    user_cols = [
                        c
                        for c in collections
                        if not c["collection"].startswith("directus_")
                    ]
                    lines = [f"Collections ({len(user_cols)} user, {len(collections)} total):\n"]
                    for c in user_cols:
                        col = c["collection"]
                        note = c.get("meta", {}).get("note", "") if c.get("meta") else ""
                        wl = " [whitelisted]" if not COLLECTION_WHITELIST or col in COLLECTION_WHITELIST else ""
                        line = f"  {col}{wl}"
                        if note:
                            line += f" — {note}"
                        lines.append(line)
                    return [TextContent(type="text", text="\n".join(lines))]
                return _error(f"HTTP {resp.status_code}: {resp.text[:200]}")

            # --- directus_get_schema ---
            elif name == "directus_get_schema":
                collection = arguments.get("collection", "")
                err = _check_collection(collection)
                if err:
                    return _error(err)
                resp = await _request(client, "GET", f"/fields/{collection}")
                if resp.status_code == 200:
                    fields = resp.json().get("data", [])
                    lines = [f"Schema for '{collection}' ({len(fields)} fields):\n"]
                    for f in fields:
                        fname = f.get("field", "?")
                        ftype = f.get("type", "?")
                        meta = f.get("meta", {}) or {}
                        required = meta.get("required", False)
                        note = meta.get("note", "")
                        line = f"  {fname}: {ftype}"
                        if required:
                            line += " [required]"
                        if note:
                            line += f" — {note}"
                        lines.append(line)
                    return [TextContent(type="text", text="\n".join(lines))]
                return _error(f"HTTP {resp.status_code}: {resp.text[:200]}")

            # --- directus_get_items ---
            elif name == "directus_get_items":
                collection = arguments.get("collection", "")
                err = _check_collection(collection)
                if err:
                    return _error(err)
                params: dict = {}
                limit = arguments.get("limit", 25)
                params["limit"] = limit
                if arguments.get("offset"):
                    params["offset"] = arguments["offset"]
                if arguments.get("sort"):
                    params["sort"] = arguments["sort"]
                if arguments.get("fields"):
                    params["fields"] = arguments["fields"]
                if arguments.get("search"):
                    params["search"] = arguments["search"]
                if arguments.get("filter"):
                    params["filter"] = json.dumps(arguments["filter"])
                resp = await _request(
                    client, "GET", f"/items/{collection}", params=params
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", [])
                    # Return full JSON for programmatic use
                    text = _format_items(items, collection, limit)
                    text += "\n\n--- Raw JSON ---\n"
                    text += json.dumps(items, ensure_ascii=False, indent=2, default=str)
                    return [TextContent(type="text", text=text)]
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            # --- directus_get_item ---
            elif name == "directus_get_item":
                collection = arguments.get("collection", "")
                item_id = arguments.get("id", "")
                err = _check_collection(collection)
                if err:
                    return _error(err)
                params = {}
                if arguments.get("fields"):
                    params["fields"] = arguments["fields"]
                resp = await _request(
                    client, "GET", f"/items/{collection}/{item_id}", params=params
                )
                if resp.status_code == 200:
                    item = resp.json().get("data", {})
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                item, ensure_ascii=False, indent=2, default=str
                            ),
                        )
                    ]
                elif resp.status_code == 404:
                    return _error(
                        f"Item {item_id} not found in '{collection}'."
                    )
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            # --- directus_create_item ---
            elif name == "directus_create_item":
                collection = arguments.get("collection", "")
                data = arguments.get("data", {})
                err = _check_collection(collection)
                if err:
                    return _error(err)
                resp = await _request(
                    client, "POST", f"/items/{collection}", json=data
                )
                if resp.status_code in (200, 201, 204):
                    result = resp.json().get("data", {}) if resp.content else {}
                    item_id = result.get("id", "?")
                    return [
                        TextContent(
                            type="text",
                            text=f"Created item #{item_id} in '{collection}'.\n{json.dumps(result, ensure_ascii=False, indent=2, default=str)}",
                        )
                    ]
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            # --- directus_update_item ---
            elif name == "directus_update_item":
                collection = arguments.get("collection", "")
                item_id = arguments.get("id", "")
                data = arguments.get("data", {})
                err = _check_collection(collection)
                if err:
                    return _error(err)
                resp = await _request(
                    client, "PATCH", f"/items/{collection}/{item_id}", json=data
                )
                if resp.status_code == 200:
                    result = resp.json().get("data", {})
                    return [
                        TextContent(
                            type="text",
                            text=f"Updated item #{item_id} in '{collection}'.\n{json.dumps(result, ensure_ascii=False, indent=2, default=str)}",
                        )
                    ]
                elif resp.status_code == 404:
                    return _error(
                        f"Item {item_id} not found in '{collection}'."
                    )
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            # --- directus_delete_item ---
            elif name == "directus_delete_item":
                collection = arguments.get("collection", "")
                item_id = arguments.get("id", "")
                err = _check_collection(collection)
                if err:
                    return _error(err)
                resp = await _request(
                    client, "DELETE", f"/items/{collection}/{item_id}"
                )
                if resp.status_code in (200, 204):
                    return [
                        TextContent(
                            type="text",
                            text=f"Deleted item #{item_id} from '{collection}'.",
                        )
                    ]
                elif resp.status_code == 404:
                    return _error(
                        f"Item {item_id} not found in '{collection}'."
                    )
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            # --- directus_list_flows ---
            elif name == "directus_list_flows":
                resp = await _request(client, "GET", "/flows")
                if resp.status_code == 200:
                    flows = resp.json().get("data", [])
                    if not flows:
                        return [TextContent(type="text", text="No flows found.")]
                    lines = [f"Flows ({len(flows)}):\n"]
                    for f in flows:
                        fid = f.get("id", "?")
                        fname = f.get("name", "Unnamed")
                        status = f.get("status", "?")
                        trigger = f.get("trigger", "?")
                        lines.append(
                            f"  {fname} [{status}] trigger={trigger}\n    id: {fid}"
                        )
                    return [TextContent(type="text", text="\n".join(lines))]
                return _error(f"HTTP {resp.status_code}: {resp.text[:200]}")

            # --- directus_trigger_flow ---
            elif name == "directus_trigger_flow":
                flow_id = arguments.get("flow_id", "")
                data = arguments.get("data", {})
                resp = await _request(
                    client, "POST", f"/flows/trigger/{flow_id}", json=data
                )
                if resp.status_code in (200, 204):
                    body = resp.json() if resp.content else {}
                    return [
                        TextContent(
                            type="text",
                            text=f"Flow {flow_id} triggered.\n{json.dumps(body, ensure_ascii=False, indent=2, default=str)}",
                        )
                    ]
                return _error(f"HTTP {resp.status_code}: {resp.text[:300]}")

            else:
                return _error(f"Unknown tool: {name}")

        except httpx.ConnectError as e:
            return _error(f"Connection failed: {e}")
        except httpx.RequestError as e:
            return _error(f"Request failed: {e}")
        except Exception as e:
            return _error(f"{type(e).__name__}: {e}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":

        async def test():
            print("Directus MCP STDIO Server Test")
            print("=" * 40)
            print(f"URL:        {DIRECTUS_URL}")
            print(f"Email:      {DIRECTUS_EMAIL}")
            print(f"Password:   {'***' if DIRECTUS_PASSWORD else '(not set)'}")
            print(f"Static tok: {'***' if DIRECTUS_STATIC_TOKEN else '(not set)'}")
            print(f"Whitelist:  {sorted(COLLECTION_WHITELIST) if COLLECTION_WHITELIST else '(all)'}")
            print()

            tools = await list_tools()
            print(f"Tools: {len(tools)}")
            for t in tools:
                print(f"  - {t.name}: {t.description[:60]}")
            print()

            # Test health (no auth needed)
            print("1. Testing directus_health...")
            result = await call_tool("directus_health", {})
            text = result[0].text
            if "ok" in text.lower():
                print(f"   PASS — {text}")
            else:
                print(f"   FAIL — {text}")

            # Test login + list collections
            print("2. Testing directus_list_collections...")
            result = await call_tool("directus_list_collections", {})
            text = result[0].text
            if "Collections" in text:
                # Count lines
                count = text.split("\n")[0]
                print(f"   PASS — {count}")
            else:
                print(f"   FAIL — {text[:100]}")

            # Test get_items
            print("3. Testing directus_get_items (tasks, limit=2)...")
            result = await call_tool(
                "directus_get_items", {"collection": "tasks", "limit": 2}
            )
            text = result[0].text
            if "Error" not in text:
                summary = text.split("\n")[0]
                print(f"   PASS — {summary}")
            else:
                print(f"   FAIL — {text[:100]}")

            # Test get_schema
            print("4. Testing directus_get_schema (tasks)...")
            result = await call_tool(
                "directus_get_schema", {"collection": "tasks"}
            )
            text = result[0].text
            if "fields" in text.lower():
                summary = text.split("\n")[0]
                print(f"   PASS — {summary}")
            else:
                print(f"   FAIL — {text[:100]}")

            # Test list_flows
            print("5. Testing directus_list_flows...")
            result = await call_tool("directus_list_flows", {})
            text = result[0].text
            if "Error" not in text:
                summary = text.split("\n")[0]
                print(f"   PASS — {summary}")
            else:
                print(f"   FAIL — {text[:100]}")

            # Test CRUD: create → get → update → delete
            print("6. Testing CRUD (task_comments)...")
            # Create
            result = await call_tool(
                "directus_create_item",
                {
                    "collection": "task_comments",
                    "data": {
                        "content": "MCP test comment — safe to delete",
                        "task_id": 1,
                        "agent_type": "mcp-test",
                        "action": "comment",
                        "tab_scope": "general",
                    },
                },
            )
            text = result[0].text
            if "Created" in text:
                # Extract ID
                import re

                m = re.search(r"#(\d+)", text)
                item_id = m.group(1) if m else None
                print(f"   CREATE PASS — id={item_id}")

                if item_id:
                    # Update
                    result = await call_tool(
                        "directus_update_item",
                        {
                            "collection": "task_comments",
                            "id": int(item_id),
                            "data": {"content": "MCP test UPDATED"},
                        },
                    )
                    text = result[0].text
                    print(
                        f"   UPDATE {'PASS' if 'Updated' in text else 'FAIL'} — {text.split(chr(10))[0]}"
                    )

                    # Delete
                    result = await call_tool(
                        "directus_delete_item",
                        {"collection": "task_comments", "id": int(item_id)},
                    )
                    text = result[0].text
                    print(
                        f"   DELETE {'PASS' if 'Deleted' in text else 'FAIL'} — {text}"
                    )
            else:
                print(f"   CREATE FAIL — {text[:100]}")

            print()
            print("=" * 40)
            print("Test completed!")

        asyncio.run(test())
    else:
        asyncio.run(main())
