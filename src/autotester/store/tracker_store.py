"""Where a project's tracker binding lives: one file per project, never shared (TB14).

Its one job is load and save of `TrackerBinding` at `ProjectPaths.tracker_file`. A file whose
`project` is not the slug it was loaded for is refused, so project A's binding is never read as
project B's even if a file is copied across.
"""

from __future__ import annotations

from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.tracker_binding import TrackerBinding
from autotester.store.filestore import read_json, write_json


class WrongProject(ValueError):
    """The stored binding belongs to another project."""


def load_binding(slug: str, root: Path | None = None) -> TrackerBinding | None:
    binding = read_json(ProjectPaths(slug, root).tracker_file, TrackerBinding)
    if binding is not None and binding.project != slug:
        raise WrongProject(f"{slug!r}: the stored binding is for {binding.project!r}")
    return binding


def save_binding(binding: TrackerBinding, root: Path | None = None) -> None:
    path = ProjectPaths(binding.project, root).tracker_file
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, binding)
