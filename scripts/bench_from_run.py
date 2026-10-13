"""T-136b: convert a real executed+graded run into the acceptance bench files.

    uv run python scripts/bench_from_run.py <slug> --run <run_id> [--bug-map FILE] [--root DIR]

Writes projects/<slug>/bench/<slug>-acceptance.json (only if absent; a human-list corpus is
never overwritten) and <slug>-acceptance-autotester.trial.json, then run
scripts/check_acceptance_comparison.py <slug>. Contract: qa/contracts/bench.md K10.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.stages.bench_from_run import RunNotUsable, bench_from_run
from autotester.store.project_store import ProjectStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project")
    parser.add_argument("--run", required=True, help="run id of an executed+graded run")
    parser.add_argument("--bug-map", type=Path, default=None,
                        help="JSON {case_id: bug_id}; only meaningful with a human-list corpus")
    parser.add_argument("--ordering", default="independent_parallel",
                        choices=["independent_parallel", "human_read_ai_first",
                                 "ai_read_human_first", "unknown"])
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    store = ProjectStore(args.project, args.root)
    bug_map = json.loads(args.bug_map.read_text(encoding="utf-8")) if args.bug_map else None
    try:
        trial = bench_from_run(store, args.project, args.run, bug_map, ordering=args.ordering)
    except RunNotUsable as exc:
        print(f"cannot build bench files: {exc}", file=sys.stderr)
        return 2
    print(f"saved {store.paths.bench_trial(trial.id)} ({len(trial.findings)} findings, "
          f"duration_s={trial.duration_s})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
