"""Drive intake: one pasted link or id becomes registered sources, or an honest typed failure.

Contract: team-intake.md TI7 (file, folder and zip ids; verify size and md5; non-videos are
listed, never downloaded; a Drive zip goes through the zip rules), TI9 (the shared upload
limit), TI11 (who and from where), hosting.md HO33. `intake_drive` always returns an
`IntakeReport` in the same shape a zip intake does, so the CLI and the page show one table.

Nothing a Drive file calls itself becomes a path: the stored path is built by `commit_video`
from the source id, the label is the scrubbed name, and the suffix comes from the allowlist.
A download lives in a private folder that is removed on every exit; a refused or failed fetch
leaves no row and no file.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autotester.core.ids import ulid
from autotester.core.paths import work_dir
from autotester.schema.base import utc_now
from autotester.schema.intake import (
    DriveItem,
    DriveOrigin,
    DriveRef,
    IntakeOutcome,
    IntakeReport,
    IntakeStatus,
    MemberResult,
    ZipLimits,
)
from autotester.sources.drive_errors import DriveError
from autotester.sources.drive_verify import DriveFetcher, DriveVerifyError, fetch_and_verify
from autotester.sources.gws_drive import GwsDrive, item_kind
from autotester.sources.intake_commit import IntakeBusy, commit_video, intake_session
from autotester.sources.zip_intake import expand_zip, overall_status
from autotester.stages.ingest import NotARecording, require_recording_suffix
from autotester.store.filestore_paths import scratch_children, scratch_mtime, scratch_rmtree
from autotester.store.project_store import ProjectStore

STALE_FETCH_S = 24 * 3600
_MIME_SUFFIX = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
                "video/x-matroska": ".mkv", "video/x-msvideo": ".avi"}
"""Only used when Drive's file name has no recording suffix; every value is re-checked against
the one allowlist (`require_recording_suffix`) before it is used."""
_F, _S = IntakeOutcome.FAILED, IntakeOutcome.SKIPPED


def default_drive(store: ProjectStore) -> GwsDrive:
    """The real seam: the `gws` CLI login, downloading under this project's working area."""
    return GwsDrive(None, work_dir(store.paths.root) / "gws" / store.paths.slug)


def _label(item: DriveItem, scrub: Callable[[str], str]) -> str:
    base = item.name.replace("\\", "/").rsplit("/", 1)[-1] or item.id
    return scrub(base)[:200]


def _suffix(item: DriveItem) -> str:
    base = item.name.replace("\\", "/").rsplit("/", 1)[-1]
    try:
        return require_recording_suffix(base)
    except NotARecording:
        suffix = _MIME_SUFFIX.get(item.mime_type)
        if suffix is None:
            raise
        return require_recording_suffix(f"recording{suffix}")


def _report(ref: DriveRef, rows: list[MemberResult], notes: list[str]) -> IntakeReport:
    return IntakeReport(archive=f"drive:{ref.id}", status=overall_status(rows), members=rows,
                        notes=notes)


def _refusal(ref: DriveRef, member: str, reason: str) -> IntakeReport:
    row = MemberResult(member=member, outcome=_F, reason=reason)
    return IntakeReport(archive=f"drive:{ref.id}", status=IntakeStatus.FAILED, members=[row])


def _sweep_stale(*roots: Path) -> None:
    """Remove fetch folders a killed run left behind (older than a day, so never a live one)."""
    for root in roots:
        for folder in scratch_children(root):
            stamp = scratch_mtime(folder)
            if stamp is not None and time.time() - stamp > STALE_FETCH_S:
                scratch_rmtree(folder)


