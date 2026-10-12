"""`autotester ingest review` through the REAL CLI: exit codes, JSON, approval, dry-run (T-197).

Contract: qa/contracts/team-video-review.md TV1 (CLI half), TV3 (exit 4), TV7 (2, 4), TV8, TV10
(idempotent). The provider is a recording fake (no model call is real); the recording is a real
130 s video cut by ffmpeg, so probing, frame cutting and blackout are the shipped code. Skipped
whole when ffmpeg is absent, like `test_video_review_redaction.py` (a skip is not evidence).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval
from typer.testing import CliRunner
from video_review_fakes import RecordingProvider, item, reply_of

from autotester import providers
from autotester.cli import app
from autotester.media.probe import ffmpeg_available
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project, Source
from autotester.stages.ingest import register_source
from autotester.store.project_store import ProjectStore

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
runner = CliRunner()
DURATION = 130


@pytest.fixture(scope="module")
def video_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("cliv") / "rec.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=blue:s=64x48:r=1:d={DURATION}",
                    "-c:v", "libx264", "-preset", "veryfast", str(out)],
                   check=True, capture_output=True, timeout=120)
    return out


@pytest.fixture
def world(tmp_path: Path, video_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    source = register_source(store, video_file, label="rec")
    provider = RecordingProvider([reply_of([item(source_id=source.id, time_s=70)])] * 20)
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: provider)
    return store, source, provider, tmp_path


def grant(store: ProjectStore, **over: object) -> None:
    kw: dict[str, object] = {"project": "demo", "target": "fake", "max_actions": 500,
                             "run_kind": ApprovalKind.VIDEO_REVIEW}
    grant_live_case_approval(store, **{**kw, **over})  # type: ignore[arg-type]


def review(source: Source, *args: str, json_out: bool = True):
    return runner.invoke(app, ["ingest", "review", "demo", source.id,
                               *(["--output", "json"] if json_out else []), *args])


def pointers(tmp: Path, text: str) -> str:
    path = tmp / "pointers.txt"
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def test_pointer_errors_exit_2_list_every_error_and_never_call_the_provider(world):
    store, source, provider, tmp = world
    grant(store)
    bad = "99:99\n1:00 | fine\n14:00-12:30\n-1:00\n2:00 | ok\n"
    r = review(source, "--pointers", pointers(tmp, bad), json_out=False)
    assert r.exit_code == 2
    for n in (1, 3, 4):
        assert f"line {n}" in r.output
    assert provider.calls == 0


def test_pointer_errors_in_json_mode_are_one_valid_document_on_stdout(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--pointers", pointers(tmp, "99:99\n14:00-12:30\n3:00:00\n"))
    assert r.exit_code == 2
    doc = json.loads(r.stdout)
    assert doc["status"] == "pointer_errors"
    assert [e["line_no"] for e in doc["errors"]] == [1, 2, 3]
    assert provider.calls == 0


def test_a_time_past_the_recording_is_refused_not_clamped(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--pointers", pointers(tmp, f"{DURATION // 60 + 1}:00\n"))
    assert r.exit_code == 2 and provider.calls == 0


def test_no_approval_exits_3_names_the_grant_and_makes_zero_calls(world):
    _, source, provider, _ = world
    r = review(source, json_out=False)
    assert r.exit_code == 3, r.output
    assert "video_review" in r.output and "approve" in r.output
    assert provider.calls == 0


@pytest.mark.parametrize("over", [
    {"project": "other"},                      # an approval for another project
    {"target": "gemini"},                      # an approval for another provider
    {"run_kind": ApprovalKind.CRAWL},          # an approval of another kind
    {"sign": False},                           # an unsigned (forged-shape) row
    {"expires_at": "2020-01-01"},              # an expired one
    {"max_actions": 1},                        # narrower than the plan's call count
])
def test_an_approval_that_does_not_cover_this_review_does_not_count(world, over):
    store, source, provider, tmp = world
    grant(store, **over)
    r = review(source, "--pointers", pointers(tmp, "0:10-2:00\n"))
    assert r.exit_code == 3, r.output
    assert provider.calls == 0


def test_approved_run_is_valid_json_on_stdout_and_never_hands_over_the_original(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--pointers", pointers(tmp, "1:00-1:30 | save is slow\n"))
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)
    assert doc["status"] == "ok" and doc["id"].startswith("rv_") and doc["items"]
    assert provider.calls >= 1
    assert all(Path(p).resolve() != Path(source.path).resolve() for p in provider.paths)
    assert all(Path(p).suffix == ".png" for p in provider.paths)
    assert r.stderr.strip()          # progress notes go to stderr, never into the JSON document


def test_dry_run_prints_the_plan_with_zero_calls_and_needs_no_approval(world):
    _, source, provider, tmp = world
    r = review(source, "--dry-run", "--redact", "1:00-1:10",
               "--pointers", pointers(tmp, "0:10-2:00\n"))
    assert r.exit_code == 0, r.output
    plan = json.loads(r.stdout)
    assert plan["call_count"] >= 2 and plan["redacted_frame_count"] >= 1
    assert plan["windows"] == [{"start_s": 60.0, "end_s": 70.0}]
    assert provider.calls == 0


def test_redaction_window_frames_never_reach_the_provider(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--redact", "0:55-1:15", "--pointers", pointers(tmp, "0:10-2:00\n"))
    assert r.exit_code == 0, r.output
    assert provider.frame_times and not any(55 <= t <= 75 for t in provider.frame_times)
    assert json.loads(r.stdout)["redaction_windows"] == [{"start_s": 55.0, "end_s": 75.0}]


def test_spend_cap_gives_a_partial_review_naming_what_was_left(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--max-cost", "0.000001", "--pointers", pointers(tmp, "0:10-2:00\n"))
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)
    assert doc["status"] == "partial" and doc["not_reviewed"] and provider.calls == 1


def test_text_mode_says_in_words_which_spans_were_not_reviewed(world):
    store, source, _, _ = world
    grant(store)
    r = review(source, "--redact", "0:55-1:15", json_out=False)
    assert r.exit_code == 0, r.output
    assert "Not reviewed" in r.output and "Redacted on request" in r.output


def test_a_second_run_returns_the_stored_review_without_new_calls(world):
    store, source, provider, _ = world
    grant(store)
    first = json.loads(review(source).stdout)
    calls = provider.calls
    second = json.loads(review(source).stdout)
    assert second["id"] == first["id"] and provider.calls == calls


@pytest.mark.parametrize("body", [b"", b"this is not a video"])
def test_unreadable_media_exits_4_before_any_approval_or_call(world, body):
    store, _, provider, tmp = world
    bad = tmp / "bad.mp4"
    bad.write_bytes(body)
    source = register_source(store, bad, label="bad")
    r = review(source)
    assert r.exit_code == 4, r.output
    assert json.loads(r.stdout)["status"] == "unreadable"
    assert provider.calls == 0


def test_unknown_source_and_bad_redact_spec_are_usage_errors_exit_1(world):
    store, source, provider, _ = world
    grant(store)
    nosrc = runner.invoke(app, ["ingest", "review", "demo", "src_nope"])
    bad = review(source, "--redact", "not-a-window")
    assert nosrc.exit_code == 1 and bad.exit_code == 1
    assert provider.calls == 0


def test_a_planted_secret_in_a_pointer_note_stays_out_of_prompt_and_output(world):
    store, source, provider, tmp = world
    (tmp / ".env").write_text("DEMO_PASSWORD=hunter2-canary-xyz\n", encoding="utf-8")
    proj = store.load_project()
    from autotester.schema.project import SecretRef
    store.save_project(proj.model_copy(update={"secrets": [
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]}))
    grant(store)
    r = review(source, "--pointers", pointers(tmp, "1:00 | password is hunter2-canary-xyz\n"))
    assert r.exit_code == 0, r.output
    assert "hunter2-canary-xyz" not in r.stdout + r.stderr
    assert not any("hunter2-canary-xyz" in p for p in provider.prompts)
    stored = "".join(p.read_text(encoding="utf-8") for p in tmp.rglob("*.json")
                     if "reviews" in str(p) or "review" in p.name)
    assert "hunter2-canary-xyz" not in stored
