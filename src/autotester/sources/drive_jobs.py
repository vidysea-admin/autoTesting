"""Persist one Drive fetch job so the page can poll it and a restart cannot lose its result.

Contract: hosting.md HO33 (a long Drive fetch shows "fetching" and then its result, never a hung
request). A job is one small JSON file under `.work/drive-jobs/<project>/<id>.json`, written
atomically. The id is checked against the ULID shape before it touches a path, so a request can
never name a file outside that folder.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from autotester.core.paths import work_dir
from autotester.schema.base import utc_now
from autotester.schema.intake import DriveJob

JOB_ID = re.compile(r"[0-9A-Z]{26}")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
REPLACE_TRIES = 5
STALE_S = 2 * 3600
"""A job still `queued`/`fetching` this long after its last update lost its worker (a restart)."""


def job_path(root: Path | None, project: str, job_id: str) -> Path | None:
    """The job's file, or None when the project or id is not shaped like ours."""
    if not JOB_ID.fullmatch(job_id) or not SLUG.fullmatch(project):
        return None
    return work_dir(root) / "drive-jobs" / project / f"{job_id}.json"


def save_job(root: Path | None, job: DriveJob) -> None:
    path = job_path(root, job.project, job.id)
    if path is None:
        raise ValueError("not a valid job id")
    job = job.model_copy(update={"updated_at": utc_now()})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(job.model_dump_json(exclude={"report": {"exit_code", "counts"}}),
                    encoding="utf-8")
    for attempt in range(REPLACE_TRIES):  # Windows: the polling page may hold the file briefly
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == REPLACE_TRIES - 1:
                raise
            time.sleep(0.05)


def load_job(root: Path | None, project: str, job_id: str) -> DriveJob | None:
    path = job_path(root, project, job_id)
    if path is None or not path.is_file():
        return None
    try:
        return DriveJob.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def effective_state(job: DriveJob, now: datetime | None = None) -> str:
    """`interrupted` for an unfinished job nobody has touched for `STALE_S`."""
    age_s = ((now or utc_now()) - job.updated_at).total_seconds()
    if job.state in ("queued", "fetching") and age_s > STALE_S:
        return "interrupted"
    return job.state
