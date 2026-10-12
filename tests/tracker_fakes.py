"""Fixtures for the tracker tests: two invented header layouts and a recording provider."""

from __future__ import annotations

from typing import Any

from autotester.providers.base import Provider
from autotester.schema.tracker_binding import MappingReply, TrackerBinding

LAYOUT_A = ["S.No", "Bug ID", "Bug Title", "Severity", "Screen", "Status", "Assigned To",
            "Date Reported", "Screenshot", "Dev notes"]
"""A tracker-like sheet: every field has one obvious column and one extra human column."""

LAYOUT_B = ["Ref", "What broke", "Impact", "Where", "State", "Owner", "Found", "Remarks"]
"""An invented sheet: the title column has a name no synonym covers."""


def ALLOWED(user: str, project: str) -> bool:
    return user == "umesh.s"


class RecordingProvider(Provider):
    """Answers with a fixed reply and keeps every prompt it was sent."""

    id = "fake"

    def __init__(self, matches: dict[str, str | None] | None = None) -> None:
        super().__init__()
        self.matches = matches or {}
        self.prompts: list[str] = []

    def available(self) -> bool:
        return True

    def act(self, prompt: str, schema: Any = None, *, prompt_file: str | None = None,
            fed_id: str | None = None) -> Any:
        self.prompts.append(prompt)
        return MappingReply(matches=self.matches)


def binding(project: str = "demo", sheet_id: str = "sheet_demo") -> TrackerBinding:
    return TrackerBinding(project=project, sheet_id=sheet_id, tab="Bugs")
