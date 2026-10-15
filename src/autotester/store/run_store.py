"""Persistence for the advisory UX track: personas and one run's `UXReport` (T-190, PU1/PU2).

Split out because `project_store.py` sits at the 300-line cap (C2); `ProjectStore` inherits
`RunStoreMixin`, so callers still say `store.save_ux_report(...)`. Not a second store (C3).
The UX report lives at `runs/<run_id>/ux_report.json` -- beside, never inside, a case's result or
verdict file -- and `RUN_AUX_FILES` is how `ProjectStore.load_results` knows to skip it.
"""

from __future__ import annotations

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.release import FlowPlan, ReleaseRecord, ReleaseScope
from autotester.schema.user_persona import UserPersona
from autotester.schema.ux_report import UXReport
from autotester.store.filestore import read_json, read_jsonl, upsert_jsonl, write_json

RUN_AUX_FILES = frozenset({
    "run.json", "ux_report.json", "state.json", "checkpoint.json", "scope.json", "release.json",
    "ingest.flowspec.json", "discover.flowspec.json",  # T-169: parked proposals
    "teaching-inputs.json", "teaching.json",  # Mixed teaching evidence and proposal
})
"""Non-result JSON files that sit in a run dir. `load_results` skips exactly these; any other
unreadable JSON there still fails loudly, as before."""


class RunStoreMixin:
    """Requires `self.paths: ProjectPaths` from `ProjectStore.__init__` -- mixed in, never alone."""

    paths: ProjectPaths

    # -- advisory personas (one jsonl row per persona, id-keyed) ---------------
    def save_user_persona(self, persona: UserPersona, secrets: SecretStore | None = None) -> None:
        """Upsert one persona. With `secrets`, the whole row is guarded first (C5): a raw
        credential value in any persona field raises `ValueError` and nothing is written."""
        if persona.project != self.paths.slug:
            raise ValueError(f"persona '{persona.id}' belongs to '{persona.project}'")
        if secrets is not None:
            secrets.guard_prompt(persona.model_dump_json())
        upsert_jsonl(self.paths.user_personas, persona, UserPersona)

    def list_user_personas(self) -> list[UserPersona]:
        return read_jsonl(self.paths.user_personas, UserPersona)

    def get_user_persona(self, persona_id: str) -> UserPersona | None:
        return next((p for p in self.list_user_personas() if p.id == persona_id), None)

    # -- the advisory report (one file per run) --------------------------------
    def save_ux_report(self, report: UXReport) -> None:
        write_json(self.paths.run_ux_report(report.run_id), report)

    def load_ux_report(self, run_id: str) -> UXReport | None:
        """`None` only when the run never had a UX pass. A file that exists but does not
        validate raises `ValueError` naming the path -- never read as "no findings"."""
        return read_json(self.paths.run_ux_report(run_id), UXReport)

    # -- release regression: per-flow plans, a frozen scope, one durable record (T-167) --------
    def save_flow_plan(self, plan: FlowPlan) -> None:
        """Upsert one flow's persisted validation plan (a flow has exactly one)."""
        if plan.project != self.paths.slug:
            raise ValueError(f"flow plan '{plan.flow_id}' belongs to '{plan.project}'")
        upsert_jsonl(self.paths.flow_plans, plan, FlowPlan, key="flow_id")

    def list_flow_plans(self) -> list[FlowPlan]:
        return read_jsonl(self.paths.flow_plans, FlowPlan)

    def save_release_scope(self, scope: ReleaseScope) -> None:
        """Write the scope once; a different scope for the same run is refused (frozen)."""
        previous = self.load_release_scope(scope.run_id)
        if previous is not None and previous.fingerprint != scope.fingerprint:
            raise ValueError("release scope is frozen for this run")
        if previous is None:
            write_json(self.paths.run_release_scope(scope.run_id), scope)

    def load_release_scope(self, run_id: str) -> ReleaseScope | None:
        return read_json(self.paths.run_release_scope(run_id), ReleaseScope)

    def save_release_record(self, record: ReleaseRecord) -> None:
        """The release's ONE record + issues log; its scope must be the frozen one."""
        frozen = self.load_release_scope(record.run_id)
        if frozen is None or frozen.fingerprint != record.scope.fingerprint:
            raise ValueError("release record must match the persisted frozen scope")
        write_json(self.paths.run_release_record(record.run_id), record)

    def load_release_record(self, run_id: str) -> ReleaseRecord | None:
        return read_json(self.paths.run_release_record(run_id), ReleaseRecord)

    def list_release_records(self) -> list[ReleaseRecord]:
        """Every release of this project, oldest first (ties broken by run id)."""
        if not self.paths.runs_dir.exists():
            return []
        found = [self.load_release_record(d.name) for d in self.paths.runs_dir.iterdir()
                 if d.is_dir()]
        return sorted((r for r in found if r is not None),
                      key=lambda r: (r.scope.created_at, r.run_id))
