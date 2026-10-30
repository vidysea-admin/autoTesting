"""mongo-store M16 (unit U3a): the stages/ and sources/ writes that go through `filestore`.

Two kinds of proof. (1) Behavioural: the moved functions run with `filestore._route` pointed at an
in-memory backend (keys are paths relative to `tmp_path`), and the bytes land there and nowhere on
disk. (2) Static: an AST walk of `stages/` and `sources/` pins every remaining raw write call, so a
new `write_text` on a state path cannot appear unlisted. Every entry of `LEFT` stays on disk for a
reason given in qa/manifests/mongo-store-u3a.md ("Left on disk"); none is a state document.
U7 routed schedule_store, drive_intake and intake_commit through `store/filestore_paths.py`, so
those three entries are gone.
"""

from __future__ import annotations

import ast
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from state_backends import InMemoryBackend

import autotester.store.filestore as filestore
from autotester.schema.intake import DriveJob

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
SHUTIL = {"copyfile", "copy", "copy2", "copytree", "move", "rmtree"}
JOB = "01J00000000000000000000000"

LEFT: dict[str, dict[str, int]] = {
    "stages/failure_bundle.py": {"shutil.rmtree": 2, "write_text": 2, "rename": 1,
                                 "shutil.copyfile": 1},
    "stages/leak_evidence.py": {"write_bytes": 1},
    "stages/real_acceptance.py": {"write_text": 1},  # checked-in evidence, not state (M49)
    "stages/report_export.py": {"write_text": 1},
    "stages/unified_report.py": {"write_text": 1},
    "sources/bounded_write.py": {"open": 1},
    "sources/gws_drive.py": {"shutil.rmtree": 3},
    "sources/pdf_worker.py": {"write_text": 1},
}


def _writes(call: ast.Call, mode_at: int) -> bool:
    mode = ""
    if len(call.args) > mode_at and isinstance(call.args[mode_at], ast.Constant):
        mode = str(call.args[mode_at].value)
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = str(kw.value.value)
    return any(c in mode for c in "wax")


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return "open" if f.id == "open" and _writes(call, 1) else None
    if not isinstance(f, ast.Attribute):
        return None
    base = ast.unparse(f.value)
    if f.attr in ("write_text", "write_bytes"):
        return f.attr
    if base == "os" and f.attr in ("replace", "rename", "open", "fdopen"):
        return f"os.{f.attr}"
    if base == "shutil" and f.attr in SHUTIL:
        return f"shutil.{f.attr}"
    if f.attr == "rename":
        return "rename"
    return "open" if f.attr == "open" and _writes(call, 0) else None


