"""
MCP Server wrapper for Agent Data
Allows Claude and other AI to connect via MCP protocol
"""

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent Data MCP Server",
    description="MCP Server wrapper for Agent Data Knowledge Base",
    version="1.0.0",
)

# CORS for browser-based MCP clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Hybrid config: local priority, cloud fallback ---
AGENT_DATA_URL = os.getenv("AGENT_DATA_URL", "http://localhost:8000")
AGENT_DATA_URL_CLOUD = os.getenv("AGENT_DATA_URL_CLOUD", "")
AGENT_DATA_API_KEY_LOCAL = os.getenv("AGENT_DATA_API_KEY_LOCAL", os.getenv("AGENT_DATA_API_KEY", ""))
AGENT_DATA_API_KEY_CLOUD = os.getenv("AGENT_DATA_API_KEY_CLOUD", "")
AGENT_DATA_PREFER = os.getenv("AGENT_DATA_PREFER", "local")

# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Search the knowledge base using semantic/RAG query. Returns relevant documents and context from the vector database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language (Vietnamese or English)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List available documents in the knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional path prefix to filter (e.g., 'docs/')",
                    "default": "",
                }
            },
        },
    },
    {
        "name": "get_document",
        "description": "Get full content of a specific document by its ID or path",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "The document ID or path",
                }
            },
            "required": ["document_id"],
        },
    },
    # --- Write tools ---
    {
        "name": "upload_document",
        "description": "Upload/create a new document in the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document path, e.g. 'docs/operations/sessions/web-50-report.md'"},
                "content": {"type": "string", "description": "Document content (markdown or plain text)"},
                "title": {"type": "string", "description": "Optional document title"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "update_document",
        "description": "Update an existing document's content and/or metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document path to update"},
                "content": {"type": "string", "description": "New document content"},
                "title": {"type": "string", "description": "Optional new title"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional new tags"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "delete_document",
        "description": "Delete a document from the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document path to delete"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_document",
        "description": "Move a document to a new parent. Use 'root' for top level.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Current document path"},
                "new_path": {"type": "string", "description": "New parent path, or 'root' for top level"},
            },
            "required": ["path", "new_path"],
        },
    },
    {
        "name": "ingest_document",
        "description": "Ingest a document from GCS URI or URL into the knowledge base for vector processing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "GCS URI (gs://bucket/path) or URL to ingest"},
            },
            "required": ["source"],
        },
    },
]


# Tool implementations
async def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
    """Execute RAG search via Agent Data /chat endpoint (hybrid)"""
    try:
        response = await _hybrid_request("POST", "/chat", json={"message": query})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"search_knowledge error: {e}")
        return {"error": str(e), "query": query}


async def list_documents(path: str = "") -> dict[str, Any]:
    """List documents from Firestore KB (hybrid)"""
    try:
        response = await _hybrid_request(
            "GET", "/kb/list", params={"prefix": path} if path else {},
        )
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError:
        pass

    return {"items": [], "error": "Failed to list documents"}


async def get_document(document_id: str) -> dict[str, Any]:
    """Get document content from Firestore KB (hybrid)"""
    try:
        response = await _hybrid_request("GET", f"/kb/get/{document_id}")
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError:
        pass

    # Fallback: try GitHub docs
    doc_path = document_id if document_id.startswith("docs/") else f"docs/{document_id}"
    try:
        response = await _hybrid_request("GET", "/api/docs/file", params={"path": doc_path})
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError:
        pass

    return {"error": f"Document '{document_id}' not found"}


def _auth_headers(url: str | None = None) -> dict[str, str]:
    """Build auth headers for write operations."""
    target = url or AGENT_DATA_URL
    if target == AGENT_DATA_URL_CLOUD and AGENT_DATA_API_KEY_CLOUD:
        return {"X-API-Key": AGENT_DATA_API_KEY_CLOUD}
    if AGENT_DATA_API_KEY_LOCAL:
        return {"X-API-Key": AGENT_DATA_API_KEY_LOCAL}
    return {}


async def _hybrid_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Try local URL first, fallback to cloud on connection error."""
    async with httpx.AsyncClient() as client:
        for url in [AGENT_DATA_URL, AGENT_DATA_URL_CLOUD]:
            if not url:
                continue
            try:
                headers = {**_auth_headers(url), **kwargs.pop("headers", {})}
                resp = await client.request(
                    method, f"{url}{path}",
                    headers=headers,
                    timeout=kwargs.pop("timeout", 30.0),
                    **kwargs,
                )
                label = "LOCAL" if url == AGENT_DATA_URL else "CLOUD"
                logger.info("Using %s endpoint: %s", label, url)
                return resp
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                label = "LOCAL" if url == AGENT_DATA_URL else "CLOUD"
                logger.warning("%s unavailable (%s), trying fallback...", label, e)
                continue
    raise httpx.ConnectError("Both LOCAL and CLOUD endpoints unavailable")


async def upload_document(path: str, content: str, title: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    """Create a new document via POST /documents (hybrid)"""
    parent_id = "/".join(path.split("/")[:-1]) if "/" in path else ""
    if not title:
        title = path.rsplit("/", 1)[-1] if "/" in path else path

    body: dict[str, Any] = {
        "document_id": path,
        "parent_id": parent_id,
        "content": {"mime_type": "text/markdown", "body": content},
        "metadata": {"title": title},
    }
    if tags:
        body["metadata"]["tags"] = tags

    try:
        response = await _hybrid_request("POST", "/documents", json=body)
        if response.status_code in (200, 201):
            return response.json()
        return {"error": f"HTTP {response.status_code}", "detail": response.text}
    except httpx.HTTPError as e:
        logger.error(f"upload_document error: {e}")
        return {"error": str(e)}


async def update_document(path: str, content: str, title: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    """Update a document via PUT /documents/{id} (hybrid)"""
    patch: dict[str, Any] = {"content": {"mime_type": "text/markdown", "body": content}}
    update_mask = ["content"]
    metadata: dict[str, Any] = {}
    if title:
        metadata["title"] = title
    if tags:
        metadata["tags"] = tags
    if metadata:
        patch["metadata"] = metadata
        update_mask.append("metadata")

    body = {"document_id": path, "patch": patch, "update_mask": update_mask}

    try:
        response = await _hybrid_request("PUT", f"/documents/{path}", json=body)
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}", "detail": response.text}
    except httpx.HTTPError as e:
        logger.error(f"update_document error: {e}")
        return {"error": str(e)}


async def delete_document(path: str) -> dict[str, Any]:
    """Delete a document via DELETE /documents/{id} (hybrid)"""
    try:
        response = await _hybrid_request("DELETE", f"/documents/{path}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}", "detail": response.text}
    except httpx.HTTPError as e:
        logger.error(f"delete_document error: {e}")
        return {"error": str(e)}


async def move_document(path: str, new_path: str) -> dict[str, Any]:
    """Move a document via POST /documents/{id}/move (hybrid)"""
    try:
        response = await _hybrid_request(
            "POST", f"/documents/{path}/move", json={"new_parent_id": new_path},
        )
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}", "detail": response.text}
    except httpx.HTTPError as e:
        logger.error(f"move_document error: {e}")
        return {"error": str(e)}


async def ingest_document(source: str) -> dict[str, Any]:
    """Ingest a document via POST /ingest (hybrid)"""
    try:
        response = await _hybrid_request("POST", "/ingest", json={"text": source})
        if response.status_code in (200, 202):
            return response.json()
        return {"error": f"HTTP {response.status_code}", "detail": response.text}
    except httpx.HTTPError as e:
        logger.error(f"ingest_document error: {e}")
        return {"error": str(e)}


# MCP Protocol Handlers
@app.get("/mcp")
async def mcp_info():
    """MCP Server info endpoint - returns server capabilities and tools"""
    return {
        "name": "agent-data-mcp",
        "version": "1.0.0",
        "description": "MCP Server for Agent Data Knowledge Base",
        "protocol_version": "2024-11-05",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False,
        },
        "tools": MCP_TOOLS,
    }


@app.post("/mcp/tools/{tool_name}")
async def execute_tool(tool_name: str, request: Request):
    """Execute an MCP tool by name"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    logger.info(f"Executing tool: {tool_name} with params: {body}")

    if tool_name == "search_knowledge":
        result = await search_knowledge(
            query=body.get("query", ""),
            limit=body.get("limit", 5),
        )
    elif tool_name == "list_documents":
        result = await list_documents(path=body.get("path", ""))
    elif tool_name == "get_document":
        result = await get_document(document_id=body.get("document_id", ""))
    elif tool_name == "upload_document":
        result = await upload_document(
            path=body.get("path", ""),
            content=body.get("content", ""),
            title=body.get("title", ""),
            tags=body.get("tags"),
        )
    elif tool_name == "update_document":
        result = await update_document(
            path=body.get("path", ""),
            content=body.get("content", ""),
            title=body.get("title", ""),
            tags=body.get("tags"),
        )
    elif tool_name == "delete_document":
        result = await delete_document(path=body.get("path", ""))
    elif tool_name == "move_document":
        result = await move_document(
            path=body.get("path", ""),
            new_path=body.get("new_path", ""),
        )
    elif tool_name == "ingest_document":
        result = await ingest_document(source=body.get("source", ""))
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown tool: {tool_name}", "available_tools": [t["name"] for t in MCP_TOOLS]},
        )

    return {"result": result}


@app.get("/mcp/sse")
async def mcp_sse(request: Request):
    """SSE endpoint for MCP streaming protocol (used by Claude Desktop)"""

    async def event_generator():
        # Send initial connection event with server info
        yield {
            "event": "open",
            "data": json.dumps(
                {
                    "status": "connected",
                    "server": "agent-data-mcp",
                    "version": "1.0.0",
                    "tools": [t["name"] for t in MCP_TOOLS],
                }
            ),
        }

        # Keep connection alive with periodic pings
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
            yield {"event": "ping", "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})}
            await asyncio.sleep(30)

    return EventSourceResponse(event_generator())


@app.get("/health")
async def health():
    """Health check - verifies Agent Data connectivity (hybrid)"""
    local_status = "unknown"
    cloud_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{AGENT_DATA_URL}/info")
            local_status = "connected" if resp.status_code == 200 else f"error:{resp.status_code}"
    except Exception as e:
        local_status = f"unavailable:{type(e).__name__}"
    if AGENT_DATA_URL_CLOUD:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{AGENT_DATA_URL_CLOUD}/info")
                cloud_status = "connected" if resp.status_code == 200 else f"error:{resp.status_code}"
        except Exception as e:
            cloud_status = f"unavailable:{type(e).__name__}"
    else:
        cloud_status = "not_configured"

    return {
        "status": "ok",
        "mode": "hybrid",
        "prefer": AGENT_DATA_PREFER,
        "local": {"url": AGENT_DATA_URL, "status": local_status},
        "cloud": {"url": AGENT_DATA_URL_CLOUD, "status": cloud_status},
    }


@app.get("/")
async def root():
    """Root endpoint with quick reference"""
    return {
        "service": "Agent Data MCP Server",
        "endpoints": {
            "/mcp": "MCP server info and tools list",
            "/mcp/tools/{tool_name}": "Execute a tool (POST)",
            "/mcp/sse": "SSE stream for MCP protocol",
            "/health": "Health check",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
