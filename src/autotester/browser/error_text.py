"""What the page SHOWED when an assertion was unmet (inbox 2026-10-28 line 12).

One job: on an unmet assertion, read a bounded excerpt of visible alert / error / toast text
(`error_text.js`) and record it as ONE DOM evidence row. `browser/assertions.py` records only the
unmet assertion itself, so a real login failure ("Invalid credentials") lived only in a
screenshot -- and with image withholding (`mask_exceeds_limit`) the case became INCONCLUSIVE with
no readable reason.

Guarantees: the row passes `session._record` (the project's Redactor); the extractor never reads
a form control's value and blanks out any typed value that a server echoed back; the row never
starts with `assert ` so the unmet counters in `stages/grade*.py` are unchanged; a failed read
adds nothing and raises nothing (C7: this records a fact, it never assigns a verdict). It spends
no probe budget -- it runs only on the already-failed path -- but it still honours the budget's
hard stops.
"""

from __future__ import annotations

from pathlib import Path

from autotester.schema.enums import EvidenceKind
from autotester.stages.run_budget import RunBudgetExceeded

SCRAPE_JS = Path(__file__).with_name("error_text.js").read_text(encoding="utf-8")
LABEL = "error text on page"
MAX_ITEMS = 5
MAX_ITEM_CHARS = 200
MAX_TOTAL_CHARS = 600


def clean(raw: object) -> list[str]:
    """Normalise the scrape: whitespace-collapsed, per-item capped, de-duplicated, fragments
    contained in a longer message dropped, at most `MAX_ITEMS`. Anything that is not a list of
    non-blank strings yields []."""
    if not isinstance(raw, list):
        return []
    items: list[str] = []
    for value in raw:
        text = " ".join(value.split())[:MAX_ITEM_CHARS] if isinstance(value, str) else ""
        if text and text not in items:
            items.append(text)
    kept = [t for t in items if not any(t != other and t in other for other in items)]
    return kept[:MAX_ITEMS]


def read(session) -> list[str]:
    """The cleaned excerpts, or [] when the page cannot be read. Never raises, except a
    budget hard stop."""
    try:
        texts = clean(session.page.evaluate(SCRAPE_JS))
        if getattr(session, "budget", None) is not None:
            session.budget.check()
        return texts
    except RunBudgetExceeded:
        raise
    except Exception:
        return []


def record_visible_error_text(session, *, step_order: int | None = None) -> list:
    """Record the page's visible error text as one DOM evidence row; [] when there is none."""
    texts = read(session)
    if not texts:
        return []
    body = " | ".join(repr(t) for t in texts)[:MAX_TOTAL_CHARS]
    return [session._record(EvidenceKind.DOM, f"{LABEL} (after an unmet assertion): {body}",
                            step_order=step_order)]
