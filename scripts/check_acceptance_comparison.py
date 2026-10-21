"""T-136 done_check: is the Pathlynks acceptance comparison complete? (bench.md K9)

    uv run python scripts/check_acceptance_comparison.py pathlynks [--root DIR]

Exit 0 only when the comparison artifact is complete: both columns, K6 kind, K7
ordering, per-measure number-or-unavailable, and the bug rows. With no human
list the human column reads `unavailable (no human list)` and that is accepted
(D-089 item 3); AutoTester FP rate and time must still be real numbers. Exit 2
means an input is missing (names it); exit 1 means incomplete. It never asserts
AutoTester won -- Umesh's verdict is recorded on the artifact, not computed.

The FP rate is over adjudicated findings only (AT-1381, option A). The output prints coverage
("adjudicated 9/11") and labels the rate PROVISIONAL while any finding is unruled; `--claim`
(an acceptance claim) then exits 1. Without `--claim` the exit code is unchanged (K9/K10).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.schema.acceptance import AcceptanceComparison
from autotester.schema.bench import BenchCorpus
from autotester.stages.acceptance_comparison import (
    ADJUDICATED,
    MissingInput,
    build_comparison,
    completeness_problems,
)
from autotester.store.filestore import write_json
from autotester.store.project_store import ProjectStore


def render(cmp: AcceptanceComparison) -> str:
    """Side-by-side text; every figure comes from the artifact."""
    lines = [f"acceptance comparison {cmp.project} (corpus {cmp.corpus_id}, "
             f"mode {cmp.corpus_mode}, human list {cmp.human_list})",
             f"  recall basis: {cmp.recall_basis}"]
    for col in (cmp.autotester, cmp.human):
        if not col.present:
            lines.append(f"  {col.participant}: unavailable ({col.absent_reason})")
            continue
        lines.append(f"  {col.participant} [{col.kind}, ordering {col.ordering}] "
                     f"reported {col.findings_reported} "
                     f"(independent {col.independent_findings}, prompted {col.prompted_findings}; "
                     f"crawl findings: {col.crawl_findings}, "
                     f"case findings: {col.findings_reported - col.crawl_findings})")
        lines.append(f"    recall: {col.severity_weighted_recall.text()}  "
                     f"detection: {col.detection_rate.text()}  "
                     f"fp_rate: {col.false_positive_rate.text()} "
                     f"({col.false_positive_population})  time_s: {col.duration_s.text()}")
    fp = cmp.autotester.false_positive_rate.text()
    ai = cmp.autotester
    note = (" (unadjudicated: no human list)" if cmp.fp_rate_unadjudicated else
            f" (adjudicated findings only: {ai.adjudicated_real} real, "
            f"{ai.adjudicated_false_positives} false positive; "
            f"{ai.unadjudicated} unadjudicated, not counted)"
            if ai.false_positive_population == ADJUDICATED else "")
    ruled, total = cmp.fp_coverage()
    label = " PROVISIONAL" if cmp.fp_rate_provisional() else ""
    lines.append(f"  coverage: adjudicated {ruled}/{total} findings")
    lines.append(f"FP rate: {fp}{note}{label}")
    for bug in cmp.bugs:
        lines.append(f"  bug {bug.bug_id} [{bug.severity}] found by: {bug.found_by or 'nobody'}")
    if cmp.bugs_unavailable_reason:
        lines.append(f"  bugs: unavailable ({cmp.bugs_unavailable_reason})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--claim", action="store_true",
                        help="an acceptance claim: also exit 1 while the FP rate is PROVISIONAL "
                             "(any AutoTester finding not yet ruled real or false; AT-1381)")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="corpus JSON outside the repo tree (e.g. the gitignored known-bugs "
                             "corpus from scripts/known_bugs_corpus.py); default: the stored one")
    args = parser.parse_args(argv)
    store = ProjectStore(args.project, args.root)
    try:
        corpus = BenchCorpus.model_validate_json(
            args.corpus.read_text(encoding="utf-8")) if args.corpus else None
        cmp = build_comparison(store, args.project, corpus)
    except MissingInput as exc:
        print(f"cannot build the acceptance comparison for {args.project!r}: "
              f"missing {exc}.\nNo numbers are invented. Produce a real run, then build the "
              "corpus and AutoTester trial (stages/bench.py::run_autotester_trial).",
              file=sys.stderr)
        return 2
    write_json(store.paths.bench_comparison(cmp.corpus_id), cmp)
    print(render(cmp))
    problems = completeness_problems(cmp)
    for problem in problems:
        print(f"INCOMPLETE: {problem}", file=sys.stderr)
    if args.claim and cmp.fp_rate_provisional():
        ruled, total = cmp.fp_coverage()
        print(f"PROVISIONAL: fp_rate rests on adjudicated {ruled}/{total} findings; rule on the "
              "rest before claiming acceptance.", file=sys.stderr)
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
