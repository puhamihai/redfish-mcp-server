"""BMC manager tools (4 tools)."""

from __future__ import annotations

from typing import Literal, Optional

from .app import client_for, err, mcp, render

ManagerResetType = Literal["GracefulRestart", "ForceRestart"]


@mcp.tool()
def list_managers(server_id: Optional[str] = None) -> str:
    """List BMC managers (the iDRAC/iLO/etc itself).

    Returns Id, Name, ManagerType, Description, FirmwareVersion, Model, Health,
    State, PowerState, DateTime, DateTimeLocalOffset.

    Args:
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        managers = c.get_collection("/redfish/v1/Managers")
        out = []
        for m in managers:
            st = m.get("Status") or {}
            out.append(
                {
                    "Id": m.get("Id"),
                    "Name": m.get("Name"),
                    "ManagerType": m.get("ManagerType"),
                    "Description": m.get("Description"),
                    "FirmwareVersion": m.get("FirmwareVersion"),
                    "Model": m.get("Model"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                    "PowerState": m.get("PowerState"),
                    "DateTime": m.get("DateTime"),
                    "DateTimeLocalOffset": m.get("DateTimeLocalOffset"),
                }
            )
        return render(out)
    except Exception as e:
        return err("list_managers", e, server_id)


@mcp.tool()
def get_manager(manager_id: str, server_id: Optional[str] = None) -> str:
    """Get full details of a BMC manager by ID.

    Args:
        manager_id: Manager ID (e.g. 'iDRAC.Embedded.1', 'BMC', '1').
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        return render(c.get(f"/redfish/v1/Managers/{manager_id}"))
    except Exception as e:
        return err(f"get_manager({manager_id})", e, server_id)


@mcp.tool()
def reset_manager(
    manager_id: str,
    reset_type: ManagerResetType = "GracefulRestart",
    server_id: Optional[str] = None,
) -> str:
    """Restart the BMC. The BMC will be temporarily unreachable.

    Args:
        manager_id: Manager ID. Use list_managers to find IDs.
        reset_type: 'GracefulRestart' (default) or 'ForceRestart'.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        result = c.post(
            f"/redfish/v1/Managers/{manager_id}/Actions/Manager.Reset",
            {"ResetType": reset_type},
        )
        return f"BMC reset ({reset_type}) initiated for manager {manager_id}.\n" + render(
            result
        )
    except Exception as e:
        return err(f"reset_manager({manager_id}, {reset_type})", e, server_id)


@mcp.tool()
def get_network_protocol(
    manager_id: str, server_id: Optional[str] = None
) -> str:
    """Get BMC network protocol settings (HTTP/HTTPS/SSH/IPMI/SNMP/Telnet).

    Returns enabled/disabled flag and port for each protocol.

    Args:
        manager_id: Manager ID. Use list_managers to find IDs.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        data = c.get(f"/redfish/v1/Managers/{manager_id}/NetworkProtocol")
        st = data.get("Status") or {}
        return render(
            {
                "HostName": data.get("HostName"),
                "FQDN": data.get("FQDN"),
                "Health": st.get("Health"),
                "State": st.get("State"),
                "Protocols": {
                    "HTTP": data.get("HTTP"),
                    "HTTPS": data.get("HTTPS"),
                    "SSH": data.get("SSH"),
                    "IPMI": data.get("IPMI"),
                    "SNMP": data.get("SNMP"),
                    "Telnet": data.get("Telnet"),
                    "SSDP": data.get("SSDP"),
                    "VirtualMedia": data.get("VirtualMedia"),
                },
            }
        )
    except Exception as e:
        return err(f"get_network_protocol({manager_id})", e, server_id)
