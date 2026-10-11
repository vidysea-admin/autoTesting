"""Seat B adversarial probes for t197 (throwaway; fake provider only, no network)."""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

W = Path("D:/autoTesting/.worktrees/t197-video-pointers")
sys.path.insert(0, str(W / "tests"))
os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "b-seat-fake-signing-key")

from run_approval_fixture import grant_live_case_approval  # noqa: E402
from typer.testing import CliRunner  # noqa: E402
from video_review_fakes import RecordingProvider, item, reply_of  # noqa: E402

from autotester import providers  # noqa: E402
from autotester.cli import app  # noqa: E402
from autotester.providers.base import ProviderError  # noqa: E402
from autotester.schema.enums import ApprovalKind  # noqa: E402
from autotester.schema.media import Transcript, TranscriptSegment  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.stages.ingest import register_source  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

runner = CliRunner()
DURATION = 130


@pytest.fixture(scope="module")
def video_file(tmp_path_factory):
    out = tmp_path_factory.mktemp("bv") / "rec.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=blue:s=64x48:r=1:d={DURATION}",
                    "-f", "lavfi", "-i", f"sine=f=440:d={DURATION}", "-shortest",
                    "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", str(out)],
                   check=True, capture_output=True, timeout=120)
    return out


def make_world(tmp_path, video_file, monkeypatch, replies=None):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    source = register_source(store, video_file, label="rec")
    provider = RecordingProvider(replies or [reply_of([item(source_id=source.id, time_s=70)])] * 50)
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: provider)
    return store, source, provider


@pytest.fixture
def world(tmp_path, video_file, monkeypatch):
    return (*make_world(tmp_path, video_file, monkeypatch), tmp_path)


def grant(store, **over):
    kw = {"project": "demo", "target": "fake", "max_actions": 500,
          "run_kind": ApprovalKind.VIDEO_REVIEW}
    return grant_live_case_approval(store, **{**kw, **over})


def review(source, *args, json_out=True):
    return runner.invoke(app, ["ingest", "review", "demo", source.id,
                               *(["--output", "json"] if json_out else []), *args])


def ptr(tmp, text, name="p.txt"):
    p = tmp / name
    p.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
    return str(p)


# ---- 1. approval gate -------------------------------------------------------------------
@pytest.mark.parametrize("over", [
    {"project": "other"}, {"target": "gemini"}, {"target": "FAKE"}, {"target": "fake "},
    {"run_kind": ApprovalKind.CRAWL}, {"run_kind": ApprovalKind.LIVE_CASE},
    {"run_kind": ApprovalKind.ADVERSARIAL}, {"run_kind": ApprovalKind.READ},
    {"sign": False}, {"expires_at": "2020-01-01"}, {"expires_at": "garbage"},
    {"max_actions": 1}, {"max_actions": 0}])
def test_gate_matrix(world, over):
    store, source, provider, tmp = world
    grant(store, **over)
    r = review(source, "--pointers", ptr(tmp, "0:10-2:00\n"))
    assert r.exit_code == 3, r.output
    assert provider.calls == 0
    assert not (store.paths.dir / "reviews").exists()


def _edit_rows(store, fn):
    path = store.paths.dir / "approvals.jsonl"
    rows = [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]
    path.write_text("\n".join(json.dumps(fn(r)) for r in rows) + "\n", "utf-8")


@pytest.mark.parametrize("tamper", ["widen", "widen_keep_id_drop_sig", "drop_id_keep_sig",
                                    "retarget", "kind_swap", "forged_key"])
def test_tampered_rows(world, tamper, monkeypatch):
    store, source, provider, tmp = world
    if tamper == "forged_key":
        monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", "attacker-key")
        grant(store)
        monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", "b-seat-fake-signing-key")
    else:
        grant(store, max_actions=1, target="gemini" if tamper == "retarget" else "fake",
              run_kind=ApprovalKind.CRAWL if tamper == "kind_swap" else ApprovalKind.VIDEO_REVIEW)

        def fn(r):
            if tamper == "widen":
                r["max_actions"] = 9999
            elif tamper == "widen_keep_id_drop_sig":
                r["max_actions"] = 9999
                r["signature"] = ""
            elif tamper == "drop_id_keep_sig":
                r["max_actions"] = 9999
                r.pop("id")
            elif tamper == "retarget":
                r["target"] = "fake"
            elif tamper == "kind_swap":
                r["run_kind"] = "video_review"
            return r
        _edit_rows(store, fn)
    r = review(source, "--pointers", ptr(tmp, "0:10-2:00\n"))
    assert r.exit_code == 3, r.output
    assert provider.calls == 0


