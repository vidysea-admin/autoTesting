"""ORCHESTRATE: drive the stage pipeline as a resumable learn-or-explore run.

One job — `run_or_resume(project, ctx)` chooses the entry path ONCE (teaching
material -> learn, credentials only -> explore), then runs each not-yet-done
stage in order, persisting a `RunState` checkpoint after every transition so an
interrupted run re-enters the first non-done stage without redoing completed
work. The stages themselves are the existing pure `run(input, ctx) -> artifact`
functions (`stages/orchestrate_runners.py` wraps INGEST/DISCOVER/MODEL); this
module owns only the sequencing, the checkpoint ledger, and the mode choice. It
adds NO new approval mechanism — both paths propose into a DRAFT FlowSpec and
stop at the existing review gate (contract orchestrator.md OR1-OR6, D-036).
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.trace import TraceWriter
from autotester.schema.base import utc_now
from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, Source
from autotester.schema.run_state import RunState, StageCheckpoint, StageName
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore

TEACHING_KINDS = frozenset({
    SourceKind.VIDEO, SourceKind.DOC, SourceKind.TEXT,
    SourceKind.AUDIO, SourceKind.EMAIL, SourceKind.DRIVE,
})
"""Source kinds that count as teaching material (OR1). URL/EVAL/CONDITION/
USE_CASE are configuration and credentials, not something to learn a FlowSpec
from — so a project holding only those bootstraps DISCOVER instead of INGEST."""

LEARN_PIPELINE = (
    StageName.INGEST, StageName.MODEL, StageName.EXPAND,
    StageName.EXECUTE, StageName.GRADE, StageName.REPORT,
)
EXPLORE_PIPELINE = (
    StageName.DISCOVER, StageName.MODEL, StageName.EXPAND,
    StageName.EXECUTE, StageName.GRADE, StageName.REPORT,
)

# A StageRunner does one stage's work: it reads the previous stage's
# `artifact_ref`, runs the existing stage, persists its own typed artifact, and
# returns the new `artifact_ref`. The driver never reaches inside — it only
# threads refs and records status, so each stage reads only the prior artifact
# (OR6). A stage with no registered runner is a STOP point, not a failure: the
# autonomous run wires {INGEST|DISCOVER, MODEL} and halts at the review gate.
StageRunner = Callable[["StageContext", "str | None"], str]


@dataclass
class StageContext:
    """Live dependencies for one run — the store to persist through, the
    `run_id` that keys this lineage's `state.json` (OR5), and the stage runners.

    NOT a schema model: it duplicates no persisted shape, following the
    `ExploreRuntime` convention (`stages/explore.py`). `clock` is injectable so
    a test can assert deterministic checkpoint timestamps.
    """

    store: ProjectStore
    run_id: str
    runners: dict[StageName, StageRunner] = field(default_factory=dict)
    clock: Callable[[], datetime] = utc_now
    trace: TraceWriter | None = None
    """The run's redacted trace (D-041 phase 1). Built automatically from
    `store.paths.run_trace(run_id)` when not given, so every run is traced by
    default and a caller never has to remember to wire it (RT1)."""
    secrets: SecretStore | None = None
    """The project's credential boundary (`browser/secrets.py`), threaded into
    the auto-built `trace`'s redactor exactly like `stages/execute.py:101` /
    `stages/explore.py:230` thread it into their own evidence. AT-561: without
    this, the default `trace` above fell back to an unredacted `Redactor({})`
    and the RT6/C5 gate could never fire on a real run."""

    def __post_init__(self) -> None:
        if self.trace is None:
            if self.secrets is not None:
                redactor = self.secrets.redactor()
            else:
                redactor = None
                warnings.warn(
                    "StageContext for run "
                    f"{self.run_id!r} was built with no `secrets=` (SecretStore) -- its "
                    "auto-built TraceWriter falls back to an unredacted Redactor({}), so "
                    "a real secret value fed into a span here would NOT be masked (AT-561, "
                    "D-041 RT6/C5). Pass `secrets=<project's SecretStore>` for any run that "
                    "might carry real credentials; this is expected only for a fixture/test "
                    "context that genuinely declares none.",
                    RuntimeWarning, stacklevel=2,
                )
            self.trace = TraceWriter(self.store.paths.run_trace(self.run_id), self.run_id,
                                     redactor)


def choose_mode(sources: list[Source]) -> tuple[str, str]:
    """The entry path and the reason for it, decided once (OR1).

    Teaching material present -> `learn` (INGEST); none (credentials only) ->
    `explore` (DISCOVER). Never silently defaulted: the reason is returned so
    `run_or_resume` records it on the RunState for a human to audit later.
    """
    teaching = [s for s in sources if s.kind in TEACHING_KINDS]
    if teaching:
        kinds = ", ".join(sorted({str(s.kind) for s in teaching}))
        return "learn", f"teaching sources present ({kinds}) -> INGEST"
    return "explore", "no teaching sources; credentials bootstrap DISCOVER"


def _state_path(ctx: StageContext) -> Path:
    """`projects/<slug>/runs/<run_id>/state.json` — keyed by run_id so two runs
    never read or overwrite each other's ledger (OR5)."""
    return ctx.store.paths.run_dir(ctx.run_id) / "state.json"


