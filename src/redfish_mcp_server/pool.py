"""Per-server RedfishClient cache.

Tools resolve `server_id` → cached client. Sessions are negotiated on first
use and reused; on 401 the client re-authenticates automatically (see
RedfishClient._request).
"""

from __future__ import annotations

import logging
from typing import Optional

from .config import Config, load_config
from .redfish_client import RedfishClient

logger = logging.getLogger(__name__)


class RedfishPool:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self._clients: dict[str, RedfishClient] = {}

    def get(self, server_id: Optional[str] = None) -> RedfishClient:
        server = self.config.get(server_id)
        if server.id not in self._clients:
            client = RedfishClient(server)
            client.authenticate()
            self._clients[server.id] = client
        return self._clients[server.id]

    def list_servers(self) -> list[dict]:
        return [s.public_summary() for s in self.config.servers.values()]


_pool: Optional[RedfishPool] = None


def get_pool() -> RedfishPool:
    global _pool
    if _pool is None:
        _pool = RedfishPool()
    return _pool
