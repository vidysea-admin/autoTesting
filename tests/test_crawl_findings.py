"""Contract: qa/contracts/bench.md K8-K11 + T-136 route (b) (Umesh, chat 2026-10-19).

Recorded fixtures only: crawl issues written to a tmp store; no browser, no network, no judge.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from autotester.schema.crawl import CrawlIssue
from autotester.schema.enums import IssueKind, Result
from autotester.schema.run import Run
from autotester.schema.screen_graph import ScreenNode
from autotester.schema.verdict import Verdict
from autotester.stages.acceptance_comparison import build_comparison, completeness_problems
from autotester.stages.bench_from_run import RunNotUsable, bench_from_run
from autotester.stages.crawl_findings import findings_from_crawl_issues
from autotester.store.project_store import ProjectStore

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bench_from_run as script  # noqa: E402
import check_acceptance_comparison as check  # noqa: E402

API = "https://pathlynks.example/api/pathlynks-quest/psychometric/status"


def _issue(kind: IssueKind, detail: str, *, node: str = "n1", crawl: str = "crawl_1",
           first_party: bool = True) -> CrawlIssue:
    return CrawlIssue(crawl_id=crawl, project="demo", kind=kind, node_id=node,
                      detail=detail, first_party=first_party)


def _store_with_r4_shaped_run(tmp_path: Path, issues: list[CrawlIssue]) -> ProjectStore:
    """Run shaped like r4: 4 cases, all INCONCLUSIVE, 0 FAIL verdicts, so 0 case findings."""
    store = ProjectStore("demo", tmp_path)
    t0 = datetime(2026, 10, 19, tzinfo=UTC)
    cases = ["a", "b", "c", "d"]
    store.save_run(Run(id="run_4", project="demo", case_ids=cases, started_at=t0,
                       finished_at=t0 + timedelta(seconds=45)))
    for case in cases:
        store.save_verdict("run_4", Verdict(run_id="run_4", case_id=case,
                                            result=Result.INCONCLUSIVE))
    for issue in issues:
        store.add_crawl_issue(issue)
    return store


def test_pathlynks_api_502_during_a_crawl_is_one_crawl_finding_however_often_it_repeats() -> None:
    issues = [_issue(IssueKind.NETWORK, f"{API} -> 502", node=n) for n in ("n1", "n2", "n1")]
    findings = findings_from_crawl_issues(issues, {})
    assert len(findings) == 1
    only = findings[0]
    assert only.source == "crawl" and only.matched_bug_id is None
    assert API in only.text and "502" in only.text
    assert only.evidence_refs and all(r.startswith("crawl/crawl_1/") for r in only.evidence_refs)


def test_same_url_with_another_status_is_a_separate_finding() -> None:
    issues = [_issue(IssueKind.NETWORK, f"{API} -> 502"),
              _issue(IssueKind.NETWORK, f"{API} -> 401")]
    assert len(findings_from_crawl_issues(issues, {})) == 2


def test_the_same_failure_seen_in_two_crawls_is_one_finding_with_both_evidence_paths() -> None:
    issues = [_issue(IssueKind.NETWORK, f"{API} -> 502", crawl="crawl_1"),
              _issue(IssueKind.NETWORK, f"{API} -> 502", crawl="crawl_2")]
    findings = findings_from_crawl_issues(issues, {})
    assert len(findings) == 1
    assert {r.split("/")[1] for r in findings[0].evidence_refs} == {"crawl_1", "crawl_2"}


def test_console_error_is_a_finding_but_the_google_sign_in_warning_is_not() -> None:
    issues = [
        _issue(IssueKind.CONSOLE, "error: Failed to load resource: the server responded "
                                  "with a status of 401 ()"),
        _issue(IssueKind.CONSOLE, "warning: [GSI_LOGGER]: google.accounts.id.initialize() "
                                  "is called multiple times."),
    ]
    findings = findings_from_crawl_issues(issues, {})
    assert [f.source for f in findings] == ["crawl"]
    assert "401" in findings[0].text


def test_tool_failures_third_party_noise_and_crawler_state_are_never_product_findings() -> None:
    issues = [
        _issue(IssueKind.EVIDENCE, "could not screenshot this screen -- TimeoutError"),
        _issue(IssueKind.NETWORK, "https://ads.example/pixel -> 500", first_party=False),
        _issue(IssueKind.NAVIGATION, "lost this screen mid-exploration"),
        _issue(IssueKind.OVERLAY, "3 control(s) on this screen are covered by an overlay"),
        _issue(IssueKind.DIALOG, "dialog repeat limit reached"),
    ]
    assert findings_from_crawl_issues(issues, {}) == []


def test_finding_evidence_includes_the_screen_shot_when_the_node_recorded_one() -> None:
    node = ScreenNode(crawl_id="crawl_1", project="demo", url_template="/dashboard",
                      url_example="https://pathlynks.example/dashboard", signature="s",
                      screenshot_ref="01-node-abc123.png")
    issue = _issue(IssueKind.NETWORK, f"{API} -> 502", node=node.id)
    findings = findings_from_crawl_issues([issue], {(node.crawl_id, node.id): node})
    assert "crawl/crawl_1/shots/01-node-abc123.png" in findings[0].evidence_refs


def test_r4_shaped_run_with_crawl_502_gets_a_numeric_fp_rate_and_the_check_exits_zero(
    tmp_path: Path,
) -> None:
    store = _store_with_r4_shaped_run(
        tmp_path, [_issue(IssueKind.NETWORK, f"{API} -> 502"),
                   _issue(IssueKind.CONSOLE, "error: Failed to load resource: 502")])
    trial = bench_from_run(store, "demo", "run_4", crawl_ids=["crawl_1"])
    assert [f.source for f in trial.findings] == ["crawl", "crawl"]
    cmp = build_comparison(store, "demo")
    assert cmp.autotester.false_positive_rate.value == 1.0  # unadjudicated: every finding counts
    assert cmp.fp_rate_unadjudicated and cmp.autotester.crawl_findings == 2
    assert completeness_problems(cmp) == []
    assert check.main(["demo", "--root", str(tmp_path)]) == 0


def test_recall_against_a_human_stays_unavailable_when_crawl_findings_exist(
    tmp_path: Path,
) -> None:
    store = _store_with_r4_shaped_run(tmp_path, [_issue(IssueKind.NETWORK, f"{API} -> 502")])
    bench_from_run(store, "demo", "run_4", crawl_ids=["crawl_1"])
    cmp = build_comparison(store, "demo")
    assert cmp.human_list == "absent"
    assert cmp.autotester.severity_weighted_recall.value is None
    assert cmp.autotester.severity_weighted_recall.unavailable_reason == "no human list"
    assert cmp.autotester.detection_rate.value is None
    assert cmp.human.present is False and cmp.human.absent_reason == "no human list"


def test_scanned_crawl_with_truly_zero_product_issues_is_an_honest_unavailable_not_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    store = _store_with_r4_shaped_run(
        tmp_path, [_issue(IssueKind.CONSOLE, "warning: [GSI_LOGGER]: initialize() called twice")])
    bench_from_run(store, "demo", "run_4", crawl_ids=["crawl_1"])
    cmp = build_comparison(store, "demo")
    fp = cmp.autotester.false_positive_rate
    assert fp.value is None and "crawl" in (fp.unavailable_reason or "")
    assert "0 product issues" in (fp.unavailable_reason or "")
    assert completeness_problems(cmp) == []
    assert check.main(["demo", "--root", str(tmp_path)]) == 0
    assert "0 product issues" in capsys.readouterr().out


def test_zero_findings_with_no_crawl_scan_still_fails_the_check_k8(tmp_path: Path) -> None:
    """The unpopulated path: a trial that scanned nothing has no precision to quote."""
    store = _store_with_r4_shaped_run(tmp_path, [])
    bench_from_run(store, "demo", "run_4")
    cmp = build_comparison(store, "demo")
    assert any("false_positive_rate" in p for p in completeness_problems(cmp))
    assert check.main(["demo", "--root", str(tmp_path)]) == 1


def test_unknown_crawl_id_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    store = _store_with_r4_shaped_run(tmp_path, [])
    with pytest.raises(RunNotUsable, match="crawl_missing"):
        bench_from_run(store, "demo", "run_4", crawl_ids=["crawl_missing"])
    assert store.list_bench_trials("demo-acceptance") == []
    assert script.main(["demo", "--run", "run_4", "--crawl", "crawl_missing",
                        "--root", str(tmp_path)]) == 2


def test_script_crawl_all_scans_every_stored_crawl_and_the_printout_labels_the_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    store = _store_with_r4_shaped_run(tmp_path, [_issue(IssueKind.NETWORK, f"{API} -> 502")])
    store.add_crawl_issue(_issue(IssueKind.NETWORK, f"{API} -> 503", crawl="crawl_2"))
    assert script.main(["demo", "--run", "run_4", "--crawl", "all", "--root", str(tmp_path)]) == 0
    trial = store.list_bench_trials("demo-acceptance")[0]
    assert sorted(trial.crawl_ids_scanned) == ["crawl_1", "crawl_2"] and len(trial.findings) == 2
    capsys.readouterr()
    assert check.main(["demo", "--root", str(tmp_path)]) == 0
    assert "crawl findings: 2" in capsys.readouterr().out


def test_case_findings_keep_source_case_and_old_trial_files_still_load(tmp_path: Path) -> None:
    store = ProjectStore("demo", tmp_path)
    t0 = datetime(2026, 10, 19, tzinfo=UTC)
    store.save_run(Run(id="run_5", project="demo", case_ids=["a"], started_at=t0,
                       finished_at=t0 + timedelta(seconds=9)))
    store.save_verdict("run_5", Verdict(run_id="run_5", case_id="a", result=Result.FAIL))
    trial = bench_from_run(store, "demo", "run_5")
    assert [f.source for f in trial.findings] == ["case"] and trial.crawl_ids_scanned == []
    path = store.paths.bench_trial(trial.id)
    raw = json.loads(path.read_text(encoding="utf-8"))
    for finding in raw["findings"]:
        finding.pop("source")
    raw.pop("crawl_ids_scanned")
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert store.list_bench_trials("demo-acceptance")[0].findings[0].source == "case"

