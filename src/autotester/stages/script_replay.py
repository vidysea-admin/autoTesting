"""SCRIPT_REPLAY: record a working live run's locators as a `Script`, then replay it for free.

Contract: qa/contracts/script-replay.md SR1-SR5 (D-041, T-176). A case that ran to completion
leaves a versioned `Script` (`projects/<slug>/scripts/<case_id>.v<N>.json`, named by
`Case.script_ref`) holding the semantic locator each step used. The next run of an unchanged case
replays it: `run_case` with the recorded locators swapped in, and no provider anywhere in this
module's signature -- the executor observes, it never grades (C7).

Fail closed, in both directions:
- a script whose inputs changed (case steps, FlowSpec version, test-id priority) is NOT replayed;
  the run says why, runs live, and records a NEW version -- the stale file stays as it was;
- a replay that cannot find its target is `ERRORED` naming the step, and the stored script is
  never rewritten, regenerated or repaired by running it (repair is T-177's explicit act).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from autotester.browser.locator_derive import Derived, derive
from autotester.browser.session import BrowserSession
from autotester.core.ids import content_hash
from autotester.schema.base import Provenance
from autotester.schema.case import Case, Script, ScriptInputs, ScriptStep
from autotester.schema.enums import Action, EvidenceKind, Outcome
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult
from autotester.stages.execute import run_case
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore

Executor = Callable[[Case, BrowserSession], RawResult]
GENERATED_BY = "stages.script_replay.record"
LOCATOR_ACTIONS = frozenset({Action.CLICK, Action.FILL, Action.SELECT, Action.UPLOAD,
                             Action.HOVER, Action.WAIT, Action.PRESS_KEY})
_persist_lock = threading.Lock()  # T-173 runs cases in threads that share one store


@dataclass
class ScriptedRun:
    """A run through the script path. `mode` is `replay` or `record`; `reason` is why a
    stored script was refused (stale / missing), None when there was nothing to refuse."""

    result: RawResult
    mode: str
    reason: str | None = None
    script: Script | None = None


@dataclass
class ScriptRecorder:
    """Attached to a session during a live run: derives each locator step's best locator."""

    test_id_attributes: list[str]
    derived: dict[int, tuple[str, Derived]] = field(default_factory=dict)

    def capture(self, session: BrowserSession, step: Step) -> None:
        if step.action in LOCATOR_ACTIONS and step.target:
            self.derived[step.order] = (
                step.target, derive(session.page, step.target, self.test_id_attributes))


def current_inputs(case: Case, store: ProjectStore, project: Project) -> ScriptInputs:
    flowspec = store.load_flowspec()
    steps = [s.model_dump(mode="json") for s in sorted(case.steps, key=lambda s: s.order)]
    return ScriptInputs(
        steps_hash=content_hash(steps),
        flowspec_version=flowspec.version if flowspec else None,
        test_id_attributes=list(project.test_id_attributes))


def _ref_of(case: Case, store: ProjectStore) -> str | None:
    if case.script_ref:
        return case.script_ref
    stored = store.get_case(case.id)
    return stored.script_ref if stored else None


def _read(ref: str, store: ProjectStore) -> Script | None:
    return read_json(store.paths.scripts_dir / f"{ref}.json", Script)


def load_script(
    case: Case, store: ProjectStore, project: Project
) -> tuple[Script | None, str | None]:
    """`(script, None)` when `case` has a script whose inputs all still hold; `(None, why)` when
    it has one that must not be trusted; `(None, None)` when it has none (SR1, SR2)."""
    ref = _ref_of(case, store)
    if ref is None:
        return None, None
    script = _read(ref, store)
    if script is None or script.inputs is None:
        return None, f"script {ref} is missing or carries no input hash"
    changed = script.inputs.differences(current_inputs(case, store, project))
    if changed:
        return None, "; ".join(changed)
    return script, None


