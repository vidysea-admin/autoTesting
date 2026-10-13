"""BUG WIRING: the one door from a finished run to the project's tracked bugs (T-199d).

Its one job is calling `bug_run.process_run` for a run `launch_run` just saved, which is the single
path every graded run takes (UI Run button and queue, team Test press, schedule tick, CLI). It
writes the internal BugStore only (D-090: no sheet client here). `process_run` is idempotent per
run (TB6), so a repeat call changes nothing. A failure is logged with the run id and returned as
None, never swallowed silently and never allowed to lose the run that already exists.
"""

from __future__ import annotations

import logging

from autotester.schema.bug_run import RunReport
from autotester.stages.bug_run import process_run
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore

log = logging.getLogger(__name__)


def record_run_bugs(store: ProjectStore, run_id: str) -> RunReport | None:
    try:
        return process_run(store, BugStore(store.paths.dir), run_id)
    except Exception:  # the run is saved; a bug-loop fault must not turn it into a failed run
        log.exception("bug loop failed for run %s of %s; re-process to retry", run_id,
                      store.paths.slug)
        return None
