"""The shapes of a project's tracker binding and the state of its sheet sync (T-199d; TB12, TB14).

Its one job is the shapes. A `TrackerBinding` is one project's sheet and the header-to-field
mapping proposed from that sheet's header row; a field the code could not map is listed under
`unmapped` with its candidates and the project still works in-product. A `SyncStatus` is the last
sheet-sync outcome: an outage is data on the tracker page, never a run failure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.sheet_plan import SheetColumns


class TrackerBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_id: str = Field(min_length=1, max_length=200)
    tab: str = Field(min_length=1, max_length=100)
    columns: dict[str, str] = Field(default_factory=dict, description="bug field -> header text")
    unmapped: dict[str, list[str]] = Field(
        default_factory=dict, description="bug field -> candidate headers (empty = none found)")

    def to_columns(self) -> SheetColumns | None:
        """The sync mapping, or None while the row key is unmapped (nothing can be located)."""
        if "bug_key" not in self.columns:
            return None
        return SheetColumns(sheet_id=self.sheet_id, tab=self.tab, columns=self.columns)


class SyncStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sync_status: Literal["ok", "error"]
    at: datetime
    last_error: str | None = None
    retry_at: datetime | None = None
