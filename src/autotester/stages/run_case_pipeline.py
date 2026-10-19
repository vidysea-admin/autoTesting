"""Observe cases and grade their persisted evidence with reusable default rubrics (RP1-RP4)."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from autotester.browser.session import BrowserSession
from autotester.browser.video import MAX_VIDEO_DURATION_S
from autotester.providers.base import Provider
from autotester.schema.base import Provenance
from autotester.schema.case import Case
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Rubric, Verdict
from autotester.stages.agent_actuator import FallbackActuator
from autotester.stages.agent_loop import AgentLoopResult, run_with_fallback
from autotester.stages.case_expectation import expects_error
from autotester.stages.execute import run_case
from autotester.stages.grade import grade
from autotester.stages.script_replay import Executor, ScriptedRun, run_scripted
from autotester.store.project_store import ProjectStore

GENERATOR = "stages.run_case_pipeline.default_rubric"


def claim_of(case: Case) -> str:
    """The single sentence a default rubric grades evidence against."""
    return case.rationale or f"the case '{case.title}' completes as its steps describe"


def _rubric_for_claim(claim: str, case_id: str, rubric_id: str) -> Rubric:
    return Rubric(
        id=rubric_id, case_id=case_id,
        criteria=[Criterion(id="c1", text=(
            f"The product behaved correctly for this case, whose stated purpose is: {claim}. "
            "Evidence of a defect (an error or rejection where success was expected, a wrong "
            "result, a missing element) means this criterion is NOT met, even when the "
            "purpose above is to catch that defect. If you cite this as a failure, "
            "use criterion id 'c1' exactly — do not invent a different id."
        ))],
        no_fire=["exact wording of any error message shown by the product"],
        provenance=Provenance(produced_by=GENERATOR, inputs=[case_id], note=claim),
    )


def default_rubric(case: Case, rubric_id: str) -> Rubric:
    """A plain, honest default: pass if the evidence is consistent with the
    case's own stated rationale. Not a substitute for a hand-tuned rubric
    when one exists — only the fallback so every case is gradeable at all.

    Stamps `provenance.note` with the exact claim it was built from, which is
    what makes `is_stale_default` below possible (AT-059)."""
    rubric = _rubric_for_claim(claim_of(case), case.id, rubric_id)
    return rubric.model_copy(update={"expects_error": expects_error(case)})


def is_stale_default(rubric: Rubric, case: Case) -> bool:
    """True when `rubric` is an auto-generated rubric, still untouched since it
    was generated, whose claim no longer matches the case's current one.

    AT-059: a rubric is persisted at `rub_<case_id>`, but its claim comes from
    `case.rationale`/`title`, which `Case.compute_id()` deliberately excludes —
    so correcting a case's rationale left the OLD claim grading forever, with no
    invalidation. Observed live: a case whose rationale was fixed still FAILed
    against the stale claim, on a screenshot that plainly showed what it asked
    for, and deleting the file by hand was the only recovery.

    Deliberately conservative on both edges, because a grading contract is not
    something to overwrite on a guess:
    - No provenance, or provenance from anything but this generator → treated as
      hand-authored and never touched. That includes rubrics written before this
      stamping existed: they are indistinguishable from hand-written, so they
      keep their claim.
    - Provenance from this generator but the criteria no longer match what it
      would have produced for its own recorded claim → a human edited it since,
      so it is hand-tuned now and is never touched.
    """
    provenance = rubric.provenance
    if provenance is None or provenance.produced_by != GENERATOR:
        return False
    recorded = provenance.note or ""
    if recorded == claim_of(case):
        return False
    untouched = _rubric_for_claim(recorded, rubric.case_id or case.id, rubric.id)
    return rubric.criteria == untouched.criteria and rubric.no_fire == untouched.no_fire


def rubric_for_case(case: Case, store: ProjectStore) -> Rubric:
    """Load `case`'s persisted rubric, or build+persist the lazy default the
    first time one doesn't exist (or the persisted one is a stale default,
    AT-059) — the single rubric-resolution seam both `run_and_grade_case` and
    `grade_errored_result` (AT-568) go through, so there is one place, not
    two, that decides what a case is graded against."""
    rubric_id = case.rubric_ref or f"rub_{case.id}"
    rubric = store.load_rubric(rubric_id)
    if rubric is None or is_stale_default(rubric, case):
        rubric = default_rubric(case, rubric_id)
        store.save_rubric(rubric)
    # T-136: a rubric saved before `expects_error` existed loads False though the case's own
    # outcome is a rejection; the flag is a fact about the case, raised in memory, never lowered.
    return rubric.model_copy(update={"expects_error": True}) if expects_error(case) else rubric


def _finalize_video(result: RawResult, verdict: Verdict, video_rel: str | None,
                     run_dir: Path) -> None:
    """T-191/AT-587 V2/V6/V8, the named prune call site: the ONE function that
    decides whether a just-recorded video survives. `video_rel` is whatever
    `BrowserSession.end_case_video()` returned (already a finished file at
    this point) or `None` when this session had no recording -- both are
    no-ops beyond this call.

    Kept only when the verdict is FAIL/INCONCLUSIVE/BLOCKED (gate answer A:
    never PASS) AND the case finished inside `MAX_VIDEO_DURATION_S` (V6's
    disk safety net -- a runaway case's video is dropped regardless of
    verdict, the same "record, then discard" shape V2 already uses for PASS,
    just gated on duration instead of result). Kept videos are appended to
    `result.evidence` as `EvidenceKind.VIDEO` (V8) -- the same envelope every
    other evidence kind uses, never a new field on `RawResult`."""
    if video_rel is None:
        return
    video_path = run_dir / video_rel
    over_budget = result.duration_s > MAX_VIDEO_DURATION_S
    if verdict.result is Result.PASS or over_budget:
        video_path.unlink(missing_ok=True)
        return
    result.evidence.append(Evidence(kind=EvidenceKind.VIDEO, path=video_rel, masked=True))


def _record_repair(loop: AgentLoopResult, case: Case, store: ProjectStore) -> None:
    """SR5's explicit, recorded act: a live run the agent repaired persists the corrected case
    (content-addressed, so the same repair twice is one row, AL3) and says so as evidence. The
    stored script is not touched here -- the corrected case's new steps hash simply makes the
    next run record a fresh version."""
    if not loop.fixed:
        return
    try:
        store.add_case(loop.case)
        note = f"agent repair: case {case.id} -> {loop.case.id} ({loop.iterations} fix(es))"
    except (OSError, ValueError) as exc:  # a good repair is never failed by its bookkeeping
        note = f"agent repair not persisted: {type(exc).__name__}: {exc}"
    loop.result.evidence.insert(0, Evidence(kind=EvidenceKind.DOM, path=note))


def fallback_executor(
    agent: Provider, actuator: FallbackActuator | None, store: ProjectStore,
) -> Executor:
    """T-177/AF5: the production call site of `run_with_fallback`. An executor for
    `run_scripted` that repairs a broken LIVE run through the agent loop. A replay is never
    repaired by running it (SR5): it reports ERRORED and leaves the stored script alone."""
    def execute(case: Case, session: BrowserSession) -> RawResult:
        if getattr(session, "replaying", False):
            return run_case(case, session)
        loop = run_with_fallback(case, session, agent, actuator=actuator)
        _record_repair(loop, case, store)
        return loop.result
    return execute


def _judging(session: BrowserSession) -> AbstractContextManager[object]:
    """The run budget's judge-time scope for `session` (a no-op when it has no budget):
    model grading is not browser time on the target, so it is accounted separately."""
    budget = getattr(session, "budget", None)
    judging = getattr(budget, "judging", None)
    return judging() if callable(judging) else nullcontext()


def _judgeable(result: RawResult) -> bool:
    """Whether `grade()` would send this result to the judge (it settles the rest by rule)."""
    return result.outcome in (Outcome.COMPLETED, Outcome.ASSERTION_FAILED)


def _unjudged_replay(result: RawResult, run_id: str) -> Verdict:
    return Verdict(
        run_id=run_id, case_id=result.case_id, result=Result.INCONCLUSIVE,
        scoreboard="not judged: replayed stored script, judging was not requested",
        grader_provider="rule", note="replay never grades (C7); re-run with judging for a verdict",
    )


def observe_case(case: Case, session: BrowserSession, store: ProjectStore, *,
                 execute: Executor = run_case) -> tuple[ScriptedRun, str | None]:
    """Observe one scripted case and finish capture without any grading."""
    session.begin_case_video(case.id)
    restarts = _take_session_events(session)
    try:
        scripted = run_scripted(case, session, store, execute)
    finally:
        video_rel = session.end_case_video()
    scripted.result = _with_events(scripted.result, restarts + _take_session_events(session))
    return scripted, video_rel


finalize_case_video = _finalize_video


def run_and_grade_case(
    case: Case, session: BrowserSession, judge: Provider, run_id: str,
    store: ProjectStore | None = None, *, judge_replays: bool = True,
    agent: Provider | None = None, actuator: FallbackActuator | None = None,
) -> tuple[RawResult, Verdict]:
    """Run `case` on `session`, then grade it against its persisted rubric —
    building and saving a `default_rubric` the first time one doesn't exist
    for this `rubric_ref`. The single source of truth for "run one case,"
    so a UI button and a CLI script call exactly the same path.

    T-176/SR1: execution goes through `run_scripted` -- a case with a still-valid stored
    script replays it (`result.used_script`), otherwise it runs live and records one.
    Grading is a separate stage and still happens by default. `judge_replays=False` is the
    zero-provider-call regression mode: a replayed run that finished is returned unjudged
    (INCONCLUSIVE by rule, never a PASS) instead of spending a model call per case.

    T-177: given an `agent`, a broken live run is repaired through `run_with_fallback`
    (`fallback_executor`); with an `actuator` too, a screen the repair loop could not resolve
    gets one bounded, guarded agent attempt. With neither (the default) nothing changes."""
    store = store or ProjectStore(case.project)
    execute = fallback_executor(agent, actuator, store) if agent is not None else run_case
    scripted, video_rel = observe_case(case, session, store, execute=execute)
    result = scripted.result
    rubric = rubric_for_case(case, store)
    if scripted.mode == "replay" and not judge_replays and _judgeable(result):
        verdict = _unjudged_replay(result, run_id)
    else:
        with _judging(session):
            verdict = grade(rubric, result, run_id, judge, run_dir=store.paths.run_dir(run_id),
                            secrets=session.secrets)
    _finalize_video(result, verdict, video_rel, store.paths.run_dir(run_id))
    return result, verdict


def _take_session_events(session: BrowserSession) -> list[Evidence]:
    """AT-888: browser-session restarts `begin_case_video` just performed for THIS case."""
    take = getattr(session, "take_session_events", None)
    return list(take()) if callable(take) else []


def _with_events(result: RawResult, events: list[Evidence]) -> RawResult:
    """Restart events become evidence on the case's result (`run_case` slices evidence after
    `begin_case_video`, so it cannot see them itself)."""
    return result.model_copy(update={"evidence": [*events, *result.evidence]}) if events else result


def run_and_grade_case_resilient(
    case: Case, session: BrowserSession, judge: Provider, run_id: str, store: ProjectStore,
    *, agent: Provider | None = None, actuator: FallbackActuator | None = None,
) -> tuple[RawResult, Verdict]:
    """Like `run_and_grade_case`, but a grader/provider exception that happens
    AFTER `run_case` already produced a real result never discards that
    result (AT-573). Used only by the parallel route (`ui/routes_runs.py::
    _run_cases_in_parallel`); the serial route still calls `run_and_grade_case`
    directly, unchanged.

    Without this, T-173's parallel fan-out (`stages/parallel_run.py::
    run_cases`) catches the propagating exception at `_run_one` and replaces
    the case's outcome with a synthetic `ERRORED` `RawResult` that carries
    NONE of the real result's evidence — a COMPLETED run with real
    screenshots reported as "execution errored", when execution had in fact
    finished; only grading failed. Here, `result` is captured first and
    always returned; any exception raised while resolving the rubric or
    grading is caught, and it produces an `INCONCLUSIVE` verdict naming the
    grader failure instead of propagating."""
    execute = fallback_executor(agent, actuator, store) if agent is not None else run_case
    scripted, video_rel = observe_case(case, session, store, execute=execute)
    result = scripted.result
    try:
        rubric = rubric_for_case(case, store)
        with _judging(session):
            verdict = grade(rubric, result, run_id, judge, run_dir=store.paths.run_dir(run_id),
                            secrets=session.secrets)
    except Exception as exc:  # the grader failed; execution did not (C7: still not a guess)
        verdict = Verdict(
            run_id=run_id, case_id=result.case_id, result=Result.INCONCLUSIVE,
            scoreboard="not judged: the grader failed after execution completed",
            grader_provider="rule", note=f"{type(exc).__name__}: {exc}",
        )
    _finalize_video(result, verdict, video_rel, store.paths.run_dir(run_id))
    return result, verdict


def grade_errored_result(
    case: Case, result: RawResult, judge: Provider, run_id: str, store: ProjectStore,
) -> Verdict:
    """A `Verdict` for a `RawResult` that never reached a `run_and_grade_case`
    call at all (AT-568). T-173's parallel fan-out (`stages/parallel_run.py::
    run_cases`) reports a `session_factory` crash, or any exception raised
    before a caller captured its own verdict, as its own ERRORED `RawResult`
    — with no matching verdict, since `run_and_grade_case` (and the `grade()`
    call inside it) was never reached for that case.

    Always safe to call here: `result.outcome` is `Outcome.ERRORED` in every
    caller of this function, and `grade()`'s own `_outcome_verdict` shortcuts
    ERRORED/BLOCKED_HITL deterministically — before ever building a prompt or
    calling `judge` — so this never risks a second crash grading the first
    one. Goes through the exact same rubric seam (`_rubric_for`) as a normal
    run, so an ERRORED case is still gradeable against its real rubric, not a
    placeholder."""
    rubric = rubric_for_case(case, store)
    return grade(rubric, result, run_id, judge, run_dir=store.paths.run_dir(run_id))
