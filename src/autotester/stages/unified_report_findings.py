"""The multi-role findings a run recorded, loaded for the unified report (AT-1038, MP8).

One job: `load_run_findings` reads `<run_dir>/multi_role_findings/*.json` (where
`cross_role_runner.run_scenario(record=True)` saves them through `leak_evidence.write_finding`)
and returns them scrubbed of every declared secret, in finding-id order. A run with no such
directory has no findings. A file that cannot be read raises, so the caller maps it to
`ReportUnreadable` -- a corrupt finding must never read as a clean report.
"""

from __future__ import annotations

from autotester.core.redact import Redactor
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages.leak_evidence import FINDINGS_DIR
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore


def load_run_findings(store: ProjectStore, run_id: str,
                      redactor: Redactor) -> list[MultiRoleFinding]:
    """Every finding recorded for `run_id`, scrubbed; raises on an unreadable file."""
    folder = store.paths.run_dir(run_id) / FINDINGS_DIR
    if not folder.is_dir():
        return []
    found: list[MultiRoleFinding] = []
    for path in sorted(folder.glob("*.json")):
        finding = read_json(path, MultiRoleFinding)
        if finding is not None:
            found.append(MultiRoleFinding.model_validate(
                redactor.scrub_obj(finding.model_dump(mode="json"))))
    return found
