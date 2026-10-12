"""TV3, TV4, TV5, TV6, TV8 (+ template): the typed review and what it refuses to claim.

Contract: qa/contracts/team-video-review.md. Fake providers only; every case names the real
scenario that reaches it (a model returning 9 items, a hallucinated second, an outage...).
"""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError
from video_review_fakes import (
    DURATION,
    SRC,
    ProviderError,
    RecordingProvider,
    item,
    make_run,
    reply_of,
    run,
    transcript,
)

from autotester.core.ids import file_sha256
from autotester.providers.mock import MockProvider
from autotester.schema.video_review import ReviewReply
from autotester.stages.video_pointers import parse_pointers
from autotester.stages.video_review import run_review
from autotester.stages.video_review_prompt import PLACEHOLDERS, build_review_prompt, load_template
from autotester.stages.video_review_render import render_markdown, render_review_html


def test_two_valid_items_stay_two_and_the_review_says_fewer_than_four(tmp_path):
    """The model finds only 2 real problems: no padding to the oracle's 4-5."""
    r = run(tmp_path, RecordingProvider([reply_of([item(time_s=5), item(time_s=50, seen="b")])]))
    assert r.status == "ok" and len(r.items) == 2
    assert r.count_note and "fewer than 4" in r.count_note


def test_nine_items_keep_the_five_most_severe_and_overflow_keeps_the_rest(tmp_path):
    """A chatty model returns 9: 5 shown by severity, 4 kept in overflow, none discarded."""
    sev = ["S3", "S3", "S3", "S3", "S2", "S2", "S1", "S1", "S1"]
    items = [item(time_s=10 + i, seen=f"s{i}", severity=s) for i, s in enumerate(sev)]
    r = run(tmp_path, RecordingProvider([reply_of(items)]))
    assert len(r.items) == 5 and len(r.overflow) == 4
    assert sorted(i.severity.value for i in r.items) == ["S1", "S1", "S1", "S2", "S2"]
    assert [i.severity.value for i in r.overflow] == ["S3"] * 4
    assert r.count_note is None


def test_malformed_item_is_rejected_with_a_reason_never_rendered_blank(tmp_path):
    r = run(tmp_path, RecordingProvider([reply_of([item(), item(suggestion="", time_s=20),
                                                   item(severity="S9", time_s=30)])]))
    assert len(r.items) == 1
    assert [x.reason for x in r.rejected] == ["missing_field:suggestion", "invalid_severity"]


@pytest.mark.parametrize("bad", [ProviderError("not json"), ValueError("bad"),
                                 "raw text", {"summary": "x"}])
def test_a_bad_model_reply_is_failed_not_an_empty_clean_review(tmp_path, bad):
    """The provider returns non-JSON / the wrong type: status failed with a reason."""
    r = run(tmp_path, RecordingProvider([bad]))
    assert r.status == "failed" and r.reason and not r.items


def test_schema_invalid_reply_raising_validation_error_is_failed(tmp_path):
    """A real provider's structured-output parse raises pydantic's ValidationError."""
    with pytest.raises(ValidationError) as caught:
        ReviewReply.model_validate({"items": "nope"})
    r = run(tmp_path, RecordingProvider([caught.value]))
    assert r.status == "failed"


def test_mock_provider_garbage_reply_is_failed(tmp_path):
    """The shipped MockProvider seeded with a non-ReviewReply value."""
    r = run(tmp_path, MockProvider(responses={"judge": [{"summary": "x"}]}))
    assert r.status == "failed"


def test_empty_summary_is_failed(tmp_path):
    assert run(tmp_path, RecordingProvider([reply_of([item()], summary=" ")])).status == "failed"


@pytest.mark.parametrize(("size", "probe"), [(0, (DURATION, 640, 360)), (9, (0.0, 0, 0)),
                                              (9, (30.0, 0, 0))])
def test_unreadable_media_is_a_status_never_a_verified_looking_review(tmp_path, size, probe):
    """Zero-length, corrupt, or audio-only (no video track) upload."""
    video, source, paths = make_run(tmp_path)
    video.write_bytes(b"x" * size)
    p = RecordingProvider()
    r = run_review(paths, source, video, p, None, gate=lambda: None, secrets={},
                   probe_fn=lambda _x: probe)
    assert r.status == "unreadable" and r.reason and p.calls == 0 and not r.items


