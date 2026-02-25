#!/usr/bin/env python3
"""
MCP Server for Claude Desktop (stdio transport)
Provides search_knowledge, list_documents, get_document (read),
upload_document, update_document, delete_document, move_document, ingest_document (write),
and get_document_for_rewrite, patch_document, batch_read (WEB-84C)
"""

import asyncio
import logging
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("mcp-stdio")

# --- Hybrid config ---
# Primary (local) and fallback (cloud) endpoints
AGENT_DATA_URL = os.getenv("AGENT_DATA_URL", "http://localhost:8000")
AGENT_DATA_URL_CLOUD = os.getenv("AGENT_DATA_URL_CLOUD", "")
AGENT_DATA_PREFER = os.getenv("AGENT_DATA_PREFER", "local")

# API keys per environment
AGENT_DATA_API_KEY_LOCAL = os.getenv(
    "AGENT_DATA_API_KEY_LOCAL", os.getenv("AGENT_DATA_API_KEY", "")
)
AGENT_DATA_API_KEY_CLOUD = os.getenv("AGENT_DATA_API_KEY_CLOUD", "")

# Track which endpoint is currently active
_active_url: str = AGENT_DATA_URL
_active_api_key: str = AGENT_DATA_API_KEY_LOCAL


def _get_auth_headers(url: str | None = None) -> dict[str, str]:
    """Build auth headers for the given URL (or active URL)."""
    target = url or _active_url
    headers: dict[str, str] = {}

    # Select correct API key based on target
    if target == AGENT_DATA_URL:
        api_key = AGENT_DATA_API_KEY_LOCAL
    elif target == AGENT_DATA_URL_CLOUD:
        api_key = AGENT_DATA_API_KEY_CLOUD
    else:
        api_key = AGENT_DATA_API_KEY_LOCAL

    if api_key:
        headers["X-API-Key"] = api_key

    # Add Google Cloud identity token if targeting Cloud Run (https://)
    if target.startswith("https://"):
        try:
            import subprocess

            result = subprocess.run(
                ["gcloud", "auth", "print-identity-token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                headers["Authorization"] = f"Bearer {result.stdout.strip()}"
        except Exception:
            pass  # Fall through without IAM token

    return headers


async def _request_with_fallback(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    """Try primary URL first; on connection error, fallback to cloud.

    Returns the httpx.Response from whichever endpoint succeeds.
    """
    global _active_url, _active_api_key

    primary = AGENT_DATA_URL
    fallback = AGENT_DATA_URL_CLOUD

    for attempt_url in [primary, fallback]:
        if not attempt_url:
            continue
        try:
            headers = _get_auth_headers(attempt_url)
            merged_headers = {**headers, **kwargs.pop("headers", {})}
            resp = await client.request(
                method,
                f"{attempt_url}{path}",
                headers=merged_headers,
                timeout=kwargs.pop("timeout", 30.0),
                **kwargs,
            )
            if _active_url != attempt_url:
                label = "LOCAL" if attempt_url == primary else "CLOUD"
                logger.info("Using %s endpoint: %s", label, attempt_url)
                _active_url = attempt_url
            return resp
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            label = "LOCAL" if attempt_url == primary else "CLOUD"
            logger.warning("%s unavailable (%s), trying fallback...", label, e)
            continue

    raise httpx.ConnectError(
        f"Both LOCAL ({primary}) and CLOUD ({fallback}) unavailable"
    )


# Create MCP server
server = Server("agent-data")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_knowledge",
            description="Search the knowledge base using semantic/RAG query. Returns relevant documents and context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_documents",
            description="List available documents in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path prefix to filter",
                        "default": "",
                    },
                },
            },
        ),
        Tool(
            name="get_document",
            description="Get full content of a specific document by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID or path",
                    },
                },
                "required": ["document_id"],
            },
        ),
        # --- Write tools ---
        Tool(
            name="upload_document",
            description="Upload/create a new document in the knowledge base.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document path, e.g. 'docs/operations/sessions/web-50-report.md'",
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content (markdown or plain text)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional document title",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for classification",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="update_document",
            description="Update an existing document's content and/or metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document path to update, e.g. 'docs/foundation/constitution.md'",
                    },
                    "content": {
                        "type": "string",
                        "description": "New document content",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional new title",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional new tags",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="delete_document",
            description="Delete a document from the knowledge base.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document path to delete, e.g. 'docs/test/old-file.md'",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="move_document",
            description="Move a document to a new parent. Use 'root' to move to top level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Current document path, e.g. 'docs/old-location/file.md'",
                    },
                    "new_path": {
                        "type": "string",
                        "description": "New parent document path, or 'root' for top level",
                    },
                },
                "required": ["path", "new_path"],
            },
        ),
        Tool(
            name="ingest_document",
            description="Ingest a document from GCS URI or URL into the knowledge base for vector processing",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "GCS URI (gs://bucket/path) or URL to ingest",
                    },
                },
                "required": ["source"],
            },
        ),
        # --- WEB-84C: Rewrite, patch, batch tools ---
        Tool(
            name="get_document_for_rewrite",
            description="Get full document content for rewriting. Only use when you need to rewrite the entire document. For reading/reference, use search_knowledge instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document path, e.g. 'knowledge/dev/ssot/operating-rules.md'",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="patch_document",
            description="Patch a specific section of a document. old_str must appear exactly once. Returns 404 if document not found, 409 if old_str not found or ambiguous (appears multiple times).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document path to patch",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Exact string to find (must appear exactly once)",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement string",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        ),
        Tool(
            name="batch_read",
            description="Read multiple documents in one call. Max 20 paths. Returns truncated content by default, use full=true for complete content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of document paths to read (max 20)",
                    },
                    "full": {
                        "type": "boolean",
                        "description": "If true, return full content instead of truncated",
                        "default": False,
                    },
                },
                "required": ["paths"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool and return results. Uses hybrid fallback (local→cloud)."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "search_knowledge":
                query = arguments.get("query", "")
                response = await _request_with_fallback(
                    client,
                    "POST",
                    "/chat",
                    json={"message": query},
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("response", data.get("content", "No response"))
                    context = data.get("context", [])
                    if context:
                        sources = "\n\nSources:\n" + "\n".join(
                            f"- {c.get('document_id', 'unknown')}" for c in context[:3]
                        )
                        result += sources
                    return [TextContent(type="text", text=result)]
                else:
                    return [
                        TextContent(
                            type="text", text=f"Error: HTTP {response.status_code}"
                        )
                    ]

            elif name == "list_documents":
                path = arguments.get("path", "")
                # Primary: list from Firestore KB (where documents are actually stored)
                response = await _request_with_fallback(
                    client,
                    "GET",
                    "/kb/list",
                    params={"prefix": path},
                )
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        result = f"Documents in '{path}' ({len(items)} items):\n\n"
                        for item in items:
                            tags = item.get("tags", [])
                            tag_str = f" [{', '.join(tags)}]" if tags else ""
                            result += f"- {item.get('document_id', '?')}{tag_str}\n"
                        return [TextContent(type="text", text=result)]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"No documents found with prefix '{path}'",
                            )
                        ]
                return [
                    TextContent(
                        type="text",
                        text=f"Error listing documents: HTTP {response.status_code}",
                    )
                ]

            elif name == "get_document":
                doc_id = arguments.get("document_id", "")
                # Primary: get from Firestore KB
                response = await _request_with_fallback(
                    client,
                    "GET",
                    f"/kb/get/{doc_id}",
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    if content:
                        meta = data.get("metadata", {})
                        title = meta.get("title", doc_id)
                        return [
                            TextContent(type="text", text=f"# {title}\n\n{content}")
                        ]

                # Fallback: try GitHub docs
                doc_path = doc_id if doc_id.startswith("docs/") else f"docs/{doc_id}"
                response = await _request_with_fallback(
                    client,
                    "GET",
                    "/api/docs/file",
                    params={"path": doc_path},
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    if content:
                        return [
                            TextContent(
                                type="text", text=f"# Document: {doc_id}\n\n{content}"
                            )
                        ]

                return [TextContent(type="text", text=f"Document '{doc_id}' not found")]

            elif name == "upload_document":
                path = arguments.get("path", "")
                content = arguments.get("content", "")
                title = arguments.get("title", "")
                tags = arguments.get("tags", [])
                parent_id = "/".join(path.split("/")[:-1]) if "/" in path else ""
                if not title:
                    title = path.rsplit("/", 1)[-1] if "/" in path else path
                body = {
                    "document_id": path,
                    "parent_id": parent_id,
                    "content": {"mime_type": "text/markdown", "body": content},
                    "metadata": {"title": title},
                }
                if tags:
                    body["metadata"]["tags"] = tags
                response = await _request_with_fallback(
                    client,
                    "POST",
                    "/documents",
                    json=body,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Document created: {data.get('id', path)} (revision {data.get('revision', 1)})",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Upload failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "update_document":
                path = arguments.get("path", "")
                content = arguments.get("content", "")
                title = arguments.get("title", "")
                tags = arguments.get("tags", [])
                patch = {"content": {"mime_type": "text/markdown", "body": content}}
                update_mask = ["content"]
                metadata = {}
                if title:
                    metadata["title"] = title
                if tags:
                    metadata["tags"] = tags
                if metadata:
                    patch["metadata"] = metadata
                    update_mask.append("metadata")
                body = {
                    "document_id": path,
                    "patch": patch,
                    "update_mask": update_mask,
                }
                response = await _request_with_fallback(
                    client,
                    "PUT",
                    f"/documents/{path}",
                    json=body,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Document updated: {data.get('id', path)} (revision {data.get('revision', '?')})",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Update failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "delete_document":
                path = arguments.get("path", "")
                response = await _request_with_fallback(
                    client,
                    "DELETE",
                    f"/documents/{path}",
                )
                if response.status_code == 200:
                    data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Document deleted: {data.get('id', path)}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Delete failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "move_document":
                path = arguments.get("path", "")
                new_path = arguments.get("new_path", "")
                response = await _request_with_fallback(
                    client,
                    "POST",
                    f"/documents/{path}/move",
                    json={"new_parent_id": new_path},
                )
                if response.status_code == 200:
                    data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Document moved: {data.get('id', path)} → {new_path}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Move failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "ingest_document":
                source = arguments.get("source", "")
                response = await _request_with_fallback(
                    client,
                    "POST",
                    "/ingest",
                    json={"text": source},
                )
                if response.status_code in (200, 202):
                    data = response.json()
                    msg = data.get(
                        "response", data.get("content", "Ingestion accepted")
                    )
                    return [TextContent(type="text", text=f"Ingest accepted: {msg}")]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Ingest failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "get_document_for_rewrite":
                path = arguments.get("path", "")
                response = await _request_with_fallback(
                    client,
                    "GET",
                    f"/documents/{path}",
                    params={"full": "true", "search": "false"},
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    meta = data.get("metadata", {})
                    title = meta.get("title", path)
                    info = f"document_id: {data.get('document_id', path)}\n"
                    info += (
                        f"content_length: {data.get('content_length', len(content))}\n"
                    )
                    info += f"revision: {data.get('revision', '?')}\n\n"
                    return [
                        TextContent(type="text", text=f"# {title}\n\n{info}{content}")
                    ]
                elif response.status_code == 404:
                    return [
                        TextContent(type="text", text=f"Document '{path}' not found")
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "patch_document":
                path = arguments.get("path", "")
                old_str = arguments.get("old_str", "")
                new_str = arguments.get("new_str", "")
                response = await _request_with_fallback(
                    client,
                    "PATCH",
                    f"/documents/{path}",
                    json={"old_str": old_str, "new_str": new_str},
                )
                if response.status_code == 200:
                    data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Document patched: {data.get('id', path)} (revision {data.get('revision', '?')})",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Patch failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            elif name == "batch_read":
                paths = arguments.get("paths", [])
                full = arguments.get("full", False)
                response = await _request_with_fallback(
                    client,
                    "POST",
                    "/documents/batch",
                    json={"paths": paths, "full": full},
                )
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    count = data.get("count", len(items))
                    result = f"Batch read: {count} documents\n\n"
                    for item in items:
                        doc_id = item.get("document_id", "?")
                        error = item.get("error")
                        if error:
                            result += f"--- {doc_id} (ERROR: {error}) ---\n\n"
                        else:
                            content = item.get("content", "")
                            truncated = item.get("truncated", False)
                            tag = " [truncated]" if truncated else ""
                            result += f"--- {doc_id}{tag} ---\n{content}\n\n"
                    return [TextContent(type="text", text=result)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Batch read failed: HTTP {response.status_code} — {response.text}",
                        )
                    ]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError as e:
            return [
                TextContent(
                    type="text",
                    text=f"Connection error: {str(e)}. Both local and cloud endpoints unavailable.",
                )
            ]
        except httpx.RequestError as e:
            return [TextContent(type="text", text=f"Request error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    # Test mode: verify tools can be listed
    if len(sys.argv) > 1 and sys.argv[1] == "--test":

        async def test():
            tools = await list_tools()
            print("MCP STDIO Server Test (Hybrid)")
            print("==============================")
            print(f"Local URL:  {AGENT_DATA_URL}")
            print(f"Cloud URL:  {AGENT_DATA_URL_CLOUD}")
            print(f"Prefer:     {AGENT_DATA_PREFER}")
            print(f"Tools:      {len(tools)}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")

            # Test connection with hybrid fallback
            import httpx

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await _request_with_fallback(client, "GET", "/info")
                    if resp.status_code == 200:
                        print(f"Agent Data connection: OK (via {_active_url})")
                    else:
                        print(f"Agent Data connection: ERROR ({resp.status_code})")
            except Exception as e:
                print(f"Agent Data connection: FAILED ({e})")

            print("==============================")
            print("Test completed successfully!")

        asyncio.run(test())

    # Full tool test mode
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-tools":

        async def test_tools():
            print("MCP Tools Integration Test")
            print("==========================\n")

            # Test 1: list_documents
            print("1. Testing list_documents...")
            result = await call_tool("list_documents", {"path": "knowledge"})
            output = result[0].text if result else "No output"
            if "knowledge/" in output:
                print("   ✅ PASS - Returns document list")
                print(f"   Preview: {output[:200]}...")
            else:
                print(f"   ❌ FAIL - {output[:100]}")

            print()

            # Test 2: get_document
            print("2. Testing get_document...")
            result = await call_tool(
                "get_document",
                {"document_id": "knowledge/current-state/firebase-hosting-status.md"},
            )
            output = result[0].text if result else "No output"
            if len(output) > 100:
                print("   ✅ PASS - Returns full document content")
                print(f"   Length: {len(output)} chars")
            else:
                print(f"   ❌ FAIL - {output[:100]}")

            print()

            # Test 3: search_knowledge
            print("3. Testing search_knowledge...")
            result = await call_tool("search_knowledge", {"query": "Terraform IaC"})
            output = result[0].text if result else "No output"
            if len(output) > 50:
                print("   ✅ PASS - Returns search results")
                print(f"   Preview: {output[:200]}...")
            else:
                print(f"   ❌ FAIL - {output[:100]}")

            print()

            # Test 4: Write tools (upload → update → delete)
            test_path = "mcp-write-test-auto"
            print("4. Testing upload_document...")
            result = await call_tool(
                "upload_document",
                {
                    "path": test_path,
                    "content": "# MCP Write Test\nAutomated test document.",
                    "title": "MCP Write Test",
                    "tags": ["test", "mcp"],
                },
            )
            output = result[0].text if result else "No output"
            if "created" in output.lower() or "revision" in output.lower():
                print(f"   ✅ PASS - {output}")
            else:
                print(f"   ❌ FAIL - {output[:200]}")

            print()

            print("5. Testing update_document...")
            result = await call_tool(
                "update_document",
                {
                    "path": test_path,
                    "content": "# MCP Write Test (Updated)\nThis content was updated.",
                },
            )
            output = result[0].text if result else "No output"
            if "updated" in output.lower() or "revision" in output.lower():
                print(f"   ✅ PASS - {output}")
            else:
                print(f"   ❌ FAIL - {output[:200]}")

            print()

            print("6. Testing delete_document...")
            result = await call_tool("delete_document", {"path": test_path})
            output = result[0].text if result else "No output"
            if "deleted" in output.lower():
                print(f"   ✅ PASS - {output}")
            else:
                print(f"   ❌ FAIL - {output[:200]}")

            print("\n==========================")
            print("Tool tests completed!")

        asyncio.run(test_tools())
    else:
        asyncio.run(main())
