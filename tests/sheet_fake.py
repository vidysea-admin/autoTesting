"""An in-memory tracker sheet that records every call: the only SheetClient in this repo."""

from __future__ import annotations

from autotester.schema.sheet_plan import SheetState


class FakeSheet:
    """Header row plus data rows, a call log, a switch for `live`, and a way to fail after k writes.
    Extra human columns (ones the mapping never names) are just more header cells."""

    def __init__(self, header: list[str], rows: list[list[str]] | None = None, *,
                 live: bool = False, fail_after_writes: int | None = None) -> None:
        self.header, self.rows = list(header), [list(r) for r in rows or []]
        self.live, self.fail_after_writes = live, fail_after_writes
        self.calls: list[tuple] = []

    @property
    def write_calls(self) -> list[tuple]:
        return [c for c in self.calls if c[0] in ("append_row", "update_cells")]

    def read_header(self, sheet_id: str, tab: str) -> list[str]:
        self.calls.append(("read_header", sheet_id, tab))
        return list(self.header)

    def read(self, sheet_id: str, tab: str) -> SheetState:
        self.calls.append(("read", sheet_id, tab))
        return SheetState(header=list(self.header), rows=[list(r) for r in self.rows])

    def _pad(self, row: list[str]) -> list[str]:
        return row + [""] * (len(self.header) - len(row))

    def _maybe_fail(self) -> None:
        if self.fail_after_writes is not None and len(self.write_calls) > self.fail_after_writes:
            raise ConnectionError("sheet went away")

    def append_row(self, sheet_id: str, tab: str, cells: dict[str, str]) -> None:
        self.calls.append(("append_row", sheet_id, tab, dict(cells)))
        self._maybe_fail()
        row = [""] * len(self.header)
        for column, value in cells.items():
            row[self.header.index(column)] = value
        self.rows.append(row)

    def update_cells(self, sheet_id: str, tab: str, row_number: int,
                     cells: dict[str, str]) -> None:
        self.calls.append(("update_cells", sheet_id, tab, row_number, dict(cells)))
        self._maybe_fail()
        row = self.rows[row_number - 2] = self._pad(self.rows[row_number - 2])
        for column, value in cells.items():
            row[self.header.index(column)] = value

    def human_edit(self, row_number: int, column: str, value: str) -> None:
        """A person types into the sheet. Not a client call, so it is not in the log."""
        row = self.rows[row_number - 2] = self._pad(self.rows[row_number - 2])
        row[self.header.index(column)] = value

    def snapshot(self) -> tuple:
        return (tuple(self.header), tuple(tuple(r) for r in self.rows))
