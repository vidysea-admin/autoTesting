"""INGEST stage. Contract: qa/contracts/ingest.md I1-I5.

No live video, no live Gemini call — MockProvider stands in for the vision
role, seeded with a VideoObservation the way a real one would answer.
"""

from __future__ import annotations

from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action
from autotester.schema.flowspec import InputField
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
)
from autotester.schema.project import Source, SourceKind
from autotester.stages.ingest import build_ingest_prompt, ingest_video


def make_source(tmp_path: Path) -> Source:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"fake video bytes")
    return Source(project="pathlynks", kind=SourceKind.VIDEO, path=str(video), label="login demo")


def make_observation() -> VideoObservation:
    return VideoObservation(
        screens=[
            ObservedScreen(name="Sign-in page", t_start=0.0, signals=["Login button visible"]),
            ObservedScreen(name="Dashboard", t_start=8.5, signals=["Logged in successfully toast"]),
        ],
        flows=[
            ObservedFlow(
                name="Login with correct credentials",
                entry_screen="Sign-in page",
                steps=[
                    ObservedStep(order=1, action=Action.NAVIGATE, target="signin page",
                                 t_start=0.0),
                    ObservedStep(order=2, action=Action.FILL, target="Email field",
                                 value="user@example.com", t_start=2.0, t_end=3.0),
                    ObservedStep(order=3, action=Action.CLICK, target="Login button", t_start=6.0),
                ],
            ),
        ],
    )


def test_ingest_video_produces_screens_and_flows(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    provider = MockProvider(responses={"vision": [make_observation()]})

    spec = ingest_video(source, "pathlynks", provider)

    assert spec.project == "pathlynks"
    assert {s.name for s in spec.screens} == {"Sign-in page", "Dashboard"}
    assert len(spec.flows) == 1
    assert spec.source_ids == [source.id]


def test_steps_carry_source_ref_to_the_video_timestamp(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    provider = MockProvider(responses={"vision": [make_observation()]})

    spec = ingest_video(source, "pathlynks", provider)

    fill_step = next(s for s in spec.flows[0].steps if s.action == Action.FILL)
    assert fill_step.source_ref is not None
    assert fill_step.source_ref.source_id == source.id
    assert fill_step.source_ref.t_start == 2.0
    assert fill_step.source_ref.t_end == 3.0


def test_flow_entry_screen_resolves_to_the_screen_id(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    provider = MockProvider(responses={"vision": [make_observation()]})

    spec = ingest_video(source, "pathlynks", provider)

    signin = next(s for s in spec.screens if s.name == "Sign-in page")
    assert spec.flows[0].entry_screen == signin.id


def test_same_video_twice_produces_the_same_screen_and_flow_ids(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    provider1 = MockProvider(responses={"vision": [make_observation()]})
    provider2 = MockProvider(responses={"vision": [make_observation()]})

    spec1 = ingest_video(source, "pathlynks", provider1)
    spec2 = ingest_video(source, "pathlynks", provider2)

    assert {s.id for s in spec1.screens} == {s.id for s in spec2.screens}
    assert {f.id for f in spec1.flows} == {f.id for f in spec2.flows}


def test_same_named_screen_seen_twice_collapses_to_one_row(tmp_path: Path) -> None:
    """AT-034: revisiting the same screen later in the video must not duplicate it."""
    source = make_source(tmp_path)
    observation = VideoObservation(
        screens=[
            ObservedScreen(name="Dashboard", t_start=8.5, signals=["toast"]),
            ObservedScreen(name="Dashboard", t_start=40.0, signals=["toast"]),
        ],
        flows=[],
    )
    provider = MockProvider(responses={"vision": [observation]})

    spec = ingest_video(source, "pathlynks", provider)

    assert len(spec.screens) == 1


def test_same_named_screens_with_different_signals_stay_distinct(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    observation = VideoObservation(
        screens=[
            ObservedScreen(name="Modal", t_start=1.0, signals=["confirm delete"]),
            ObservedScreen(name="Modal", t_start=20.0, signals=["confirm logout"]),
        ],
        flows=[],
    )
    provider = MockProvider(responses={"vision": [observation]})

    spec = ingest_video(source, "pathlynks", provider)

    assert len(spec.screens) == 2
    assert spec.screens[0].id != spec.screens[1].id


def test_ingest_raises_on_a_source_with_no_path() -> None:
    source = Source(project="pathlynks", kind=SourceKind.VIDEO, path=None)
    provider = MockProvider(responses={"vision": [make_observation()]})

    try:
        ingest_video(source, "pathlynks", provider)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "no path" in str(exc)


def test_prompt_is_read_from_a_file_and_carries_the_source_label(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    docs = RepoDocs()
    prompt = build_ingest_prompt(source, docs)
    assert "login demo" in prompt
    assert "{{SOURCE_LABEL}}" not in prompt


def test_ingest_video_wraps_observed_field_labels_as_inputfields(tmp_path: Path) -> None:
    """A real video observation carries visible input LABELS (list[str]); FlowSpec
    `Screen.fields` is list[InputField]. The conversion lives in `_to_screen`."""
    source = make_source(tmp_path)
    observation = VideoObservation(
        screens=[ObservedScreen(name="Sign-up", t_start=0.0, signals=["Sign-up form visible"],
                                fields=["Email", "Phone Number"])],
    )
    provider = MockProvider(responses={"vision": [observation]})

    spec = ingest_video(source, "pathlynks", provider)

    fields = spec.screens[0].fields
    assert all(isinstance(f, InputField) for f in fields)
    assert [(f.name, f.label) for f in fields] == [("Email", "Email"),
                                                   ("Phone Number", "Phone Number")]
