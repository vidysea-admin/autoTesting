"""`autotester sweep stamp`: the one append-only writer of the checker's sweep log (AT-699).

One job: append exactly one line to `qa/.last-sweep` and never rewrite what is already there
(living-ledger L11, the `autotester ledger add` pattern). An empty, whitespace-only or multi-line
argument is refused with exit 2 and the file is left byte-identical. The log is opened append-only
in binary mode, so existing lines keep their bytes (CRLF or LF) and the new line borrows the
log's own line ending. Registered through `cli_subapps.py`, never `cli.py`.
"""

from __future__ import annotations

from pathlib import Path

import typer

from autotester.core.paths import repo_root

SWEEP_LOG = Path("qa") / ".last-sweep"

app = typer.Typer(help="The checker's append-only sweep log (qa/.last-sweep).")


class StampRefused(ValueError):
    """The argument is not exactly one non-blank line; nothing was written."""


def _eol_of(existing: bytes) -> bytes:
    """The line ending the log already uses (its last one); LF for an empty log."""
    last = existing.rfind(b"\n")
    return b"\r\n" if last > 0 and existing[last - 1:last] == b"\r" else b"\n"


def append_stamp(root: Path, line: str) -> Path:
    """Append `line` as one new line of `<root>/qa/.last-sweep`; return the log path."""
    if not line.strip():
        raise StampRefused("empty or whitespace-only line")
    if line.splitlines() != [line]:
        raise StampRefused("one stamp is one line; the argument contains a line break")
    path = root / SWEEP_LOG
    existing = path.read_bytes() if path.exists() else b""
    eol = _eol_of(existing)
    lead = eol if existing and not existing.endswith(b"\n") else b""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:  # append-only: never "w" (L11 sabotage)
        handle.write(lead + line.encode("utf-8") + eol)
    return path


@app.command("stamp")
def stamp_cmd(line: str = typer.Argument(..., help="the one-line sweep record to append")) -> None:
    """Append LINE to qa/.last-sweep. Refuses an empty, blank or multi-line argument (exit 2)."""
    try:
        path = append_stamp(repo_root(), line)
    except StampRefused as exc:
        typer.secho(f"sweep stamp refused: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None
    typer.secho(f"stamped {path}", fg=typer.colors.GREEN)
