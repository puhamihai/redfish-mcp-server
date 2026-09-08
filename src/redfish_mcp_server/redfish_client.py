"""Redfish HTTP client.

Authenticates via Redfish session token (POST to SessionService/Sessions)
and falls back to HTTP Basic if the BMC rejects sessions or returns no
X-Auth-Token. Sessions are re-established lazily on 401.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.ssl_ import create_urllib3_context

from .config import ServerConfig

logger = logging.getLogger(__name__)


class _LegacyTLSAdapter(HTTPAdapter):
    """Accept the weak TLS parameters of older BMCs (e.g. iDRAC7/8 ship
    small DH keys that OpenSSL 3 rejects with DH_KEY_TOO_SMALL)."""

    def _ctx(self) -> ssl.SSLContext:
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        ctx.minimum_version = ssl.TLSVersion.TLSv1
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ctx()
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ctx()
        return super().proxy_manager_for(*args, **kwargs)


class RedfishError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Redfish API error ({status}): {message}")
        self.status = status
        self.message = message


class RedfishClient:
    def __init__(self, server: ServerConfig, timeout: float = 30.0):
        self.server = server
        self.timeout = timeout
        self._session_token: Optional[str] = None
        self._session_url: Optional[str] = None
        self._http = requests.Session()
        self._http.verify = server.verify_ssl
        if not server.verify_ssl:
            # Suppress per-request warnings; emit one informational note.
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            # Old BMC firmware negotiates TLS parameters that OpenSSL 3
            # refuses at default security level; relax only when the user
            # already opted out of verification.
            self._http.mount("https://", _LegacyTLSAdapter())
            logger.debug(
                "TLS verification disabled for %s (%s)", server.id, server.host
            )

    # ── Auth ─────────────────────────────────────────────────────────────
    def authenticate(self) -> None:
        """Try session-token auth; fall through to Basic on any failure."""
        url = f"{self.server.base_url}/redfish/v1/SessionService/Sessions"
        try:
            resp = self._http.post(
                url,
                json={
                    "UserName": self.server.username,
                    "Password": self.server.password,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            logger.debug("Session auth failed for %s: %s — using Basic", self.server.id, e)
            self._session_token = None
            return

        if resp.ok:
            token = resp.headers.get("X-Auth-Token")
            location = resp.headers.get("Location")
            if token:
                self._session_token = token
                self._session_url = location
                logger.debug("Session established for %s", self.server.id)
                return
        # Some BMCs return a body but no token, or a 4xx on the session endpoint.
        # In all cases we silently fall through to Basic.
        self._session_token = None

    def logout(self) -> None:
        if not self._session_token or not self._session_url:
            return
        url = self._session_url
        if url and not url.startswith("http"):
            url = f"{self.server.base_url}{url}"
        try:
            self._http.delete(
                url,
                headers={"X-Auth-Token": self._session_token},
                timeout=self.timeout,
            )
        except requests.RequestException:
            pass
        self._session_token = None
        self._session_url = None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._session_token:
            headers["X-Auth-Token"] = self._session_token
        return headers

    def _auth(self) -> Optional[HTTPBasicAuth]:
        if self._session_token:
            return None
        return HTTPBasicAuth(self.server.username, self.server.password)

    # ── Core HTTP ────────────────────────────────────────────────────────
    def _request(
        self,
        method: str,
        path: str,
        body: Any = None,
        _retry_on_401: bool = True,
    ) -> Any:
        url = path if path.startswith("http") else f"{self.server.base_url}{path}"
        headers = self._headers()
        if body is not None and method.upper() in ("POST", "PUT", "PATCH"):
            headers["Content-Type"] = "application/json"

        resp = self._http.request(
            method,
            url,
            headers=headers,
            auth=self._auth(),
            json=body if body is not None else None,
            timeout=self.timeout,
        )

        # Session expired? Re-auth and retry once.
        if resp.status_code == 401 and self._session_token and _retry_on_401:
            logger.debug("Session token rejected for %s; re-authenticating", self.server.id)
            self._session_token = None
            self.authenticate()
            return self._request(method, path, body, _retry_on_401=False)

        # No-content responses
        if resp.status_code == 204 or (
            resp.status_code == 200 and resp.headers.get("content-length") == "0"
        ):
            return {"success": True, "status": resp.status_code}

        ctype = resp.headers.get("content-type", "")
        data: Any
        if "application/json" in ctype:
            try:
                data = resp.json()
            except ValueError:
                data = resp.text
        else:
            data = resp.text

        if not resp.ok:
            msg = self._extract_error(data)
            raise RedfishError(resp.status_code, msg)

        return data

    @staticmethod
    def _extract_error(data: Any) -> str:
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                ext = err.get("@Message.ExtendedInfo")
                if isinstance(ext, list) and ext:
                    extra = ext[0].get("Message") if isinstance(ext[0], dict) else None
                    if extra:
                        return f"{msg or ''} {extra}".strip()
                if msg:
                    return msg
            if data.get("Message"):
                return str(data["Message"])
        return str(data)[:500]

    # ── Verbs ────────────────────────────────────────────────────────────
    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, body: Any = None) -> Any:
        return self._request("POST", path, body if body is not None else {})

    def patch(self, path: str, body: Any) -> Any:
        return self._request("PATCH", path, body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # ── Redfish helpers ──────────────────────────────────────────────────
    def expand_members(self, members: list[dict]) -> list[Any]:
        """Resolve a list of {'@odata.id': '...'} entries into full objects."""
        return [self.get(m["@odata.id"]) for m in members]

    def get_collection(self, path: str) -> list[Any]:
        """GET a collection and expand its Members array."""
        data = self.get(path)
        members = data.get("Members", []) if isinstance(data, dict) else []
        return self.expand_members(members)