def test_valid_baseline_works(world):
    store, source, provider, tmp = world
    grant(store)
    assert review(source).exit_code == 0 and provider.calls >= 1


def test_direct_run_review_needs_gate_and_noop_gate_passes(tmp_path):
    from autotester.stages.video_review import run_review
    from video_review_fakes import run
    with pytest.raises(TypeError):
        run_review(None, None, None, None, None, secrets={})
    prov = RecordingProvider([reply_of([item()])] * 3)
    run(tmp_path / "b", prov)  # helper passes gate=lambda: None
    assert prov.calls >= 1  # the stage trusts whatever gate it is handed


def test_approval_not_consumed_by_use(world):
    store, source, provider, tmp = world
    from autotester.stages.video_review import preview_review
    n = preview_review(Path(source.path), "", [], provider_label="fake").call_count
    grant(store, max_actions=n)
    for _ in range(3):
        assert review(source, "--refresh").exit_code == 0
    print("approval of", n, "actions allowed", provider.calls, "calls over 3 runs")
    assert provider.calls == 3 * n


def test_cached_review_still_needs_approval_and_makes_no_call(world):
    store, source, provider, tmp = world
    grant(store)
    assert review(source).exit_code == 0
    calls = provider.calls
    (store.paths.dir / "approvals.jsonl").write_text("", "utf-8")
    r = review(source)
    assert r.exit_code == 3 and provider.calls == calls


def _snap(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size)
                  for p in root.rglob("*"))


def test_dry_run_zero_calls_writes_nothing(world):
    store, source, provider, tmp = world
    pf = ptr(tmp, "0:10-2:00\n", "pp.txt")
    before = _snap(tmp)
    r = review(source, "--dry-run", "--redact", "1:00-1:10", "--pointers", pf)
    after = _snap(tmp)
    assert r.exit_code == 0 and provider.calls == 0
    assert before == after, set(after) ^ set(before)


def test_dry_run_with_bad_pointers_exit_2(world):
    store, source, provider, tmp = world
    r = review(source, "--dry-run", "--pointers", ptr(tmp, "99:99\n"))
    assert r.exit_code == 2 and provider.calls == 0


# ---- 4. spend cap ----------------------------------------------------------------------
@pytest.mark.parametrize("cap", ["nan", "inf", "-1", "0", "1e-9", "-0.0"])
def test_cap_values(world, cap):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--max-cost", cap, "--pointers", ptr(tmp, "0:10-2:00\n"))
    doc = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    print("CAP", cap, "exit", r.exit_code, "status", doc.get("status"), "calls", provider.calls)
    if cap == "nan":
        pass


# ---- 5. input handling -----------------------------------------------------------------
@pytest.mark.parametrize("text,code", [
    ("", 0), ("\n\n", 0), ("0:00\n", 0), ("2:10\n", 2), ("2:09\n", 0), ("nan\n", 0),
    ("1e3\n", 0), ("-0:10\n", 2), ("0:10-0:10\n", 2), ("0:10-2:11\n", 2), ("0:10-2:10\n", 0),
    ("999999999999:00\n", 2), ("0:10\n0:10\n0:10\n0:10\n", 0), ("a\nb\nc\nd\n", 2),
    ("|\n", 2), ("0:10|\n", 0), ("٣:٠٠\n", 0), ("１:００\n", 0), ("0:10\x00\n", 0),
    ("\ufeff0:10\r\n", 0)])
def test_pointer_inputs(world, text, code):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--pointers", ptr(tmp, text))
    print(repr(text), "->", r.exit_code, "calls", provider.calls)
    if code == 2:
        assert r.exit_code == 2 and provider.calls == 0


