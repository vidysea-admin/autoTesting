"""Find the stored reviews of one recording (T-197 TV10): newest first, read-only.

One job: list `VideoReview` artifacts under the project's review store for a source id, so the
video page can show the latest one. Writing stays in `stages.video_review.run_review`.
"""

from __future__ import annotations

from autotester.core.paths import ProjectPaths
from autotester.schema.video_review import VideoReview
from autotester.store.filestore import list_children, mtime_path, read_json


def stored_reviews(paths: ProjectPaths, source_id: str) -> list[VideoReview]:
    folder = paths.review_path("x").parent
    files = sorted((folder / n for n in list_children(folder, suffix=".json")),
                   key=lambda p: mtime_path(p) or 0.0, reverse=True)
    found = (read_json(f, VideoReview) for f in files)
    return [r for r in found if r is not None and r.source_id == source_id]