class _Intake:
    """One Drive intake into one project: the shared inputs, so each step takes one argument."""

    def __init__(self, store, drive, uploaded_by, scrub, now, limits):
        self.store, self.drive, self.uploaded_by = store, drive, uploaded_by
        self.scrub, self.now, self.limits = scrub, now, limits
        self.fetch_root = work_dir(store.paths.root) / "drive-fetch" / store.paths.slug
        self.notes: list[str] = []

    def fetch(self, item: DriveItem, folder: Path):
        staged = fetch_and_verify(self.drive, item.id, folder)
        if not staged.verified:
            self.notes.append(f"{_label(item, self.scrub)}: Drive supplied no size or checksum, "
                              "so the download was not verified")
        return staged

    def one_video(self, item: DriveItem) -> MemberResult:
        member = _label(item, self.scrub)
        folder = self.fetch_root / ulid()
        try:
            suffix = _suffix(item)
            staged = self.fetch(item, folder)
            with intake_session(self.store) as _session:
                source, created = commit_video(
                    self.store, staged.path, digest=staged.sha256, suffix=suffix, label=member,
                    origin=DriveOrigin(file_id=item.id), uploaded_by=self.uploaded_by,
                    uploaded_at=self.now())
        except NotARecording:
            return MemberResult(member=member, outcome=_F,
                                reason="that video type is not one AutoTester registers")
        except (DriveError, DriveVerifyError) as exc:
            return MemberResult(member=member, outcome=_F, reason=str(exc))
        except IntakeBusy as exc:
            return MemberResult(member=member, outcome=_F, reason=str(exc))
        except OSError:
            return MemberResult(member=member, outcome=_F,
                                reason="could not be stored (the destination write failed)")
        finally:
            scratch_rmtree(folder)
        if created:
            return MemberResult(member=member, outcome=IntakeOutcome.REGISTERED,
                                source_id=source.id)
        return MemberResult(member=member, outcome=IntakeOutcome.DUPLICATE,
                            duplicate_of=source.id, reason="same bytes are already registered")

    def one_zip(self, item: DriveItem, ref: DriveRef) -> IntakeReport:
        folder = self.fetch_root / ulid()
        try:
            staged = self.fetch(item, folder)
            report = expand_zip(self.store, staged.path, archive_name=_label(item, self.scrub),
                                limits=self.limits, uploaded_by=self.uploaded_by,
                                scrub=self.scrub, now=self.now)
        except (DriveError, DriveVerifyError) as exc:
            return _refusal(ref, _label(item, self.scrub), str(exc))
        finally:
            scratch_rmtree(folder)
        return report.model_copy(update={"notes": [*self.notes, *report.notes]})

    def folder(self, ref: DriveRef) -> IntakeReport:
        items = self.drive.list_folder(ref.id)
        videos = [i for i in items if item_kind(i) == "video"]
        if len(videos) > self.limits.max_videos:
            return _refusal(ref, "(folder)", f"video count {len(videos)} exceeds the limit of "
                                             f"{self.limits.max_videos}")
        if sum(i.size or 0 for i in videos) > self.limits.max_total_bytes:
            return _refusal(ref, "(folder)", "the videos in this folder add up to more than the "
                                             "total size limit")
        rows = [self.one_video(i) if item_kind(i) == "video" else self._skipped(i)
                for i in items]
        if not rows:
            self.notes.append("the folder is empty")
        return _report(ref, rows, self.notes)

    def _skipped(self, item: DriveItem) -> MemberResult:
        kind = item_kind(item)
        why = {"zip": "a zip inside a folder is not opened; paste the zip's own link",
               "folder": "sub-folders are not opened; paste the sub-folder's own link"
               }.get(kind, f"not a recording ({item.mime_type or 'unknown type'}); "
                           "only video files are fetched")
        return MemberResult(member=_label(item, self.scrub), outcome=_S, reason=why)


def intake_drive(store: ProjectStore, ref: DriveRef, drive: DriveFetcher | None = None, *,
                 uploaded_by: str | None = None, scrub: Callable[[str], str] = lambda t: t,
                 now: Callable[[], datetime] = utc_now, limits: ZipLimits | None = None
                 ) -> IntakeReport:
    """Fetch a Drive file, zip or folder into `store`'s project; always returns a report.

    `uploaded_by` is the signed-in member the caller resolved, never a request field."""
    drive = drive or default_drive(store)
    run = _Intake(store, drive, uploaded_by, scrub, now, limits or ZipLimits())
    _sweep_stale(run.fetch_root, work_dir(store.paths.root) / "gws" / store.paths.slug)
    try:
        if ref.kind == "folder":
            return run.folder(ref)
        item = drive.metadata(ref.id)
        kind = item_kind(item)
        if kind == "folder":
            return run.folder(ref)
        if kind == "zip":
            return run.one_zip(item, ref)
        if kind != "video":
            return _refusal(ref, _label(item, scrub), "that Drive file is not a video or a zip; "
                                                       "only recordings are fetched")
        return _report(ref, [run.one_video(item)], run.notes)
    except (DriveError, DriveVerifyError) as exc:
        return _refusal(ref, "(Drive file)", str(exc))
