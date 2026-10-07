"""TV1 (stage side), TV2 (provider side), TV7 (pure parts), TV10: before and across calls.

Contract: qa/contracts/team-video-review.md. The permission/approval gate itself is owed to T-204;
here the injected `gate` is proven to run first and to stop everything with zero provider calls.
"""

from __future__ import annotations

import pytest
from video_review_fakes import (
    DURATION,
    SRC,
    FakeFrames,
    RecordingProvider,
    item,
    make_run,
    reply_of,
    run,
    transcript,
)

from autotester.providers.anthropic import AnthropicProvider
from autotester.providers.gemini import GeminiProvider
from autotester.schema.video_review import RedactionWindow, ReviewReply
from autotester.stages.video_review import (
    PointerErrors,
    ReviewRefused,
    load_review,
    preview_review,
    run_review,
)
from autotester.stages.video_review_plan import in_any


def _refuse() -> None:
    raise ReviewRefused("caller lacks video.upload on this project")


def test_gate_refusal_means_zero_provider_calls(tmp_path):
    """A viewer without permission (or without a per-use approval) presses Run."""
    p = RecordingProvider([reply_of([item()])])
    with pytest.raises(ReviewRefused, match=r"video.upload"):
        run(tmp_path, p, gate=_refuse)
    assert p.calls == 0


def test_pointer_errors_stop_before_any_call_and_list_every_error(tmp_path):
    """A reviewer pastes three bad lines: all three come back, nothing is analysed."""
    p = RecordingProvider([reply_of([item()])])
    with pytest.raises(PointerErrors) as caught:
        run(tmp_path, p, pointer_text="99:99\n9:00\n14:00-12:30\n-1:00")
    assert [e.line_no for e in caught.value.parse.errors] == [1, 3, 4]
    assert p.calls == 0


def test_pointers_add_frames_and_never_remove_any_at_the_provider(tmp_path):
    """TV2 at the provider: 0, 1 and 3 pointers, one a window, one approximate."""
    seen = []
    for n, text in enumerate(["", "2:00-4:00", "2:00-4:00\n~7:00 | x\nlook at the footer"]):
        p = RecordingProvider([reply_of([item()])] * 20)
        run(tmp_path / str(n), p, pointer_text=text)
        seen.append(set(p.frame_times))
    assert seen[0] <= seen[1] <= seen[2] and seen[0] < seen[2]
    assert max(seen[0]) >= DURATION - 15 - 1e-9          # the unpointed recording runs end to end


def test_redacted_frames_never_reach_the_provider_and_redaction_comes_first(tmp_path):
    """A reviewer blanks 2:00-3:00: no frame from it is sent, the copy is built before the call."""
    log: list[str] = []
    FakeFrames.log = log
    video, source, paths = make_run(tmp_path)
    win = RedactionWindow(start_s=120.0, end_s=180.0)
    p = RecordingProvider([reply_of([item()])] * 20, forbidden=[video], log=log)
    try:
        r = run_review(paths, source, video, p, None, gate=lambda: None, secrets={}, windows=[win],
                       probe_fn=lambda _x: (DURATION, 640, 360), frames_fn=FakeFrames)
    finally:
        FakeFrames.log = None
    assert log[0] == "redact" and "judge" in log
    assert p.frame_times and not any(in_any(t, [(120.0, 180.0)]) for t in p.frame_times)
    assert all(video != x and video not in x.parents for x in p.paths)
    assert any(s <= 120.0 and e >= 180.0 for s, e in r.not_reviewed)
    assert "Redacted on request" in r.coverage_note
    from autotester.stages.video_review_render import render_html, render_markdown
    assert "Not reviewed" in render_markdown(r) and "Not reviewed" in render_html(r)


def test_a_failed_redaction_check_refuses_before_any_call(tmp_path):
    """The copy is not black inside the window (ffmpeg problem): refuse, spend nothing."""
    from autotester.media.redacted import RedactionError

    def broken(*_a: object) -> object:
        raise RedactionError("window not blacked out")

    p = RecordingProvider([reply_of([item()])])
    with pytest.raises(ReviewRefused, match="redaction"):
        run(tmp_path, p, windows=[RedactionWindow(start_s=1, end_s=2)], frames_fn=broken)
    assert p.calls == 0


