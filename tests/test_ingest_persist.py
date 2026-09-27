"""Track A2 (T-131): registering a recording, hardening the vision call, and
persisting what was learned. Contract: qa/contracts/ingest.md I6-I9.

The defect this unit closes is not a crash -- `ingest_video` worked. It
returned a FlowSpec and persisted nothing, and no caller saved it, so learning
from a recording left no trace on disk at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.core.paths import RepoDocs
from autotester.providers.mock import MockProvider
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    VideoObservation,
    VisionOptions,
)
from autotester.schema.project import Project
from autotester.stages.ingest import (
    FlowSpecApproved,
    build_ingest_prompt,
    ingest_video,
    persist_ingest,
    register_source,
)
from autotester.store.project_store import ProjectStore


def make_store(tmp_path: Path) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    return store


def a_video(tmp_path: Path, name: str = "erp1.mp4", body: bytes = b"fake-mp4") -> Path:
    path = tmp_path / name
    path.write_bytes(body)
    return path


def an_observation() -> VideoObservation:
    return VideoObservation(
        screens=[ObservedScreen(name="Trainers", t_start=1.0, t_end=9.0,
                                url="https://demo.test/trainers/123?tab=2",
                                signals=["Trainers"])],
        flows=[ObservedFlow(name="Open a trainer", entry_screen="Trainers", steps=[])],
        summary="A trainer admin tool.",
    )


# -- register_source -------------------------------------------------------

def test_the_same_recording_registered_twice_is_one_source(tmp_path: Path) -> None:
    """A shell command is re-run by habit. If that doubled the corpus, every
    recall number scored against a human's sheet would be quietly wrong."""
    store = make_store(tmp_path)
    video = a_video(tmp_path)

    first = register_source(store, video, label="erp1")
    second = register_source(store, video, label="erp1 again")

    assert first.id == second.id
    assert len(store.list_sources()) == 1


def test_a_different_recording_is_a_different_source(tmp_path: Path) -> None:
    """The dedupe is on CONTENT, not on filename -- otherwise renaming a file
    would hide it from the corpus."""
    store = make_store(tmp_path)
    register_source(store, a_video(tmp_path, "a.mp4", b"one"))
    register_source(store, a_video(tmp_path, "b.mp4", b"two"))

    assert len({s.id for s in store.list_sources()}) == 2


def test_registering_a_missing_file_says_so(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError, match="no such recording"):
        register_source(store, tmp_path / "nope.mp4")


# -- persist_ingest --------------------------------------------------------

def test_ingesting_persists_the_flowspec(tmp_path: Path) -> None:
    """The whole point of T-131: before it, `ingest_video` returned a spec that
    nothing wrote, so `stages/ingest.py` never touched ProjectStore at all."""
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    provider = MockProvider(responses={"vision": [an_observation()]})

    spec = ingest_video(source, "demo", provider, RepoDocs())
    persist_ingest(store, spec)

    saved = store.load_flowspec()
    assert saved is not None
    assert [s.name for s in saved.screens] == ["Trainers"]


def test_an_approved_flowspec_is_never_silently_overwritten(tmp_path: Path) -> None:
    """Overwriting an APPROVED spec discards a human's review, not just data.
    The refusal names `--replace` so the operator can say they meant it."""
    store = make_store(tmp_path)
    store.save_flowspec(FlowSpec(project="demo",
                                 review=Review(status=ReviewStatus.APPROVED, by="umesh")))
    source = register_source(store, a_video(tmp_path))
    spec = ingest_video(source, "demo", MockProvider(responses={"vision": [an_observation()]}),
                        RepoDocs())

    with pytest.raises(FlowSpecApproved, match="--replace"):
        persist_ingest(store, spec)

    saved = store.load_flowspec()
    assert saved is not None
    assert saved.review.status is ReviewStatus.APPROVED


