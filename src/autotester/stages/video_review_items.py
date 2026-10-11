"""Turn a model reply into validated confirm-list items (TV3, TV4, TV5, TV6).

One bad item never sinks the review: it goes to `rejected` with a reason. A narration claim
survives only as a verbatim quote of a transcript segment that overlaps its second, else it is
downgraded to `suspected` and the downgrade is recorded (TV5). The model can never set a human
status, and the system never writes the word "confirmed" itself.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.core.ids import content_id
from autotester.schema.enums import Severity
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.video_review import (
    MAX_ITEMS,
    ORIGINS,
    ConfirmItem,
    RejectedItem,
    ReplyItem,
)
from autotester.stages.video_review_prompt import NARRATION_NOTES, narration_state

NARRATION_SLACK_S = 0.0
"""A quote counts only when its segment covers the item's second (TV5): no slack, so speech
that ends before, or starts after, the second is not narration of it."""
_SEV_RANK = {Severity.S1: 0, Severity.S2: 1, Severity.S3: 2}
MIN_LIST = 4
"""The oracle shows 4-5 rows; fewer is reported as fewer, never padded to reach it."""


def _text(v: object) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def overlapping(transcript: Transcript | None, t: float) -> list[TranscriptSegment]:
    if transcript is None or narration_state(transcript) != "speech":
        return []   # F6: segments carried by a none/unreadable engine are not narration
    return [s for s in transcript.segments
            if s.start - NARRATION_SLACK_S <= t <= s.end + NARRATION_SLACK_S]


def _narration_note(transcript: Transcript | None, t: float) -> str:
    state = narration_state(transcript)
    if state != "speech":
        return NARRATION_NOTES[state]
    heard = "narration" if overlapping(transcript, t) else "no narration"
    return f"{heard} at this moment"


def _quote_verbatim(quote: str, segs: list[TranscriptSegment], scrub: Callable[[str], str]) -> bool:
    return any(quote in s.text or quote in scrub(s.text) for s in segs)


def _fields(raw: ReplyItem) -> tuple[dict[str, object], str | None]:
    """The five required fields + origin, or the first reason this item is unusable."""
    out: dict[str, object] = {}
    for name in ("screen", "seen", "suggestion", "source_id"):
        value = _text(getattr(raw, name))
        if value is None:
            return out, f"missing_field:{name}"
        out[name] = value
    t = raw.time_s
    if isinstance(t, bool) or not isinstance(t, (int, float)):
        return out, "missing_field:time_s"
    out["time_s"] = float(t)
    sev = _text(raw.severity)
    if sev is None:
        return out, "missing_field:severity"
    if sev not in {s.value for s in Severity}:
        return out, "invalid_severity"
    out["severity"] = Severity(sev)
    origin = _text(raw.origin)
    if origin is None:
        return out, "missing_field:origin"
    if origin not in ORIGINS:
        return out, "invalid_origin"
    out["origin"] = origin
    return out, None


def _provenance(f: dict[str, object], raw: ReplyItem, transcript: Transcript | None,
                pointer_lines: set[int], scrub: Callable[[str], str]) -> dict[str, object]:
    """Apply TV5: keep `narration` only with a verbatim overlapping quote, `pointer` only with
    a real pointer line; otherwise `suspected` plus a recorded reason."""
    origin, t = str(f["origin"]), float(f["time_s"])  # type: ignore[arg-type]
    extra: dict[str, object] = {"quote": None, "pointer_line": None, "downgrade": None}
    if origin == "narration":
        quote = _text(raw.quote)
        if quote and _quote_verbatim(quote, overlapping(transcript, t), scrub):
            extra["quote"] = scrub(quote)
        else:
            f["origin"] = "suspected"
            extra["downgrade"] = ("narration claim downgraded: no verbatim quote from a "
                                  "transcript segment at this second")
    elif origin == "pointer":
        line = raw.pointer_line
        if isinstance(line, int) and not isinstance(line, bool) and line in pointer_lines:
            extra["pointer_line"] = line
        else:
            f["origin"] = "suspected"
            extra["downgrade"] = "pointer claim downgraded: no valid pointer line cited"
    return extra


def validate_item(raw: ReplyItem, *, review_id: str, duration_s: float, known_sources: set[str],
                  transcript: Transcript | None, pointer_lines: set[int],
                  scrub: Callable[[str], str]) -> ConfirmItem | RejectedItem:
    fields, bad = _fields(raw)
    dump = {k: v for k, v in raw.model_dump().items() if v is not None}
    if bad:
        return RejectedItem(reason=bad, item=dump)
    t = float(fields["time_s"])  # type: ignore[arg-type]
    if not 0 <= t <= duration_s:
        return RejectedItem(reason="time_outside_recording", item=dump)
    if fields["source_id"] not in known_sources:
        return RejectedItem(reason="unknown_source", item=dump)
    extra = _provenance(fields, raw, transcript, pointer_lines, scrub)
    item_id = content_id("it", {"r": review_id, "t": round(t, 1), "s": fields["screen"],
                                "x": fields["seen"]})
    return ConfirmItem(id=item_id, narration_note=_narration_note(transcript, t),
                       **fields, **extra)  # type: ignore[arg-type]


def build_items(raws: list[ReplyItem], **ctx: object
                ) -> tuple[list[ConfirmItem], list[ConfirmItem], list[RejectedItem]]:
    """(items<=5 in time order, overflow in severity order, rejected). Nothing is discarded."""
    kept: list[ConfirmItem] = []
    rejected: list[RejectedItem] = []
    seen_ids: set[str] = set()
    for raw in raws:
        out = validate_item(raw, **ctx)  # type: ignore[arg-type]
        if isinstance(out, RejectedItem):
            rejected.append(out)
        elif out.id in seen_ids:
            rejected.append(RejectedItem(reason="duplicate_item", item=out.model_dump(mode="json")))
        else:
            seen_ids.add(out.id)
            kept.append(out)
    ranked = sorted(kept, key=lambda i: (_SEV_RANK[i.severity], i.time_s))
    top, overflow = ranked[:MAX_ITEMS], ranked[MAX_ITEMS:]
    return sorted(top, key=lambda i: i.time_s), overflow, rejected


def count_note(n: int) -> str | None:
    if n >= MIN_LIST:
        return None
    plural = "s" if n != 1 else ""
    return f"Only {n} item{plural} found (fewer than {MIN_LIST}); the list is not padded."