def test_pointers_path_is_dir_and_nonutf8(world):
    store, source, provider, tmp = world
    grant(store)
    assert review(source, "--pointers", str(tmp)).exit_code == 1
    assert review(source, "--pointers", ptr(tmp, b"\xff\xfe\x00bad")).exit_code == 1
    assert review(source, "--pointers", str(tmp / "nope.txt")).exit_code == 1
    assert provider.calls == 0


def test_oversized_free_pointer_reaches_prompt(world):
    store, source, provider, tmp = world
    grant(store)
    big = "x" * 3_000_000
    r = review(source, "--pointers", ptr(tmp, big + "\n"))
    print("big free pointer exit", r.exit_code, "calls", provider.calls,
          "max prompt len", max((len(p) for p in provider.prompts), default=0))


def test_many_pointer_lines_time(world):
    store, source, provider, tmp = world
    grant(store)
    text = "\n".join(f"{(i % 120) // 60}:{(i % 60):02d}" for i in range(60000)) + "\n"
    t0 = time.time()
    r = review(source, "--pointers", ptr(tmp, text))
    print("60k lines exit", r.exit_code, "secs", round(time.time() - t0, 1), "calls", provider.calls,
          "max prompt", max((len(p) for p in provider.prompts), default=0))


def test_slug_traversal_writes_nothing_outside(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    r = runner.invoke(app, ["ingest", "review", "../../evil", "src_x", "--dry-run"])
    print("slug traversal exit", r.exit_code)
    assert not (tmp_path / "evil").exists()
    assert r.exit_code == 1


def test_audio_only_exit_4_beats_pointer_errors(world):
    store, source, provider, tmp = world
    a = tmp / "audio.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=440:d=5", "-c:a", "aac", str(a)],
                   check=True, capture_output=True)
    s2 = register_source(store, a, label="a")
    r = runner.invoke(app, ["ingest", "review", "demo", s2.id, "--output", "json"])
    assert r.exit_code == 4 and provider.calls == 0
    r = runner.invoke(app, ["ingest", "review", "demo", s2.id, "--pointers", ptr(tmp, "99:99\n")])
    assert r.exit_code == 4


