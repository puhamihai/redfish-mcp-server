# Redfish MCP Server

A Model Context Protocol server for **multi-host BMC management** via the
DMTF Redfish API. One MCP instance talks to as many iDRAC / iLO / XCC /
Supermicro BMCs as you list in `config.json`; every tool takes an optional
`server_id` argument that names which one to address.

Built by combining the rich tool surface of
[fredriksknese/mcp-redfish](https://github.com/fredriksknese/mcp-redfish)
(firmware inventory, thermal, power, BIOS, drives, event logs, managers)
with the multi-host config shape of
[filthyrake/damens_mcps/idrac-mcp](https://github.com/filthyrake/damens_mcps/tree/main/idrac-mcp).

## Tools

19 tools across 7 families. Every non-meta tool accepts `server_id` (omit to
use `default_server`).

| Family | Tool | What it does |
|---|---|---|
| meta | `list_servers` | List configured BMCs (no secrets) |
| meta | `test_connection` | Probe `/redfish/v1`, report version/product/auth mode |
| systems | `list_systems` | Id, model, power state, memory, CPU summary, health |
| systems | `get_system` | Full ComputerSystem detail incl. BiosVersion, Boot, HostName |
| systems | `set_power_state` | On / ForceOff / GracefulShutdown / GracefulRestart / ForceRestart / Nmi / PushPowerButton |
| systems | `get_bios_settings` | Current BIOS attributes |
| chassis | `list_chassis` | Chassis type, manufacturer, serial, health |
| chassis | `get_chassis` | Full chassis detail |
| chassis | `get_thermal` | Temperatures + fans with thresholds and health |
| chassis | `get_power` | Power supplies + power consumption metrics |
| managers | `list_managers` | BMC type, firmware version, datetime, health |
| managers | `get_manager` | Full BMC detail |
| managers | `reset_manager` | GracefulRestart / ForceRestart the BMC |
| managers | `get_network_protocol` | HTTP/HTTPS/SSH/IPMI/SNMP/Telnet enabled + ports |
| storage | `list_storage` | Storage controllers (RAID/AHCI/NVMe), firmware, supported RAID types |
| storage | `list_drives` | Physical drives — capacity, protocol, MediaType, RPM, health |
| eventlog | `list_event_log` | Read SEL / Lifecycle / System log entries (auto-discovered, severity filter) |
| eventlog | `clear_event_log` | Clear a log service (irreversible) |
| firmware | `get_firmware_inventory` | All firmware versions on the box (BIOS, BMC, NICs, RAID, PSUs, drives, …) |

## Install

Requires Python 3.10+ (tested on 3.14).

```bash
git clone https://github.com/<your-org>/redfish-mcp-server.git
cd redfish-mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configure

Two modes:

### Multi-host (recommended) — `config.json`

Copy `config.example.json` to `config.json` and edit:

```json
{
  "servers": {
    "server1": {
      "host": "192.0.2.10",
      "username": "root",
      "password": "REPLACE_ME",
      "verify_ssl": false,
      "label": "Dell PowerEdge R630 — primary"
    },
    "server2": {
      "host": "192.0.2.11",
      "username": "root",
      "password": "REPLACE_ME",
      "verify_ssl": false,
      "label": "Dell PowerEdge R630 — secondary"
    }
  },
  "default_server": "server1"
}
```

The server looks for `config.json` at:
1. `$REDFISH_MCP_CONFIG` (if set, must exist)
2. `./config.json`
3. `~/.redfish-mcp-server/config.json`
4. `~/.config/redfish-mcp-server/config.json`

### Single-host (env vars)

If `REDFISH_HOST` and `REDFISH_PASSWORD` are set, single-host mode is used
(`server_id` defaults to `"default"`):

```bash
export REDFISH_HOST=192.0.2.10
export REDFISH_USERNAME=root
export REDFISH_PASSWORD=secret
export REDFISH_VERIFY_SSL=false
```

## Register with Claude Code

Add to `~/.claude.json` or your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "redfish": {
      "command": "/path/to/redfish-mcp-server/.venv/bin/python",
      "args": ["/path/to/redfish-mcp-server/redfish_mcp_server.py"]
    }
  }
}
```

After restart, every BMC listed in `config.json` is reachable through the 19
tools — much lighter on Claude Code's tool-list context than running a separate
single-host instance per BMC.

## Auth

- Tries Redfish session-token auth first (POST to
  `/redfish/v1/SessionService/Sessions`, captures `X-Auth-Token`).
- Falls back to HTTP Basic if the BMC rejects sessions or returns no token.
- On 401 mid-session, re-authenticates once and retries.
- TLS verification defaults to **off** (BMCs typically ship self-signed certs);
  set `verify_ssl: true` per-server in `config.json` if you've installed a CA.

## Usage examples

```text
list_servers
# → [{id: server1, host: 192.0.2.10, label: "Dell PowerEdge R630 — primary"}, ...]

get_firmware_inventory(server_id="server1")
# → {TotalComponents: 27, FirmwareInventory: [{Name: "Intel Ethernet ...", Version: "1.67.0", ...}, ...]}

list_event_log(server_id="server1", resource_type="Managers",
               resource_id="iDRAC.Embedded.1", severity_filter="Critical",
               max_entries=20)
# → newest 20 critical Lifecycle Log entries

get_thermal(server_id="server2", chassis_id="System.Embedded.1")
# → fan and temperature sensor readings
```

## Development layout

```
redfish-mcp-server/
├── redfish_mcp_server.py             # stdio entrypoint
├── requirements.txt
├── config.example.json
├── env.example
└── src/redfish_mcp_server/
    ├── app.py              # shared FastMCP instance + helpers
    ├── config.py           # multi-host config loader
    ├── pool.py             # per-server RedfishClient cache
    ├── redfish_client.py   # HTTP client (session/basic auth, @odata.id expand)
    ├── server.py           # imports each tool module to register tools
    ├── tools_meta.py       # list_servers, test_connection
    ├── tools_systems.py    # 4 tools
    ├── tools_chassis.py    # 4 tools
    ├── tools_managers.py   # 4 tools
    ├── tools_storage.py    # 2 tools
    ├── tools_eventlog.py   # 2 tools
    └── tools_firmware.py   # 1 tool
```

## License

MIT — same shape as the upstream projects this draws from.
