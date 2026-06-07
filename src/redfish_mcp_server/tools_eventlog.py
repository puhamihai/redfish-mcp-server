"""Event/SEL log read and clear (2 tools)."""

from __future__ import annotations

from typing import Literal, Optional

from .app import client_for, err, mcp, render
from .redfish_client import RedfishClient

ResourceType = Literal["Systems", "Managers"]
SeverityFilter = Literal["Critical", "Warning", "OK"]

# Common log IDs in priority order. iDRAC uses "Sel" / "Lclog" (Lifecycle Log);
# generic Redfish uses "Log1" / "System".
_PREFERRED_LOG_NAMES = ["Sel", "SEL", "Lclog", "LCLog", "System", "Log1", "BIOS", "Fault"]


def _discover_log(
    c: RedfishClient,
    resource_type: str,
    resource_id: str,
    preferred: Optional[str],
) -> Optional[tuple[str, str]]:
    base = f"/redfish/v1/{resource_type}/{resource_id}/LogServices"
    try:
        data = c.get(base)
    except Exception:
        return None
    members = data.get("Members") or []
    if not members:
        return None
    if preferred:
        for m in members:
            if preferred.lower() in m["@odata.id"].lower():
                return base, m["@odata.id"].rstrip("/").split("/")[-1]
    for name in _PREFERRED_LOG_NAMES:
        for m in members:
            if name.lower() in m["@odata.id"].lower():
                return base, m["@odata.id"].rstrip("/").split("/")[-1]
    return base, members[0]["@odata.id"].rstrip("/").split("/")[-1]


@mcp.tool()
def list_event_log(
    resource_type: ResourceType,
    resource_id: str,
    log_id: Optional[str] = None,
    max_entries: int = 50,
    severity_filter: Optional[SeverityFilter] = None,
    server_id: Optional[str] = None,
) -> str:
    """Read entries from a log service. Newest entries first.

    Args:
        resource_type: 'Systems' for system event log, 'Managers' for BMC/SEL.
        resource_id: Resource ID (e.g. '1', 'iDRAC.Embedded.1').
        log_id: Specific log id (e.g. 'Sel', 'Lclog', 'Log1'). Auto-discovered if omitted.
        max_entries: Max entries to return (default 50).
        severity_filter: Restrict to 'Critical', 'Warning', or 'OK'.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        discovered = _discover_log(c, resource_type, resource_id, log_id)
        if discovered is None:
            return (
                f"No log services found for {resource_type}/{resource_id}."
            )
        base, lid = discovered
        # Resolve entries link from the LogService — Dell iDRAC8/2.75 puts
        # entries at /Managers/.../Logs/<id>, not /LogServices/<id>/Entries.
        log_service = c.get(f"{base}/{lid}")
        entries_link = (log_service.get("Entries") or {}).get("@odata.id") if isinstance(log_service, dict) else None
        entries_path = entries_link or f"{base}/{lid}/Entries"
        data = c.get(entries_path)
        members = list(data.get("Members") or []) if isinstance(data, dict) else []
        total = data.get("Members@odata.count", len(members)) if isinstance(data, dict) else len(members)
        # Force newest-first by Id (iDRAC IDs are monotonically increasing).
        # Vendor BMCs disagree on default sort order; sorting here is robust.
        def _sort_key(e):
            try:
                return int(e.get("Id") or 0)
            except (ValueError, TypeError):
                return 0
        entries = sorted(members, key=_sort_key, reverse=True)

        if severity_filter:
            entries = [
                e
                for e in entries
                if (e.get("Severity") or "").lower() == severity_filter.lower()
            ]
        entries = entries[:max_entries]

        summary = [
            {
                "Id": e.get("Id"),
                "Severity": e.get("Severity"),
                "Message": e.get("Message"),
                "MessageId": e.get("MessageId"),
                "Created": e.get("Created"),
                "EntryType": e.get("EntryType"),
            }
            for e in entries
        ]
        return render(
            {
                "LogService": f"{base}/{lid}",
                "TotalEntries": total,
                "ReturnedEntries": len(summary),
                "Entries": summary,
            }
        )
    except Exception as e:
        return err(f"list_event_log({resource_type}/{resource_id})", e, server_id)


@mcp.tool()
def clear_event_log(
    resource_type: ResourceType,
    resource_id: str,
    log_id: Optional[str] = None,
    server_id: Optional[str] = None,
) -> str:
    """Clear a log service. Irreversible.

    Args:
        resource_type: 'Systems' or 'Managers'.
        resource_id: Resource ID.
        log_id: Specific log id. Auto-discovered if omitted.
        server_id: Server id from list_servers. If omitted, uses default.
    """
    try:
        c = client_for(server_id)
        discovered = _discover_log(c, resource_type, resource_id, log_id)
        if discovered is None:
            return f"No log services found for {resource_type}/{resource_id}."
        base, lid = discovered
        log_path = f"{base}/{lid}"
        svc = c.get(log_path)
        actions = svc.get("Actions") or {}
        clear = actions.get("#LogService.ClearLog") or {}
        target = clear.get("target")
        if not target:
            return f"Log service '{lid}' does not advertise a ClearLog action."
        result = c.post(target, {})
        return f"Event log '{lid}' cleared.\n" + render(result)
    except Exception as e:
        return err(
            f"clear_event_log({resource_type}/{resource_id})", e, server_id
        )
