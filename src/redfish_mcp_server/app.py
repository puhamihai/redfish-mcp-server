"""Shared FastMCP instance and helpers used by all tool modules."""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .pool import get_pool
from .redfish_client import RedfishClient, RedfishError

mcp = FastMCP("Redfish MCP Server")


def client_for(server_id: Optional[str]) -> RedfishClient:
    """Resolve a server_id to a cached RedfishClient (lazy auth)."""
    return get_pool().get(server_id)


def render(data: Any) -> str:
    """Stable JSON dump used as tool return payload."""
    return json.dumps(data, indent=2, default=str, sort_keys=False)


def err(operation: str, e: Exception, server_id: Optional[str] = None) -> str:
    target = f" on {server_id}" if server_id else ""
    if isinstance(e, RedfishError):
        return f"{operation} failed{target}: {e}"
    return f"{operation} failed{target}: {type(e).__name__}: {e}"


def status_health(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        st = obj.get("Status")
        if isinstance(st, dict):
            return st.get("Health")
    return None


def status_state(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        st = obj.get("Status")
        if isinstance(st, dict):
            return st.get("State")
    return None
