"""Computer system tools (4 tools)."""

from __future__ import annotations

from typing import Literal, Optional

from .app import client_for, err, mcp, render

ResetType = Literal[
    "On",
    "ForceOff",
    "GracefulShutdown",
    "GracefulRestart",
    "ForceRestart",
    "Nmi",
    "PushPowerButton",
]


@mcp.tool()
def list_systems(server_id: Optional[str] = None) -> str:
    """List ComputerSystem objects on a BMC.

    Returns Id, Name, Model, Manufacturer, SerialNumber, PowerState, Health,
    State, MemoryGiB, ProcessorCount, ProcessorModel for each system.

    Args:
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        systems = c.get_collection("/redfish/v1/Systems")
        out = []
        for s in systems:
            mem = s.get("MemorySummary") or {}
            cpu = s.get("ProcessorSummary") or {}
            st = s.get("Status") or {}
            out.append(
                {
                    "Id": s.get("Id"),
                    "Name": s.get("Name"),
                    "Model": s.get("Model"),
                    "Manufacturer": s.get("Manufacturer"),
                    "SerialNumber": s.get("SerialNumber"),
                    "PowerState": s.get("PowerState"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                    "MemoryGiB": mem.get("TotalSystemMemoryGiB"),
                    "MemoryHealth": (mem.get("Status") or {}).get("Health"),
                    "ProcessorCount": cpu.get("Count"),
                    "ProcessorModel": cpu.get("Model"),
                    "ProcessorHealth": (cpu.get("Status") or {}).get("Health"),
                }
            )
        return render(out)
    except Exception as e:
        return err("list_systems", e, server_id)


@mcp.tool()
def get_system(system_id: str, server_id: Optional[str] = None) -> str:
    """Get full details of a ComputerSystem by ID.

    Includes BiosVersion, HostName, IndicatorLED, Boot settings, and all
    hardware-summary fields.

    Args:
        system_id: System ID (e.g. '1', 'System.Embedded.1'). Use list_systems.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        return render(c.get(f"/redfish/v1/Systems/{system_id}"))
    except Exception as e:
        return err(f"get_system({system_id})", e, server_id)


@mcp.tool()
def set_power_state(
    system_id: str,
    reset_type: ResetType,
    server_id: Optional[str] = None,
) -> str:
    """Send a power-state action to a ComputerSystem.

    Args:
        system_id: System ID (e.g. '1', 'System.Embedded.1'). Use list_systems.
        reset_type: One of On, ForceOff, GracefulShutdown, GracefulRestart,
            ForceRestart, Nmi, PushPowerButton.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        result = c.post(
            f"/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
            {"ResetType": reset_type},
        )
        return f"Power action '{reset_type}' sent to system {system_id}.\n" + render(
            result
        )
    except Exception as e:
        return err(f"set_power_state({system_id}, {reset_type})", e, server_id)


@mcp.tool()
def get_bios_settings(system_id: str, server_id: Optional[str] = None) -> str:
    """Get current BIOS attributes for a system.

    Args:
        system_id: System ID (e.g. '1', 'System.Embedded.1'). Use list_systems.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        return render(c.get(f"/redfish/v1/Systems/{system_id}/Bios"))
    except Exception as e:
        return err(f"get_bios_settings({system_id})", e, server_id)
