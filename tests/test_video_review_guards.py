"""T-197 cycle-1 follow-ups: F6 (narration state gates `overlapping`), F8 (depth constants in
`stages/video_pointers.py`), the honest preview cost, the "no baseline" phrase (TV9) and the
shared unreadable-media check the CLI maps to exit 4 (TV3).

Contract: qa/contracts/team-video-review.md TV2, TV3, TV5, TV6, TV9. Fake providers only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from video_review_fakes import RecordingProvider, item, reply_of, run, transcript

from autotester.schema.video_pointer import PointerParse
from autotester.stages import video_pointers, video_review_plan
from autotester.stages.video_review import unreadable_reason
from autotester.stages.video_review_items import overlapping
from autotester.stages.video_review_plan import plan_review
from autotester.stages.video_review_render import render_html, render_markdown


@pytest.mark.parametrize("engine", ["none", "unreadable"])
def test_f6_a_transcript_with_no_speech_state_yields_no_narration_item(tmp_path, engine):
    """A Transcript whose engine says none/unreadable but still carries segments (a stale or
    hand-edited sidecar) must not let a model claim narration with a 'verbatim' quote."""
    tx = transcript((5.0, 15.0, "the save button does nothing"), engine=engine)
    assert overlapping(tx, 10.0) == []
    reply = reply_of([item(time_s=10, origin="narration", quote="the save button does nothing")])
    r = run(tmp_path, RecordingProvider([reply]), tx)
    assert not any(i.origin == "narration" for i in r.items)
    assert r.items[0].origin == "suspected" and r.items[0].downgrade
    assert r.narration_state == ("none" if engine == "none" else "unreadable")


def test_f8_depth_constants_live_in_video_pointers_and_pointer_depth_is_denser():
    assert video_pointers.POINTER_FRAMES_PER_MIN > video_pointers.BASE_FRAMES_PER_MIN
    assert video_pointers.POINTER_FRAMES_PER_MIN % video_pointers.BASE_FRAMES_PER_MIN == 0
    # one concept, one place: the plan module reads the same objects, it does not redefine them
    assert video_review_plan.BASE_FRAMES_PER_MIN is video_pointers.BASE_FRAMES_PER_MIN
    assert video_review_plan.POINTER_FRAMES_PER_MIN is video_pointers.POINTER_FRAMES_PER_MIN
    src = Path(video_review_plan.__file__).read_text(encoding="utf-8")
    assert "BASE_FRAMES_PER_MIN =" not in src and "POINTER_FRAMES_PER_MIN =" not in src


def test_dry_run_cost_of_an_unpriced_provider_is_not_zero():
    """`--dry-run` for a real provider id must not print $0.00 just because the table has no
    bare 'gemini' row: the cap and the preview read the same conservative rate."""
    plan = plan_review(600.0, PointerParse(), [], provider_label="gemini")
    assert plan.est_cost_usd > 0
    assert plan_review(600.0, PointerParse(), [], provider_label="mock").est_cost_usd == 0


def test_tv9_review_says_no_baseline_to_compare_and_never_matches_the_product(tmp_path):
    r = run(tmp_path, RecordingProvider([reply_of([item()])]))
    for text in (render_markdown(r), render_html(r)):
        assert "no baseline to compare" in text.lower()
        assert "matches the product" not in text.lower()


@pytest.mark.parametrize("make,expect", [
    (lambda p: p / "missing.mp4", "missing"),
    (lambda p: _write(p / "empty.mp4", b""), "empty"),
])
def test_unreadable_reason_names_a_missing_or_empty_recording(tmp_path, make, expect):
    video = make(tmp_path)
    why = unreadable_reason(video, lambda _p: (0.0, 0, 0))
    assert why and expect in why


def test_unreadable_reason_is_none_for_a_probed_video(tmp_path):
    video = _write(tmp_path / "ok.mp4", b"x")
    assert unreadable_reason(video, lambda _p: (60.0, 640, 360)) is None
    assert unreadable_reason(video, lambda _p: (60.0, 0, 0))  # audio-only: no video track


def _write(path: Path, body: bytes) -> Path:
    path.write_bytes(body)
    return path
