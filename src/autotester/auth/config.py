"""Auth startup configuration (AU3 cookie Secure rule, AU17 gate switch, AU20 hosted
settings). Reads the process environment only; refuses to start on an unsafe mix.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

HOSTED_ENV = "AUTOTESTER_HOSTED"
DISABLED_ENV = "AUTOTESTER_AUTH_DISABLED"
COOKIE_SECURE_ENV = "AUTOTESTER_COOKIE_SECURE"
FIRST_ADMIN_ENV = "AUTOTESTER_FIRST_ADMIN_EMAIL"
PUBLIC_ORIGIN_ENV = "AUTOTESTER_PUBLIC_ORIGIN"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_WILDCARD = {"", "*", "0.0.0.0", "::"}  # bound to everything: no single own origin is knowable


class AuthConfigError(RuntimeError):
    """The server must not start with this configuration."""


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
    if hosted():
        _check_hosted()


def _check_hosted() -> None:
    """AU20: a parsed allow-list entry exists (a `*` or `,` is not one: the list parser drops
    it), and a server bound to one address is reachable under that address (own origin).
    The request-time guard is asked, so startup and the guard cannot disagree."""
    from autotester.ui.helpers import _listed  # lazy: `ui` imports `auth` at load
    if not (_listed("AUTOTESTER_ALLOWED_HOSTS") or _listed("AUTOTESTER_ALLOWED_ORIGINS")):
        raise AuthConfigError(
            f"{HOSTED_ENV}=1 needs AUTOTESTER_ALLOWED_HOSTS or AUTOTESTER_ALLOWED_ORIGINS "
            "naming the server")
    if bind_host().strip().lower() in _WILDCARD:
        _check_public_origin(required=True)  # owner gate answer option A (D-082)
        return
    _check_own_origin()
    _check_public_origin(required=False)


def _check_public_origin(required: bool) -> None:
    """AU20: `AUTOTESTER_PUBLIC_ORIGIN` is the origin users open. A wildcard bind (`0.0.0.0`,
    `::`, the container) cannot know it, so it must be set there (`required`); when set anywhere
    it must be a bare origin the Host and Origin guards both admit. Wrong at startup, never a
    403 on every request."""
    raw = os.environ.get(PUBLIC_ORIGIN_ENV, "").strip()
    if not raw:
        if required:
            raise AuthConfigError(
                f"{PUBLIC_ORIGIN_ENV} is required when the server binds every address "
                "(--host 0.0.0.0 or ::): set it to the origin users open, for example "
                "https://qa.example.com or http://192.168.1.20:8000 (AU20)")
        return
    from autotester.ui.helpers import _host_allowed, _origin_allowed
    try:
        parts = urlparse(raw.rstrip("/").lower())
        port = parts.port
        valid = (parts.scheme in {"http", "https"} and bool(parts.hostname)
                 and not (parts.username or parts.path or parts.query or parts.fragment))
    except ValueError:
        valid = False
    if not valid:
        raise AuthConfigError(
            f"{PUBLIC_ORIGIN_ENV}={raw!r} is not an origin: use scheme://host[:port] with no "
            "path, such as https://qa.example.com (AU20)")
    name = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    host = name if port in {None, {"http": 80, "https": 443}[parts.scheme]} else f"{name}:{port}"
    if not (_host_allowed(host) and _origin_allowed(f"{parts.scheme}://{host}")):
        raise AuthConfigError(
            f"{PUBLIC_ORIGIN_ENV}={parts.scheme}://{host} is not allowed: its Host must be in "
            "AUTOTESTER_ALLOWED_HOSTS (or be the host of an allowed origin) and the origin "
            "itself in AUTOTESTER_ALLOWED_ORIGINS (AU20)")


def _browser_hosts(name: str, port: str) -> list[tuple[str, str]]:
    """(scheme, Host header) a browser at this bind sends: the port is left out only when it is
    the scheme's default (80 for http, 443 for https)."""
    return [(scheme, name if port == default else f"{name}:{port}")
            for scheme, default in (("http", "80"), ("https", "443"))]


def _check_own_origin() -> None:
    """AU20: "the server's own origin must be an allowed one", for a bind on one address. For
    some scheme, the Host a browser would send must pass the Host guard (AU19) AND the origin it
    would send must pass the Origin guard (AU18): the guards' own functions decide. Loopback
    passes by their rules, not by a rule here."""
    from autotester.ui.helpers import _host_allowed, _origin_allowed
    host = bind_host().strip().lower()
    name = host if host.startswith("[") or ":" not in host else f"[{host}]"
    forms = _browser_hosts(name, bind_port())
    if any(_host_allowed(h) and _origin_allowed(f"{s}://{h}") for s, h in forms):
        return
    raise AuthConfigError(
        f"the server's own origin {' or '.join(f'{s}://{h}' for s, h in forms)} is not "
        "allowed: its Host must be in AUTOTESTER_ALLOWED_HOSTS (or be the host of an allowed "
        "origin) and the origin itself, with the port unless it is the scheme's default, in "
        "AUTOTESTER_ALLOWED_ORIGINS (AU20)")


def cookie_secure(scheme: str) -> bool:
    """AU3: Secure over HTTPS (uvicorn applies a trusted proxy's X-Forwarded-Proto to
    the scheme) or when hosted; AUTOTESTER_COOKIE_SECURE=0 is the documented opt-out."""
    if os.environ.get(COOKIE_SECURE_ENV, "").strip() == "0":
        return False
    return scheme == "https" or hosted()
