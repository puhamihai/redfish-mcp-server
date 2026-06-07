"""FastMCP server wiring — imports each tool module so its `@mcp.tool()`
decorators register against the shared FastMCP instance in app.py.
"""

from __future__ import annotations

from .app import mcp  # the singleton

# Import side-effects: each module decorates its tools onto `mcp`.
from . import tools_meta  # noqa: F401
from . import tools_systems  # noqa: F401
from . import tools_chassis  # noqa: F401
from . import tools_managers  # noqa: F401
from . import tools_storage  # noqa: F401
from . import tools_eventlog  # noqa: F401
from . import tools_firmware  # noqa: F401

__all__ = ["mcp"]