def _scripted_case(case: Case, script: Script) -> Case:
    locators = {s.order: s.locator for s in script.steps}
    steps = [s.model_copy(update={"target": locators[s.order]}) if s.order in locators else s
             for s in case.steps]
    return case.model_copy(update={"steps": steps})


def _brittle_evidence(steps: list[ScriptStep]) -> list[Evidence]:
    return [Evidence(
        kind=EvidenceKind.DOM, step_order=s.order,
        path=f"brittle locator step {s.order}: css {s.source_target!r} has no role, label "
             "or declared test-id") for s in steps if s.brittle]


def _persist(case: Case, recorder: ScriptRecorder, store: ProjectStore, project: Project,
             previous: Script | None) -> Script | None:
    """Write the next script version and point the stored case at it. Only a case that is on
    file can be pointed at; anything else records nothing rather than an orphan."""
    with _persist_lock:
        if store.get_case(case.id) is None or not recorder.derived:
            return None
        version = previous.version + 1 if previous else 1
        ref = f"{case.id}.v{version}"
        file = store.paths.scripts_dir / f"{ref}.json"
        script = Script(
            case_id=case.id, path=file.relative_to(store.paths.root).as_posix(),
            generated_by=GENERATED_BY, version=version,
            inputs=current_inputs(case, store, project),
            steps=[ScriptStep(order=order, locator=d.locator, strategy=d.strategy,
                              brittle=d.brittle, source_target=source)
                   for order, (source, d) in sorted(recorder.derived.items())],
            provenance=Provenance(produced_by=GENERATED_BY, inputs=[case.id]))
        write_json(file, script)
        stored = store.get_case(case.id)
        if stored is not None:
            store.update_case(stored.model_copy(update={"script_ref": ref}))
        return script


def _replay(case: Case, script: Script, session: BrowserSession,
            execute: Executor) -> ScriptedRun:
    session.replaying = True
    try:
        result = execute(_scripted_case(case, script), session)
    finally:
        session.replaying = False
    result.used_script = True
    result.evidence = [
        Evidence(kind=EvidenceKind.DOM, path=f"replay: script {script.case_id}.v{script.version}"
                                              " (stored locators, no provider call)"),
        *result.evidence, *_brittle_evidence(script.steps)]
    return ScriptedRun(result, "replay", script=script)


def _record(case: Case, session: BrowserSession, store: ProjectStore,
            reason: str | None, execute: Executor) -> ScriptedRun:
    recorder = ScriptRecorder(list(session.project.test_id_attributes))
    session.recorder = recorder
    try:
        result = execute(case, session)
    finally:
        session.recorder = None
    script = None
    if result.outcome is Outcome.COMPLETED:
        ref = _ref_of(case, store)
        try:
            script = _persist(case, recorder, store, session.project,
                              _read(ref, store) if ref else None)
        except (OSError, ValueError) as exc:  # a good run is never failed by its recording
            lost = f"script not recorded: {type(exc).__name__}: {exc}"
            result.evidence.insert(0, Evidence(kind=EvidenceKind.DOM, path=lost))
    notes = []
    if reason:
        tail = f"; ran live, recorded v{script.version}" if script else "; ran live"
        notes.append(Evidence(kind=EvidenceKind.DOM, path=f"script stale: {reason}{tail}"))
    if script:
        notes.extend(_brittle_evidence(script.steps))
    result.evidence = [*notes, *result.evidence]
    return ScriptedRun(result, "record", reason, script)


def run_scripted(case: Case, session: BrowserSession, store: ProjectStore,
                 execute: Executor = run_case) -> ScriptedRun:
    """Replay `case`'s stored script when it is still valid; otherwise run it live and record
    one. Never calls a provider (there is none to call) and never edits a stored script.
    `execute` is the stage that actually runs steps (`stages/execute.py::run_case`); the
    pipeline passes its own reference so its existing seam stays the one place to substitute."""
    script, reason = load_script(case, store, session.project)
    if script is not None:
        return _replay(case, script, session, execute)
    return _record(case, session, store, reason, execute)
