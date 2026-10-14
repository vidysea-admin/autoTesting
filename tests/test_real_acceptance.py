"""T-169 real-target driver, proved on the local fixture product with the mock seams.

No browser, no model, no live site: the driver's approval gate, evidence files and GR1-GR4
checklist are exercised through TestClient exactly as `scripts/run_real_acceptance.py` does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval
from test_generic_acceptance import (
    SITE,
    _crawl_fixture,
    _drive,
    _spec,
    _vision,
    client,  # noqa: F401 - pytest fixture
    product_url,  # noqa: F401 - pytest fixture
    scratch_root,  # noqa: F401 - pytest fixture
)

from autotester.core.consent import ApprovalRequired
from autotester.schema.enums import ApprovalKind
from autotester.stages.generic_acceptance import ModeSeams
from autotester.stages.real_acceptance import (
    EVIDENCE_DIR,
    drive_real,
    preflight,
    required_kinds,
)
from autotester.store.project_store import ProjectStore

assert SITE.exists()


def test_required_kinds_follow_the_mode() -> None:
    assert required_kinds("teaching") == [ApprovalKind.LIVE_CASE]
    assert required_kinds("url_only") == [ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE]


def test_refuses_without_approval_and_names_the_grant(
    client: TestClient, scratch_root: Path, product_url: str, tmp_path: Path,  # noqa: F811
) -> None:
    spec = _spec("url_only", product_url, tmp_path)
    assert client.post("/onboard", data=spec.form(), follow_redirects=False).status_code == 303
    store = ProjectStore(spec.slug, scratch_root)
    with pytest.raises(ApprovalRequired, match="Grant one with"):
        preflight(store, "url_only")
    assert not (scratch_root / EVIDENCE_DIR).exists()  # nothing started, nothing written


@pytest.mark.parametrize("mode", ["teaching", "url_only"])
def test_driver_writes_evidence_and_checklist(
    mode: str, client: TestClient, scratch_root: Path,  # noqa: F811
    product_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
) -> None:
    first, store, spec = _drive(mode, client, scratch_root, product_url, tmp_path, monkeypatch)
    target = store.load_project().base_url  # type: ignore[union-attr]
    grant_live_case_approval(store, project=spec.slug, target=target,
                             run_kind=ApprovalKind.CRAWL)
    spec.onboard = False
    seams = ModeSeams(crawl_fn=_crawl_fixture(product_url, store),
                      ingest_provider=None, before_run=None)
    if mode == "teaching":  # reuse the stored video source; vision seam from the first drive
        seams.ingest_provider = _vision(product_url)
    result, out, lines = drive_real(client, store, spec, seams, scratch_root)

    assert out == scratch_root / EVIDENCE_DIR / mode and result.run_id != first.run_id
    evidence = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["run_id"] == result.run_id and evidence["mode"] == mode
    assert sum(evidence["verdict_counts"].values()) >= 1
    assert set(evidence["verdict_counts"]) >= {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}
    assert isinstance(evidence["inconclusive_breakdown"], dict)
    assert evidence["human_verdict"] is None  # GR3 is never filled by the driver
    assert (out / "comparison.json").read_text(encoding="utf-8").strip().startswith("{")
    text = "\n".join(lines)
    assert "GR1" in text and "GR2" in text and "GR3 human" in text and "AT-281" in text
    assert (out / "checklist.md").read_text(encoding="utf-8") == text + "\n"




def _prod_project(root: Path) -> ProjectStore:
    from autotester.schema.project import Project
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                               allowed_domains=["demo.test"], production=True))
    return store


def _row(variant: str):
    from autotester.schema.approval import RunApproval
    row = RunApproval(project="demo", run_kind=ApprovalKind.LIVE_CASE,
                      target="https://demo.test/app", scope="t", max_actions=1000,
                      max_probes=0, wall_clock_s=100_000.0, granted_by="Umesh",
                      granted_at="2026-10-13", expires_at="2099-01-01",
                      production=variant != "production_false")
    return row if variant == "unsigned" else row.sign()


@pytest.mark.parametrize("variant", ["unsigned", "production_false"])
def test_production_preflight_refuses_a_bad_row(
    variant: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _prod_project(tmp_path)
    store.add_approval(_row(variant))
    with pytest.raises(ApprovalRequired):
        preflight(store, "teaching")


def test_ui_run_trigger_refuses_production_without_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GR4/AT-570 truth test: the real route refuses (403) before any browser launches."""
    from test_ui_runs_live_case_approval import _case

    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession
    from autotester.ui.app import app

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _prod_project(tmp_path)
    store.add_case(_case(0))
    launched: list[str] = []
    monkeypatch.setattr(BrowserSession, "start", lambda self: launched.append("start"))
    judge = type("J", (), {"available": lambda self: True})()
    monkeypatch.setattr(routes_runs_module, "for_role", lambda project, role: judge)
    response = TestClient(app).post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403, response.text
    assert launched == [] and store.list_approvals() == []


