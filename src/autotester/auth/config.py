"""Auth startup configuration (AU3 cookie Secure rule, AU17 gate switch, AU20 hosted
settings). Reads the process environment only; refuses to start on an unsafe mix.
"""

from __future__ import annotations

import os
import sys

HOSTED_ENV = "AUTOTESTER_HOSTED"
DISABLED_ENV = "AUTOTESTER_AUTH_DISABLED"
COOKIE_SECURE_ENV = "AUTOTESTER_COOKIE_SECURE"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class AuthConfigError(RuntimeError):
    """The server must not start with this configuration."""


def hosted() -> bool:
    return os.environ.get(HOSTED_ENV, "").strip() == "1"


def bind_host() -> str:
    """The address uvicorn was told to bind (`--host`), else uvicorn's default."""
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == "--host" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--host="):
            return arg.split("=", 1)[1]
    return os.environ.get("UVICORN_HOST", "127.0.0.1")


def auth_disabled() -> bool:
    """AU17: honoured only when not hosted AND bound to loopback; otherwise False."""
    if os.environ.get(DISABLED_ENV, "").strip() != "1":
        return False
    return not hosted() and bind_host() in _LOOPBACK


def check_startup() -> None:
    """Raise AuthConfigError on a configuration the gate must refuse (AU17, AU20)."""
    if os.environ.get(DISABLED_ENV, "").strip() == "1":
        if not auth_disabled():
            raise AuthConfigError(
                f"{DISABLED_ENV}=1 is refused when {HOSTED_ENV}=1 or the bind address "
                "is not loopback")
        print(f"WARNING: {DISABLED_ENV}=1 -- login is OFF (loopback, single-user only)",
              file=sys.stderr)
    if hosted() and not (os.environ.get("AUTOTESTER_ALLOWED_HOSTS", "").strip()
                         or os.environ.get("AUTOTESTER_ALLOWED_ORIGINS", "").strip()):
        raise AuthConfigError(
            f"{HOSTED_ENV}=1 needs AUTOTESTER_ALLOWED_HOSTS or AUTOTESTER_ALLOWED_ORIGINS "
            "naming the server")


def cookie_secure(scheme: str) -> bool:
    """AU3: Secure over HTTPS (uvicorn applies a trusted proxy's X-Forwarded-Proto to
    the scheme) or when hosted; AUTOTESTER_COOKIE_SECURE=0 is the documented opt-out."""
    if os.environ.get(COOKIE_SECURE_ENV, "").strip() == "0":
        return False
    return scheme == "https" or hosted()
