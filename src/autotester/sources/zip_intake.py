"""Safe zip expansion: one video source per video member, everything else accounted for.

Contract: team-intake.md TI1-TI6 (R39, R65), TI9 (the per-file cap is the admin upload limit)
and TI11 (origin = the archive name and member path). A zip is untrusted input, so:

* Nothing is extracted with `extractall` / `extract`. The central directory is read first and
  every member is PLANNED (names vetted by `zip_names`, declared sizes and ratio checked)
  before any byte is written; an archive-level violation refuses the whole archive.
* Each member that survives is inflated into a generated name inside the run's staging folder
  (`copy_bounded` re-enforces the per-file and total caps on the bytes actually inflated, so a
  header that lies is caught), hashed, then committed atomically by `intake_commit`.
* No path is built from a member name; the name becomes a scrubbed label and origin only.
* A hostile, corrupt or encrypted member is `failed`, the rest still register, and the overall
  status is `partial` with exit code 2, never `ok`.
"""

from __future__ import annotations

import zipfile
import zlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from autotester.core.upload_limit import human_bytes, read_max_upload_bytes
from autotester.schema.base import utc_now
from autotester.schema.intake import (
    IntakeOutcome,
    IntakeReport,
    IntakeStatus,
    MemberResult,
    ZipLimits,
    ZipOrigin,
)
from autotester.sources.bounded_write import CopyResult, LimitExceeded, copy_bounded, read_chunks
from autotester.sources.intake_commit import LOCK_TIMEOUT_S, commit_video, intake_session
from autotester.sources.zip_names import (
    display_name,
    ensure_inside,
    is_nested_archive_name,
    looks_like_archive,
    special_mode_kind,
    vet_member_name,
)
from autotester.stages.ingest import NotARecording, require_recording_suffix
from autotester.store.project_store import ProjectStore

_F, _S = IntakeOutcome.FAILED, IntakeOutcome.SKIPPED


class _Plan(NamedTuple):
    """One member's decision, made from the central directory alone."""

    info: zipfile.ZipInfo
    shown: str
    suffix: str | None
    outcome: IntakeOutcome | None  # None = extract it
    reason: str | None


class _Ctx(NamedTuple):
    store: ProjectStore
    archive_name: str
    per_file: int
    limits: ZipLimits
    uploaded_by: str | None
    scrub: Callable[[str], str]
    now: Callable[[], datetime]
    lock_timeout_s: float


def _basename(raw: str) -> str:
    return raw.replace("\\", "/").rsplit("/", 1)[-1]


def _classify(info: zipfile.ZipInfo, per_file: int, limits: ZipLimits,
              scrub: Callable[[str], str]) -> _Plan | None:
    """`None` for a directory entry (never listed); otherwise the member's decision."""
    raw = info.orig_filename
    shown = scrub(display_name(raw))

    def plan(outcome, reason, suffix=None):
        return _Plan(info, shown, suffix, outcome, reason)

    why = vet_member_name(raw)
    if why:
        return plan(_F, f"refused: {why}")
    kind = special_mode_kind(info)
    if kind:
        return plan(_F, f"refused: {kind} entries are not allowed")
    if raw.replace("\\", "/").endswith("/"):
        return None
    if is_nested_archive_name(raw):
        return plan(_F, "refused: nested archive (archives inside archives are not opened)")
    try:
        suffix = require_recording_suffix(_basename(raw))
    except NotARecording:
        ext = Path(_basename(raw)).suffix.lower() or "no extension"
        return plan(_S, f"not a recording ({ext}); only video files are registered")
    if info.flag_bits & 0x1:
        return plan(_F, "encrypted member (password-protected zips are not supported)", suffix)
    if info.file_size > per_file:
        return plan(_F, f"{human_bytes(info.file_size)} exceeds the per-file limit of "
                        f"{human_bytes(per_file)}", suffix)
    ratio = info.file_size / max(info.compress_size, 1)
    if info.file_size > limits.ratio_min_bytes and ratio > limits.max_ratio:
        return plan(_F, f"compression ratio {ratio:.0f}:1 exceeds the {limits.max_ratio}:1 limit",
                    suffix)
    return plan(None, None, suffix)


def _archive_refusal(infos: list[zipfile.ZipInfo], plans: list[_Plan],
                     limits: ZipLimits) -> str | None:
    """The archive-level cap this archive breaks, if any (decided before any write)."""
    total = sum(i.file_size for i in infos)
    videos = sum(1 for p in plans if p.suffix is not None)
    if total > limits.max_total_bytes:
        return (f"total uncompressed size {human_bytes(total)} exceeds the limit of "
                f"{human_bytes(limits.max_total_bytes)}")
    if videos > limits.max_videos:
        return f"video count {videos} exceeds the limit of {limits.max_videos}"
    return None


def _failed_report(name: str, reason: str, notes: list[str]) -> IntakeReport:
    row = MemberResult(member="(archive)", outcome=_F, reason=reason)
    return IntakeReport(archive=name, status=IntakeStatus.FAILED, members=[row], notes=notes)


class _NestedByContent(Exception):
    """A video-suffixed member whose first bytes are an archive signature."""


def _inflate(zf: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path, cap: int) -> CopyResult:
    with zf.open(info) as stream:
        head = stream.read(8)
        if looks_like_archive(head):
            raise _NestedByContent
        return copy_bounded(read_chunks(stream, head), dest, cap)


def _fail(plan: _Plan, reason: str) -> MemberResult:
    return MemberResult(member=plan.shown, outcome=_F, reason=reason)


