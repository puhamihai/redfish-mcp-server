"""Firmware inventory (1 tool).

Surfaces all firmware versions reported by the BMC: BIOS, BMC firmware,
NIC firmware (e.g. Intel I350 `igb`, Broadcom BCM5720 `tg3`), PSUs, RAID
controllers, and physical drives.
"""

from __future__ import annotations

from typing import Optional

from .app import client_for, err, mcp, render


@mcp.tool()
def get_firmware_inventory(server_id: Optional[str] = None) -> str:
    """List every firmware component on the server.

    Pulls /redfish/v1/UpdateService/FirmwareInventory and returns Name,
    Version, Manufacturer, ReleaseDate, Updateable, Health, State for each
    component (BIOS, BMC, NICs incl. Intel I350 / Broadcom BCM5720, RAID
    controller, disks, PSUs, lifecycle controller, etc).

    Args:
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        inventory_path = "/redfish/v1/UpdateService/FirmwareInventory"
        try:
            us = c.get("/redfish/v1/UpdateService")
            link = us.get("FirmwareInventory") if isinstance(us, dict) else None
            if isinstance(link, dict) and link.get("@odata.id"):
                inventory_path = link["@odata.id"]
        except Exception:
            pass

        data = c.get(inventory_path)
        members = data.get("Members") or []
        if not members:
            return "No firmware inventory entries found."
        items = c.expand_members(members)
        summary = []
        for item in items:
            st = item.get("Status") or {}
            summary.append(
                {
                    "Id": item.get("Id"),
                    "Name": item.get("Name"),
                    "Description": item.get("Description"),
                    "Version": item.get("Version"),
                    "Manufacturer": item.get("Manufacturer"),
                    "SoftwareId": item.get("SoftwareId"),
                    "ReleaseDate": item.get("ReleaseDate"),
                    "Updateable": item.get("Updateable"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                }
            )
        summary.sort(key=lambda s: (s.get("Name") or "").lower())
        return render(
            {
                "TotalComponents": len(summary),
                "UpdateableComponents": sum(1 for s in summary if s.get("Updateable")),
                "FirmwareInventory": summary,
            }
        )
    except Exception as e:
        return err("get_firmware_inventory", e, server_id)
