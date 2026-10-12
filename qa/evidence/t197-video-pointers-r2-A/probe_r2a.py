"""Checker A (r2) probes for t197-video-pointers. Scratch only; never part of the unit."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import test_cli_video_review as base

from autotester.cli import app
from autotester.schema.project import SecretRef

grant, review, runner, world = base.grant, base.review, base.runner, base.world
video_file = base.video_file


def _argv(source, *extra):
    return ["ingest", "review", "demo", source.id, *extra]


def _one_doc_or_empty(r):
    return json.loads(r.stdout) if r.stdout.strip() else None


JSON_FAMILY = {
    "last-wins-text-after-json": ["--output", "json", "--output", "text", "--bogus"],
    "text-then-json": ["--output", "text", "--output", "json", "--bogus"],
    "double-dash-json": ["--bogus", "--", "--output", "json"],
    "equals-json-cap-abc": ["--output=json", "--max-cost", "abc"],
    "cap-swallows-output": ["--max-cost", "--output", "json"],
    "json-then-bare-output": ["--output", "json", "--output"],
    "uppercase-JSON": ["--output", "JSON", "--bogus"],
    "xml": ["--output", "xml"],
    "short-o": ["-o", "json"],
    "abbrev": ["--out", "json", "--bogus"],
    "nan-cap": ["--output", "json", "--max-cost", "nan"],
    "inf-cap": ["--output", "json", "--max-cost", "inf"],
    "neg-cap": ["--output", "json", "--max-cost", "-0.01"],
    "extra-positional": ["--output", "json", "extra"],
}


@pytest.mark.parametrize("name", list(JSON_FAMILY))
def test_argv_shapes(world, name):
    store, source, provider, tmp = world
    grant(store)
    r = runner.invoke(app, _argv(source, *JSON_FAMILY[name]))
    doc = None
    try:
        doc = _one_doc_or_empty(r)
        parse = "ok"
    except Exception as e:  # noqa: BLE001
        parse = f"NOT-JSON({e})"
    print(f"PROBE {name}: exit={r.exit_code} stdout_doc={doc} parse={parse} "
          f"stderr_head={r.stderr.strip()[:80]!r} calls={provider.calls}")
    assert r.exit_code != 2, name
    assert provider.calls == 0


def test_help_still_works(world):
    r = runner.invoke(app, ["ingest", "review", "--help"])
    print("PROBE help exit", r.exit_code, len(r.stdout))
    assert r.exit_code == 0 and "--output" in r.stdout


def test_missing_both_args_text_and_json(world):
    r1 = runner.invoke(app, ["ingest", "review"])
    r2 = runner.invoke(app, ["ingest", "review", "--output", "json"])
    print("PROBE noargs text", r1.exit_code, repr(r1.stdout), "| json", r2.exit_code, r2.stdout)
    assert r1.exit_code == 1 and r2.exit_code == 1


@pytest.mark.parametrize("variant", ["upper", "backslash", "quoted"])
def test_internal_error_path_variants(world, monkeypatch, variant):
    store, source, provider, tmp = world
    grant(store)
    video = Path(next(s for s in store.list_sources() if s.id == source.id).path)
    leaks = {"upper": [str(video).upper(), video.name.upper()],
             "backslash": [str(video).replace("/", "\\"), video.name],
             "quoted": [repr(str(video)), video.name]}[variant]

    def boom(*_a, **_k):
        raise RuntimeError(f"ffmpeg failed on {leaks[0]} ({leaks[1]})")

    monkeypatch.setattr(provider, "judge", boom)
    r = runner.invoke(app, _argv(source, "--output", "json"))
    doc = json.loads(r.stdout)
    print(f"PROBE internal {variant}: exit={r.exit_code} reason={doc['reason']!r}")
    assert doc["status"] == "internal_error"
    assert "Traceback" not in r.stderr + r.stdout
    assert video.name.lower() not in (r.stdout + r.stderr).lower(), "NAME LEAK"


def test_internal_error_when_scrub_itself_fails_does_not_leak(world, monkeypatch):
    """_failure_reason's last-resort path: if building the safe text raises, the message is dropped."""
    store, source, provider, tmp = world
    grant(store)
    import autotester.cli_video_review as m

    def bad_values(_store):
        raise OSError("env unreadable SECRETVALUE")

    monkeypatch.setattr(m, "_secret_values", bad_values)
    video = Path(next(s for s in store.list_sources() if s.id == source.id).path)
    # the stage itself uses _secret_values too (secrets= arg) -> crash comes from _review, before the stage
    r = runner.invoke(app, _argv(source, "--output", "json"))
    doc = json.loads(r.stdout)
    print("PROBE scrub-fails:", r.exit_code, doc)
    assert doc["status"] == "internal_error" and "SECRETVALUE" not in r.stdout + r.stderr
    assert video.name not in r.stdout + r.stderr


def test_sigint_second_path_dry_run_interrupt(world, monkeypatch):
    store, source, provider, tmp = world
    import autotester.cli_video_review as m

    def kb(*_a, **_k):
        raise KeyboardInterrupt

    monkeypatch.setattr(m, "preview_review", kb)
    r = runner.invoke(app, _argv(source, "--output", "json", "--dry-run"))
    print("PROBE dry-run interrupt", r.exit_code, r.stdout)
    assert r.exit_code == 130 and json.loads(r.stdout)["status"] == "interrupted"


def test_systemexit_from_provider(world, monkeypatch):
    store, source, provider, tmp = world
    grant(store)

    def se(*_a, **_k):
        raise SystemExit(7)

    monkeypatch.setattr(provider, "judge", se)
    r = runner.invoke(app, _argv(source, "--output", "json"))
    print("PROBE SystemExit(7):", r.exit_code, repr(r.stdout), "scratch:",
          list((tmp / "projects" / "demo").rglob("rv_*")))


def test_real_oserror_repr_path_leaks_directory(world, monkeypatch):
    store, source, provider, tmp = world
    grant(store)
    video = Path(next(s for s in store.list_sources() if s.id == source.id).path)

    def real(*_a, **_k):
        open(video.with_suffix(".nope"), "rb")     # genuine FileNotFoundError, repr'd path

    monkeypatch.setattr(provider, "judge", real)
    r = runner.invoke(app, _argv(source, "--output", "json"))
    doc = json.loads(r.stdout)
    print("PROBE real-oserror:", r.exit_code, doc["reason"])
    assert str(video.parent).replace("\\", "\\\\") not in doc["reason"], "DIR LEAK (repr form)"
