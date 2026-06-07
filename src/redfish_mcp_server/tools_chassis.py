"""Chassis, thermal, power tools (4 tools)."""

from __future__ import annotations

from typing import Optional

from .app import client_for, err, mcp, render


@mcp.tool()
def list_chassis(server_id: Optional[str] = None) -> str:
    """List all Chassis objects on a BMC.

    Returns Id, Name, ChassisType, Manufacturer, Model, SerialNumber,
    PartNumber, Health, State, IndicatorLED, PowerState.

    Args:
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        items = c.get_collection("/redfish/v1/Chassis")
        out = []
        for ch in items:
            st = ch.get("Status") or {}
            out.append(
                {
                    "Id": ch.get("Id"),
                    "Name": ch.get("Name"),
                    "ChassisType": ch.get("ChassisType"),
                    "Manufacturer": ch.get("Manufacturer"),
                    "Model": ch.get("Model"),
                    "SerialNumber": ch.get("SerialNumber"),
                    "PartNumber": ch.get("PartNumber"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                    "IndicatorLED": ch.get("IndicatorLED"),
                    "PowerState": ch.get("PowerState"),
                }
            )
        return render(out)
    except Exception as e:
        return err("list_chassis", e, server_id)


@mcp.tool()
def get_chassis(chassis_id: str, server_id: Optional[str] = None) -> str:
    """Get full details of a Chassis by ID.

    Args:
        chassis_id: Chassis ID (e.g. 'System.Embedded.1', 'Chassis.1').
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        return render(c.get(f"/redfish/v1/Chassis/{chassis_id}"))
    except Exception as e:
        return err(f"get_chassis({chassis_id})", e, server_id)


@mcp.tool()
def get_thermal(chassis_id: str, server_id: Optional[str] = None) -> str:
    """Get temperature sensors and fans for a chassis.

    Returns each Temperature sensor (Name, ReadingCelsius, thresholds, health)
    and each Fan (Name, Reading, ReadingUnits, thresholds, health).

    Args:
        chassis_id: Chassis ID. Use list_chassis to find IDs.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        data = c.get(f"/redfish/v1/Chassis/{chassis_id}/Thermal")
        temps = []
        for t in (data.get("Temperatures") or []):
            st = t.get("Status") or {}
            temps.append(
                {
                    "Name": t.get("Name"),
                    "SensorNumber": t.get("SensorNumber"),
                    "ReadingCelsius": t.get("ReadingCelsius"),
                    "UpperThresholdNonCritical": t.get("UpperThresholdNonCritical"),
                    "UpperThresholdCritical": t.get("UpperThresholdCritical"),
                    "UpperThresholdFatal": t.get("UpperThresholdFatal"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                }
            )
        fans = []
        for f in (data.get("Fans") or []):
            st = f.get("Status") or {}
            fans.append(
                {
                    "Name": f.get("Name") or f.get("FanName"),
                    "Reading": f.get("Reading"),
                    "ReadingUnits": f.get("ReadingUnits"),
                    "UpperThresholdNonCritical": f.get("UpperThresholdNonCritical"),
                    "UpperThresholdCritical": f.get("UpperThresholdCritical"),
                    "LowerThresholdNonCritical": f.get("LowerThresholdNonCritical"),
                    "LowerThresholdCritical": f.get("LowerThresholdCritical"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                }
            )
        return render({"Temperatures": temps, "Fans": fans})
    except Exception as e:
        return err(f"get_thermal({chassis_id})", e, server_id)


@mcp.tool()
def get_power(chassis_id: str, server_id: Optional[str] = None) -> str:
    """Get power supplies and consumption for a chassis.

    Returns PowerControl (consumption metrics) and PowerSupplies
    (model, capacity, health, firmware).

    Args:
        chassis_id: Chassis ID. Use list_chassis to find IDs.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        data = c.get(f"/redfish/v1/Chassis/{chassis_id}/Power")
        supplies = []
        for ps in (data.get("PowerSupplies") or []):
            st = ps.get("Status") or {}
            supplies.append(
                {
                    "Name": ps.get("Name"),
                    "PowerSupplyType": ps.get("PowerSupplyType"),
                    "LineInputVoltage": ps.get("LineInputVoltage"),
                    "PowerCapacityWatts": ps.get("PowerCapacityWatts"),
                    "LastPowerOutputWatts": ps.get("LastPowerOutputWatts"),
                    "Model": ps.get("Model"),
                    "Manufacturer": ps.get("Manufacturer"),
                    "SerialNumber": ps.get("SerialNumber"),
                    "FirmwareVersion": ps.get("FirmwareVersion"),
                    "Health": st.get("Health"),
                    "State": st.get("State"),
                }
            )
        controls = []
        for pc in (data.get("PowerControl") or []):
            controls.append(
                {
                    "Name": pc.get("Name"),
                    "PowerConsumedWatts": pc.get("PowerConsumedWatts"),
                    "PowerRequestedWatts": pc.get("PowerRequestedWatts"),
                    "PowerAvailableWatts": pc.get("PowerAvailableWatts"),
                    "PowerCapacityWatts": pc.get("PowerCapacityWatts"),
                    "PowerAllocatedWatts": pc.get("PowerAllocatedWatts"),
                    "PowerMetrics": pc.get("PowerMetrics"),
                }
            )
        return render({"PowerControl": controls, "PowerSupplies": supplies})
    except Exception as e:
        return err(f"get_power({chassis_id})", e, server_id)
