"""Review one recording with human pointers: the typed, redacted, capped, idempotent run (T-197).

Contract: qa/contracts/team-video-review.md TV1-TV8, TV10. The ORDER is the safety property, and
nothing reaches the Provider until the first five steps are done:

    gate -> probe -> pointer parse -> redacted frames -> prompt (scrubbed, secret-gated) -> call

`gate` is injected by the caller (the permission + per-use approval check, which needs T-204) and
raises `ReviewRefused`. It is a required argument on purpose: there is no permissive default.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import ValidationError

from autotester.core.ids import content_hash, content_id, file_sha256
from autotester.core.paths import ProjectPaths
from autotester.core.pricing import estimate_cost_conservative
from autotester.core.redact import Redactor, assert_no_raw_secrets, mask_pii
from autotester.media.probe import probe
from autotester.media.redacted import (
    FrameSource,
    RedactedFrames,
    RedactionError,
    review_scratch,
)
from autotester.providers.base import Provider, ProviderError
from autotester.schema.media import Transcript
from autotester.schema.project import Source
from autotester.schema.video_pointer import PointerParse
from autotester.schema.video_review import (
    MAX_ITEMS,
    RedactionWindow,
    ReviewPlan,
    ReviewReply,
    VideoReview,
)
from autotester.stages.video_pointers import canonical_pointers, parse_pointers
from autotester.stages.video_review_items import build_items, count_note
from autotester.stages.video_review_plan import (
    in_any,
    order_batches,
    plan_frames,
    plan_review,
    spans_from_plan,
)
from autotester.stages.video_review_prompt import (
    NARRATION_NOTES,
    PROMPT_FILE,
    build_review_prompt,
    clock,
    load_template,
    narration_state,
    visible_transcript,
)
from autotester.store.filestore import read_json, write_json

logger = logging.getLogger(__name__)

DEFAULT_MAX_COST_USD = 0.50
"""Per-review spend cap in USD (TV7.4): cheap by default; a caller raises it deliberately."""
ReviewGate = Callable[[], None]
FramesFactory = Callable[[Path, Path, list[RedactionWindow]], FrameSource]


class ReviewRefused(RuntimeError):
    """A TV7 precondition failed (permission, approval, redaction check, secret in prompt)."""


class PointerErrors(ValueError):
    """The pointer file had refused lines (TV1): CLI exit 2 / HTTP 422, provider never called."""

    def __init__(self, parse: PointerParse) -> None:
        super().__init__(f"{len(parse.errors)} pointer line(s) refused")
        self.parse = parse


def provider_cost(provider: Provider) -> float:
    """Spend so far. An unpriced label is charged the dearest known rate, never zero (TV7.4)."""
    return sum(estimate_cost_conservative(provider.label, u.input_tokens, u.output_tokens)
               for u in provider.usage)


def transcript_hash(t: Transcript | None) -> str:
    return content_hash(None if t is None else {
        "engine": t.engine, "segments": [s.model_dump() for s in t.segments]})


def review_id(sha256: str, parse: PointerParse, tx_hash: str,
              windows: Sequence[RedactionWindow]) -> str:
    """Content-derived (TV10): source bytes + canonical pointers + transcript + windows."""
    wins = sorted((round(w.start_s, 3), round(w.end_s, 3)) for w in windows)
    return content_id("rv", {"src": sha256, "ptr": canonical_pointers(parse), "tx": tx_hash,
                             "red": wins})


def load_review(paths: ProjectPaths, rid: str) -> VideoReview | None:
    return read_json(paths.review_path(rid), VideoReview)


def preview_review(video: Path, pointer_text: str, windows: Sequence[RedactionWindow], *,
                   provider_label: str = "mock", probe_fn: Callable[[Path], tuple[float, int, int]]
                   = probe) -> ReviewPlan:
    """`--dry-run`: windows, frame count, estimated cost. Zero provider calls (TV7.4)."""
    duration, _, _ = probe_fn(video)
    parse = parse_pointers(pointer_text, duration)
    if parse.errors:
        raise PointerErrors(parse)
    return plan_review(duration, parse, list(windows), provider_label=provider_label)


def _merge_human_status(new: VideoReview, stored: VideoReview | None) -> VideoReview:
    """A re-run never resets what a human decided (TV10); decided items stay listed."""
    if stored is None:
        return new
    human = {i.id: i for i in [*stored.items, *stored.overflow] if i.status != "open"}
    items = [i.model_copy(update={"status": human[i.id].status}) if i.id in human else i
             for i in new.items]
    overflow = [i.model_copy(update={"status": human[i.id].status}) if i.id in human else i
                for i in new.overflow]
    present = {i.id for i in [*items, *overflow]}
    for kept in (h for i, h in human.items() if i not in present):
        (items if len(items) < MAX_ITEMS else overflow).append(kept)
    return new.model_copy(update={"items": items, "overflow": overflow})


def _coverage_note(spans: list[tuple[float, float]], windows: Sequence[RedactionWindow]) -> str:
    if not spans:
        return "Every part of the recording was looked at."
    parts = ", ".join(f"{clock(s)}-{clock(e)}" for s, e in spans)
    red = " Redacted on request: " + ", ".join(
        f"{clock(w.start_s)}-{clock(w.end_s)}" for w in windows) + "." if windows else ""
    return f"Not reviewed: {parts}.{red}"


class _Analysis:
    """Accumulator for the batch loop: replies, frames really shown, calls, why it stopped."""

    def __init__(self) -> None:
        self.replies: list[ReviewReply] = []
        self.shown: list[float] = []
        self.calls = 0
        self.stopped: str | None = None
        self.failure: str | None = None


def _analyse(*, batches: list[list[float]], frames: FrameSource, provider: Provider,
             prompt_for: Callable[[list[float]], str], rid: str, max_cost_usd: float,
             cost_of: Callable[[Provider], float]) -> _Analysis:
    out = _Analysis()
    for times in batches:
        if not cost_of(provider) < max_cost_usd:   # also stops on a NaN cap
            out.stopped = f"spend cap ${max_cost_usd:g} reached"
            break
        pairs = [(t, frames.frame(t)) for t in times]
        shown = [(t, p) for t, p in pairs if p is not None]
        if not shown:
            continue
        prompt = mask_pii(prompt_for([t for t, _ in shown]))  # AT-840
        try:
            reply = provider.judge(prompt, ReviewReply, images=[p for _, p in shown],
                                   prompt_file=PROMPT_FILE, fed_id=rid)
            out.calls += 1
            if not isinstance(reply, ReviewReply):
                raise ProviderError(f"reply is {type(reply).__name__}, not a ReviewReply")
            if not reply.summary.strip():
                raise ProviderError("reply has no flow summary")
        except (ProviderError, ValidationError, ValueError) as exc:
            out.failure = f"model reply was not usable: {type(exc).__name__}: {str(exc)[:200]}"
            break
        out.replies.append(reply)
        out.shown.extend(t for t, _ in shown)
    return out


def _unreadable(rid: str, source: Source, sha: str, why: str, tx: str) -> VideoReview:
    return VideoReview(id=rid, source_id=source.id, status="unreadable", reason=why,
                       source_sha256=sha, transcript_hash=tx)


def _prompter(source_id: str, duration: float, parse: PointerParse,
              transcript: Transcript | None, redactor: Redactor, secrets: dict[str, str]
              ) -> Callable[[list[float]], str]:
    """Prompt text for a batch: free text scrubbed, then hard-gated on raw secrets (C5)."""
    template = load_template()

    def prompt_for(times: list[float]) -> str:
        prompt = build_review_prompt(
            template, source_id=source_id, duration_s=duration, times=times, parse=parse,
            transcript=transcript, scrub=redactor.scrub, max_items=MAX_ITEMS)
        try:
            assert_no_raw_secrets(prompt, secrets.values())
        except ValueError as exc:
            raise ReviewRefused(str(exc)) from exc
        return prompt

    return prompt_for


def unreadable_reason(video: Path, probe_fn: Callable[[Path], tuple[float, int, int]] = probe
                      ) -> str | None:
    """Why this recording cannot be reviewed (missing, empty, corrupt, audio-only), or None."""
    if not video.is_file() or video.stat().st_size == 0:
        return "recording is missing or empty"
    duration, width, _ = probe_fn(video)
    if duration <= 0 or width <= 0:
        return "recording is corrupt or has no video track"
    return None


def run_review(paths: ProjectPaths, source: Source, video: Path, provider: Provider,
               transcript: Transcript | None, *, gate: ReviewGate, secrets: dict[str, str],
               pointer_text: str = "", windows: Sequence[RedactionWindow] = (),
               max_cost_usd: float = DEFAULT_MAX_COST_USD, refresh: bool = False,
               known_sources: set[str] | None = None,
               probe_fn: Callable[[Path], tuple[float, int, int]] = probe,
               frames_fn: FramesFactory = RedactedFrames,
               cost_of: Callable[[Provider], float] = provider_cost) -> VideoReview:
    """Run (or return the stored) review. Raises `ReviewRefused` / `PointerErrors` BEFORE any
    provider call; a bad media file or a bad model reply comes back as a typed status."""
    if not math.isfinite(max_cost_usd):
        raise ReviewRefused("the spend cap must be a finite number of dollars")
    gate()
    wins = list(windows)
    duration, width, _ = probe_fn(video)
    sha = file_sha256(video) if video.is_file() else ""
    tx = transcript_hash(transcript)
    if why := unreadable_reason(video, lambda _p: (duration, width, 0)):
        return _unreadable(content_id("rv", {"src": sha, "bad": pointer_text, "tx": tx}),
                           source, sha, why, tx)
    parse = parse_pointers(pointer_text, duration)
    if parse.errors:
        raise PointerErrors(parse)
    rid = review_id(sha, parse, tx, wins)
    stored = load_review(paths, rid)
    if stored is not None and stored.status == "ok" and not refresh:
        return stored
    redactor = Redactor(secrets)
    plan = plan_frames(duration, parse)
    hidden = [(w.start_s, w.end_s) for w in wins]
    sendable = [t for t in plan.times if not in_any(t, hidden)]
    with review_scratch(paths.review_work_dir(rid)) as work:   # nothing outlives the calls (F1)
        try:
            frames = frames_fn(video, work, wins)
        except RedactionError as exc:
            raise ReviewRefused(f"redaction check failed: {exc}") from exc
        shown_tx = visible_transcript(transcript, wins)   # speech inside a window never leaves
        prompt_for = _prompter(source.id, duration, parse, shown_tx, redactor, secrets)
        batches = order_batches(sendable, plan)
        for times in batches:
            prompt_for(times)  # secret gate for EVERY prompt before the first call (TV7, C5)
        run = _analyse(batches=batches, frames=frames, provider=provider,
                       prompt_for=prompt_for, rid=rid, max_cost_usd=max_cost_usd, cost_of=cost_of)
    review = _assemble(rid, source, duration, sha, tx, parse, wins, plan.times, run, transcript,
                       redactor, known_sources or {source.id}, cost_of(provider))
    review = _merge_human_status(review, stored)
    write_json(paths.review_path(rid), review)
    logger.info("video review %s status=%s calls=%d", rid, review.status, run.calls)
    return review


def _assemble(rid: str, source: Source, duration: float, sha: str, tx: str, parse: PointerParse,
              wins: list[RedactionWindow], planned: list[float], run: _Analysis,
              transcript: Transcript | None, redactor: Redactor, known: set[str],
              cost: float) -> VideoReview:
    state = narration_state(transcript)
    spans = spans_from_plan(duration, planned, run.shown,
                            windows=[(w.start_s, w.end_s) for w in wins])
    base = {"id": rid, "source_id": source.id, "duration_s": duration, "source_sha256": sha,
            "transcript_hash": tx, "pointers": parse.parsed, "redaction_windows": wins,
            "frame_times": run.shown, "analysed": spans.analysed,
            "not_reviewed": spans.not_reviewed, "calls": run.calls, "cost_usd": cost,
            "narration_state": state, "narration_note": NARRATION_NOTES[state],
            "coverage_note": _coverage_note(spans.not_reviewed, wins)}
    if not run.replies:
        base.update(status="failed", reason=run.failure or run.stopped or "no frames were analysed")
        return _finish(base, redactor)
    items, overflow, rejected = build_items(
        [i for r in run.replies for i in r.items], review_id=rid, duration_s=duration,
        known_sources=known, transcript=visible_transcript(transcript, wins),
        pointer_lines={p.line_no for p in parse.parsed}, scrub=redactor.scrub)
    reason = run.failure or run.stopped
    base.update(status="partial" if reason else "ok", reason=reason,
                summary=" ".join(r.summary.strip() for r in run.replies), items=items,
                overflow=overflow, rejected=rejected, count_note=count_note(len(items)))
    return _finish(base, redactor)


def _finish(fields: dict[str, object], redactor: Redactor) -> VideoReview:
    """Validate, then scrub every string once more (TV8): nothing secret reaches disk."""
    review = VideoReview.model_validate(fields)
    return VideoReview.model_validate(redactor.scrub_obj(review.model_dump(mode="json")))
