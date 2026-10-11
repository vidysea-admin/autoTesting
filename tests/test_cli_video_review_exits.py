"""`ingest review --output json`: ONE valid JSON document on stdout for EVERY exit code (T-197).

Contract: qa/contracts/team-video-review.md "CLI contract": exit 0 ok, 2 pointer errors, 3
approval or permission missing, 4 source unreadable, 1 usage; "`--output json` is a valid
document on stdout with logs on stderr". Also the non-finite spend cap (P2), the pointer size
limits (P5) and `--dry-run` writing nothing. Real CLI, real ffmpeg, fake provider.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import test_cli_video_review as base

from autotester.cli import app
from autotester.schema.project import SecretRef
from autotester.stages.ingest import register_source
from autotester.stages.video_pointers import (
    MAX_POINTER_FILE_BYTES,
    MAX_POINTER_LINES,
    MAX_POINTER_NOTE_CHARS,
)

grant, pointers, review, runner = base.grant, base.pointers, base.review, base.runner
video_file, world = base.video_file, base.world     # shared fixtures


def _doc(r) -> dict:
    """stdout must be exactly one JSON document, nothing before or after it."""
    return json.loads(r.stdout)


def _unavailable(world):
    world[2].available = lambda: False
    return review(world[1])


def _bad_media(world):
    store, _, _, tmp = world
    bad = tmp / "bad.mp4"
    bad.write_bytes(b"this is not a video")
    return review(register_source(store, bad, label="bad"))


CASES = {
    "ok-0": (0, lambda w: (grant(w[0]), review(w[1]))[1]),
    "dry-run-0": (0, lambda w: review(w[1], "--dry-run")),
    "unknown-source-1": (1, lambda w: runner.invoke(
        app, ["ingest", "review", "demo", "src_nope", "--output", "json"])),
    "unknown-project-1": (1, lambda w: runner.invoke(
        app, ["ingest", "review", "ghost", "src_x", "--output", "json"])),
    "bad-redact-1": (1, lambda w: review(w[1], "--redact", "not-a-window")),
    "missing-pointer-file-1": (1, lambda w: review(w[1], "--pointers", str(w[3] / "nope.txt"))),
    "provider-unavailable-1": (1, _unavailable),
    "nan-cap-1": (1, lambda w: (grant(w[0]), review(w[1], "--max-cost", "nan"))[1]),
    "inf-cap-1": (1, lambda w: (grant(w[0]), review(w[1], "--max-cost", "inf"))[1]),
    "negative-cap-1": (1, lambda w: (grant(w[0]), review(w[1], "--max-cost", "-1"))[1]),
    "dry-run-bad-redact-1": (1, lambda w: review(w[1], "--dry-run", "--redact", "x")),
    "pointer-errors-2": (2, lambda w: (grant(w[0]), review(
        w[1], "--pointers", pointers(w[3], "99:99\n")))[1]),
    "no-approval-3": (3, lambda w: review(w[1])),
    "unreadable-4": (4, _bad_media),
}


@pytest.mark.parametrize("name", list(CASES))
def test_every_exit_path_writes_exactly_one_json_document_to_stdout(world, name):
    code, call = CASES[name]
    store, source, provider, tmp = world
    (tmp / ".env").write_text("DEMO_PASSWORD=hunter2-canary-xyz\n", encoding="utf-8")
    store.save_project(store.load_project().model_copy(update={"secrets": [
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]}))
    r = call((store, source, provider, tmp))
    assert r.exit_code == code, r.output
    doc = _doc(r)
    assert isinstance(doc, dict) and (doc.get("status") or "call_count" in doc)   # a plan
    if code:
        assert doc["exit_code"] == code
        assert doc.get("reason") or doc.get("errors")
        assert r.stderr.strip()                      # the human note still goes to stderr
    assert "hunter2-canary-xyz" not in r.stdout
    assert str(tmp) not in r.stdout and tmp.name not in r.stdout   # no path outside the project
    if code in (1, 3):
        assert set(doc) == {"status", "reason", "exit_code"}
        assert doc["status"] == ("refused" if code == 3 else "usage_error")


def test_the_refusal_document_names_the_grant_and_made_no_calls(world):
    _, source, provider, _ = world
    r = review(source)
    assert r.exit_code == 3 and provider.calls == 0
    assert "approve" in _doc(r)["reason"] and "video_review" in _doc(r)["reason"]


@pytest.mark.parametrize("cap", ["nan", "inf", "-inf", "-1", "NaN"])
def test_a_non_finite_or_negative_spend_cap_is_a_usage_error_not_no_cap(world, cap):
    store, source, provider, _ = world
    grant(store)
    r = review(source, "--max-cost", cap)
    assert r.exit_code == 1 and provider.calls == 0
    assert _doc(r)["status"] == "usage_error" and "--max-cost" in _doc(r)["reason"]


def test_a_finite_cap_still_works(world):
    store, source, provider, _ = world
    grant(store)
    assert math.isfinite(0.25)
    r = review(source, "--max-cost", "0.25")
    assert r.exit_code == 0 and provider.calls >= 1


def test_dry_run_writes_nothing_anywhere(world):
    _, source, provider, tmp = world
    ptr = pointers(tmp, "0:10-2:00\n")
    before = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*"))
    r = review(source, "--dry-run", "--redact", "1:00-1:10", "--pointers", ptr)
    assert r.exit_code == 0 and provider.calls == 0
    after = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*"))
    assert after == before and not (tmp / "projects" / "demo" / "reviews").exists()


def test_a_real_run_leaves_only_the_stored_review_and_no_media(world):
    store, source, _, tmp = world
    grant(store)
    r = review(source, "--redact", "1:00-1:10", "--pointers", pointers(tmp, "0:10-2:00\n"))
    assert r.exit_code == 0, r.output
    listing = sorted(p.name for p in (tmp / "projects" / "demo" / "reviews").rglob("*"))
    assert listing == [f"{_doc(r)['id']}.json"]


def test_a_too_long_note_is_a_pointer_error_with_the_whole_list(world):
    store, source, provider, tmp = world
    grant(store)
    long = "x" * (MAX_POINTER_NOTE_CHARS + 1)
    text = f"1:00 | {long}\n99:99\nfree {long}\n2:00 | fine\n"
    r = review(source, "--pointers", pointers(tmp, text))
    assert r.exit_code == 2 and provider.calls == 0
    assert [e["line_no"] for e in _doc(r)["errors"]] == [1, 2, 3]
    assert long not in r.stdout + r.stderr


def test_too_many_pointer_lines_is_a_pointer_error_naming_each_extra_line(world):
    store, source, provider, tmp = world
    grant(store)
    text = "".join(f"0:{n % 60:02d} | note {n}\n" for n in range(MAX_POINTER_LINES + 3))
    r = review(source, "--pointers", pointers(tmp, text))
    assert r.exit_code == 2 and provider.calls == 0
    assert [e["line_no"] for e in _doc(r)["errors"]] == [
        MAX_POINTER_LINES + 1, MAX_POINTER_LINES + 2, MAX_POINTER_LINES + 3]


def test_an_oversized_pointer_file_is_refused_unread_and_never_sent(world, monkeypatch):
    store, source, provider, tmp = world
    grant(store)
    big = tmp / "big.txt"
    big.write_bytes(b"a" * (MAX_POINTER_FILE_BYTES + 1))
    real = Path.read_bytes

    def guarded(self):
        assert self != big, "the oversized pointer file was read into memory"
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    r = review(source, "--pointers", str(big))
    assert r.exit_code == 2 and provider.calls == 0
    errors = _doc(r)["errors"]
    assert len(errors) == 1 and "bytes" in errors[0]["reason"]
    assert Path(big).name not in r.stdout


# --- fix cycle 2: usage errors, unexpected exceptions, interrupts, exit_code everywhere ---------

def _args(source, *extra: str, output: bool = True) -> list[str]:
    return ["ingest", "review", "demo", source.id, *(["--output", "json"] if output else []),
            *extra]


USAGE_ERRORS = {
    "cap-abc": ["--max-cost", "abc"],
    "cap-empty": ["--max-cost", ""],
    "cap-hex": ["--max-cost", "0x10"],
    "unknown-option": ["--bogus"],
    "output-without-value-after-json": ["--output"],       # json was already named earlier
}


@pytest.mark.parametrize("name", list(USAGE_ERRORS))
def test_a_click_usage_error_is_one_json_document_and_not_the_pointer_error_code(world, name):
    store, source, provider, _ = world
    grant(store)
    r = runner.invoke(app, _args(source, *USAGE_ERRORS[name]))
    assert r.exit_code == 1, r.output                  # 2 is the pointer-errors code
    assert _doc(r) == {"status": "usage_error", "reason": _doc(r)["reason"], "exit_code": 1}
    assert _doc(r)["reason"] and r.stderr.strip() and provider.calls == 0


def test_a_missing_source_argument_is_a_json_usage_error(world):
    r = runner.invoke(app, ["ingest", "review", "demo", "--output", "json"])
    assert r.exit_code == 1 and _doc(r)["status"] == "usage_error" and _doc(r)["exit_code"] == 1


def test_the_equals_form_of_the_json_flag_is_recognised_too(world):
    _, source, _, _ = world
    r = runner.invoke(app, ["ingest", "review", "demo", source.id, "--output=json", "--bogus"])
    assert r.exit_code == 1 and _doc(r)["status"] == "usage_error"


def test_a_usage_error_without_json_stays_text_and_still_avoids_exit_2(world):
    """Text mode (and `--output` with no value anywhere, so json is unknowable) stays text on
    stderr with an empty stdout; the exit code is still 1, never the pointer-errors 2."""
    _, source, _, _ = world
    bare = [*_args(source, output=False), "--output"]
    for argv in (_args(source, "--bogus", output=False), bare):
        r = runner.invoke(app, argv)
        assert r.exit_code == 1 and r.stdout == "" and r.stderr.strip(), argv


@pytest.mark.parametrize("boom", [RuntimeError, OSError], ids=["runtime", "oserror"])
def test_an_unexpected_provider_exception_is_one_json_failure_with_no_secret_or_path(
        world, monkeypatch, boom):
    store, source, provider, tmp = world
    grant(store)
    (tmp / ".env").write_text("DEMO_PASSWORD=hunter2-canary-xyz\n", encoding="utf-8")
    store.save_project(store.load_project().model_copy(update={"secrets": [
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]}))
    video = Path(next(s for s in store.list_sources() if s.id == source.id).path)

    def explode(*_a, **_k):
        raise boom(f"hunter2-canary-xyz at {video} and {video.name}")

    monkeypatch.setattr(provider, "judge", explode)
    r = runner.invoke(app, _args(source))
    assert r.exit_code == 1, r.output
    doc = _doc(r)
    assert doc["status"] == "internal_error" and doc["exit_code"] == 1
    assert set(doc) == {"status", "reason", "exit_code"} and boom.__name__ in doc["reason"]
    for leak in ("hunter2-canary-xyz", str(video), video.name):
        assert leak not in r.stdout + r.stderr
    assert "Traceback" not in r.stderr
    assert not any((tmp / "projects" / "demo").rglob("rv_*"))      # scratch and review: none


def test_ctrl_c_is_one_json_interrupted_document_exit_130_and_cleans_the_scratch(
        world, monkeypatch):
    store, source, provider, tmp = world
    grant(store)

    def interrupt(*_a, **_k):
        raise KeyboardInterrupt

    monkeypatch.setattr(provider, "judge", interrupt)
    r = runner.invoke(app, _args(source, "--redact", "1:00-1:10"))
    assert r.exit_code == 130, r.output
    assert _doc(r)["status"] == "interrupted" and _doc(r)["exit_code"] == 130
    assert set(_doc(r)) == {"status", "reason", "exit_code"}
    assert not any((tmp / "projects" / "demo").rglob("rv_*"))


@pytest.mark.parametrize("extra", [[], ["--dry-run"], ["--max-cost", "1e-9"], ["--max-cost", "0"]],
                         ids=["ok", "dry-run", "partial", "failed"])
def test_every_success_dry_run_partial_and_failed_document_carries_the_real_exit_code(
        world, extra):
    store, source, _, _ = world
    grant(store)
    r = runner.invoke(app, _args(source, *extra))
    doc = _doc(r)
    assert doc["exit_code"] == r.exit_code
    assert {"ok": 0, "partial": 0, "failed": 1}.get(doc.get("status", "dry"), 0) == r.exit_code


def test_exit_code_is_an_envelope_key_not_a_stored_field_and_old_reviews_still_load(world):
    from autotester.schema.video_review import VideoReview
    store, source, _, tmp = world
    grant(store)
    doc = _doc(runner.invoke(app, _args(source)))
    stored = next((tmp / "projects" / "demo" / "reviews").glob("rv_*.json"))
    on_disk = json.loads(stored.read_text(encoding="utf-8"))
    assert "exit_code" not in on_disk and VideoReview.model_validate(on_disk).id == doc["id"]
    assert VideoReview.model_validate({k: v for k, v in doc.items() if k != "exit_code"})
    again = _doc(runner.invoke(app, _args(source)))               # a stored review is re-served
    assert again["exit_code"] == 0 and again["id"] == doc["id"]
