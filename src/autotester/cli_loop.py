"""`autotester loop-status` — was the maker-checker loop alive, and if not, on purpose?

AT-368. Separate from `cli.py` because that file is at its line budget and this
command drives a different concern, which is the same reason `cli_issues.py` and
`cli_video.py` are separate from it.

The logic lives in `loop_status.py`; this file is only the terminal in front of
it, so the wording stays testable without a terminal.
"""

from __future__ import annotations

import typer

from autotester import loop_status, tick_guard

_LEVEL_COLOR = {"ok": typer.colors.GREEN, "warn": typer.colors.YELLOW,
                "bad": typer.colors.RED, "plain": None}


def loop_status_cmd(
    strict: bool = typer.Option(False, "--strict", help="exit 1 if the loop is asleep right now"),
    hours: float = typer.Option(
        loop_status.DEFAULT_GAP_HOURS, "--hours", help="a gap this long or longer is reported"
    ),
) -> None:
    """Report gaps in `qa/.last-tick` — was the maker loop alive, and was any stop deliberate?

    Read-only, and deliberately NOT part of `doctor`: doctor sits in the
    adapter's verify chain, so a stale loop would fail every unit's verification
    — a liveness signal that breaks the build is worse than the silence it
    replaces (AT-368)."""
    # AT-644 (D-087): a truncated/partial log must not read as a clean history.
    damaged = tick_guard.problems(tick_guard.tick_path())
    for why in damaged:
        typer.secho(f"TICK LOG DAMAGED: {why}", fg=typer.colors.RED)
    report = loop_status.status(threshold_hours=hours)
    for text, level in loop_status.report_lines(report):
        typer.secho(text, fg=_LEVEL_COLOR.get(level))
    # AT-592: `asleep_now` alone misses an all-future log -- no open gap to key
    # off, yet `report_lines` above just printed CORRUPT and "last: none
    # credible". `strict_unhealthy` covers both the silent-now case and that one.
    raise typer.Exit(1 if (strict and (report.strict_unhealthy or damaged)) else 0)


def tick_append_cmd(line: str = typer.Argument(..., help="ISO-stamped tick line")) -> None:
    """Append a line to qa/.last-tick atomically (AT-644); refuses a damaging write."""
    try:
        tick_guard.append_tick(tick_guard.tick_path(), line)
    except tick_guard.TickGuardError as exc:
        typer.secho(f"REFUSED: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc
