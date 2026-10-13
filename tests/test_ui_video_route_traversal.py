"""Every attacker-controlled-input refusal for `ui/routes_video.py`
(ISS-t191-run-video-2). `video_path` arrives verbatim from the URL, so each
test here treats it as hostile: `..` traversal, symlink/junction escapes,
an absolute path, a non-`.webm` file, and UNC/drive-rooted values (the
senior-software-engineer review's UNC finding, this cycle -- see
`_safe_video_path`'s docstring in `routes_video.py`). Split out of
`test_ui_video_route.py` (serving/linking/validity) to stay under doctor's
300-line file cap.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from symlink_support import link_dir

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app
from autotester.ui.routes_video import _safe_video_path

RUN_ID = "run-video-route-test"


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _seed_with_video(scratch_root: Path, *, video_bytes: bytes = b"FAKE-WEBM") -> ProjectStore:
    store = ProjectStore("demo", scratch_root)
    store.save_project(
        Project(slug="demo", name="Demo", base_url="https://demo.test",
                allowed_domains=["demo.test"])
    )
    case = Case(
        project="demo", flow_id="flow-login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Login attempt", steps=[Step(order=1, action=Action.NAVIGATE, target="/login")],
    )
    store.add_case(case)
    store.save_run(Run(id=RUN_ID, project="demo", case_ids=[case.id]))
    run_dir = store.paths.run_dir(RUN_ID)
    video_rel = "video.webm"  # fixed name: this fixture's `case.id` is a
    # content hash, irrelevant to what's under test here
    (run_dir / video_rel).write_bytes(video_bytes)
    store.save_result(RUN_ID, RawResult(
        case_id=case.id, outcome=Outcome.COMPLETED,
        evidence=[Evidence(kind=EvidenceKind.VIDEO, path=video_rel, masked=True)],
    ))
    store.save_verdict(RUN_ID, Verdict(
        run_id=RUN_ID, case_id=case.id, result=Result.FAIL, criteria_met=0, criteria_total=1,
        grader_provider="mock",
    ))
    return store


def test_serve_run_video_refuses_percent_encoded_traversal_end_to_end(
    client: TestClient, scratch_root: Path
) -> None:
    """The mandatory falsification target: `video_path` is attacker-controlled
    over HTTP. A bare `../` never even reaches the guard -- httpx normalizes
    dot-segments in the URL client-side before the request is sent, so
    requesting a literal `../` 404s at ROUTING, proving nothing (confirmed
    empirically: it never matched the `{video_path:path}` route at all).
    Percent-encoding (`%2e%2e`) survives that normalization and arrives in
    the handler as a real `..` segment -- the shape a manual HTTP client
    (curl, Burp, a scripted attacker) would actually send. The outside file
    is a real `.webm` at the EXACT depth `run_dir` sits below `scratch_root`
    -- a wrong depth or a non-`.webm` outside file would make this pass even
    with the containment check deleted (caught by this unit's own
    falsification pass: an earlier draft used a `.txt` file and too many
    `..` segments, and disabling `is_relative_to` alone did not redden it --
    the suffix check and a missing-file 404 were silently doing the proving
    instead)."""
    store = _seed_with_video(scratch_root)
    depth = len(store.paths.run_dir(RUN_ID).relative_to(scratch_root).parts)
    (scratch_root / "secret.webm").write_bytes(b"must-not-leak")
    dots = "/".join(["%2e%2e"] * depth)

    response = client.get(f"/projects/demo/runs/{RUN_ID}/videos/{dots}/secret.webm")

    assert response.status_code == 404
    assert response.content != b"must-not-leak"


def test_serve_run_video_refuses_an_absolute_path(client: TestClient, scratch_root: Path) -> None:
    """Same depth/extension care as the traversal test above: the outside
    file must be a real `.webm` or the suffix check alone (not the
    containment check under test) would explain a 404."""
    _seed_with_video(scratch_root)
    outside = scratch_root / "secret.webm"
    outside.write_bytes(b"must-not-leak")

    response = client.get(
        f"/projects/demo/runs/{RUN_ID}/videos/{quote(str(outside), safe='')}"
    )

    assert response.status_code == 404


def test_serve_run_video_refuses_a_non_webm_file_even_inside_the_run_dir(
    client: TestClient, scratch_root: Path
) -> None:
    store = _seed_with_video(scratch_root)
    (store.paths.run_dir(RUN_ID) / "01-shot.png").write_bytes(b"not-a-video")

    response = client.get(f"/projects/demo/runs/{RUN_ID}/videos/01-shot.png")

    assert response.status_code == 404


def test_safe_video_path_refuses_a_dotdot_segment(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (tmp_path / "secret.webm").write_bytes(b"must-not-leak")

    assert _safe_video_path(run_dir, "../secret.webm") is None


def test_safe_video_path_refuses_a_symlinked_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.webm").write_bytes(b"must-not-leak")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    link_dir(run_dir / "escape", outside)

    assert _safe_video_path(run_dir, "escape/secret.webm") is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction regression")
def test_safe_video_path_refuses_a_windows_junction_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.webm").write_bytes(b"must-not-leak")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    junction = run_dir / "escape"
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True,
    )
    assert made.returncode == 0, made.stderr.decode(errors="replace")

    assert _safe_video_path(run_dir, "escape/secret.webm") is None


def test_safe_video_path_refuses_a_unc_path_without_touching_the_network(tmp_path: Path) -> None:
    """senior-software-engineer review, this cycle: before the string-level
    guard existed, an attacker-controlled `\\\\host\\share\\...` reached
    `Path.resolve()`, which makes Windows attempt a real SMB connection to
    `host` -- measured ~21s against an unreachable host in review, a
    blocking DoS / forced-SMB-auth vector, not merely a wrong answer. Weak
    signal only: in this sandbox a real UNC lookup itself fails in <1ms (no
    real network stack to hang against), so this bounded budget could not
    be reddened by removing the guard here -- see
    test_safe_video_path_never_calls_resolve_for_a_dangerous_value below
    for the mechanism-level proof that does redden."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    start = time.perf_counter()

    result = _safe_video_path(run_dir, r"\\198.51.100.1\share\x.webm")

    assert result is None
    assert time.perf_counter() - start < 2.0


def test_safe_video_path_never_calls_resolve_for_a_dangerous_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual falsifiable proof for the UNC finding: patches
    `Path.resolve` to raise if it is EVER called, then asserts the guard
    returns `None` for each dangerous shape without tripping it. This is
    reddened by deleting the guard (`run_dir.resolve()` then raises,
    uncaught) regardless of how fast or slow a real OS-level UNC lookup
    happens to be on the machine running the test -- confirmed in a
    git-archive throwaway copy with the guard's two lines removed: all
    three inputs below raise the monkeypatched AssertionError instead of
    returning None."""
    def _must_not_be_called(self: Path) -> Path:
        raise AssertionError(f"Path.resolve() must not be called for {self!r}")

    monkeypatch.setattr(Path, "resolve", _must_not_be_called)
    run_dir = tmp_path / "run"  # deliberately never created: a real guard
    # never touches disk for these inputs either

    for dangerous in (r"\\host\share\x.webm", "/etc/passwd", r"C:\Windows\x.webm"):
        assert _safe_video_path(run_dir, dangerous) is None


def test_safe_video_path_refuses_a_drive_rooted_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    assert _safe_video_path(run_dir, r"C:\Windows\System32\drivers\etc\hosts") is None


def test_serve_run_video_refuses_a_unc_path_end_to_end(
    client: TestClient, scratch_root: Path
) -> None:
    _seed_with_video(scratch_root)
    unc = r"\\198.51.100.1\share\x.webm"

    response = client.get(f"/projects/demo/runs/{RUN_ID}/videos/{quote(unc, safe='')}")

    assert response.status_code == 404