def test_spend_cap_marks_the_review_partial_and_names_the_leftover(tmp_path):
    """A priced fake at $0.10 per call with a $0.20 cap on a long, pointed recording."""
    p = RecordingProvider([reply_of([item(time_s=10)]), reply_of([item(time_s=20, seen="b")])]
                          + [reply_of([])] * 30)
    r = run(tmp_path, p, pointer_text="5:00-7:00",
            max_cost_usd=0.20, cost_of=lambda prov: 0.10 * prov.calls)
    assert p.calls == 2 and r.status == "partial" and "spend cap" in (r.reason or "")
    assert r.not_reviewed, "what was left must be named"
    assert r.analysed and sorted(r.analysed + r.not_reviewed)[0][0] == 0.0
    pointed = [t for t in p.frame_times if 300 - 20 <= t <= 420]
    assert pointed, "pointer frames are analysed first, so the cap cuts the unpointed tail"


def test_ignoring_the_cap_would_make_more_calls(tmp_path):
    p = RecordingProvider([reply_of([item()])] * 40)
    r = run(tmp_path, p, max_cost_usd=10.0, cost_of=lambda prov: 0.10 * prov.calls)
    assert r.status == "ok" and p.calls >= 3


def test_preview_prints_the_plan_with_zero_provider_calls(tmp_path):
    video, _, _ = make_run(tmp_path)
    win = RedactionWindow(start_s=120.0, end_s=180.0)
    plan = preview_review(video, "2:00-4:00", [win], probe_fn=lambda _x: (DURATION, 640, 360))
    assert plan.frame_count > 0 and plan.call_count >= 1 and plan.redacted_frame_count > 0
    assert plan.windows == [win] and plan.pointer_windows
    with pytest.raises(PointerErrors):
        preview_review(video, "99:99", [], probe_fn=lambda _x: (DURATION, 640, 360))


def test_gate_is_a_required_argument(tmp_path):
    """There is no permissive default: omitting the gate is a TypeError, not an open door."""
    video, source, paths = make_run(tmp_path)
    with pytest.raises(TypeError):
        run_review(paths, source, video, RecordingProvider(), None)  # type: ignore[call-arg]


# ---------------------------------------------------------------- TV10

def test_same_inputs_same_id_one_artifact_and_no_second_spend(tmp_path):
    """A reviewer presses Run twice on the same pointers: one stored review, one spend."""
    p = RecordingProvider([reply_of([item()])] * 20)
    first = run(tmp_path, p, pointer_text="2:00-3:00")
    calls = p.calls
    second = run(tmp_path, p, pointer_text="2:00-3:00")
    assert first.id == second.id and p.calls == calls
    files = list((tmp_path / "root" / "projects" / "p" / "reviews").glob("*.json"))
    assert len(files) == 1


def test_id_has_no_clock_in_it(tmp_path):
    """Two runs in separate project dirs give the same id although created_at differs."""
    a = run(tmp_path / "a", RecordingProvider([reply_of([item()])] * 20))
    b = run(tmp_path / "b", RecordingProvider([reply_of([item()])] * 20))
    assert a.id == b.id and a.created_at != b.created_at


def test_human_status_survives_a_refresh_and_decided_items_stay_listed(tmp_path):
    p = RecordingProvider([reply_of([item(), item(time_s=50, seen="gone")])] * 20)
    first = run(tmp_path, p)
    paths = make_run(tmp_path)[2]
    marked = first.model_copy(update={"items": [
        first.items[0].model_copy(update={"status": "confirmed"}),
        first.items[1].model_copy(update={"status": "dismissed"})]})
    from autotester.store.filestore import write_json
    write_json(paths.review_path(first.id), marked)
    p2 = RecordingProvider([reply_of([item()])] * 20)          # the re-run finds only one
    again = run(tmp_path, p2, refresh=True)
    status = {i.seen: i.status for i in again.items}
    assert status["Button looks disabled"] == "confirmed" and status["gone"] == "dismissed"
    assert load_review(paths, first.id).items[0].status == "confirmed"