# ---- 3. redaction / egress --------------------------------------------------------------
def test_noop_blackout_stops_the_call_and_what_is_left_on_disk(world, monkeypatch):
    store, source, provider, tmp = world
    grant(store)
    import autotester.media.redacted as red

    def fake_redact(video, windows, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(video, out)
        return out
    monkeypatch.setattr(red, "redact_video", fake_redact)
    r = review(source, "--redact", "0:55-1:15")
    print("noop blackout exit", r.exit_code, r.output[-200:])
    assert r.exit_code == 3 and provider.calls == 0
    left = [p for p in (store.paths.dir / "reviews").rglob("*") if p.is_file()]
    print("LEFT ON DISK after failed blackout:", [str(p.relative_to(tmp)) for p in left])


def test_redacted_run_paths_and_files(world):
    store, source, provider, tmp = world
    grant(store)
    r = review(source, "--redact", "0:55-1:15", "--redact", "0:00-0:03",
               "--pointers", ptr(tmp, "0:10-2:00\n"))
    assert r.exit_code == 0, r.output
    rid = json.loads(r.stdout)["id"]
    work = store.paths.dir / "reviews" / rid
    handed = {Path(p).resolve() for p in provider.paths}
    assert all(work.resolve() in p.parents for p in handed)
    assert all(p.suffix == ".png" for p in handed)
    assert not any(55 <= t <= 75 or t <= 3 for t in provider.frame_times), provider.frame_times
    files = sorted(p.name for p in work.rglob("*") if p.is_file() and p.suffix != ".png")
    print("work dir non-png:", files)
    assert str(Path(source.path).resolve()) not in "".join(provider.prompts)


def test_redact_edge_windows(world):
    store, source, provider, tmp = world
    grant(store)
    for spec in ["0:00-0:05", "2:00-2:10", "0:00-2:10"]:
        provider.calls = 0
        provider.frame_times = []
        r = review(source, "--redact", spec, "--refresh")
        print("edge window", spec, "exit", r.exit_code, "calls", provider.calls,
              "frames", sorted(set(provider.frame_times))[:6])


# ---- 3/8 secrets -----------------------------------------------------------------------
CANARY = "hunter2-canary-xyz-9071"


def _with_secret(store, tmp, undeclared=False):
    (tmp / ".env").write_text(f"DEMO_PASSWORD={CANARY}\n", "utf-8")
    if not undeclared:
        proj = store.load_project()
        store.save_project(proj.model_copy(update={"secrets": [
            SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]}))


@pytest.mark.parametrize("undeclared", [False, True])
@pytest.mark.parametrize("where", ["note", "free", "transcript", "provider_error", "reply_item"])
def test_canary(world, caplog, where, undeclared):
    store, source, provider, tmp = world
    _with_secret(store, tmp, undeclared)
    grant(store)
    caplog.set_level(logging.DEBUG)
    args = []
    if where == "note":
        args = ["--pointers", ptr(tmp, f"1:00 | pw is {CANARY}\n")]
    elif where == "free":
        args = ["--pointers", ptr(tmp, f"the password {CANARY} is shown\n")]
    elif where == "transcript":
        store.save_transcript(Transcript(source_id=source.id, engine="sidecar", segments=[
            TranscriptSegment(start=60, end=70, text=f"type {CANARY} now")]))
    elif where == "provider_error":
        provider.replies = [ProviderError(f"upstream said {CANARY}")]
    elif where == "reply_item":
        provider.replies = [reply_of([item(source_id=source.id, time_s=70,
                                           seen=f"shows {CANARY}", suggestion=f"quote {CANARY}",
                                           screen=f"S {CANARY}")], summary=f"sum {CANARY}")] * 20
    r = review(source, *args)
    out = r.stdout + r.stderr
    hits = []
    rev = store.paths.dir / "reviews"
    for p in (rev.rglob("*") if rev.exists() else []):
        if p.is_file() and p.suffix in (".json", ".md", ".html", ".txt") \
                and CANARY in p.read_text("utf-8", "ignore"):
            hits.append(str(p.relative_to(tmp)))
    if CANARY in out:
        hits.append("stdio")
    if CANARY in caplog.text:
        hits.append("log")
    sent = [p for p in provider.prompts if CANARY in p]
    print(where, "undeclared" if undeclared else "declared", "exit", r.exit_code, "hits", hits,
          "prompts_with_canary", len(sent))
    assert not hits and not sent


@pytest.mark.parametrize("enc", ["b64", "hex", "rev", "pct"])
def test_encoded_canary_refused(world, enc):
    store, source, provider, tmp = world
    _with_secret(store, tmp)
    grant(store)
    v = {"b64": base64.b64encode(CANARY.encode()).decode(), "hex": CANARY.encode().hex(),
         "rev": CANARY[::-1], "pct": "".join(f"%{b:02x}" for b in CANARY.encode())}[enc]
    r = review(source, "--pointers", ptr(tmp, f"1:00 | {v}\n"))
    out = r.stdout + r.stderr
    print(enc, "exit", r.exit_code, "calls", provider.calls, "raw canary in output:", CANARY in out)
    assert provider.calls == 0 and CANARY not in out


def test_scrub_values_not_logged_in_repr(world):
    store, source, provider, tmp = world
    _with_secret(store, tmp)
    from autotester.browser.secrets import SecretStore
    st = SecretStore.load(store.load_project(), store.paths.env_file, strict=False)
    print("repr:", repr(st)[:160])
    assert CANARY not in repr(st) + str(st)
    assert CANARY in st.scrub_values().values().__iter__().__next__()  # raw by design


# ---- 6. determinism --------------------------------------------------------------------
def test_determinism(tmp_path, video_file, monkeypatch):
    outs = []
    for i in range(2):
        root = tmp_path / f"r{i}"
        root.mkdir()
        store, source, provider = make_world(root, video_file, monkeypatch)
        grant(store)
        r = review(source, "--redact", "0:55-1:15", "--pointers", ptr(root, "0:10-2:00 | n\n1:00\n"))
        assert r.exit_code == 0, r.output
        rid = json.loads(r.stdout)["id"]
        outs.append((rid, (store.paths.dir / "reviews" / f"{rid}.json").read_bytes(), r.stdout))
        time.sleep(1.1)
    assert outs[0][0] == outs[1][0]
    assert outs[0][1] == outs[1][1], "stored review bytes differ"
    assert outs[0][2] == outs[1][2], "stdout differs"
