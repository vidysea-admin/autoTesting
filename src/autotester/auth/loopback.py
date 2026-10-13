"""The AU17 loopback switch, kept import-free: whether login is OFF (single-user loopback only).

Pure environment and argv reads, no `ui` or `browser` import, so the scheduler side (HO24 owner
guard) can ask `auth_disabled()` without reaching the browser. `auth.config` re-exports these
names; behaviour is unchanged: the switch is honoured only when not hosted AND bound to loopback.
"""

from __future__ import annotations

import os
import sys

HOSTED_ENV = "AUTOTESTER_HOSTED"
DISABLED_ENV = "AUTOTESTER_AUTH_DISABLED"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def hosted() -> bool:
    return os.environ.get(HOSTED_ENV, "").strip() == "1"


def _option(name: str) -> str | None:
    """The value of a `--name value` / `--name=value` uvicorn option in argv, else None.
    The LAST one wins, as it does in uvicorn (click)."""
    found = None
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            found = argv[i + 1]
        elif arg.startswith(name + "="):
            found = arg.split("=", 1)[1]
    return found


def bind_host() -> str:
    """The address uvicorn was told to bind (`--host`), else uvicorn's default."""
    found = _option("--host")
    return found if found is not None else os.environ.get("UVICORN_HOST", "127.0.0.1")


def bind_port() -> str:
    """The port uvicorn was told to bind (`--port`, else `UVICORN_PORT`, else 8000)."""
    found = _option("--port") or os.environ.get("UVICORN_PORT", "").strip()
    return str(int(found)) if found.isdigit() else "8000"


def auth_disabled() -> bool:
    """AU17: honoured only when not hosted AND bound to loopback; otherwise False."""
    if os.environ.get(DISABLED_ENV, "").strip() != "1":
        return False
    return not hosted() and bind_host() in _LOOPBACK
