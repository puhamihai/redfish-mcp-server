"""Storage controllers and drives (2 tools)."""

from __future__ import annotations

from typing import Optional

from .app import client_for, err, mcp, render


def _format_bytes(n: Optional[int]) -> Optional[str]:
    if n is None:
        return None
    gb = n / 1_000_000_000
    if gb >= 1000:
        return f"{gb / 1000:.2f} TB"
    return f"{gb:.2f} GB"


@mcp.tool()
def list_storage(system_id: str, server_id: Optional[str] = None) -> str:
    """List storage controllers under a ComputerSystem.

    Returns Id, Name, Description, Health, HealthRollup, StorageControllers
    (model, firmware, RAID types, health), DriveCount, and DriveLinks.

    Args:
        system_id: System ID. Use list_systems to find IDs.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        coll = c.get(f"/redfish/v1/Systems/{system_id}/Storage")
        out = []
        for m in coll.get("Members") or []:
            sd = c.get(m["@odata.id"])
            st = sd.get("Status") or {}
            controllers = []
            for sc in sd.get("StorageControllers") or []:
                csts = sc.get("Status") or {}
                controllers.append(
                    {
                        "MemberId": sc.get("MemberId"),
                        "Name": sc.get("Name"),
                        "Manufacturer": sc.get("Manufacturer"),
                        "Model": sc.get("Model"),
                        "FirmwareVersion": sc.get("FirmwareVersion"),
                        "SerialNumber": sc.get("SerialNumber"),
                        "SpeedGbps": sc.get("SpeedGbps"),
                        "Health": csts.get("Health"),
                        "HealthRollup": csts.get("HealthRollup"),
                        "State": csts.get("State"),
                        "SupportedRAIDTypes": sc.get("SupportedRAIDTypes"),
                        "SupportedDeviceProtocols": sc.get("SupportedDeviceProtocols"),
                    }
                )
            drive_links = sd.get("Drives") or []
            out.append(
                {
                    "Id": sd.get("Id"),
                    "Name": sd.get("Name"),
                    "Description": sd.get("Description"),
                    "Health": st.get("Health"),
                    "HealthRollup": st.get("HealthRollup"),
                    "StorageControllers": controllers,
                    "DriveCount": len(drive_links),
                    "DriveLinks": [d.get("@odata.id") for d in drive_links],
                }
            )
        return render(out)
    except Exception as e:
        return err(f"list_storage({system_id})", e, server_id)


@mcp.tool()
def list_drives(
    system_id: str, storage_id: str, server_id: Optional[str] = None
) -> str:
    """List physical drives behind a storage controller.

    Returns Id, Name, Manufacturer, Model, SerialNumber, Capacity (bytes +
    formatted), Protocol (SAS/SATA/NVMe), MediaType (SSD/HDD), RPM, Speed,
    BlockSize, FailurePredicted, Hotspare/encryption flags, Health, State.

    Args:
        system_id: System ID. Use list_systems.
        storage_id: Storage controller ID (e.g. 'RAID.Integrated.1-1').
                    Use list_storage to find IDs.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        sd = c.get(f"/redfish/v1/Systems/{system_id}/Storage/{storage_id}")
        drive_links = sd.get("Drives") or []
        if not drive_links:
            return f"No drives found for storage controller '{storage_id}'."
        drives = c.expand_members(drive_links)
        out = []
        for d in drives:
            st = d.get("Status") or {}
            cap = d.get("CapacityBytes")
            out.append(
                {
                    "Id": d.get("Id"),
                    "Name": d.get("Name"),
                    "Manufacturer": d.get("Manufacturer"),
                    "Model": d.get("Model"),
                    "SerialNumber": d.get("SerialNumber"),
                    "CapacityBytes": cap,
                    "Capacity": _format_bytes(cap),
                    "Protocol": d.get("Protocol"),
                    "MediaType": d.get("MediaType"),
                    "RotationSpeedRPM": d.get("RotationSpeedRPM"),
                    "CapableSpeedGbs": d.get("CapableSpeedGbs"),
                    "NegotiatedSpeedGbs": d.get("NegotiatedSpeedGbs"),
                    "BlockSizeBytes": d.get("BlockSizeBytes"),
                    "FailurePredicted": d.get("FailurePredicted"),
                    "HotspareType": d.get("HotspareType"),
                    "EncryptionAbility": d.get("EncryptionAbility"),
                    "EncryptionStatus": d.get("EncryptionStatus"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                }
            )
        return render(out)
    except Exception as e:
        return err(f"list_drives({system_id}, {storage_id})", e, server_id)