@pytest.mark.parametrize("change", ["pointer", "transcript", "window"])
def test_changing_a_pointer_the_transcript_or_a_window_gives_a_new_id(tmp_path, change):
    base = dict(pointer_text="2:00", tx=transcript((1.0, 2.0, "a")), windows=[])
    other = dict(base)
    other.update({"pointer": {"pointer_text": "2:01"},
                  "transcript": {"tx": transcript((1.0, 2.0, "b"))},
                  "window": {"windows": [RedactionWindow(start_s=5, end_s=6)]}}[change])

    def go(sub: str, kw: dict) -> str:
        tx = kw.pop("tx")
        return run(tmp_path / sub, RecordingProvider([reply_of([item()])] * 20), tx, **kw).id

    assert go("a", dict(base)) != go("b", other)


def test_review_lives_under_the_project_not_beside_the_video(tmp_path):
    r = run(tmp_path, RecordingProvider([reply_of([item()])] * 20))
    assert (tmp_path / "root" / "projects" / "p" / "reviews" / f"{r.id}.json").exists()
    assert not list(tmp_path.glob("*.json")) and r.source_id == SRC


# ---------------------------------------------------------------- cycle 1 (checker F1, F2, F7)

CANARY = "CANARY-SPOKEN-PASSWORD"


def test_speech_inside_a_redaction_window_never_reaches_any_prompt(tmp_path):
    """A tester spoke a password at 100-110 s and the reviewer blanked 90-120 s (F1, TV7.3)."""
    tx = transcript((5.0, 8.0, "intro line"), (100.0, 110.0, CANARY),
                    (118.0, 125.0, f"tail {CANARY}"), (85.0, 92.0, f"lead {CANARY}"),
                    (80.0, 130.0, f"span {CANARY}"), (300.0, 304.0, "later line"))
    p = RecordingProvider([reply_of([item()])] * 40)
    run(tmp_path, p, tx, windows=[RedactionWindow(start_s=90.0, end_s=120.0)])
    assert p.prompts and all(CANARY not in pr for pr in p.prompts)
    assert any("intro line" in pr for pr in p.prompts), "speech outside the window is still shown"


class _PricedLikeProduction(AnthropicProvider):
    """The real class and the real default label ("anthropic"), only the network is replaced."""

    def __init__(self) -> None:
        super().__init__(api_key="test")
        self.calls = 0

    def judge(self, prompt, schema, images=None, *, prompt_file=None, fed_id=None):
        self.calls += 1
        self.record("judge", 50_000, 10_000)
        return ReviewReply(summary="A flow.", items=[])


class _GeminiLike(_PricedLikeProduction, GeminiProvider):
    id = "gemini"


@pytest.mark.parametrize("cls", [_PricedLikeProduction, _GeminiLike])
def test_default_cost_function_binds_the_cap_for_real_provider_classes(tmp_path, cls):
    """No injected cost_of: an unpriced real label must still stop at the cap (F2, TV7.4)."""
    prov = cls()
    r = run(tmp_path, prov, pointer_text="2:00-8:00", max_cost_usd=0.50)
    assert prov.label in ("anthropic", "gemini")            # the unpriced production label
    assert 1 <= prov.calls <= 3, prov.calls
    assert r.status == "partial" and "spend cap" in (r.reason or "") and r.not_reviewed


def test_secrets_is_a_required_argument_like_the_gate(tmp_path):
    """A caller that forgets `secrets` is a TypeError, not an empty redactor (F7, C5)."""
    video, source, paths = make_run(tmp_path)
    with pytest.raises(TypeError):
        run_review(paths, source, video, RecordingProvider(), None,  # type: ignore[call-arg]
                   gate=lambda: None, probe_fn=lambda _x: (DURATION, 640, 360))
