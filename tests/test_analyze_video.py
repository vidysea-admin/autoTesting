"""The ensemble driver — VL2/VL3: what it reads, what it refuses, what it saves.

The COST half of this stage — the cache, and the rule that a re-run never
re-spends a provider call — lives in `test_analyze_cache.py`. Split at the
300-line cap along that line, because "does it spend money twice" and "does it
hand each chunk its own narration" are answered by different assertions.

Contract: qa/contracts/video-learning.md VL2/VL3.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from video_fakes import SpyProvider, prepared

from autotester.core.paths import RepoDocs
from autotester.schema.enums import SourceKind
from autotester.schema.media import MediaChunk, Transcript, TranscriptSegment
from autotester.schema.project import Project, Source
from autotester.stages.analyze_video import (
    PROMPT_NAMES,
    SKILL_NAMES,
    NoObservations,
    analyze,
    build_chunk_prompt,
    load_transcript,
)
from autotester.store.project_store import ProjectStore

__all__ = ["prepared"]


# -- failure is partial, never total ---------------------------------------

def test_one_failing_model_does_not_lose_the_other(prepared) -> None:
    """A single failed provider must not throw away the answers that arrived."""
    store, source = prepared
    working, broken = SpyProvider("spy:pro"), SpyProvider("spy:broken", fail=True)

    analysis = analyze(store, source, [working, broken], docs=RepoDocs())

    assert analysis.provider_labels == ["spy:pro"]
    assert analysis.screens


def test_every_model_failing_refuses_instead_of_writing_an_empty_analysis(
    prepared,
) -> None:
    """An empty analysis persisted after a total failure would read as "we
    watched it and found nothing" — the opposite of what happened."""
    store, source = prepared

    with pytest.raises(NoObservations, match="nothing to adjudicate"):
        analyze(store, source, [SpyProvider("spy:broken", fail=True)], docs=RepoDocs())

    assert store.load_analysis(source.id) is None


def test_two_providers_under_one_label_are_refused(prepared) -> None:
    """AT-204. The label is the cache key, so the second provider would read
    the first's answers, never be called, and leave `models_agreeing` at 1 —
    an ensemble of one wearing the shape of an ensemble of two. Agreement is
    the only reason this stage costs money."""
    from autotester.stages.analyze_video import DuplicateProviders

    store, source = prepared

    with pytest.raises(DuplicateProviders, match="cache key"):
        analyze(store, source, [SpyProvider("spy:pro"), SpyProvider("spy:pro")],
                docs=RepoDocs())


