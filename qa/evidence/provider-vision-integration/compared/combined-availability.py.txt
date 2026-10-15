"""Classify transport availability failures without examining vendor payload text."""
from __future__ import annotations

from autotester.providers.base import ProviderError, Unsupported


class AvailabilityFailure(ProviderError):
    """An allowlisted transport failure; safe reason doubles as fallback evidence."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"provider availability failure: {reason}")


def availability_reason(exc: Exception) -> str | None:
    """Fail closed: privacy/schema/policy/generic errors never imply availability.

    403 is deliberately excluded: a permission or safety refusal is ambiguous.
    Unsupported is the Provider seam's explicit capability declaration.
    """
    if isinstance(exc, Unsupported):
        return "capability"
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "service"
    # LiteLLM normalizes vendor exceptions to these SDK exception types.
    names = {cls.__name__ for cls in type(exc).__mro__}
    if names & {"AuthenticationError"}:
        return "authentication"
    if names & {"APIConnectionError", "ServiceUnavailableError", "Timeout"}:
        return "service"
    if getattr(exc, "status_code", None) == 401:
        return "authentication"
    if getattr(exc, "status_code", None) in (502, 503, 504):
        return "service"
    return None
