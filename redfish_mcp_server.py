"""Entry point for the Redfish MCP server (stdio transport)."""

from src.redfish_mcp_server.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
