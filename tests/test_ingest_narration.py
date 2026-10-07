"""AT-779 / RC3 (amended): ingest saves a narration only as a verified, scrubbed quote.

A model-authored narration that is not in the recording's transcript must not reach the
saved FlowSpec, and a secret in a real quote is masked at the save path -- not later,
at reconcile. MockProvider stands in for the vision role.
"""

from __future__ import annotations

from pathlib import Path

from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action
from autotester.schema.flowspec import FlowSpec
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.project import Source, SourceKind
from autotester.stages.ingest import ingest_video, persist_ingest
from autotester.store.project_store import ProjectStore

SECRET = "Zq7-hunter-Secret-991"
SAID = f"now I type the password {SECRET} and press login"


def _source(tmp_path: Path) -> Source:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"fake video bytes")
    return Source(project="pathlynks", kind=SourceKind.VIDEO, path=str(video))


def _observation(*narrations: str | None) -> VideoObservation:
    steps = [ObservedStep(order=i + 1, action=Action.CLICK, target=f"button {i}",
                          t_start=float(i), narration=n) for i, n in enumerate(narrations)]
    return VideoObservation(
        screens=[ObservedScreen(name="Home", t_start=0.0, signals=["Home"])],
        flows=[ObservedFlow(name="Go", entry_screen="Home", steps=steps)])


def _transcript(source: Source) -> Transcript:
    return Transcript(source_id=source.id, segments=[
        TranscriptSegment(start=0, end=3, text=f"first {SAID}"),
        TranscriptSegment(start=3, end=6, text="Then we  OPEN the dashboard")])


def _ingest(tmp_path: Path, *narrations: str | None, transcript: bool = True,
            redactor: Redactor | None = None) -> FlowSpec:
    source = _source(tmp_path)
    provider = MockProvider(responses={"vision": [_observation(*narrations)]})
    return ingest_video(source, "pathlynks", provider,
                        transcript=_transcript(source) if transcript else None,
                        redactor=redactor or Redactor({}))


def _narrations(spec: FlowSpec) -> list[str | None]:
    return [s.narration for s in spec.flows[0].steps]


def test_a_narration_the_model_invented_is_dropped_and_the_step_kept(tmp_path: Path) -> None:
    spec = _ingest(tmp_path, "then we open the dashboard", "the user is delighted by the page")
    assert _narrations(spec) == ["then we open the dashboard", None]  # quote kept, invention gone
    assert len(spec.flows[0].steps) == 2


def test_a_secret_in_a_real_quote_is_redacted_at_the_save_path(tmp_path: Path) -> None:
    spec = _ingest(tmp_path, SAID, redactor=Redactor({"PATHLYNKS_PW": SECRET}))
    assert "[REDACTED]" in (_narrations(spec)[0] or "")
    store = ProjectStore("pathlynks", root=tmp_path / "root")
    persist_ingest(store, spec)
    saved = store.paths.flowspec.read_text(encoding="utf-8")
    assert SECRET not in saved and "[REDACTED]" in saved


def test_without_a_transcript_no_narration_can_be_a_quote(tmp_path: Path) -> None:
    assert _narrations(_ingest(tmp_path, SAID, "x", transcript=False)) == [None, None]


def test_a_step_with_no_narration_stays_none_not_empty(tmp_path: Path) -> None:
    assert _narrations(_ingest(tmp_path, None, "")) == [None, None]


def test_a_flowspec_saved_before_this_change_still_loads(tmp_path: Path) -> None:
    spec = _ingest(tmp_path, None)
    store = ProjectStore("pathlynks", root=tmp_path / "root")
    drop = {"flows": {"__all__": {"steps": {"__all__": {"narration"}}}}}
    old = spec.model_dump_json(exclude=drop)
    store.paths.flowspec.parent.mkdir(parents=True, exist_ok=True)
    store.paths.flowspec.write_text(old, encoding="utf-8")
    loaded = store.load_flowspec()
    assert loaded is not None and loaded.flows[0].steps[0].narration is None
