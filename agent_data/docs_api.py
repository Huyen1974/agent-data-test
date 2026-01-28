"""
Docs API - Proxy GitHub content for documentation access.

Provides endpoints to browse and fetch documentation from GitHub repository.
"""

import base64
import logging
import os
from functools import lru_cache
from time import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docs", tags=["docs"])

# Configuration
GITHUB_REPO = os.getenv("GITHUB_DOCS_REPO", "Huyen1974/web-test")
GITHUB_API_BASE = "https://api.github.com"

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_github_token() -> str | None:
    """Get GitHub token from environment."""
    return os.getenv("GITHUB_TOKEN")


def _get_github_headers() -> dict[str, str]:
    """Build headers for GitHub API requests."""
    token = _get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "agent-data-docs-api",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _cache_get(key: str) -> Any | None:
    """Get value from cache if not expired."""
    if key in _cache:
        timestamp, value = _cache[key]
        if time() - timestamp < CACHE_TTL_SECONDS:
            return value
        del _cache[key]
    return None


def _cache_set(key: str, value: Any) -> None:
    """Set value in cache with current timestamp."""
    _cache[key] = (time(), value)


class TreeItem(BaseModel):
    """Single item in the docs tree."""

    name: str
    path: str
    type: str  # "file" or "dir"
    sha: str
    size: int | None = None


class TreeResponse(BaseModel):
    """Response for tree endpoint."""

    ref: str
    path: str
    items: list[TreeItem]


class FileResponse(BaseModel):
    """Response for file endpoint."""

    path: str
    ref: str
    sha: str
    content: str
    size: int | None = None


@router.get("/tree", response_model=TreeResponse)
async def get_docs_tree(
    ref: str = Query(default="main", description="Git ref (branch/tag/commit)"),
    path: str = Query(default="docs/", description="Path to directory"),
):
    """Get folder/file structure from GitHub.

    Returns a list of files and directories at the specified path.
    """
    # Normalize path
    path = path.strip("/")
    if not path:
        path = "docs"

    cache_key = f"tree:{ref}:{path}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{path}"
    params = {"ref": ref}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, headers=_get_github_headers(), params=params
            )
    except httpx.RequestError as exc:
        logger.error("GitHub API request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to connect to GitHub API")

    if response.status_code == 404:
        raise HTTPException(
            status_code=404, detail=f"Path not found: {path} (ref: {ref})"
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=403, detail="GitHub API rate limit exceeded or access denied"
        )
    if response.status_code != 200:
        logger.error("GitHub API error: %s %s", response.status_code, response.text)
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error: {response.status_code}",
        )

    data = response.json()

    # GitHub returns a single object for files, list for directories
    if isinstance(data, dict):
        # Single file requested, not a directory
        raise HTTPException(
            status_code=400,
            detail=f"Path is a file, not a directory: {path}. Use /api/docs/file endpoint.",
        )

    items = []
    for item in data:
        items.append(
            TreeItem(
                name=item["name"],
                path=item["path"],
                type=item["type"],
                sha=item["sha"],
                size=item.get("size"),
            )
        )

    # Sort: directories first, then files, alphabetically
    items.sort(key=lambda x: (0 if x.type == "dir" else 1, x.name.lower()))

    result = TreeResponse(ref=ref, path=path, items=items)
    _cache_set(cache_key, result)
    return result


@router.get("/file", response_model=FileResponse)
async def get_docs_file(
    path: str = Query(..., description="Path to file"),
    ref: str = Query(default="main", description="Git ref (branch/tag/commit)"),
):
    """Get file content from GitHub.

    Returns the decoded content of the specified file.
    """
    # Normalize path
    path = path.strip("/")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    cache_key = f"file:{ref}:{path}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{path}"
    params = {"ref": ref}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, headers=_get_github_headers(), params=params
            )
    except httpx.RequestError as exc:
        logger.error("GitHub API request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to connect to GitHub API")

    if response.status_code == 404:
        raise HTTPException(
            status_code=404, detail=f"File not found: {path} (ref: {ref})"
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=403, detail="GitHub API rate limit exceeded or access denied"
        )
    if response.status_code != 200:
        logger.error("GitHub API error: %s %s", response.status_code, response.text)
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error: {response.status_code}",
        )

    data = response.json()

    # Check if it's a file (not a directory)
    if isinstance(data, list):
        raise HTTPException(
            status_code=400,
            detail=f"Path is a directory, not a file: {path}. Use /api/docs/tree endpoint.",
        )

    if data.get("type") != "file":
        raise HTTPException(
            status_code=400, detail=f"Path is not a file: {path} (type: {data.get('type')})"
        )

    # Decode base64 content
    encoded_content = data.get("content", "")
    try:
        # GitHub returns content with newlines, need to handle that
        content = base64.b64decode(encoded_content).decode("utf-8")
    except Exception as exc:
        logger.error("Failed to decode file content: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to decode file content")

    result = FileResponse(
        path=path,
        ref=ref,
        sha=data["sha"],
        content=content,
        size=data.get("size"),
    )
    _cache_set(cache_key, result)
    return result
