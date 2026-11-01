"""One job: the run page's cards about what bounded a run -- its preflight warnings and its
"Run bounds" card (the approval, the D-112 clock arithmetic, and why it stopped, if it did)."""

from __future__ import annotations

from html import escape

from autotester.schema.run import Run
from autotester.stages.report_export import bounds_text
from autotester.ui import theme

STOP_TEXT = {
    "wall_clock_s": "the wall_clock_s bound was reached; cases not yet started were recorded "
                    "INCONCLUSIVE with that reason",
    "max_actions": "the max_actions bound was reached; cases not yet started were recorded "
                   "INCONCLUSIVE with that reason",
    "max_probes": "the max_probes bound was reached; cases not yet started were recorded "
                  "INCONCLUSIVE with that reason",
    "target_unreachable": "the target did not answer, so no case was run (each recorded "
                          "INCONCLUSIVE)",
}
"""`Run.stop_reason` -> the sentence the page shows; an unknown reason is shown as recorded."""


def warnings_card(warnings: list[str] | None, *, stopped: bool = False) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
    note = ("The run did not start: no case was run." if stopped
            else "Warnings only: every case below still ran.")
    return (f"<div class='card preflight-warnings'><h3>Preflight warnings ({len(warnings)})</h3>"
            f"<p>{note}</p><ul>{items}</ul></div>")


def _secs(value: float | None) -> str:
    return "NOT RECORDED" if value is None else f"{value:.1f}s"


def clock_text(run: Run | None) -> str:
    """D-112: the approval's clock counts only time ACTING on the target; judge and housekeeping
    seconds are held off it. A run from before D-112 (`excluded_s` None) is NOT RECORDED, not 0."""
    held = run.excluded_s if run else None
    if held is None:
        return "clock accounting NOT RECORDED (a run from before D-112)"
    acting = f"acting {_secs(held['acting'])}" if "acting" in held else "acting time NOT RECORDED"
    return (f"clock (only time acting on the target counts): {acting}; held off it: "
            f"judging {_secs(held.get('judging'))}, housekeeping {_secs(held.get('housekeeping'))}")


def bounds_card(run: Run | None) -> str:
    lines = [bounds_text(run), clock_text(run)]
    if run is not None and run.stop_reason:
        lines.append("stopped early: " + STOP_TEXT.get(run.stop_reason, run.stop_reason))
    return theme.card("".join(f"<p>{escape(line)}</p>" for line in lines), title="Run bounds")


def run_cards(run: Run | None) -> str:
    """Preflight warnings, then the bounds card, for the run page."""
    stopped = bool(run and run.stop_reason == "target_unreachable")
    return warnings_card(run.preflight_warnings if run else None, stopped=stopped) \
        + bounds_card(run)