def test_evidence_is_scrubbed_and_gated(
    client: TestClient, scratch_root: Path, product_url: str,  # noqa: F811
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autotester.schema.enums import Result
    from autotester.schema.verdict import Failure, Verdict
    from autotester.stages.real_acceptance import write_evidence

    first, store, _ = _drive("url_only", client, scratch_root, product_url, tmp_path,
                                monkeypatch)
    secret = "not-a-real-secret-9x"
    reason = (f"login failed for {secret} at https://x.test/cb?access_token=abc123XYZ&a=1 "
              "user tester@fixture.test")
    bad = Verdict(run_id=first.run_id, case_id="c1", result=Result.INCONCLUSIVE,
                  grader_provider="fake", failures=[Failure(criterion_id="c", reason=reason)])
    monkeypatch.setattr(store, "load_verdicts", lambda run_id: [bad])
    out, _lines = write_evidence(store, first, ["ap1"], scratch_root)
    for name in ("evidence.json", "comparison.json", "checklist.md"):
        text = (out / name).read_text(encoding="utf-8")
        assert secret not in text and "abc123XYZ" not in text
        assert "tester@fixture.test" not in text
    ev = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
    assert any("[REDACTED" in k for k in ev["inconclusive_breakdown"])


# --- scripts-env-bounds: .env key loading, bounds fit the approval, newest wide row wins ---

def _crawl_row(actions: int, wall: float, granted_at: str):
    from autotester.schema.approval import RunApproval
    return RunApproval(project="demo", run_kind=ApprovalKind.CRAWL, target="https://demo.test/app",
                       scope="t", max_actions=actions, max_probes=0, wall_clock_s=wall,
                       granted_by="Umesh", granted_at=granted_at, expires_at="2099-01-01",
                       production=True).sign()


def _two_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", "k" * 32)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _prod_project(tmp_path)
    old, new = _crawl_row(150, 600.0, "2026-10-13"), _crawl_row(150, 1800.0, "2026-10-14")
    store.add_approval(old)
    store.add_approval(new)
    store.add_approval(_row("production"))
    return store


def test_bounds_never_exceed_the_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.stages.real_acceptance import crawl_bounds
    store = _two_rows(tmp_path, monkeypatch)
    b = crawl_bounds(store)
    assert (b.max_actions, b.wall_clock_s) == (150, 600.0)  # default 200 clamped to 150
    ids = preflight(store, "url_only", b)
    assert len(ids) == 2
    with pytest.raises(ApprovalRequired):
        crawl_bounds(store, max_actions=151)


def test_1800s_run_selects_the_1800s_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.stages.real_acceptance import crawl_bounds
    store = _two_rows(tmp_path, monkeypatch)
    new_id = next(a.id for a in store.list_approvals() if a.wall_clock_s == 1800.0)
    b = crawl_bounds(store, wall_clock_s=1800.0)
    assert (b.max_actions, b.wall_clock_s) == (150, 1800.0)
    assert preflight(store, "url_only", b)[0] == new_id
    with pytest.raises(ApprovalRequired):
        crawl_bounds(store, wall_clock_s=1801.0)


def test_script_verifies_with_the_key_only_in_dotenv(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    import subprocess
    import sys
    store = _two_rows(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text("AUTOTESTER_APPROVAL_KEY=" + "k" * 32 + "\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if k not in ("AUTOTESTER_APPROVAL_KEY", "PYTEST_CURRENT_TEST")}
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_real_acceptance.py"
    out = subprocess.run([sys.executable, str(script), store.paths.slug, "--mode", "url_only",
                          "--dry-run", "--root", str(tmp_path), "--wall-clock", "1800"],
                         capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr
    assert "crawl bounds: max_actions=150 wall_clock_s=1800.0" in out.stdout
    assert "cannot verify" not in out.stderr + out.stdout
