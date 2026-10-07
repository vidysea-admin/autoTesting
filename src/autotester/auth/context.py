"""The current request's principal, set by the auth middleware for the request's
duration. Outside an HTTP request (CLI exports, direct renders in tests) it is None."""

from __future__ import annotations

from contextvars import ContextVar

from autotester.schema.auth import Principal

CURRENT_PRINCIPAL: ContextVar[Principal | None] = ContextVar("autotester_principal",
                                                              default=None)


def current_principal() -> Principal | None:
    return CURRENT_PRINCIPAL.get()