# ---------------------------------------------------------------- TV4

def test_hallucinated_second_and_unknown_source_never_reach_items_or_exports(tmp_path):
    items = [item(time_s=99999, seen="farout"), item(time_s=-3, seen="negative"),
             item(source_id="other", seen="foreign"), item(time_s=DURATION + 0.1, seen="edge"),
             item(time_s=10, seen="good")]
    r = run(tmp_path, RecordingProvider([reply_of(items)]))
    assert [i.seen for i in r.items] == ["good"]
    assert sorted(x.reason for x in r.rejected) == (
        ["time_outside_recording"] * 3 + ["unknown_source"])
    for text in (render_markdown(r), render_review_html(r)):
        assert "good" in text
        assert not any(w in text for w in ("farout", "negative", "foreign", "edge"))
    assert all(0 <= i.time_s <= DURATION and i.source_id == SRC for i in r.items)


# ---------------------------------------------------------------- TV5 / TV6

TX = transcript((8.0, 14.0, "this save button does nothing"), (300.0, 305.0, "later remark"))


def test_narration_needs_a_verbatim_quote_from_an_overlapping_segment(tmp_path):
    items = [item(time_s=10, seen="real", origin="narration", quote="save button does nothing"),
             item(time_s=11, seen="fake", origin="narration", quote="the narrator said hello"),
             item(time_s=400, seen="far", origin="narration", quote="later remark"),
             item(time_s=12, seen="ptr", origin="pointer", pointer_line=99)]
    r = run(tmp_path, RecordingProvider([reply_of(items)]), TX, pointer_text="1:00")
    by = {i.seen: i for i in r.items}
    assert by["real"].origin == "narration" and by["real"].quote == "save button does nothing"
    for k in ("fake", "far", "ptr"):
        assert by[k].origin == "suspected" and by[k].downgrade and by[k].quote is None


def test_pointer_item_cites_its_line_and_transcript_file_is_untouched(tmp_path):
    sidecar = tmp_path / "t.json"
    sidecar.write_text('{"segments": []}', encoding="utf-8")
    before = file_sha256(sidecar)
    r = run(tmp_path, RecordingProvider([reply_of([item(origin="pointer", pointer_line=1)])]),
            TX, pointer_text="0:10 | look here")
    assert r.items[0].origin == "pointer" and r.items[0].pointer_line == 1
    assert file_sha256(sidecar) == before


FORBIDDEN = ("nothing was said", "no issues", "narrator agrees", "confirmed")


@pytest.mark.parametrize(("tx", "state", "phrase"), [
    (None, "none", "no narration on record"),
    (transcript(engine="none"), "none", "no narration on record"),
    (transcript(engine="unreadable"), "unreadable", "narration unreadable"),
])
def test_silence_and_unreadable_are_never_reported_as_nothing_said(tmp_path, tx, state, phrase):
    """No transcript / engine none / unreadable sidecar: no item may claim narration."""
    items = [item(origin="narration", quote="anything"), item(time_s=30, seen="v")]
    r = run(tmp_path, RecordingProvider([reply_of(items)]), tx)
    assert r.narration_state == state and not any(i.origin == "narration" for i in r.items)
    for text in (render_markdown(r), render_review_html(r)):
        assert phrase in text.lower()
        assert not any(w in text.lower() for w in FORBIDDEN)


def test_speech_elsewhere_reads_no_narration_at_this_moment(tmp_path):
    r = run(tmp_path, RecordingProvider([reply_of([item(time_s=100, seen="v")])]), TX)
    assert r.items[0].narration_note == "no narration at this moment"
    md = render_markdown(r)
    assert "no narration at this moment" in md and "nothing was said" not in md.lower()


# ---------------------------------------------------------------- TV8

CANARY = "Sup3rS3cretCanary!"