def test_analyzing_an_unprepared_recording_is_refused(tmp_path: Path) -> None:
    """Prep is where chunking and narration happen; skipping it changes the
    answer without saying so."""
    from autotester.stages.media_prep import SourceNotPrepared

    store = ProjectStore("erp", tmp_path)
    store.save_project(Project(slug="erp", name="ERP", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    source = store.add_source(Source(project="erp", kind=SourceKind.VIDEO,
                                     path=str(tmp_path / "x.mp4"), sha256="d"))

    with pytest.raises(SourceNotPrepared):
        analyze(store, source, [SpyProvider("spy:pro")], docs=RepoDocs())


# -- narration is sliced per chunk -----------------------------------------

def test_a_chunk_gets_only_its_own_narration(prepared) -> None:
    """Handing a model the whole recording's transcript while it watches three
    minutes of it invites alignment to speech it cannot see, and a quote
    attached to the wrong screen is worse than no quote."""
    store, source = prepared
    store.save_transcript(Transcript(source_id=source.id, engine="sidecar", segments=[
        TranscriptSegment(start=5.0, end=7.0, text="early words"),
        TranscriptSegment(start=200.0, end=202.0, text="later words"),
    ]))
    pro = SpyProvider("spy:pro")

    analyze(store, source, [pro], docs=RepoDocs())

    first_chunk = next(p for path, p in pro.calls if "erp1" in path)
    assert "early words" in first_chunk
    assert "later words" not in first_chunk, "chunk 0 was handed chunk 1's speech"


def test_a_silent_section_says_so_rather_than_leaving_a_gap(prepared) -> None:
    """An empty narration block invites the model to fill it."""
    store, source = prepared
    store.save_transcript(Transcript(source_id=source.id, engine="sidecar", segments=[
        TranscriptSegment(start=300.0, end=302.0, text="only late speech"),
    ]))

    prompt = build_chunk_prompt(PROMPT_NAMES[0], source, RepoDocs(),
                          MediaChunk(index=0, path="x", offset_s=0.0, length_s=180.0),
                          store.load_transcript(source.id))

    assert "no speech in this section" in prompt
    assert "{{NARRATION}}" not in prompt


@pytest.mark.parametrize("prompt_name", PROMPT_NAMES)
def test_both_prompts_exist_and_carry_the_placeholders(prompt_name: str) -> None:
    """A prompt named by the driver but absent from disk fails only when a
    real analyze runs, which is the most expensive place to find out. And a
    template missing `{{NARRATION}}` makes the injection a silent no-op —
    AT-133's lesson, one stage over.

    T-175: both now ship as `SKILL.md` folders under `skills_dir`, named by
    `SKILL_NAMES[prompt_name]`."""
    skill_path = RepoDocs().skills_dir / SKILL_NAMES[prompt_name] / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")

    assert "{{NARRATION}}" in text
    assert "{{SOURCE_LABEL}}" in text


def test_the_analysis_is_persisted_not_just_returned(prepared) -> None:
    """T-131's lesson: a stage that returns without persisting leaves no trace,
    and no caller remembers to save for it."""
    store, source = prepared

    analyze(store, source, [SpyProvider("spy:pro")], docs=RepoDocs())

    assert store.load_analysis(source.id) is not None


def test_timestamps_from_a_later_chunk_land_in_whole_video_time(prepared) -> None:
    """The spy reports t_start=1.0 for every chunk. Chunk 1 is offset 165s, so
    an unshifted merge would collapse both into one screen at 1.0 — the bug
    `shift` exists to prevent, seen from the driver's side."""
    store, source = prepared

    analysis = analyze(store, source, [SpyProvider("spy:pro")], docs=RepoDocs())

    assert {round(s.t_start) for s in analysis.screens} == {1, 166}


# -- an unreadable transcript is a third state, never silence (AT-216) -------

def test_a_malformed_sidecar_is_loaded_as_unreadable_not_as_no_transcript(prepared) -> None:
    """VL1: "an unreadable sidecar is a third state". load_transcript used to swallow the
    parse error into None, the same value as a recording that was never transcribed."""
    store, source = prepared
    Path(source.path).with_suffix(".transcript.json").write_text("{not json", encoding="utf-8")

    transcript = load_transcript(store, source)

    assert transcript is not None and transcript.engine == "unreadable"
    assert "JSONDecodeError" in (transcript.unreadable_reason or ""), "AT-466: the cause survives"


def test_every_chunk_prompt_says_the_transcript_is_unreadable_not_silent(prepared) -> None:
    """The analysed prompt must not assert "no speech detected" about a recording whose
    narration exists but could not be read: the model then reports a silent video."""
    store, source = prepared
    Path(source.path).with_suffix(".transcript.json").write_text('{"segments": 3}',
                                                                  encoding="utf-8")
    pro = SpyProvider("spy:pro")

    analyze(store, source, [pro], docs=RepoDocs())

    assert pro.calls, "no chunk was analysed"
    for _path, prompt in pro.calls:
        assert "could not be read" in prompt
        assert "no speech detected" not in prompt


def test_an_unreadable_transcript_saved_by_media_prep_is_not_rendered_as_silence(prepared) -> None:
    """media_prep already persists `engine="unreadable"` for a bad sidecar (VL1); that is
    the path production takes, and the chunk prompt still called it "no speech"."""
    store, source = prepared
    store.save_transcript(Transcript(source_id=source.id, engine="unreadable"))

    prompt = build_chunk_prompt(PROMPT_NAMES[0], source, RepoDocs(),
                                MediaChunk(index=0, path="x", offset_s=0.0, length_s=180.0),
                                load_transcript(store, source))

    assert "could not be read" in prompt
    assert "no speech detected" not in prompt
