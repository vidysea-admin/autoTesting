"""Serves a kept run video (T-191 evidence) by its evidence-relative path --
the one job this module has (ISS-t191-run-video-2). Before this route
existed, a FAIL/INCONCLUSIVE case's video was recorded and retained but no
verified path reached it: `download_report_html` writes its export to an
OS-temp path so the relative `href` `report_export.py::_video_link_html`
emits never resolves there, and `ui/routes_report.py::run_view`'s
`_step_flow` renders `EvidenceKind.SCREENSHOT` only. This is the actual
working path; `run_view` links to it (`ui/routes_report.py::_video_section`).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from autotester.stages.report_export import valid_runs_newest_first
from autotester.store.run_store import local_blob
from autotester.ui.helpers import _load_project_or_404, _require_safe_id

router = APIRouter()


def _safe_video_path(run_dir: Path, video_path: str) -> Path | None:
    """Resolve an `Evidence.path`-shaped identifier against its run
    directory and refuse anything that would land outside it. `video_path`
    arrives verbatim from the URL -- an attacker-controlled string -- so a
    `..` segment, an absolute or drive-rooted path, a URL-decoded traversal,
    or a symlink planted under `run_dir` must all fail closed here, never
    resolve to a file outside `run_dir`. `Path.resolve()` both normalizes
    `..`/`.` segments and follows any symlink along the way, so containment
    is decided by one `is_relative_to` check against the resolved root --
    same shape `report_export.png_base64` already uses for screenshots.
    Serves only `.webm` (the one container this feature produces), never a
    generic serve-any-file-under-run_dir route.

    A leading slash/backslash or an embedded `:` is rejected by a plain
    string check BEFORE any `Path.resolve()` call touches `video_path`
    (senior-software-engineer review, this cycle): a UNC-shaped value such
    as `\\\\host\\share\\x.webm` joined onto a Windows `Path` and resolved
    makes the OS attempt a real SMB connection to `host` -- a blocking
    network round-trip (measured ~21s against an unreachable host) that a
    later `is_relative_to` containment check is too late to prevent. The
    same check also covers POSIX-absolute (`/etc/passwd`) and drive-rooted
    (`C:\\Windows\\...`) values, none of which a relative evidence path
    would ever legitimately contain.
    """
    if not video_path or video_path[0] in "\\/" or ":" in video_path:
        return None
    trusted_root = run_dir.resolve()  # the file may live only in the blob store
    try:
        candidate = (run_dir / video_path).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(trusted_root):
        return None
    if candidate.suffix.lower() != ".webm":
        return None
    candidate = local_blob(candidate)  # M24: a verified cache copy when the local file is gone
    return candidate if candidate.is_file() else None


@router.get("/projects/{slug}/runs/{run_id}/videos/{video_path:path}")
def serve_run_video(slug: str, run_id: str, video_path: str) -> FileResponse:
    store, _project = _load_project_or_404(slug)
    _require_safe_id(run_id, "run_id")
    if run_id not in {run.id for run in valid_runs_newest_first(store)}:
        raise HTTPException(404, "no such run")
    candidate = _safe_video_path(store.paths.run_dir(run_id), video_path)
    if candidate is None:
        raise HTTPException(404, "video not found")
    return FileResponse(candidate, media_type="video/webm")
