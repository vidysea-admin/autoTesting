"""C1 (T-136 marks): a person's real / false-positive rulings reach the scorer.

Fixture runs and crawl issues only; no browser, no judge. The marks live beside the bench files
and are overlaid when the comparison is built, so `scripts/check_acceptance_comparison.py`
reports an FP rate computed from them, and unmarked findings stay unadjudicated.
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from autotester.schema.bench import BenchCorpus, Finding, SeededBug
from autotester.schema.crawl import CrawlIssue
from autotester.schema.enums import IssueKind, Result, Severity
from autotester.schema.run import Run
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import bench_marks
from autotester.stages.acceptance_comparison import build_comparison, completeness_problems
from autotester.stages.bench_from_run import bench_from_run
from autotester.store.project_store import ProjectStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_acceptance_comparison as check

CORPUS = "demo-acceptance"


def _seed(tmp_path: Path, reasons: tuple[str, ...] = ("a broke", "b broke", "c broke"),
          ) -> ProjectStore:
    """A graded run with one FAIL verdict per reason; no human list, so every finding is
    unmatched."""
    store = ProjectStore("demo", tmp_path)
    t0 = datetime(2026, 10, 21, tzinfo=UTC)
    cases = [f"case{i}" for i, _ in enumerate(reasons)]
    store.save_run(Run(id="run_1", project="demo", case_ids=cases, started_at=t0,
                       finished_at=t0 + timedelta(seconds=30)))
    for case, why in zip(cases, reasons, strict=True):
        store.save_verdict("run_1", Verdict(
            run_id="run_1", case_id=case, result=Result.FAIL,
            failures=[Failure(criterion_id="c1", reason=why)]))
    bench_from_run(store, "demo", "run_1")
    return store


def _key(store: ProjectStore, reason: str) -> str:
    trial = store.list_bench_trials(CORPUS)[0]
    return next(bench_marks.finding_key(f) for f in trial.findings if reason in f.text)


def test_one_real_one_false_one_unmarked_gives_fp_rate_over_the_two_adjudicated(
        tmp_path: Path, capsys) -> None:
    store = _seed(tmp_path)
    bench_marks.set_mark(store, CORPUS, _key(store, "a broke"), "real", "umesh@x.test")
    bench_marks.set_mark(store, CORPUS, _key(store, "b broke"), "false_positive", "umesh@x.test")
    cmp = build_comparison(store, "demo")
    col = cmp.autotester
    assert col.false_positive_rate.value == 0.5  # 1 false / (1 real + 1 false); 3rd not counted
    assert (col.adjudicated_real, col.adjudicated_false_positives, col.unadjudicated) == (1, 1, 1)
    assert col.false_positive_population == "adjudicated_findings_only"
    assert cmp.fp_rate_unadjudicated is False and completeness_problems(cmp) == []
    assert check.main(["demo", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "FP rate: 0.5 (adjudicated findings only: 1 real, 1 false positive; " \
           "1 unadjudicated, not counted)" in out


def test_with_no_mark_every_finding_stays_unadjudicated_and_the_old_rate_is_unchanged(
        tmp_path: Path) -> None:
    store = _seed(tmp_path)
    col = build_comparison(store, "demo").autotester
    assert col.false_positive_rate.value == 1.0
    assert col.false_positive_population == "all_reported_findings"
    assert (col.adjudicated_real, col.adjudicated_false_positives, col.unadjudicated) == (0, 0, 3)


def test_a_mark_survives_bench_from_run_replacing_the_trial(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    bench_marks.set_mark(store, CORPUS, _key(store, "c broke"), "false_positive", "u@x.test")
    bench_from_run(store, "demo", "run_1")  # re-conversion rewrites the trial in place
    col = build_comparison(store, "demo").autotester
    assert col.adjudicated_false_positives == 1 and col.false_positive_rate.value == 1.0


def test_undo_returns_the_finding_to_unadjudicated(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    key = _key(store, "a broke")
    bench_marks.set_mark(store, CORPUS, key, "real", "u@x.test")
    bench_marks.set_mark(store, CORPUS, key, None, "u@x.test")
    col = build_comparison(store, "demo").autotester
    assert col.adjudicated_real == 0 and col.false_positive_population == "all_reported_findings"
    assert bench_marks.load_marks(store, CORPUS).marks == {}


def test_the_stored_trial_is_not_rewritten_by_a_mark(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    before = store.paths.bench_trial("demo-acceptance-autotester").read_bytes()
    bench_marks.set_mark(store, CORPUS, _key(store, "a broke"), "real", "u@x.test")
    assert store.paths.bench_trial("demo-acceptance-autotester").read_bytes() == before


def test_the_marks_file_holds_hashes_and_rulings_never_finding_text(tmp_path: Path) -> None:
    store = _seed(tmp_path, ("secret-looking detail xyz",))
    bench_marks.set_mark(store, CORPUS, _key(store, "xyz"), "real", "u@x.test")
    text = store.paths.bench_marks(CORPUS).read_text(encoding="utf-8")
    assert "secret-looking" not in text and "xyz" not in text and '"real"' in text


def test_a_finding_already_matched_to_a_known_bug_is_never_re_ruled(tmp_path: Path) -> None:
    store = _seed(tmp_path, ("only",))
    corpus = BenchCorpus(
        id=CORPUS, app="demo", build_ref="b", mode="human_confirmed",
        seeded_bugs=[SeededBug(id="bug1", description="d", location="/x", detect_hint="h",
                               severity=Severity.S1, provenance="human_independent")])
    store.save_bench_corpus(corpus)
    trial = store.list_bench_trials(CORPUS)[0]
    matched = trial.model_copy(update={"findings": [
        trial.findings[0].model_copy(update={"matched_bug_id": "bug1"})]})
    store.save_bench_trial(matched)
    bench_marks.set_mark(store, CORPUS, bench_marks.finding_key(matched.findings[0]),
                         "false_positive", "u@x.test")
    shown = bench_marks.apply_marks(matched, bench_marks.load_marks(store, CORPUS))
    assert shown.findings[0].adjudication is None


def test_a_crawl_findings_key_ignores_how_many_crawls_saw_it() -> None:
    one = Finding(text="crawl: first-party request https://a/b failed with 502 "
                       "(seen 1x on 1 screen(s))", source="crawl")
    many = Finding(text="crawl: first-party request https://a/b failed with 502 "
                        "(seen 9x on 4 screen(s))", source="crawl")
    other = Finding(text="crawl: first-party request https://a/c failed with 502 "
                         "(seen 1x on 1 screen(s))", source="crawl")
    assert bench_marks.finding_key(one) == bench_marks.finding_key(many)
    assert bench_marks.finding_key(one) != bench_marks.finding_key(other)


def test_marks_apply_to_crawl_findings_the_same_way(tmp_path: Path) -> None:
    store = ProjectStore("demo", tmp_path)
    t0 = datetime(2026, 10, 21, tzinfo=UTC)
    store.save_run(Run(id="run_1", project="demo", case_ids=["k"], started_at=t0,
                       finished_at=t0 + timedelta(seconds=5)))
    store.save_verdict("run_1", Verdict(run_id="run_1", case_id="k", result=Result.PASS))
    store.add_crawl_issue(CrawlIssue(
        crawl_id="crawl_1", project="demo", kind=IssueKind.NETWORK, node_id="n1",
        detail="https://demo.test/api/x -> 502"))
    (store.paths.crawl_dir("crawl_1")).mkdir(parents=True, exist_ok=True)
    bench_from_run(store, "demo", "run_1", crawl_ids=["crawl_1"])
    key = _key(store, "502")
    bench_marks.set_mark(store, CORPUS, key, "false_positive", "u@x.test")
    col = build_comparison(store, "demo").autotester
    assert col.adjudicated_false_positives == 1 and col.crawl_findings == 1
    assert col.false_positive_rate.value == 1.0


def test_simultaneous_set_mark_calls_lose_no_ruling(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    keys = [f"{i:016x}" for i in range(32)]
    gate = threading.Barrier(len(keys))

    def mark(key: str) -> None:
        gate.wait()  # line every writer up on the same read-modify-write
        bench_marks.set_mark(store, CORPUS, key, "real", "u@x.test")

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        list(pool.map(mark, keys))  # a writer that raises fails the test here
    assert set(bench_marks.load_marks(store, CORPUS).marks) == set(keys)


# --- AT-1381: adjudication coverage and the PROVISIONAL fp_rate label ----------------------

def test_two_of_three_findings_ruled_reports_coverage_and_a_provisional_fp_rate(
        tmp_path: Path, capsys) -> None:
    store = _seed(tmp_path)
    bench_marks.set_mark(store, CORPUS, _key(store, "a broke"), "real", "u@x.test")
    bench_marks.set_mark(store, CORPUS, _key(store, "b broke"), "false_positive", "u@x.test")
    cmp = build_comparison(store, "demo")
    assert (cmp.autotester.adjudicated_findings, cmp.autotester.findings_reported) == (2, 3)
    assert cmp.fp_coverage() == (2, 3) and cmp.fp_rate_provisional()
    assert cmp.autotester.false_positive_rate.value == 0.5  # fp_rate itself is unchanged
    assert check.main(["demo", "--root", str(tmp_path)]) == 0  # no acceptance claim made
    out = capsys.readouterr().out
    assert "adjudicated 2/3" in out and "FP rate: 0.5" in out
    assert "PROVISIONAL" in out.split("FP rate:")[1].splitlines()[0]


def test_an_acceptance_claim_on_a_provisional_fp_rate_exits_non_zero(
        tmp_path: Path, capsys) -> None:
    store = _seed(tmp_path)
    bench_marks.set_mark(store, CORPUS, _key(store, "a broke"), "real", "u@x.test")
    assert check.main(["demo", "--root", str(tmp_path), "--claim"]) == 1
    err = capsys.readouterr().err
    assert "PROVISIONAL" in err and "adjudicated 1/3" in err


def test_a_run_with_no_rulings_at_all_is_adjudicated_zero_of_three_and_provisional(
        tmp_path: Path, capsys) -> None:
    _seed(tmp_path)
    assert check.main(["demo", "--root", str(tmp_path), "--claim"]) == 1
    captured = capsys.readouterr()
    assert "adjudicated 0/3" in captured.out and "PROVISIONAL" in captured.out


def test_with_every_finding_ruled_the_fp_rate_is_final_and_the_claim_passes(
        tmp_path: Path, capsys) -> None:
    store = _seed(tmp_path)
    for reason, verdict in (("a broke", "real"), ("b broke", "false_positive"),
                            ("c broke", "false_positive")):
        bench_marks.set_mark(store, CORPUS, _key(store, reason), verdict, "u@x.test")
    cmp = build_comparison(store, "demo")
    assert cmp.fp_coverage() == (3, 3) and not cmp.fp_rate_provisional()
    assert check.main(["demo", "--root", str(tmp_path), "--claim"]) == 0
    out = capsys.readouterr().out
    assert "adjudicated 3/3" in out and "PROVISIONAL" not in out


def test_a_finding_matched_to_a_known_bug_counts_as_ruled_by_the_corpus(tmp_path: Path) -> None:
    store = _seed(tmp_path, ("only", "other"))
    corpus = BenchCorpus(
        id=CORPUS, app="demo", build_ref="b", mode="human_confirmed",
        seeded_bugs=[SeededBug(id="bug1", description="d", location="/x", detect_hint="h",
                               severity=Severity.S1, provenance="human_independent")])
    store.save_bench_corpus(corpus)
    trial = store.list_bench_trials(CORPUS)[0]
    store.save_bench_trial(trial.model_copy(update={"findings": [
        trial.findings[0].model_copy(update={"matched_bug_id": "bug1"}), trial.findings[1]]}))
    col = build_comparison(store, "demo").autotester
    assert (col.adjudicated_findings, col.findings_reported, col.unadjudicated) == (1, 2, 1)


def test_the_scorecard_itself_exposes_the_adjudicated_count_and_the_total(
        tmp_path: Path) -> None:
    store = _seed(tmp_path)
    bench_marks.set_mark(store, CORPUS, _key(store, "a broke"), "real", "u@x.test")
    trial = bench_marks.apply_marks(store.list_bench_trials(CORPUS)[0],
                                    bench_marks.load_marks(store, CORPUS))
    corpus = store.load_bench_corpus(CORPUS)
    score = trial.score(corpus)
    assert (score["adjudicated_findings"], score["findings_total"]) == (1, 3)
