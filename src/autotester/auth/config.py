"""Auth startup configuration (AU3 cookie Secure rule, AU17 gate switch, AU20 hosted
settings). Reads the process environment only; refuses to start on an unsafe mix.
"""

from __future__ import annotations

import ipaddress
import os
import sys

HOSTED_ENV = "AUTOTESTER_HOSTED"
DISABLED_ENV = "AUTOTESTER_AUTH_DISABLED"
COOKIE_SECURE_ENV = "AUTOTESTER_COOKIE_SECURE"
FIRST_ADMIN_ENV = "AUTOTESTER_FIRST_ADMIN_EMAIL"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_WILDCARD = {"", "*", "0.0.0.0", "::"}  # bound to everything: no single own origin is knowable


class AuthConfigError(RuntimeError):
    """The server must not start with this configuration."""


def hosted() -> bool:
    return os.environ.get(HOSTED_ENV, "").strip() == "1"


def _option(name: str) -> str | None:
    """The value of a `--name value` / `--name=value` uvicorn option in argv, else None."""
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def bind_host() -> str:
    """The address uvicorn was told to bind (`--host`), else uvicorn's default."""
    found = _option("--host")
    return found if found is not None else os.environ.get("UVICORN_HOST", "127.0.0.1")


def auth_disabled() -> bool:
    """AU17: honoured only when not hosted AND bound to loopback; otherwise False."""
    if os.environ.get(DISABLED_ENV, "").strip() != "1":
        return False
    return not hosted() and bind_host() in _LOOPBACK


def public_facing(secure_cookie: bool = False) -> bool:
    """Hosted, bound to something other than loopback, or serving a Secure session cookie
    (an HTTPS proxy in front): anyone who can reach the server can sign up, so the first
    signup must not be handed admin (D-074 (d), AU7)."""
    return hosted() or secure_cookie or bind_host() not in _LOOPBACK


def first_admin_email() -> str:
    return os.environ.get(FIRST_ADMIN_ENV, "").strip().lower()


def check_startup() -> None:
    """Raise AuthConfigError on a configuration the gate must refuse (AU17, AU20)."""
    if os.environ.get(DISABLED_ENV, "").strip() == "1":
        if not auth_disabled():
            raise AuthConfigError(
                f"{DISABLED_ENV}=1 is refused when {HOSTED_ENV}=1 or the bind address "
                "is not loopback")
        print(f"WARNING: {DISABLED_ENV}=1 -- login is OFF (loopback, single-user only)",
              file=sys.stderr)
    if public_facing() and not first_admin_email():
        print(f"WARNING: {FIRST_ADMIN_ENV} is not set on a hosted / non-loopback server: no "
              "signup will be made an admin. Create the first admin with "
              "`autotester auth bootstrap-admin --email <address> --password-stdin`, or set "
              f"{FIRST_ADMIN_ENV} in the server's .env (D-074).", file=sys.stderr)
    if hosted() and not (os.environ.get("AUTOTESTER_ALLOWED_HOSTS", "").strip()
                         or os.environ.get("AUTOTESTER_ALLOWED_ORIGINS", "").strip()):
        raise AuthConfigError(
            f"{HOSTED_ENV}=1 needs AUTOTESTER_ALLOWED_HOSTS or AUTOTESTER_ALLOWED_ORIGINS "
            "naming the server")
    if hosted():
        _check_own_origin()


def _check_own_origin() -> None:
    """AU20: "the server's own origin must be an allowed one". Known only for a server bound
    to one concrete address (`--host 10.0.0.5 [--port 8443]`): that address, with or without
    the port, must be allowed as a Host or an origin. Loopback is always allowed (AU19). A
    wildcard bind (`0.0.0.0`, `::`, the shipped container) names no single origin -- the
    public name belongs to the proxy -- so nothing is guessed there."""
    host = bind_host().strip().lower()
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if loopback or host in _LOOPBACK or host in _WILDCARD:
        return
    from autotester.ui.helpers import _host_allowed  # lazy: `ui` imports `auth` at load
    name = f"[{host}]" if ":" in host else host
    port = _option("--port") or "8000"
    if not (_host_allowed(name) or _host_allowed(f"{name}:{port}")):
        raise AuthConfigError(
            f"the server's own origin {name}:{port} is not allowed: list it in "
            "AUTOTESTER_ALLOWED_HOSTS or AUTOTESTER_ALLOWED_ORIGINS (AU20)")


def cookie_secure(scheme: str) -> bool:
    """AU3: Secure over HTTPS (uvicorn applies a trusted proxy's X-Forwarded-Proto to
    the scheme) or when hosted; AUTOTESTER_COOKIE_SECURE=0 is the documented opt-out."""
    if os.environ.get(COOKIE_SECURE_ENV, "").strip() == "0":
        return False
    return scheme == "https" or hosted()
