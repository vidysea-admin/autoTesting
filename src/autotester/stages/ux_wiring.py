"""Run the advisory UX pass after a run is saved, and never let it touch the run (AT-794).

One job: the non-fatal call site of `ux_advisory.run_ux_advisory` for the run launcher. The
pass reads results and verdicts that are already on disk and writes only `ux_report.json`
(PU2/PU3), so any failure here is logged and swallowed -- the run, its verdicts and the
report that follows are unchanged. Model calls use the run's judge `Provider` (PU5) and the
project's own `ux_policy.max_calls` budget; the prompt redaction gate is inside the stage (PU6).
"""

from __future__ import annotations

import logging

from autotester.providers.base import Provider
from autotester.schema.ux_report import UXReport
from autotester.stages.ux_advisory import run_ux_advisory
from autotester.store.project_store import ProjectStore

log = logging.getLogger(__name__)


def advise_after_run(store: ProjectStore, run_id: str, provider: Provider) -> UXReport | None:
    """The run's `UXReport`, or None when the project is not opted in or the pass failed."""
    try:
        return run_ux_advisory(store, run_id, provider)
    except Exception as exc:  # advisory only (plan decision 5): never fail or flip a run
        log.warning("UX advisory pass failed for %s (%s); the run is unaffected",
                    run_id, type(exc).__name__)
        return None
