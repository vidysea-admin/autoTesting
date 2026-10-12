"""The one seam where sign-in and project permission plug into video intake.

Contract: team-intake.md TI10 (who may add videos) and TI11 (who did). The real check is T-204's
(accounts, groups, the `video.upload` permission) and is HELD on it. What lives here is the seam:
every intake route asks `get_gate().check(request, slug)` BEFORE it reads one byte of the body
and again (`recheck`) when a queued Drive fetch starts, and the only identity an intake row may
carry is the `IntakeActor` the gate returned, never a form field.

Until T-204 installs a gate, the default is `OpenGate`: it admits everyone and names nobody, so
`uploaded_by` stays empty rather than being made up.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import Request

from autotester.schema.intake import IntakeActor

__all__ = ["IntakeActor", "IntakeGate", "IntakeRefused", "OpenGate", "get_gate", "set_gate"]


class IntakeRefused(Exception):
    """The gate said no. `status` is the HTTP status (403 not allowed, 404 no such project) and
    `message` is the sentence the page shows."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


class IntakeGate(Protocol):
    def check(self, request: Request, slug: str) -> IntakeActor:
        """Who is asking, or `IntakeRefused`. Called before the body is read."""

    def recheck(self, actor: IntakeActor, slug: str) -> None:
        """Still allowed? Called when a queued job starts; `IntakeRefused` if not."""


class OpenGate:
    """No sign-in exists yet (T-204): admit everyone, record nobody."""

    def check(self, request: Request, slug: str) -> IntakeActor:
        return IntakeActor(email=None)

    def recheck(self, actor: IntakeActor, slug: str) -> None:
        return None


_gate: IntakeGate = OpenGate()


def get_gate() -> IntakeGate:
    return _gate


def set_gate(gate: IntakeGate) -> IntakeGate:
    """Install `gate`; returns the previous one so a caller (T-204, a test) can restore it."""
    global _gate
    previous, _gate = _gate, gate
    return previous