def test_a_planted_secret_never_reaches_disk_exports_logs_or_the_prompt(tmp_path, caplog):
    """A tester says their password aloud and types it in a pointer note."""
    tx = transcript((8.0, 14.0, f"my password is {CANARY} ok"))
    echo = item(time_s=10, origin="narration", quote=f"password is {CANARY} ok",
                seen=f"saw {CANARY}")
    p = RecordingProvider([reply_of([echo], summary=f"flow with {CANARY}")])
    with caplog.at_level(logging.DEBUG):
        r = run(tmp_path, p, tx, pointer_text=f"0:10 | note {CANARY}", secrets={"PW": CANARY})
    stored = (tmp_path / "root" / "projects" / "p" / "reviews" / f"{r.id}.json")
    blobs = [stored.read_text("utf-8"), render_markdown(r), render_review_html(r), caplog.text,
             *p.prompts]
    assert all(CANARY not in b for b in blobs)
    assert r.items[0].origin == "narration"          # the scrubbed quote still verifies


# ---------------------------------------------------------------- template

def test_prompt_template_carries_every_placeholder_and_a_lost_one_is_refused():
    tpl = load_template()
    assert all(ph in tpl for ph in PLACEHOLDERS)
    kw = {"source_id": SRC, "duration_s": 60.0, "times": [0.0], "parse": parse_pointers("", 60.0),
          "transcript": TX, "scrub": str, "max_items": 5}
    out = build_review_prompt(tpl, **kw)
    assert "this save button does nothing" in out and "{{" not in out
    with pytest.raises(ValueError, match="NARRATION"):
        build_review_prompt(tpl.replace("{{NARRATION}}", ""), **kw)


# ---------------------------------------------------------------- cycle 1 (checker F3, F4)

@pytest.mark.parametrize(("segment", "second", "kept"), [
    ((10.0, 12.0), 12.9, False),      # ends 0.9 s before the item
    ((100.8, 104.0), 100.0, False),   # starts 0.8 s after the item
    ((10.0, 12.0), 12.0, True),       # touches the item's second: overlap
    ((100.0, 104.0), 100.0, True),
    ((10.0, 12.0), 11.0, True),
])
def test_narration_must_strictly_overlap_the_items_second(tmp_path, segment, second, kept):
    """The model cites a second just outside the speech it quotes (F3, TV5 'overlaps')."""
    tx = transcript((*segment, "the quoted words"))
    r = run(tmp_path, RecordingProvider([reply_of([item(
        time_s=second, origin="narration", quote="the quoted words")])]), tx)
    assert r.items[0].origin == ("narration" if kept else "suspected")


def test_markdown_and_html_exports_carry_the_same_item_ids(tmp_path):
    """The reviewer exports both formats and compares item ids (F4, TV10)."""
    import re

    items = [item(time_s=10 + i, seen=f"s{i}") for i in range(4)]
    r = run(tmp_path, RecordingProvider([reply_of(items)]))
    md_ids = set(re.findall(r"\bit_[0-9a-f]+\b", render_markdown(r)))
    html_ids = set(re.findall(r'data-item-id="(it_[0-9a-f]+)"', render_review_html(r)))
    assert md_ids == html_ids == {i.id for i in r.items} and len(md_ids) == 4


def test_a_model_that_quotes_the_scrubbed_narration_keeps_a_scrubbed_quote(tmp_path):
    """TV8 mutation "skip the scrub on quotes": the model only ever saw scrubbed narration, so
    it quotes the scrubbed words. That must still count as a verbatim quote (the narration
    claim stays) and what is stored is scrubbed, with the raw secret nowhere."""
    from autotester.core.redact import Redactor

    spoken = f"my password is {CANARY} ok"
    scrubbed = Redactor({"K": CANARY}).scrub(spoken)
    assert CANARY not in scrubbed and scrubbed != spoken
    echo = item(time_s=10, origin="narration", quote=scrubbed, seen="typed it aloud")
    r = run(tmp_path, RecordingProvider([reply_of([echo])]), transcript((8.0, 14.0, spoken)),
            secrets={"K": CANARY})
    (kept,) = r.items
    assert kept.origin == "narration" and kept.downgrade is None
    assert kept.quote == scrubbed and CANARY not in r.model_dump_json()

