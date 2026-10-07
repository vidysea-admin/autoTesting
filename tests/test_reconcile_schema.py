"""Reconcile's schema and ingest half. Contract: qa/contracts/reconcile.md RC1, RC2, RC8, RC14.

Offline: MockProvider only, no network, no real credential (RC13).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from reconcile_fakes import flow, frozen, judge_mock, node, screen, video

from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Screen, SourceRef, Step
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.project import Source, SourceKind
from autotester.stages import reconcile as rc
from autotester.stages.ingest import (
    flow_id,
    flowspec_from_observation,
    ingest_video,
    legacy_flow_id,
)
from autotester.stages.merge_flowspec import merge_flowspec
from autotester.stages.reconcile import reconcile
from autotester.store.filestore import write_json

FIXTURE = Path(__file__).parent / "fixtures" / "reconcile" / "frozen_sample.json"
PRE_UNIT = {  # a FlowSpec as written before this unit: none of the new keys present
    "schema_version": 1, "created_at": "2026-10-01T00:00:00Z", "project": "p", "version": 2,
    "screens": [{"id": "scr_a", "name": "Home", "signals": ["Logo"], "fields": [],
                 "source_ref": {"source_id": "src_1", "t_start": 0.0}}],
    "flows": [{"id": "flow_old", "name": "Login", "entry_screen": "scr_a", "preconditions": [],
               "steps": [{"order": 1, "action": "click", "target": "Login",
                          "expected": {"visible_text": [], "absent_text": [],
                                       "dom_asserts": [], "network": []},
                          "source_ref": {"source_id": "src_1", "t_start": 1.0}}],
               "requires_auth": False}],
    "source_ids": ["src_1"], "conflicts": [], "review": {"status": "approved"},
}


def observation(*, with_evidence: bool = True, step_screen: str | None = "Sign-in") -> (
        VideoObservation):
    said = {"narration": "type your email here", "on_screen_text": "Email"}
    extra = said if with_evidence else {}
    return VideoObservation(
        screens=[ObservedScreen(name="Sign-in", t_start=0.0, url="/login"),
                 ObservedScreen(name="Home", t_start=5.0, url="/home")],
        flows=[ObservedFlow(
            name="Login", entry_screen="Sign-in",
            exit_screen="Home" if with_evidence else None,
            steps=[ObservedStep(order=1, action=Action.FILL, target="Email", value="x",
                                t_start=1.0, screen=step_screen, **extra)])])


def test_rc1_new_fields_default_and_extra_stays_forbidden() -> None:
    step = Step(order=1, action=Action.CLICK, target="x")
    assert (step.screen_id, step.narration, step.on_screen_text) == (None, None, None)
    assert Screen(id="s", name="n").video_only is False
    flow = Flow(id="f", name="n", entry_screen="s")
    assert (flow.kind, flow.ideal_basis, flow.variant_of, flow.diverges_at) == (None,) * 4
    assert ObservedStep(order=1, action=Action.CLICK, target="x", t_start=0).screen is None
    with pytest.raises(ValidationError):
        Step(order=1, action=Action.CLICK, target="x", screen="typo")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Flow(id="f", name="n", entry_screen="s", kind="other")  # type: ignore[arg-type]


def test_rc1_pre_unit_flowspec_loads_and_round_trips_byte_identically(tmp_path: Path) -> None:
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    write_json(first, FlowSpec.model_validate(PRE_UNIT))
    write_json(second, FlowSpec.model_validate_json(first.read_text(encoding="utf-8")))
    assert first.read_bytes() == second.read_bytes()
    saved = json.loads(first.read_text(encoding="utf-8"))
    for key in ("screen_id", "narration", "video_only", "kind", "ideal_basis", "variant_of"):
        assert key not in first.read_text(encoding="utf-8"), key
    assert saved["flows"][0]["id"] == "flow_old"


def test_rc1_step_screen_resolves_through_the_same_name_map_as_entry_screen() -> None:
    spec = flowspec_from_observation(observation(), "src_1", "p")
    step = spec.flows[0].steps[0]
    assert step.screen_id == spec.flows[0].entry_screen
    assert spec.screen(step.screen_id) is not None


def test_rc1_unresolvable_step_screen_keeps_none_and_the_step() -> None:
    spec = flowspec_from_observation(observation(step_screen="No such screen"), "src_1", "p")
    assert len(spec.flows[0].steps) == 1
    assert spec.flows[0].steps[0].screen_id is None


def test_rc1_frozen_sample_steps_resolve_at_least_95_percent() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    specs = [flowspec_from_observation(VideoObservation.model_validate(s["observation"]),
                                       s["source_id"], "fixture") for s in data["sources"]]
    steps = [st for sp in specs for f in sp.flows for st in f.steps]
    resolved = [st for sp in specs for f in sp.flows for st in f.steps
                if st.screen_id and sp.screen(st.screen_id)]
    assert len(resolved) / len(steps) >= 0.95
    assert len(resolved) < len(steps)  # the sample exercises the unresolved path too


def _source(tmp_path: Path) -> Source:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"fake video bytes")
    return Source(project="p", kind=SourceKind.VIDEO, path=str(video))


def test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen(tmp_path: Path) -> None:
    source = _source(tmp_path)
    spec = ingest_video(source, "p", MockProvider(responses={"vision": [observation()]}))
    flow, step = spec.flows[0], spec.flows[0].steps[0]
    assert step.narration == "type your email here"
    assert step.on_screen_text == "Email"
    home = next(s for s in spec.screens if s.name == "Home")
    assert flow.exit_screen == home.id


def test_rc2_absent_evidence_is_none_not_empty_or_invented(tmp_path: Path) -> None:
    obs = observation(with_evidence=False)
    obs.flows[0].steps[0].narration = ""
    spec = ingest_video(_source(tmp_path), "p", MockProvider(responses={"vision": [obs]}))
    step = spec.flows[0].steps[0]
    assert (step.narration, step.on_screen_text, spec.flows[0].exit_screen) == (None, None, None)


def test_rc8_same_named_flows_from_two_recordings_get_two_ids() -> None:
    a = flowspec_from_observation(observation(), "src_a", "p")
    b = flowspec_from_observation(observation(), "src_b", "p")
    assert a.flows[0].id != b.flows[0].id
    assert a.flows[0].id == flow_id("Login", "src_a")
    merged = merge_flowspec(a, b)
    assert len(merged.flows) == 2
    assert merge_flowspec(merged, b) is merged  # idempotent: nothing added the second time


def test_rc8_existing_flow_ids_are_never_rewritten_and_a_reingest_is_recognised() -> None:
    existing = FlowSpec.model_validate(PRE_UNIT)
    assert existing.flows[0].id == "flow_old"
    old = existing.model_copy(update={"flows": [existing.flows[0].model_copy(
        update={"id": legacy_flow_id("Login")})]})
    again = flowspec_from_observation(observation(), "src_1", "p")
    merged = merge_flowspec(old, again)
    assert [f.id for f in merged.flows] == [legacy_flow_id("Login")]
    other = flowspec_from_observation(observation(), "src_2", "p")
    assert len(merge_flowspec(old, other).flows) == 2  # a different recording is new


def test_rc8_flow_source_id_is_its_first_sourced_step() -> None:
    flow = Flow(id="f", name="n", entry_screen="s", steps=[
        Step(order=1, action=Action.CLICK, target="t", source_ref=SourceRef(source_id="src_9"))])
    assert flow.source_id == "src_9"
    assert Flow(id="f", name="n", entry_screen="s").source_id is None


# -- RC8-RC10 at the reconcile level: keep every flow, one kind each, no gate ----------------
def test_rc8_frozen_sample_keeps_every_flow_including_the_same_named_pair() -> None:
    videos, crawl, said = frozen()
    out, report = reconcile(videos, crawl, judge_mock(), transcripts=said)
    assert report.flows_in == report.flows_out == len(out.flows) == 6
    same = [f.id for f in out.flows if f.name == "Sign in"]
    assert len(same) == 2 and len(set(same)) == 2


def test_rc8_an_existing_flow_id_is_byte_identical_after_reconcile() -> None:
    existing = FlowSpec.model_validate(PRE_UNIT)
    videos, crawl, said = frozen()
    out, report = reconcile(videos, crawl, judge_mock(), existing=existing, transcripts=said)
    assert out.flows[0].id == "flow_old" and report.flows_out == 7


def _task_specs() -> list[FlowSpec]:
    shared = [screen("scr_1", "Start", "/start"), screen("scr_2", "Middle", "/middle")]
    return [video("src_a", shared, [flow("Task", "src_a", ["scr_1", "scr_2"], narration="go on")]),
            video("src_b", shared, [flow("Task", "src_b", ["scr_1", "scr_2"])]),
            video("src_c", [screen("scr_3", "Crawl page", "/crawl", ("Save",), source="src_c")],
                  [flow("task ", "src_c", ["scr_3"], narration="this way works too")])]


def test_rc9_the_crawl_path_is_ideal_even_when_a_video_path_is_more_common() -> None:
    out, _ = reconcile(_task_specs(), [node("/crawl", "Crawl page", [("button", "Save")])])
    kinds = {f.source_id: (f.kind, f.ideal_basis) for f in out.flows}
    assert kinds == {"src_c": ("ideal", "crawl"), "src_a": ("variant", "crawl"),
                     "src_b": ("variant", "crawl")}


def test_rc9_without_a_crawl_the_modal_path_is_ideal() -> None:
    out, _ = reconcile(_task_specs(), [])
    kinds = {f.source_id: (f.kind, f.ideal_basis) for f in out.flows}
    assert kinds == {"src_a": ("ideal", "modal"), "src_b": ("narrated", "modal"),
                     "src_c": ("variant", "modal")}


def test_rc9_a_tie_resolves_to_the_earliest_source_every_time() -> None:
    specs = [video("src_b", [screen("scr_9", "B", "/b")], [flow("Tie", "src_b", ["scr_9"])]),
             video("src_a", [screen("scr_8", "A", "/a")], [flow("Tie", "src_a", ["scr_8"])])]
    runs = {tuple((f.source_id, f.kind) for f in reconcile(order, [])[0].flows)
            for order in (specs, specs[::-1], specs, specs[::-1], specs)}
    assert len(runs) == 1
    assert dict(next(iter(runs))) == {"src_a": "ideal", "src_b": "variant"}


def test_rc9_assign_kinds_breaks_a_tie_by_source_whatever_the_input_order() -> None:
    late, early = flow("Tie", "src_b", ["scr_9"]), flow("Tie", "src_a", ["scr_8"])
    for order in ([late, early], [early, late]):
        kinds = {f.source_id: f.kind for f in rc.assign_kinds(order, set())[0]}
        assert kinds == {"src_a": "ideal", "src_b": "variant"}


def test_rc9_rc10_every_flow_has_one_kind_and_the_counts_balance() -> None:
    videos, crawl, said = frozen()
    out, report = reconcile(videos, crawl, judge_mock(), transcripts=said)
    assert all(f.kind in ("ideal", "narrated", "variant") and f.ideal_basis for f in out.flows)
    assert sum(report.kinds.values()) == report.flows_out == len(out.flows)
    assert report.kinds == {k: sum(f.kind == k for f in out.flows)
                            for k in ("ideal", "narrated", "variant")}


def test_rc10_each_variant_is_an_another_possibility_with_step_second_and_quote() -> None:
    said = {"src_c": Transcript(source_id="src_c", segments=[
        TranscriptSegment(start=0, end=3, text="This way works too.")])}
    out, report = reconcile(_task_specs(), [], transcripts=said)
    variant = next(f for f in out.flows if f.kind == "variant")
    [row] = report.possibilities
    assert (row.flow_id, row.ideal_flow_id, row.diverges_at) == (
        variant.id, variant.variant_of, variant.diverges_at)
    assert row.source_ref is not None and row.source_ref.source_id == "src_c"
    assert row.source_ref.t_start == 1.0 and row.quote == "this way works too"


def test_rc10_review_status_changes_nothing_and_is_never_read() -> None:
    videos, crawl, said = frozen()
    base = FlowSpec.model_validate(PRE_UNIT)
    results = []
    for status in (ReviewStatus.DRAFT, ReviewStatus.APPROVED):
        existing = base.model_copy(update={"review": Review(status=status)})
        out, report = reconcile(videos, crawl, judge_mock(), existing=existing, transcripts=said)
        assert out.review.status is status
        results.append((out.fingerprint, report.model_dump_json()))
    assert results[0] == results[1]
    source = Path(rc.__file__).read_text(encoding="utf-8")
    assert "require_reviewed" not in source and "ReviewStatus" not in source
    assert ".review" not in source
