"""Multi-host configuration loader.

Resolution order:
  1. If REDFISH_HOST + REDFISH_PASSWORD env vars are set → single-host mode (id="default").
  2. Else load JSON config from REDFISH_MCP_CONFIG, ./config.json, or
     ~/.config/redfish-mcp-server/config.json (first that exists).

Config schema:
{
  "servers": {
    "<server_id>": {
      "host":        "10.0.0.1",       # required (IP or hostname, no scheme)
      "username":    "root",            # optional, defaults to "root"
      "password":    "secret",          # required
      "verify_ssl":  false,             # optional, defaults to false (BMC self-signed certs)
      "port":        443,               # optional, defaults to 443
      "label":       "human readable"   # optional, free-form description
    }
  },
  "default_server": "<server_id>"        # optional; if omitted, first key in `servers`
}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    pass


class ServerConfig:
    __slots__ = ("id", "host", "username", "password", "verify_ssl", "port", "label")

    def __init__(
        self,
        server_id: str,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        port: int = 443,
        label: Optional[str] = None,
    ):
        self.id = server_id
        self.host = host
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.port = port
        self.label = label or server_id

    @property
    def base_url(self) -> str:
        if self.port == 443:
            return f"https://{self.host}"
        return f"https://{self.host}:{self.port}"

    def public_summary(self) -> dict:
        """Safe-to-log/return summary — no secrets."""
        return {
            "id": self.id,
            "host": self.host,
            "username": self.username,
            "verify_ssl": self.verify_ssl,
            "port": self.port,
            "label": self.label,
        }


class Config:
    def __init__(self, servers: dict[str, ServerConfig], default_server: str):
        if not servers:
            raise ConfigError("No servers configured.")
        if default_server not in servers:
            raise ConfigError(
                f"default_server '{default_server}' not in servers: {list(servers)}"
            )
        self.servers = servers
        self.default_server = default_server

    def get(self, server_id: Optional[str]) -> ServerConfig:
        sid = server_id or self.default_server
        if sid not in self.servers:
            raise ConfigError(
                f"Unknown server_id '{sid}'. Known: {sorted(self.servers)}"
            )
        return self.servers[sid]


def _from_single_host_env() -> Optional[Config]:
    host = os.environ.get("REDFISH_HOST")
    password = os.environ.get("REDFISH_PASSWORD")
    if not host or not password:
        return None
    srv = ServerConfig(
        server_id="default",
        host=host,
        username=os.environ.get("REDFISH_USERNAME", "root"),
        password=password,
        verify_ssl=os.environ.get("REDFISH_VERIFY_SSL", "false").lower() == "true",
        port=int(os.environ.get("REDFISH_PORT", "443")),
        label=os.environ.get("REDFISH_LABEL", host),
    )
    return Config({"default": srv}, "default")


def _config_path() -> Optional[Path]:
    explicit = os.environ.get("REDFISH_MCP_CONFIG")
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
        raise ConfigError(f"REDFISH_MCP_CONFIG points to missing file: {p}")
    for candidate in (
        Path.cwd() / "config.json",
        Path.home() / ".redfish-mcp-server" / "config.json",
        Path.home() / ".config" / "redfish-mcp-server" / "config.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _from_json(path: Path) -> Config:
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"Failed to read {path}: {e}") from e

    raw_servers = raw.get("servers")
    if not isinstance(raw_servers, dict) or not raw_servers:
        raise ConfigError(f"{path}: 'servers' must be a non-empty object")

    servers: dict[str, ServerConfig] = {}
    for sid, entry in raw_servers.items():
        if not isinstance(entry, dict):
            raise ConfigError(f"{path}: servers.{sid} must be an object")
        host = entry.get("host")
        password = entry.get("password")
        if not host:
            raise ConfigError(f"{path}: servers.{sid}.host is required")
        if not password:
            raise ConfigError(f"{path}: servers.{sid}.password is required")
        servers[sid] = ServerConfig(
            server_id=sid,
            host=host,
            username=entry.get("username", "root"),
            password=password,
            verify_ssl=bool(entry.get("verify_ssl", False)),
            port=int(entry.get("port", 443)),
            label=entry.get("label"),
        )

    default_server = raw.get("default_server") or next(iter(servers))
    return Config(servers, default_server)


_cached: Optional[Config] = None


def load_config() -> Config:
    """Load and cache config. Single-host env vars win over config.json."""
    global _cached
    if _cached is not None:
        return _cached

    cfg = _from_single_host_env()
    if cfg is None:
        path = _config_path()
        if path is None:
            raise ConfigError(
                "No config found. Set REDFISH_HOST+REDFISH_PASSWORD for single-host mode, "
                "or provide config.json (REDFISH_MCP_CONFIG, ./config.json, or "
                "~/.config/redfish-mcp-server/config.json)."
            )
        cfg = _from_json(path)

    _cached = cfg
    return cfg
