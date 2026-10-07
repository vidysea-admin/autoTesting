"""AT-783 / AT-784 / AT-785: ingest verifies narration against the transcript the project HAS,
and reports what verification dropped.

AT-783: the orchestrated ingest runner passed no transcript, so every narration was dropped.
AT-784: `ingest run` read only the sidecar, ignoring the transcript media prep persisted.
AT-785: dropped narrations were invisible; only a count and step ids may be reported.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester import providers
from autotester.cli import app
from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action
from autotester.schema.flowspec import FlowSpec, StepRef
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.project import Project, Source, SourceKind
from autotester.stages.ingest import ingest_video
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_ingest_runner
from autotester.stages.reconcile import narration_drop_report
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

REAL = "then we open the dashboard"
INVENTED = "the user is delighted by this wonderful page"
runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    st = ProjectStore("demo", tmp_path)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                            allowed_domains=["demo.test"]))
    return st


def _video(tmp_path: Path) -> Path:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"fake video bytes")
    return video


def _observation() -> VideoObservation:
    steps = [ObservedStep(order=1, action=Action.CLICK, target="Open", t_start=0.0,
                          narration=REAL),
             ObservedStep(order=2, action=Action.CLICK, target="Save", t_start=1.0,
                          narration=INVENTED)]
    return VideoObservation(
        screens=[ObservedScreen(name="Home", t_start=0.0, signals=["Home"])],
        flows=[ObservedFlow(name="Go", entry_screen="Home", steps=steps)])


def _mock() -> MockProvider:
    return MockProvider(responses={"vision": [_observation()]})


def _persist_transcript(store: ProjectStore, source: Source) -> None:
    store.save_transcript(Transcript(source_id=source.id, segments=[
        TranscriptSegment(start=0, end=3, text=f"first, {REAL} and go")]))


def _narrations(spec: FlowSpec) -> list[str | None]:
    return [s.narration for s in spec.flows[0].steps]


# -- AT-783: the orchestrate ingest runner ------------------------------------

def _run_runner(store: ProjectStore, source: Source, *, secrets=None) -> FlowSpec:
    ctx = StageContext(store=store, run_id="run_t", secrets=secrets)
    ref = make_ingest_runner(source, "demo", _mock())(ctx, None)
    spec = read_json(Path(ref), FlowSpec)
    assert spec is not None
    return spec


def test_orchestrated_ingest_keeps_a_narration_the_transcript_contains(
        store: ProjectStore, tmp_path: Path) -> None:
    source = store.add_source(Source(project="demo", kind=SourceKind.VIDEO,
                                     path=str(_video(tmp_path))))
    _persist_transcript(store, source)
    assert _narrations(_run_runner(store, source)) == [REAL, None]


# -- AT-784: the CLI falls back to the media-prep transcript -------------------

def test_cli_ingest_uses_the_transcript_media_prep_persisted(
        store: ProjectStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _mock()
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: provider)
    reg = runner.invoke(app, ["ingest", "register", "demo", str(_video(tmp_path))])
    assert reg.exit_code == 0, reg.output
    source = store.list_sources()[-1]
    assert not _video(tmp_path).with_suffix(".transcript.json").exists()  # no sidecar
    _persist_transcript(store, source)

    result = runner.invoke(app, ["ingest", "run", "demo", source.id, "--provider", "mock"])

    assert result.exit_code == 0, result.output
    saved = store.load_flowspec()
    assert saved is not None and _narrations(saved) == [REAL, None]


# -- AT-785: dropped narrations are reported, ids and a count only -------------

def test_ingest_lists_the_steps_whose_narration_it_dropped(tmp_path: Path) -> None:
    source = Source(project="demo", kind=SourceKind.VIDEO, path=str(_video(tmp_path)))
    transcript = Transcript(source_id=source.id, segments=[
        TranscriptSegment(start=0, end=3, text=REAL)])
    dropped: list[StepRef] = []
    spec = ingest_video(source, "demo", _mock(), transcript=transcript,
                        redactor=Redactor({}), dropped=dropped)
    assert [(r.flow_id, r.order) for r in dropped] == [(spec.flows[0].id, 2)]


def test_the_report_names_a_count_and_step_ids_never_the_text() -> None:
    refs = [StepRef(flow_id="flow_a", order=2), StepRef(flow_id="flow_a", order=5)]
    report = narration_drop_report(refs)
    assert report is not None and "2 narration(s)" in report
    assert "flow_a#2" in report and "flow_a#5" in report
    assert narration_drop_report([]) is None


def test_the_runner_logs_the_drop_without_the_narration_text(
        store: ProjectStore, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    source = store.add_source(Source(project="demo", kind=SourceKind.VIDEO,
                                     path=str(_video(tmp_path))))
    _persist_transcript(store, source)
    with caplog.at_level(logging.WARNING):
        spec = _run_runner(store, source)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "1 narration(s) dropped" in text and f"{spec.flows[0].id}#2" in text
    assert INVENTED not in text and REAL not in text


def test_the_cli_prints_the_drop_without_the_narration_text(
        store: ProjectStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: _mock())
    runner.invoke(app, ["ingest", "register", "demo", str(_video(tmp_path))])
    source = store.list_sources()[-1]
    _persist_transcript(store, source)
    result = runner.invoke(app, ["ingest", "run", "demo", source.id, "--provider", "mock"])
    assert "1 narration(s) dropped" in result.output
    assert INVENTED not in result.output and REAL not in result.output


def test_a_secret_in_a_dropped_narration_never_reaches_the_report(
        store: ProjectStore, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from autotester.browser.secrets import SecretStore
    from autotester.schema.project import SecretRef

    secret = "Zq7-hunter-Secret-991"
    proj = Project(slug="demo", name="Demo", base_url="https://demo.test",
                   secrets=[SecretRef(key="DEMO_PW")])
    leaky = _observation()
    leaky.flows[0].steps[1].narration = f"I type {secret} now"
    source = store.add_source(Source(project="demo", kind=SourceKind.VIDEO,
                                     path=str(_video(tmp_path))))
    _persist_transcript(store, source)
    ctx = StageContext(store=store, run_id="run_s", secrets=SecretStore(proj, {"DEMO_PW": secret}))
    with caplog.at_level(logging.WARNING):
        make_ingest_runner(source, "demo", MockProvider(responses={"vision": [leaky]}))(ctx, None)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "1 narration(s) dropped" in text and secret not in text
