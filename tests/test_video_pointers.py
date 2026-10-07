"""TV1 + TV2 (pure parts): pointer grammar and the frame plan.

Contract: qa/contracts/team-video-review.md TV1, TV2. Every case names the reviewer
action that reaches it: a person types or pastes lines into the pointer box / file.
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from autotester.stages.video_pointers import (
    MAX_FREE_POINTERS,
    PointerParse,
    canonical_pointers,
    parse_pointers,
)
from autotester.stages.video_review_plan import (
    BASE_FRAMES_PER_MIN,
    POINTER_FRAMES_PER_MIN,
    plan_frames,
    spans_from_plan,
)

DURATION = 3600.0


def _parse(text: str, duration: float = DURATION) -> PointerParse:
    return parse_pointers(text, duration)


@pytest.mark.parametrize(
    ("line", "start", "end", "approx", "text"),
    [
        ("12:30", 750.0, None, False, None),
        ("1:02:03", 3723.0, None, False, None),
        ("~12:30", 750.0, None, True, None),
        ("12:30 | the save button does nothing", 750.0, None, False,
         "the save button does nothing"),
        ("12:30-14:00", 750.0, 840.0, False, None),
        ("~12:30-14:00 | slow", 750.0, 840.0, True, "slow"),
        ("  0:05  |  early  ", 5.0, None, False, "early"),
    ],
)
def test_reviewer_types_each_time_form_and_it_parses(line, start, end, approx, text):
    """A reviewer types one of the documented time forms (optionally with a note)."""
    parsed = _parse(line, duration=7200.0)
    assert not parsed.errors, parsed.errors
    (p,) = parsed.parsed
    assert (p.start_s, p.end_s, p.approx, p.text) == (start, end, approx, text)
    assert p.line_no == 1


@pytest.mark.parametrize(
    ("line", "needle"),
    [
        ("-5:00", "negative"),
        ("14:00-12:30", "reversed"),
        ("99:99", "seconds"),
        ("12:3x | oops", "unparsable"),
        ("62:00", "duration"),           # 3720 s >= 3600 s
        ("60:00", "duration"),           # exactly at the end
        ("10:00-70:00", "duration"),     # window runs past the end
        ("1:75:00", "minutes"),          # H:MM:SS with minutes >= 60
        ("not a time | note", "unparsable"),
    ],
)
def test_bad_line_comes_back_with_line_number_and_reason(line, needle):
    """A reviewer typo is returned whole with its 1-based line number, never clamped."""
    parsed = _parse(f"\n{line}\n")
    assert parsed.parsed == []
    (err,) = parsed.errors
    assert err.line_no == 2
    assert needle in err.reason.lower()


def test_free_text_pointers_kept_and_fourth_refused():
    """A reviewer writes more than three free pointers; the fourth is refused, not dropped."""
    text = "\n".join(["login feels slow", "check the exports", "dates look odd",
                      "also the footer"])
    parsed = _parse(text)
    assert [p.line_no for p in parsed.parsed] == [1, 2, 3]
    assert all(p.kind == "free" and p.start_s is None for p in parsed.parsed)
    (err,) = parsed.errors
    assert err.line_no == 4
    assert str(MAX_FREE_POINTERS) in err.reason


def test_count_identity_holds_for_a_messy_file():
    """BOM + Windows line endings + blanks + good + bad lines: nothing vanishes."""
    lines = ["\ufeff12:30 | a", "", "99:99", "   ", "14:00-12:30", "free one", "~1:00",
             "-3:00", "", "5:00-6:00 | win", "a", "b", "c", "d"]
    text = "\r\n".join(lines)
    parsed = _parse(text)
    non_blank = sum(1 for ln in text.replace("\ufeff", "").splitlines() if ln.strip())
    assert len(parsed.parsed) + len(parsed.errors) == non_blank == parsed.non_blank_lines
    # line numbers are physical (blank lines count), 1-based, and strictly ordered
    assert [e.line_no for e in parsed.errors] == sorted(e.line_no for e in parsed.errors)
    assert parsed.parsed[0].line_no == 1 and parsed.parsed[0].start_s == 750.0


def test_empty_after_pipe_is_kept_as_a_time_pointer():
    """`12:30 |` (a half-typed note) still points at 12:30; the empty note is not an error."""
    parsed = _parse("12:30 |")
    assert not parsed.errors
    assert parsed.parsed[0].start_s == 750.0 and parsed.parsed[0].text is None


def test_old_mac_and_unicode_line_separators_do_not_split_lines():
    """`\\r`-only files split like lines; a pasted U+2028 stays inside one note."""
    parsed = _parse("1:00\r2:00 | a\u2028b\r\n3:00")
    assert [p.start_s for p in parsed.parsed] == [60.0, 120.0, 180.0]
    assert "\u2028" in (parsed.parsed[1].text or "")


def test_windows_drive_letter_path_is_free_text_not_a_time():
    """A reviewer pastes a path in a free note (R65: both separators, drive letter)."""
    parsed = _parse("see C:\\clips\\a.mp4 and D:/b.mp4")
    (p,) = parsed.parsed
    assert p.kind == "free" and "C:\\clips" in (p.text or "")


def test_canonical_form_ignores_line_order_and_numbers():
    a = canonical_pointers(_parse("1:00\n2:00 | x"))
    b = canonical_pointers(_parse("\n2:00 | x\n\n1:00"))
    assert a == b
    assert canonical_pointers(_parse("1:00")) != canonical_pointers(_parse("1:01"))


# ------------------------------------------------------------------ TV2 frame plan

def test_pointer_depth_is_strictly_greater_than_base_depth():
    assert POINTER_FRAMES_PER_MIN > BASE_FRAMES_PER_MIN


def test_pointers_only_add_frames_never_remove():
    """Same recording with and without a pointer file: the with-set is a superset."""
    plain = plan_frames(DURATION, _parse(""))
    pointed = plan_frames(DURATION, _parse("12:30-14:00\n~30:00 | x\n50:00\nfree"))
    assert set(plain.times) <= set(pointed.times)
    assert len(pointed.times) > len(plain.times)
    inside = [t for t in pointed.times if any(a <= t <= b for a, b in pointed.pointer_windows)]
    outside = [t for t in pointed.times if t not in inside]
    assert set(outside) <= set(plain.times)            # outside the windows: base depth only
    assert set(inside) >= {t for t in plain.times if t in inside}


def test_depth_ratio_inside_a_window_matches_the_constants():
    pointed = plan_frames(600.0, _parse("2:00-7:00"))
    (win,) = pointed.pointer_windows
    n_inside = len([t for t in pointed.times if win[0] <= t <= win[1]])
    minutes = (win[1] - win[0]) / 60
    assert n_inside / minutes >= POINTER_FRAMES_PER_MIN * 0.9


def test_recording_nobody_pointed_at_is_still_analysed_end_to_end():
    plan = plan_frames(DURATION, _parse(""))
    assert plan.times[0] == 0.0 and plan.times[-1] >= DURATION - 60 / BASE_FRAMES_PER_MIN
    spans = spans_from_plan(DURATION, plan.times, plan.times)
    assert spans.not_reviewed == []


def test_analysed_plus_not_reviewed_is_an_exact_partition():
    """Frames dropped (a spend cap) + a redaction window: the two lists tile [0, D]."""
    plan = plan_frames(300.0, _parse("1:00-2:00"))
    done = [t for t in plan.times if t < 100.0 or t > 200.0]
    spans = spans_from_plan(300.0, plan.times, done, windows=[(40.0, 70.0)])
    allspans = sorted(spans.analysed + spans.not_reviewed)
    assert allspans[0][0] == 0.0 and allspans[-1][1] == 300.0
    for (_, e1), (s2, _) in pairwise(allspans):
        assert e1 == s2
    assert spans.not_reviewed, "dropped frames and redaction must be named"
    assert any(s <= 40.0 and e >= 70.0 for s, e in spans.not_reviewed)