def load_or_create(project: Project, ctx: StageContext) -> RunState:
    """This run's ledger: the persisted `state.json` if `run_id` already has one
    (resume — the mode is NOT re-decided), else a fresh RunState with the chosen
    mode and one `pending` checkpoint per stage of that mode's pipeline."""
    existing = read_json(_state_path(ctx), RunState)
    if existing is not None:
        return existing
    mode, reason = choose_mode(ctx.store.list_sources())
    pipeline = LEARN_PIPELINE if mode == "learn" else EXPLORE_PIPELINE
    now = ctx.clock()
    return RunState(
        run_id=ctx.run_id, project_slug=project.slug, mode=mode, mode_reason=reason,
        stages=[StageCheckpoint(stage=s) for s in pipeline], created=now, updated=now,
    )


def _persist(ctx: StageContext, state: RunState) -> RunState:
    """Write `state.json` atomically, stamping `updated`. Every checkpoint
    transition goes through here, so a crash always leaves a consistent ledger."""
    state = state.model_copy(update={"updated": ctx.clock()})
    write_json(_state_path(ctx), state)
    return state


def _record(ctx: StageContext, state: RunState, index: int,
            checkpoint: StageCheckpoint) -> RunState:
    """Replace the checkpoint at `index` and persist.

    A checkpoint reaching a terminal status (RT3) also gets its stage span
    written here — the single place every checkpoint transition already
    passes through, so a `pending`/`running` checkpoint (never terminal)
    produces no span, matching "a stage that never ran produces no span"."""
    stages = list(state.stages)
    stages[index] = checkpoint
    if checkpoint.status in ("done", "failed", "skipped") and ctx.trace is not None:
        ctx.trace.record_stage(checkpoint)
    return _persist(ctx, state.model_copy(update={"stages": stages}))


def _run_stage(ctx: StageContext, state: RunState, index: int) -> tuple[RunState, bool]:
    """Run one stage: mark it `running`, invoke its runner with the previous
    stage's `artifact_ref`, and record `done`+ref on success or `failed`+error
    on a raise (OR4) — persisting after each transition. Returns whether the
    driver may continue to the next stage."""
    prev = state.stages[index - 1].artifact_ref if index > 0 else None
    runner = ctx.runners[state.stages[index].stage]
    state = _record(ctx, state, index, state.stages[index].model_copy(
        update={"status": "running", "started": ctx.clock(), "error": None}))
    try:
        ref = runner(ctx, prev)
    except Exception as exc:  # OR4: an honest failed checkpoint, never `done`
        failed = state.stages[index].model_copy(update={
            "status": "failed", "error": f"{type(exc).__name__}: {exc}",
            "finished": ctx.clock()})
        return _record(ctx, state, index, failed), False
    done = state.stages[index].model_copy(update={
        "status": "done", "artifact_ref": ref, "error": None, "finished": ctx.clock()})
    return _record(ctx, state, index, done), True


def run_or_resume(project: Project, ctx: StageContext) -> RunState:
    """Run (or resume) the pipeline for `project`, returning its `RunState`.

    Loads or creates the run's ledger, then walks the stages in order:
    - a `done`/`skipped` stage is never re-run, so its artifact is never
      rewritten (OR2 — resume enters at the first non-done stage);
    - a stage with no registered runner is a STOP point left `pending` (the
      autonomous run halts here at the review gate, and a later, more fully
      wired invocation resumes it);
    - the first stage that fails stops the walk, leaving its `failed`
      checkpoint for the next call to re-enter (OR4).
    """
    state = _persist(ctx, load_or_create(project, ctx))
    for index, checkpoint in enumerate(state.stages):
        if checkpoint.status in ("done", "skipped"):
            continue
        if checkpoint.stage not in ctx.runners:
            break
        state, proceed = _run_stage(ctx, state, index)
        if not proceed:
            break
    return state
