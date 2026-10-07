"""Which seconds of a recording get looked at, and which do not (TV2, TV7 preview).

Pure arithmetic over seconds, no I/O. Pointers ADD frames and never remove any: the
base grid is always planned, pointer windows are planned at a denser grid that contains
the base grid, so the with-pointers set is a superset of the without set by construction.
`spans_from_plan` then names every second with no analysed frame (`not_reviewed`).
"""

from __future__ import annotations

from autotester.core.pricing import estimate_cost
from autotester.schema.video_pointer import PointerParse
from autotester.schema.video_review import FramePlan, RedactionWindow, ReviewPlan, Span, Spans

BASE_FRAMES_PER_MIN = 4
POINTER_FRAMES_PER_MIN = 12
"""Pointer depth, a whole multiple of base depth so the denser grid contains the base grid."""
POINTER_HALF_WINDOW_S = 20.0
"""A single-second pointer (`12:30`) is read as `12:30 +- this`: reviewers' times are rough."""
FRAMES_PER_CALL = 12
PROMPT_TOKENS_PER_CALL = 1500
TOKENS_PER_FRAME = 300
OUTPUT_TOKENS_PER_CALL = 800


def _r(x: float) -> float:
    return round(x, 3)


def pointer_windows(parse: PointerParse, duration_s: float) -> list[Span]:
    """Merged `[start, end]` stretches the reviewer pointed at (free pointers add none)."""
    raw: list[Span] = []
    for p in parse.parsed:
        if p.start_s is None:
            continue
        if p.end_s is not None:
            raw.append((_r(p.start_s), _r(min(p.end_s, duration_s))))
        else:
            raw.append((_r(max(0.0, p.start_s - POINTER_HALF_WINDOW_S)),
                        _r(min(duration_s, p.start_s + POINTER_HALF_WINDOW_S))))
    return _merge(raw)


def _merge(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _grid(step_s: float, lo: float, hi: float, duration_s: float) -> list[float]:
    """Multiples of `step_s` in `[lo, hi]` that fall strictly inside the recording."""
    k = int(lo // step_s) + (0 if lo % step_s == 0 else 1)
    out = []
    while _r(k * step_s) <= hi and k * step_s < duration_s:
        out.append(_r(k * step_s))
        k += 1
    return out


def plan_frames(duration_s: float, parse: PointerParse) -> FramePlan:
    """Base grid over the whole recording plus the denser grid inside pointer windows."""
    wins = pointer_windows(parse, duration_s)
    times = set(_grid(60.0 / BASE_FRAMES_PER_MIN, 0.0, duration_s, duration_s))
    for lo, hi in wins:
        times.update(_grid(60.0 / POINTER_FRAMES_PER_MIN, lo, hi, duration_s))
    return FramePlan(times=sorted(times), pointer_windows=wins)


def in_any(t: float, spans: list[Span]) -> bool:
    return any(a <= t <= b for a, b in spans)


def spans_from_plan(duration_s: float, planned: list[float], analysed: list[float], *,
                    windows: list[Span] | None = None) -> Spans:
    """`analysed` and `not_reviewed` as an exact partition of `[0, duration_s]`.

    A frame covers the time from itself to the next PLANNED frame (or the end), so a dropped
    frame leaves its stretch unreviewed, and a redaction window is always subtracted."""
    ordered = sorted(set(planned))
    done = set(analysed)
    cover: list[Span] = []
    for i, t in enumerate(ordered):
        end = ordered[i + 1] if i + 1 < len(ordered) else duration_s
        if t in done:
            cover.append((_r(t), _r(end)))
    cover = _subtract(_merge(cover), windows or [])
    return Spans(analysed=cover, not_reviewed=_subtract([(0.0, _r(duration_s))], cover))


def _subtract(spans: list[Span], holes: list[Span]) -> list[Span]:
    out = list(spans)
    for hs, he in _merge(list(holes)):
        nxt: list[Span] = []
        for s, e in out:
            if he <= s or hs >= e:
                nxt.append((s, e))
                continue
            if s < hs:
                nxt.append((s, _r(hs)))
            if e > he:
                nxt.append((_r(he), e))
        out = nxt
    return [(s, e) for s, e in out if e > s]


def order_batches(times: list[float], plan: FramePlan, size: int = FRAMES_PER_CALL
                  ) -> list[list[float]]:
    """Frames grouped into calls, pointer-window frames first (pointers prioritise, so a
    spend cap cuts the unpointed tail, not the stretch a human cared about)."""
    ranked = sorted(times, key=lambda t: (not in_any(t, plan.pointer_windows), t))
    return [sorted(ranked[i:i + size]) for i in range(0, len(ranked), size)]


def plan_review(duration_s: float, parse: PointerParse, windows: list[RedactionWindow], *,
                provider_label: str = "mock") -> ReviewPlan:
    """The preview: windows, frame count and estimated cost. Calls no provider."""
    plan = plan_frames(duration_s, parse)
    hidden = [(w.start_s, w.end_s) for w in windows]
    sendable = [t for t in plan.times if not in_any(t, hidden)]
    calls = len(order_batches(sendable, plan))
    cost = estimate_cost(provider_label,
                         calls * PROMPT_TOKENS_PER_CALL + len(sendable) * TOKENS_PER_FRAME,
                         calls * OUTPUT_TOKENS_PER_CALL)
    return ReviewPlan(frame_count=len(sendable),
                      redacted_frame_count=len(plan.times) - len(sendable), call_count=calls,
                      est_cost_usd=cost, windows=windows,
                      pointer_windows=plan.pointer_windows)