def test_replace_overwrites_an_approved_flowspec_when_asked(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save_flowspec(FlowSpec(project="demo",
                                 review=Review(status=ReviewStatus.APPROVED, by="umesh")))
    source = register_source(store, a_video(tmp_path))
    spec = ingest_video(source, "demo", MockProvider(responses={"vision": [an_observation()]}),
                        RepoDocs())

    persist_ingest(store, spec, replace=True)

    saved = store.load_flowspec()
    assert saved is not None
    assert [s.name for s in saved.screens] == ["Trainers"]


# -- what the ingested screen carries --------------------------------------

def test_an_observed_url_is_templated_the_same_way_the_crawler_templates_it(
    tmp_path: Path,
) -> None:
    """A screen learned from a video and the same screen found by a crawl must
    produce ONE row. They only do if both sides normalise the URL identically,
    so this asserts the crawler's own `url_template` output, not a lookalike."""
    from autotester.core.urls import url_template

    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    spec = ingest_video(source, "demo", MockProvider(responses={"vision": [an_observation()]}),
                        RepoDocs())

    assert spec.screens[0].url_pattern == url_template(
        "https://demo.test/trainers/123?tab=2", keep_host=False)
    assert "123" not in (spec.screens[0].url_pattern or "")


def test_a_screen_with_no_visible_url_gets_no_url_pattern(tmp_path: Path) -> None:
    """Inventing one would report a coverage gap closed that nothing has seen."""
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    observation = VideoObservation(screens=[ObservedScreen(name="Modal", t_start=1.0)])

    spec = ingest_video(source, "demo",
                        MockProvider(responses={"vision": [observation]}), RepoDocs())

    assert spec.screens[0].url_pattern is None


def test_every_ingested_screen_points_back_at_the_second_it_came_from(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    spec = ingest_video(source, "demo", MockProvider(responses={"vision": [an_observation()]}),
                        RepoDocs())

    ref = spec.screens[0].source_ref
    assert ref is not None
    assert ref.source_id == source.id
    assert (ref.t_start, ref.t_end) == (1.0, 9.0)


# -- narration as ground truth ---------------------------------------------

def test_the_transcript_is_injected_verbatim_into_the_prompt(tmp_path: Path) -> None:
    """A tester saying "this should be X" is the highest-value signal in a
    recording and the one a vision model can least recover from pixels."""
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    transcript = Transcript(source_id=source.id, engine="whisper",
                            segments=[TranscriptSegment(start=1.0, end=3.0,
                                                        text="this button should say Save")])

    prompt = build_ingest_prompt(source, RepoDocs(), transcript)

    assert "this button should say Save" in prompt
    assert "{{NARRATION}}" not in prompt, "the placeholder survived -- nothing was injected"


def test_a_silent_recording_says_so_instead_of_leaving_a_gap(tmp_path: Path) -> None:
    """An empty narration block invites the model to fill it. Saying "no speech
    detected" is an instruction; leaving it blank is an opening."""
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))

    prompt = build_ingest_prompt(source, RepoDocs(), None)

    assert "no speech detected" in prompt
    assert "{{NARRATION}}" not in prompt


def test_the_prompt_template_still_carries_the_placeholder_the_code_replaces() -> None:
    """If the template loses `{{NARRATION}}`, injection becomes a silent no-op
    and every ingest runs blind to what the tester actually said.

    T-175: the ingest prompt now ships as `skills/ingest-video/SKILL.md`."""
    template = (RepoDocs().skills_dir / "ingest-video" / "SKILL.md").read_text(encoding="utf-8")
    assert "{{NARRATION}}" in template
    assert "{{SOURCE_LABEL}}" in template


# -- the options actually reach the provider -------------------------------

def test_vision_options_reach_the_provider(tmp_path: Path) -> None:
    """`VisionOptions` existed in the schema and no caller passed it, so seed
    and resolution were built and dropped. A non-deterministic vision call
    makes the observation cache meaningless."""
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    provider = MockProvider(responses={"vision": [an_observation()]})
    options = VisionOptions(seed=7, fps=2.0)

    ingest_video(source, "demo", provider, RepoDocs(), options=options)

    assert provider.vision_options == [options]


# -- I7's actual purpose, finally tested (AT-287's root cause) ----------------

def test_a_video_screen_and_a_crawled_screen_of_one_url_produce_one_pattern(
    tmp_path: Path,
) -> None:
    """I7's stated purpose is that "a screen learned from a video and the same
    screen found by a crawl collapse to one row instead of two". They did not:
    `ingest.py` stored `url_pattern` host-ful and `explore_merge.py` stored it
    host-less, so the same screen produced TWO different patterns and never
    collapsed. I7 was asserted but never tested across the seam — only that each
    side called `url_template`, not that they agreed. AT-287 was the symptom.
    """
    from autotester.schema.screen_graph import ScreenNode
    from autotester.stages.explore_merge import screen_from

    # The two sides genuinely differ in shape, which is the whole point:
    # a vision model reads the address bar, and browsers HIDE the scheme, so the
    # video side is schemeless. The crawler gets its url from the browser API and
    # always has one. Feeding both the same scheme-ful string made the first
    # version of this test pass vacuously (checker A, cycle 2) — it never
    # exercised the shape that actually broke, which is the only shape
    # `projects/erp`'s real recorded data contains.
    from_the_address_bar = "vidysea.com/erp/trainers"
    from_the_browser_api = "https://vidysea.com/erp/trainers"
    store = make_store(tmp_path)
    source = register_source(store, a_video(tmp_path))
    observation = VideoObservation(
        screens=[ObservedScreen(name="Trainers", t_start=1.0, t_end=9.0,
                                url=from_the_address_bar)])

    from_video = ingest_video(source, "demo",
                              MockProvider(responses={"vision": [observation]}),
                              RepoDocs()).screens[0]
    from_crawl = screen_from(ScreenNode(
        crawl_id="crawl_1", project="demo", url_example=from_the_browser_api,
        url_template=from_the_browser_api, signature="sig-trainers",
        title="Trainers", name="Trainers"))

    assert from_video.url_pattern == from_crawl.url_pattern == "/erp/trainers"
