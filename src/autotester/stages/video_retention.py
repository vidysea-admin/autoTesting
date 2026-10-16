"""T-191/AT-587 V5: keep at most the N most recent kept videos, project-wide.

`run_and_grade_case`/`_resilient` (`run_case_pipeline.py::_finalize_video`)
already decide whether ONE case's video survives its own verdict. This is
the second, separate prune: across every run a project has, at most `keep`
videos stay on disk in total, chosen deterministically by `(run_id, case
order within that run)` -- never filesystem `mtime` (two videos written in
the same second are indistinguishable by mtime; `run_id` is a ULID and
already sorts lexicographically by creation time, `core/ids.py::run_id`).

Called once per completed run (`ui/routes_runs.py::trigger_run`), not per
case -- retention is a project-wide property, unlike the per-case prune.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from autotester.schema.enums import EvidenceKind
from autotester.store.project_store import ProjectStore

_LOG = logging.getLogger(__name__)

DEFAULT_KEEP = 20
"""The gate answer's own number (qa/gates/meeting-run-video-scope.md,
D-048) -- not a knob this unit may retune."""


@dataclass(frozen=True)
class _VideoRef:
    run_id: str
    case_order: int
    case_id: str
    rel_path: str


def _ordering_key(ref: _VideoRef) -> tuple[str, int, str]:
    """`run_id` first (ULID -> chronological), then position within that
    run's own `Run.case_ids` (never mtime), then `case_id` as a final,
    stable tiebreak."""
    return (ref.run_id, ref.case_order, ref.case_id)


def _collect(store: ProjectStore) -> list[_VideoRef]:
    refs: list[_VideoRef] = []
    runs_dir = store.paths.runs_dir
    if not runs_dir.exists():
        return refs
    for run_path in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        run_id = run_path.name
        run = store.load_run(run_id)
        order = {cid: i for i, cid in enumerate(run.case_ids)} if run is not None else {}
        for result in store.load_results(run_id):
            case_order = order.get(result.case_id, len(order))
            for item in result.evidence:
                if item.kind is EvidenceKind.VIDEO:
                    refs.append(_VideoRef(run_id, case_order, result.case_id, item.path))
    return refs


def prune_old_videos(store: ProjectStore, keep: int = DEFAULT_KEEP) -> list[str]:
    """Delete every kept video beyond the most recent `keep`, and drop its
    `Evidence` row from the owning `RawResult` so the report never links a
    file that no longer exists. Returns the run-relative paths deleted.
    Idempotent: a second call with nothing new to prune deletes nothing."""
    refs = sorted(_collect(store), key=_ordering_key)
    if len(refs) <= keep:
        return []
    to_drop = refs[:-keep] if keep > 0 else refs
    drop_by_run: dict[str, set[str]] = {}
    for ref in to_drop:
        drop_by_run.setdefault(ref.run_id, set()).add(ref.rel_path)

    deleted: list[str] = []
    for run_id, rel_paths in drop_by_run.items():
        for result in store.load_results(run_id):
            kept_evidence = []
            changed = False
            for item in result.evidence:
                if item.kind is EvidenceKind.VIDEO and item.path in rel_paths:
                    (store.paths.run_dir(run_id) / item.path).unlink(missing_ok=True)
                    deleted.append(item.path)
                    changed = True
                    continue
                kept_evidence.append(item)
            if changed:
                result.evidence = kept_evidence
                store.save_result(run_id, result)
    return deleted


def prune_old_videos_safely(store: ProjectStore, keep: int = DEFAULT_KEEP) -> list[str]:
    """AT-735: housekeeping must never fail a saved run. Any error is logged and the
    prune is skipped (nothing deleted is the safe side); callers run it AFTER the O5 ask."""
    try:
        return prune_old_videos(store, keep)
    except Exception:  # fail safe: skip the prune, keep the run
        _LOG.warning("video prune skipped after error", exc_info=True)
        return []
