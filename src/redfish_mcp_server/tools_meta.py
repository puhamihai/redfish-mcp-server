"""Cross-cutting tools: server inventory + connection check."""

from __future__ import annotations

from typing import Optional

from .app import client_for, err, mcp, render
from .pool import get_pool


@mcp.tool()
def list_servers() -> str:
    """List all configured Redfish servers (BMCs/iDRACs) known to this MCP.

    Returns each server's id, host, username, label, port, and verify_ssl flag.
    No secrets are returned. Use the returned `id` field as the `server_id`
    argument for any other tool.
    """
    return render(get_pool().list_servers())


@mcp.tool()
def test_connection(server_id: Optional[str] = None) -> str:
    """Probe a Redfish endpoint and report version + product info.

    Args:
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        root = c.get("/redfish/v1")
        return render(
            {
                "server_id": server_id or get_pool().config.default_server,
                "host": c.server.host,
                "RedfishVersion": root.get("RedfishVersion") if isinstance(root, dict) else None,
                "Product": root.get("Product") if isinstance(root, dict) else None,
                "Vendor": root.get("Vendor") if isinstance(root, dict) else None,
                "Name": root.get("Name") if isinstance(root, dict) else None,
                "auth_mode": "session" if c._session_token else "basic",
            }
        )
    except Exception as e:
        return err("test_connection", e, server_id)