def _store_member(ctx: _Ctx, plan: _Plan, dest: Path, result: CopyResult) -> MemberResult:
    origin = ZipOrigin(archive_name=ctx.archive_name, member_path=plan.shown)
    try:
        source, created = commit_video(
            ctx.store, dest, digest=result.sha256, suffix=plan.suffix, label=plan.shown,
            origin=origin, uploaded_by=ctx.uploaded_by, uploaded_at=ctx.now())
    except OSError:
        return _fail(plan, "could not be stored (the destination write failed)")
    if created:
        return MemberResult(member=plan.shown, outcome=IntakeOutcome.REGISTERED,
                            source_id=source.id)
    return MemberResult(member=plan.shown, outcome=IntakeOutcome.DUPLICATE,
                        duplicate_of=source.id, reason="same bytes are already registered")


def _extract_one(ctx: _Ctx, zf: zipfile.ZipFile, plan: _Plan, staging: Path, index: int,
                 used: int) -> tuple[MemberResult, int]:
    """Inflate one member under both caps, then commit it. Returns the row and bytes inflated."""
    dest = ensure_inside(staging / f"m{index:06d}{plan.suffix}", staging)
    remaining = ctx.limits.max_total_bytes - used
    cap = min(ctx.per_file, remaining)
    try:
        try:
            result = _inflate(zf, plan.info, dest, cap)
        except LimitExceeded:
            total_bound = remaining < ctx.per_file
            what = ("total uncompressed limit of " + human_bytes(ctx.limits.max_total_bytes)
                    if total_bound else "per-file limit of " + human_bytes(ctx.per_file))
            return _fail(plan, f"inflated past the {what}; the member was removed"), 0
        except _NestedByContent:
            return _fail(plan, "refused: nested archive (the bytes are an archive)"), 0
        except (zipfile.BadZipFile, zlib.error, EOFError):
            return _fail(plan, "corrupt member (bad checksum or truncated data)"), 0
        except NotImplementedError:
            return _fail(plan, "unsupported compression method"), 0
        except OSError:
            return _fail(plan, "could not be staged (the write failed)"), 0
        if result.size == 0:
            return _fail(plan, "empty file"), 0
        return _store_member(ctx, plan, dest, result), result.size
    finally:
        dest.unlink(missing_ok=True)


def _run_plans(ctx: _Ctx, zf: zipfile.ZipFile, plans: list[_Plan]) -> list[MemberResult]:
    results: list[MemberResult] = []
    used = 0
    with intake_session(ctx.store, timeout_s=ctx.lock_timeout_s) as (staging, beat):
        for index, plan in enumerate(plans):
            if plan.outcome is not None:
                results.append(MemberResult(member=plan.shown, outcome=plan.outcome,
                                            reason=plan.reason))
                continue
            row, written = _extract_one(ctx, zf, plan, staging, index, used)
            results.append(row)
            used += written
            beat()
    return results


def overall_status(results: list[MemberResult]) -> IntakeStatus:
    if not any(r.outcome is _F for r in results):
        return IntakeStatus.OK
    good = (IntakeOutcome.REGISTERED, IntakeOutcome.DUPLICATE)
    return IntakeStatus.PARTIAL if any(r.outcome in good for r in results) else IntakeStatus.FAILED


def expand_zip(store: ProjectStore, archive: Path, *, archive_name: str | None = None,
               limits: ZipLimits | None = None, max_file_bytes: int | None = None,
               uploaded_by: str | None = None, scrub: Callable[[str], str] = lambda text: text,
               now: Callable[[], datetime] = utc_now,
               lock_timeout_s: float = LOCK_TIMEOUT_S) -> IntakeReport:
    """Expand `archive` into `store`'s project as video sources; always returns a report.

    `max_file_bytes=None` reads the admin upload limit through the shared accessor (TI9);
    a value is for tests and for a caller that already read it. `uploaded_by` comes from the
    caller's authenticated session (T-204), never from a request field. `scrub` is the project's
    `Redactor.scrub`, applied to every name before it is shown or stored."""
    limits = limits or ZipLimits()
    notes: list[str] = []
    if max_file_bytes is None:
        limit = read_max_upload_bytes(store.paths.root)
        max_file_bytes = limit.bytes
        notes.extend([limit.note] if limit.from_default else [])
    name = scrub(display_name(archive_name or archive.name))
    try:
        zf = zipfile.ZipFile(archive)
    except (zipfile.BadZipFile, OSError):
        return _failed_report(name, "not a zip archive (or it cannot be read)", notes)
    with zf:
        infos = zf.infolist()
        if len(infos) > limits.max_entries:
            return _failed_report(name, f"too many entries ({len(infos)}; limit "
                                        f"{limits.max_entries})", notes)
        size = archive.stat().st_size
        if size > limits.max_archive_bytes:
            return _failed_report(name, f"archive size {human_bytes(size)} exceeds the limit of "
                                        f"{human_bytes(limits.max_archive_bytes)}", notes)
        plans = [p for i in infos if (p := _classify(i, max_file_bytes, limits, scrub))]
        refusal = _archive_refusal(infos, plans, limits)
        if refusal:
            return _failed_report(name, refusal, notes)
        ctx = _Ctx(store, name, max_file_bytes, limits, uploaded_by, scrub, now, lock_timeout_s)
        results = _run_plans(ctx, zf, plans)
    if not plans:
        notes.append("the archive has no files")
    return IntakeReport(archive=name, status=overall_status(results), members=results, notes=notes)
