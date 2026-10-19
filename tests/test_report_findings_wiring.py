"""g11-oracle-wiring W5 (multi-role-platform.md MP8; AT-1038): a P0 leak reaches the unified report.

`render_html(report, findings)` always knew how to open with the release-blocking banner, but
`unified_html` never passed it a finding and `run_scenario` never saved one, so the banner was
unreachable. Now `run_scenario(record=True)` persists each finding under the run directory and
`unified_html` loads that run's findings. The banner rules are not under test here
(test_report_banner owns them); this file proves the wire.
Synthetic only (MPI2); no browser, no provider.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from cross_role_fakes import FakeClock, ScriptedPort, make_scenario
from test_report_banner import LEAK, P1, PRIV
from test_unified_report import _case, _flows, _release, _store

from autotester.schema.enums import Result
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages.cross_role_runner import run_scenario
from autotester.stages.leak_evidence import FINDINGS_DIR, write_finding
from autotester.stages.unified_report import ReportUnreadable, unified_html
from autotester.store.project_store import ProjectStore


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text("DEMO_PASSWORD=hunter2-unit-test-secret\n", encoding="utf-8")
    return tmp_path


def _run(root: Path, run_id: str = "rel1", day: int = 1) -> ProjectStore:
    store = _store(root)
    _flows(store, "f1")
    _case(store, "c1", "f1")
    _release(store, run_id, day, {"c1": Result.PASS})
    return store


def _importer(*findings: MultiRoleFinding):
    """An oracle module that reports the given findings, standing in for stages/oracle_*.py."""
    return lambda name: SimpleNamespace(run=lambda context: list(findings))


def _scenario_run(run_dir: Path, *findings: MultiRoleFinding, record: bool = True):
    clock = FakeClock()
    return run_scenario(
        make_scenario(within_s=1), ScriptedPort(clock, 0.0), clock, project_slug="demo",
        run_dir=str(run_dir), oracles=[OracleName.TENANT], importer=_importer(*findings),
        record=record)


def test_w5_a_recorded_p0_leak_opens_the_report_with_the_banner_and_its_repro(root) -> None:
    store = _run(root)
    _scenario_run(store.paths.run_dir("rel1"), LEAK)
    html = unified_html(store, "rel1")
    assert html.index('id="release-blocker"') < html.index("<h1>")
    assert "1 release-blocking" in html
    assert f'href="#repro-{LEAK.finding_id}"' in html and f'id="repro-{LEAK.finding_id}"' in html


def test_w5_run_scenario_does_not_write_unless_asked_to_record(root) -> None:
    store = _run(root)
    result = _scenario_run(store.paths.run_dir("rel1"), LEAK, record=False)
    assert [f.finding_id for f in result.findings] == [LEAK.finding_id]
    assert not (store.paths.run_dir("rel1") / FINDINGS_DIR).exists()
    assert "release-blocker" not in unified_html(store, "rel1")


def test_w5_recording_writes_one_file_per_finding_returned_in_the_result(root) -> None:
    store = _run(root)
    result = _scenario_run(store.paths.run_dir("rel1"), LEAK, PRIV, P1)
    written = sorted(p.stem for p in (store.paths.run_dir("rel1") / FINDINGS_DIR).iterdir())
    assert written == sorted(f.finding_id for f in result.findings) == sorted(
        [LEAK.finding_id, PRIV.finding_id, P1.finding_id])
    html = unified_html(store, "rel1")
    assert "2 release-blocking" in html


def test_w5_no_banner_without_findings_or_with_only_p1(root) -> None:
    store = _run(root)
    plain = unified_html(store, "rel1")
    assert "release-blocker" not in plain
    _scenario_run(store.paths.run_dir("rel1"), P1)
    assert "release-blocker" not in unified_html(store, "rel1")


def test_w5_another_runs_findings_are_not_shown(root) -> None:
    store = _run(root, "rel1", 1)
    _release(store, "rel2", 2, {"c1": Result.PASS})
    write_finding(store.paths.run_dir("rel2"), LEAK)
    assert "release-blocker" not in unified_html(store, "rel1")
    assert "release-blocker" in unified_html(store, "rel2")


def test_w5_an_unreadable_finding_file_is_ReportUnreadable_never_a_clean_report(root) -> None:
    store = _run(root)
    d = store.paths.run_dir("rel1") / FINDINGS_DIR
    d.mkdir(parents=True)
    (d / "bad-1.json").write_text('{"finding_id": "canary-leak-value", "bogus": 1}',
                                  encoding="utf-8")
    with pytest.raises(ReportUnreadable) as err:
        unified_html(store, "rel1")
    assert "canary-leak-value" not in str(err.value)


def test_w5_a_finding_is_scrubbed_of_secrets_before_it_is_rendered(root) -> None:
    store = _run(root)
    leaky = LEAK.model_copy(update={"title": "leak of hunter2-unit-test-secret"})
    write_finding(store.paths.run_dir("rel1"), leaky)
    html = unified_html(store, "rel1")
    assert "release-blocker" in html and "hunter2-unit-test-secret" not in html
