#!/usr/bin/env python3
"""
MCP Server for Claude Desktop (stdio transport)
Provides search_knowledge, list_documents, get_document (read)
and upload_document, update_document, delete_document, move_document, ingest_document (write)
"""

import asyncio
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Agent Data backend URL
AGENT_DATA_URL = os.getenv("AGENT_DATA_URL", "http://localhost:8000")

# API key for write operations (from Secret Manager: agent-data-api-key)
AGENT_DATA_API_KEY = os.getenv("AGENT_DATA_API_KEY", "")


def _get_auth_headers() -> dict[str, str]:
    """Build auth headers. Includes IAM identity token for Cloud Run and API key for write ops."""
    headers: dict[str, str] = {}

    # Add API key for write operations
    if AGENT_DATA_API_KEY:
        headers["X-API-Key"] = AGENT_DATA_API_KEY

    # Add Google Cloud identity token if targeting Cloud Run (https://)
    if AGENT_DATA_URL.startswith("https://"):
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "auth", "print-identity-token"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                headers["Authorization"] = f"Bearer {result.stdout.strip()}"
        except Exception:
            pass  # Fall through without IAM token (may 403 on Cloud Run)

    return headers

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
            description="Upload/create a new document in the knowledge base. Use flat IDs (e.g. 'web-50-report') for full CRUD support, or path-style IDs (e.g. 'docs/reports/web-50') for create-only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document ID. Use flat ID like 'web-50-report' (recommended) or path like 'docs/reports/web-50-report.md'. Flat IDs support update/delete/move; path IDs only support create.",
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
            description="Update an existing document's content and/or metadata. Document must have a flat ID (no slashes).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document ID to update (flat ID, no slashes)",
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
            description="Delete a document from the knowledge base. Document must have a flat ID (no slashes).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Document ID to delete (flat ID, no slashes)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="move_document",
            description="Move a document to a new parent. Document must have a flat ID (no slashes). Use 'root' to move to top level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Current document ID (flat ID, no slashes)",
                    },
                    "new_path": {
                        "type": "string",
                        "description": "New parent document ID, or 'root' for top level",
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
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool and return results."""

    auth_headers = _get_auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "search_knowledge":
                query = arguments.get("query", "")
                response = await client.post(
                    f"{AGENT_DATA_URL}/chat",
                    json={"message": query},
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("response", data.get("content", "No response"))

                    # Add context if available
                    context = data.get("context", [])
                    if context:
                        sources = "\n\nSources:\n" + "\n".join(
                            f"- {c.get('document_id', 'unknown')}" for c in context[:3]
                        )
                        result += sources

                    return [TextContent(type="text", text=result)]
                else:
                    return [TextContent(type="text", text=f"Error: HTTP {response.status_code}")]

            elif name == "list_documents":
                path = arguments.get("path", "docs")
                # Use /api/docs/tree endpoint to list documents
                response = await client.get(
                    f"{AGENT_DATA_URL}/api/docs/tree",
                    params={"path": path},
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        result = f"Documents in '{path}':\n\n"
                        for item in items:
                            item_type = "📁" if item.get("type") == "dir" else "📄"
                            name = item.get("name", "unknown")
                            item_path = item.get("path", "")
                            result += f"{item_type} {name}\n   Path: {item_path}\n"
                        return [TextContent(type="text", text=result)]
                    else:
                        return [TextContent(type="text", text=f"No documents found in '{path}'")]

                return [TextContent(type="text", text=f"Error listing documents: HTTP {response.status_code}")]

            elif name == "get_document":
                doc_id = arguments.get("document_id", "")

                # Try /api/docs/file endpoint first (for GitHub docs)
                # Handle both full path and short name
                doc_path = doc_id if doc_id.startswith("docs/") else f"docs/{doc_id}"
                response = await client.get(
                    f"{AGENT_DATA_URL}/api/docs/file",
                    params={"path": doc_path},
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    if content:
                        return [TextContent(type="text", text=f"# Document: {doc_id}\n\n{content}")]

                # Fallback: search in Qdrant via chat
                response = await client.post(
                    f"{AGENT_DATA_URL}/chat",
                    json={"message": f"Get the full content of document: {doc_id}"},
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("response", "")
                    context = data.get("context", [])
                    if context:
                        # Include source info
                        sources = "\n\n---\nSource: " + ", ".join(
                            c.get("document_id", "unknown") for c in context[:3]
                        )
                        result += sources
                    return [TextContent(type="text", text=result)]

                return [TextContent(type="text", text=f"Document '{doc_id}' not found")]

            elif name == "upload_document":
                path = arguments.get("path", "")
                content = arguments.get("content", "")
                title = arguments.get("title", "")
                tags = arguments.get("tags", [])

                # Derive parent_id from path (e.g. "docs/test/file.md" → "docs/test")
                parent_id = "/".join(path.split("/")[:-1]) if "/" in path else ""

                body = {
                    "document_id": path,
                    "parent_id": parent_id,
                    "content": {"mime_type": "text/markdown", "body": content},
                    "metadata": {},
                }
                if title:
                    body["metadata"]["title"] = title
                if tags:
                    body["metadata"]["tags"] = tags

                response = await client.post(
                    f"{AGENT_DATA_URL}/documents",
                    json=body,
                    headers=auth_headers,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    return [TextContent(type="text", text=f"Document created: {data.get('id', path)} (revision {data.get('revision', 1)})")]
                else:
                    return [TextContent(type="text", text=f"Upload failed: HTTP {response.status_code} — {response.text}")]

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

                response = await client.put(
                    f"{AGENT_DATA_URL}/documents/{path}",
                    json=body,
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"Document updated: {data.get('id', path)} (revision {data.get('revision', '?')})")]
                else:
                    return [TextContent(type="text", text=f"Update failed: HTTP {response.status_code} — {response.text}")]

            elif name == "delete_document":
                path = arguments.get("path", "")

                response = await client.delete(
                    f"{AGENT_DATA_URL}/documents/{path}",
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"Document deleted: {data.get('id', path)}")]
                else:
                    return [TextContent(type="text", text=f"Delete failed: HTTP {response.status_code} — {response.text}")]

            elif name == "move_document":
                path = arguments.get("path", "")
                new_path = arguments.get("new_path", "")

                response = await client.post(
                    f"{AGENT_DATA_URL}/documents/{path}/move",
                    json={"new_parent_id": new_path},
                    headers=auth_headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"Document moved: {data.get('id', path)} → {new_path}")]
                else:
                    return [TextContent(type="text", text=f"Move failed: HTTP {response.status_code} — {response.text}")]

            elif name == "ingest_document":
                source = arguments.get("source", "")

                response = await client.post(
                    f"{AGENT_DATA_URL}/ingest",
                    json={"text": source},
                    headers=auth_headers,
                )
                if response.status_code in (200, 202):
                    data = response.json()
                    msg = data.get("response", data.get("content", "Ingestion accepted"))
                    return [TextContent(type="text", text=f"Ingest accepted: {msg}")]
                else:
                    return [TextContent(type="text", text=f"Ingest failed: HTTP {response.status_code} — {response.text}")]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.RequestError as e:
            return [TextContent(type="text", text=f"Connection error: {str(e)}. Is Agent Data running at {AGENT_DATA_URL}?")]
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
            print(f"MCP STDIO Server Test")
            print(f"=====================")
            print(f"Agent Data URL: {AGENT_DATA_URL}")
            print(f"Tools available: {len(tools)}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")

            # Test connection to Agent Data
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{AGENT_DATA_URL}/info")
                    if resp.status_code == 200:
                        print(f"Agent Data connection: OK")
                    else:
                        print(f"Agent Data connection: ERROR ({resp.status_code})")
            except Exception as e:
                print(f"Agent Data connection: FAILED ({e})")

            print("=====================")
            print("Test completed successfully!")

        asyncio.run(test())

    # Full tool test mode
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-tools":
        async def test_tools():
            print("MCP Tools Integration Test")
            print("==========================\n")

            # Test 1: list_documents
            print("1. Testing list_documents...")
            result = await call_tool("list_documents", {"path": "docs"})
            output = result[0].text if result else "No output"
            if "📁" in output or "📄" in output:
                print("   ✅ PASS - Returns document list")
                print(f"   Preview: {output[:200]}...")
            else:
                print(f"   ❌ FAIL - {output[:100]}")

            print()

            # Test 2: get_document
            print("2. Testing get_document...")
            result = await call_tool("get_document", {"document_id": "AGENCY_OS_E1_BLUEPRINT.md"})
            output = result[0].text if result else "No output"
            if len(output) > 500 and "AGENCY" in output:
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
            result = await call_tool("upload_document", {
                "path": test_path,
                "content": "# MCP Write Test\nAutomated test document.",
                "title": "MCP Write Test",
                "tags": ["test", "mcp"],
            })
            output = result[0].text if result else "No output"
            if "created" in output.lower() or "revision" in output.lower():
                print(f"   ✅ PASS - {output}")
            else:
                print(f"   ❌ FAIL - {output[:200]}")

            print()

            print("5. Testing update_document...")
            result = await call_tool("update_document", {
                "path": test_path,
                "content": "# MCP Write Test (Updated)\nThis content was updated.",
            })
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
