"""Turn a real project's executed+graded run into the T-136 bench files. Contract: bench.md K10.

One job: read a stored `Run` + its `Verdict`s, then save the corpus (no-list mode) and the
AutoTester `BenchTrial` where `stages/acceptance_comparison.py` looks for them. Findings and
the trial come from `stages.bench` (one concept, one place); nothing is scored here.
"""

from __future__ import annotations

from typing import Literal

from autotester.schema.bench import BenchCorpus, BenchTrial
from autotester.stages import bench
from autotester.stages.acceptance_comparison import corpus_id_for
from autotester.store.project_store import ProjectStore

Ordering = Literal["independent_parallel", "human_read_ai_first", "ai_read_human_first", "unknown"]


class RunNotUsable(Exception):
    """The named run is absent, ungraded, or incompletely graded; no numbers are invented."""


def trial_id_for(slug: str) -> str:
    """One AutoTester trial per project corpus; re-running replaces it in place."""
    return f"{corpus_id_for(slug)}-autotester"


def _duration_s(store: ProjectStore, run_id: str) -> float | None:
    """Measured wall-clock: the run's own span, else the sum of per-case durations."""
    run = store.load_run(run_id)
    if run is not None and run.started_at and run.finished_at:
        return max(0.0, (run.finished_at - run.started_at).total_seconds())
    results = store.load_results(run_id)
    return sum(r.duration_s for r in results) if results else None


def corpus_for(store: ProjectStore, slug: str) -> BenchCorpus:
    """The human-supplied corpus when one is stored; else an empty no-list corpus (D-090).

    The no-list corpus declares no ground truth and mode `unknown`, so recall reads
    unavailable and every AutoTester finding is unadjudicated (K8/K10)."""
    existing = store.load_bench_corpus(corpus_id_for(slug))
    if existing is not None:
        return existing
    project = store.load_project()
    return BenchCorpus(
        id=corpus_id_for(slug), app=slug, mode="unknown",
        build_ref=(project.base_url if project else slug),
    )


def bench_from_run(
    store: ProjectStore, slug: str, run_id: str, case_bug_map: dict[str, str] | None = None,
    *, ordering: Ordering = "independent_parallel",
) -> BenchTrial:
    """Build and save the corpus (if absent) and AutoTester trial for `run_id`."""
    run = store.load_run(run_id)
    if run is None:
        raise RunNotUsable(f"run {run_id!r} not found under {store.paths.run_dir(run_id)}")
    verdicts = store.load_verdicts(run_id)
    graded = {v.case_id for v in verdicts}
    missing = [c for c in run.case_ids if c not in graded]
    if not verdicts or missing:
        raise RunNotUsable(
            f"run {run_id!r} is not fully graded: no verdict for "
            f"{missing or 'any case'} (execute and grade first)"
        )
    corpus = corpus_for(store, slug)
    if store.load_bench_corpus(corpus.id) is None:
        store.save_bench_corpus(corpus)
    trial = bench.run_autotester_trial(
        trial_id_for(slug), corpus, verdicts, case_bug_map or {},
        _duration_s(store, run_id), ordering=ordering,
    )
    store.save_bench_trial(trial)
    return trial