def _found() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for folder in ("stages", "sources"):
        for path in sorted((SRC / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = [n for c in ast.walk(tree) if isinstance(c, ast.Call)
                     if (n := _call_name(c))]
            if names:
                out[path.relative_to(SRC).as_posix()] = dict(Counter(names))
    return out


def test_every_raw_write_left_in_stages_and_sources_is_listed() -> None:
    assert _found() == LEFT


@pytest.fixture
def routed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    backend = InMemoryBackend()

    def route(path: Path) -> tuple[InMemoryBackend, str]:
        return backend, Path(path).relative_to(tmp_path).as_posix()

    monkeypatch.setattr(filestore, "_route", route)
    return backend


def _no_file_on_disk(tmp_path: Path) -> None:
    assert not [p for p in tmp_path.rglob("*") if p.is_file()], "a file reached the disk"


def test_a_drive_job_is_saved_and_loaded_through_the_backend(
        routed: InMemoryBackend, tmp_path: Path) -> None:
    from autotester.sources.drive_jobs import load_job, save_job
    save_job(tmp_path, DriveJob(id=JOB, project="demo", state="fetching"))
    assert list(routed.docs) == [f".work/drive-jobs/demo/{JOB}.json"]
    _no_file_on_disk(tmp_path)
    loaded = load_job(tmp_path, "demo", JOB)
    assert loaded is not None and loaded.state == "fetching"
    assert load_job(tmp_path, "demo", "01J00000000000000000000001") is None


def test_a_corrupt_drive_job_reads_as_absent(routed: InMemoryBackend, tmp_path: Path) -> None:
    from autotester.sources.drive_jobs import load_job
    routed.put(f".work/drive-jobs/demo/{JOB}.json", "{not json")
    assert load_job(tmp_path, "demo", JOB) is None


def _busy_then_ok(drive_jobs: Any, monkeypatch: pytest.MonkeyPatch, fail: int) -> list[int]:
    calls: list[int] = []

    def flaky(path: Path, text: str) -> None:
        calls.append(1)
        if len(calls) <= fail:
            raise PermissionError("busy")

    monkeypatch.setattr(drive_jobs, "write_text", flaky)
    monkeypatch.setattr(drive_jobs.time, "sleep", lambda _s: None)
    return calls


def test_save_job_retries_a_busy_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from autotester.sources import drive_jobs
    calls = _busy_then_ok(drive_jobs, monkeypatch, fail=2)
    drive_jobs.save_job(tmp_path, DriveJob(id=JOB, project="demo", state="queued"))
    assert len(calls) == 3


def test_save_job_gives_up_after_the_last_try(monkeypatch: pytest.MonkeyPatch,
                                              tmp_path: Path) -> None:
    from autotester.sources import drive_jobs
    calls = _busy_then_ok(drive_jobs, monkeypatch, fail=99)
    with pytest.raises(PermissionError):
        drive_jobs.save_job(tmp_path, DriveJob(id=JOB, project="demo", state="queued"))
    assert len(calls) == drive_jobs.REPLACE_TRIES


def test_the_payment_report_is_written_through_the_backend(
        routed: InMemoryBackend, tmp_path: Path) -> None:
    from autotester.stages.oracle_payment import REPORT_FILE, _write_report
    _write_report(str(tmp_path), [])
    assert routed.docs == {REPORT_FILE: "[]"}
    _no_file_on_disk(tmp_path)


def test_the_payment_report_is_not_written_into_a_missing_folder(
        routed: InMemoryBackend, tmp_path: Path) -> None:
    from autotester.stages.oracle_payment import _write_report
    _write_report(str(tmp_path / "absent"), [])
    assert routed.docs == {}


def test_a_payment_declaration_and_a_credential_policy_load_through_the_backend(
        routed: InMemoryBackend, tmp_path: Path) -> None:
    from autotester.stages import oracle_credential_policy as policy
    from autotester.stages import oracle_payment as payment
    with pytest.raises(payment.PaymentNotDeclaredError, match="no payment"):
        payment.load_declaration(str(tmp_path))
    with pytest.raises(policy.PolicyNotDeclaredError, match="no credential"):
        policy.load_policy(str(tmp_path))
    routed.put(payment.PAYMENT_FILE, "{broken")
    routed.put(policy.POLICY_FILE, "{broken")
    with pytest.raises(payment.PaymentNotDeclaredError, match="invalid"):
        payment.load_declaration(str(tmp_path))
    with pytest.raises(policy.PolicyNotDeclaredError, match="invalid"):
        policy.load_policy(str(tmp_path))


def test_a_masked_leak_screenshot_is_stored_through_the_backend(
        routed: InMemoryBackend, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.stages import leak_evidence

    @contextmanager
    def fake(paths: list[Path]) -> Any:
        masked = paths[0].with_name("masked.png")
        masked.write_bytes(b"MASKED")
        yield SimpleNamespace(incomplete=False, paths=[masked], reasons=[])

    monkeypatch.setattr(leak_evidence, "sanitized_images", fake)
    dest = tmp_path / "run" / "leak" / "f1.png"
    assert leak_evidence.store_masked_screenshot(b"RAW", dest) == (dest, None)
    assert routed.docs == {"run/leak/f1.png": "MASKED"}
    _no_file_on_disk(tmp_path)
