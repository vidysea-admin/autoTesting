"""Find the stored reviews of one recording (T-197 TV10): newest first, read-only.

One job: list `VideoReview` artifacts under the project's review store for a source id, so the
video page can show the latest one. Writing stays in `stages.video_review.run_review`.
"""

from __future__ import annotations

from autotester.core.paths import ProjectPaths
from autotester.schema.video_review import VideoReview
from autotester.store.filestore import read_json


def stored_reviews(paths: ProjectPaths, source_id: str) -> list[VideoReview]:
    folder = paths.review_path("x").parent
    if not folder.is_dir():
        return []
    files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    found = (read_json(f, VideoReview) for f in files)
    return [r for r in found if r is not None and r.source_id == source_id]
