"""TV9: the analyze route proposes the adjudicated flows into the DRAFT FlowSpec.

Contract: qa/contracts/team-video-review.md TV9. Fake providers only, no ffmpeg, no browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review
from autotester.schema.media import MediaChunk, MediaPrep
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.project import Project
from autotester.stages.ingest import register_source
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _flow(target: str) -> ObservedFlow:
    return ObservedFlow(name="Pay", entry_screen="Cart", steps=[ObservedStep(
        order=1, action=Action.CLICK, target=target, t_start=1, screen="Cart")])


def _setup(root: Path, monkeypatch: pytest.MonkeyPatch, label: str = "Checkout",
           flows: list[ObservedFlow] | None = None):
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test"))
    recording = root / "rec.mp4"
    recording.write_bytes(b"video")
    source = register_source(store, recording, label=label)
    store.save_media_prep(MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(recording), offset_s=0, length_s=3)]))
    observation = VideoObservation(
        screens=[ObservedScreen(name="Cart", t_start=0)],
        flows=flows or [_flow("Pay now")])
    provider = MockProvider(responses={"vision": [observation, observation]})
    monkeypatch.setattr("autotester.ui.routes_sources.providers.get", lambda _n: provider)
    return store, source


def _analyze(source) -> int:
    return TestClient(app).post(
        f"/projects/demo/sources/{source.id}/analyze", follow_redirects=False).status_code


def test_analyze_writes_draft_flows_carrying_source_id(root, monkeypatch) -> None:
    store, source = _setup(root, monkeypatch)
    assert _analyze(source) == 303
    spec = store.load_flowspec()
    assert spec is not None and spec.review.status is ReviewStatus.DRAFT
    flows = [f for f in spec.flows if f.name == "Pay"]
    assert len(flows) == 1
    assert flows[0].steps[0].source_ref.source_id == source.id
    assert spec.source_ids == [source.id]


def test_rerun_is_idempotent_and_keeps_a_hand_made_flow(root, monkeypatch) -> None:
    store, source = _setup(root, monkeypatch)
    hand = Flow(id="flow_hand", name="Hand", entry_screen="x")
    store.save_flowspec(FlowSpec(project="demo", flows=[hand]))
    assert _analyze(source) == 303
    first = store.paths.flowspec.read_bytes()
    assert _analyze(source) == 303
    assert store.paths.flowspec.read_bytes() == first
    names = {f.name for f in store.load_flowspec().flows}
    assert names == {"Hand", "Pay"}


def test_an_approved_flowspec_is_never_rewritten(root, monkeypatch) -> None:
    store, source = _setup(root, monkeypatch)
    store.save_flowspec(FlowSpec(
        project="demo", flows=[Flow(id="flow_hand", name="Hand", entry_screen="x")],
        review=Review(status=ReviewStatus.APPROVED, by="Umesh")))
    before = store.paths.flowspec.read_bytes()
    assert _analyze(source) == 303
    assert store.paths.flowspec.read_bytes() == before


def test_same_named_flows_with_different_steps_are_all_retained(root, monkeypatch) -> None:
    store, source = _setup(root, monkeypatch, flows=[_flow("Pay now"), _flow("Pay later")])
    assert _analyze(source) == 303
    flows = store.load_flowspec().flows
    assert sorted(s.target for f in flows for s in f.steps) == ["Pay later", "Pay now"]
    assert len({f.id for f in flows}) == 2
    first = store.paths.flowspec.read_bytes()
    assert _analyze(source) == 303
    assert store.paths.flowspec.read_bytes() == first   # idempotent, no third row


def test_a_hand_corrected_flow_inside_a_draft_spec_is_untouched(root, monkeypatch) -> None:
    store, source = _setup(root, monkeypatch)
    assert _analyze(source) == 303
    spec = store.load_flowspec()
    fixed = spec.flows[0].model_copy(update={"name": "Pay (Ana)", "preconditions": ["x"]})
    store.save_flowspec(spec.model_copy(update={"flows": [fixed]}))
    assert _analyze(source) == 303
    after = store.load_flowspec()
    assert after.flows == [fixed] and after.review.status is ReviewStatus.DRAFT


@pytest.mark.xfail(strict=True, reason=(
    "expand() still calls require_reviewed on DRAFT (review-gate R5: changing it is a separate L "
    "unit, D-073, not authorized here; video flows are also kind=None/unreconciled)"))
def test_expand_over_a_draft_only_spec_generates_cases(root, monkeypatch) -> None:
    from autotester.stages.expand import propose_cases
    store, source = _setup(root, monkeypatch)
    assert _analyze(source) == 303
    spec = store.load_flowspec()
    assert spec.review.status is ReviewStatus.DRAFT
    assert propose_cases(spec)
