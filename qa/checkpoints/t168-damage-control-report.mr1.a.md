# Checkpoint t168-damage-control-report mr1 A (merge reconcile 1)

Attribution: SEAT A coordinator, verdict qa/verdicts/t168-damage-control-report.mr1.a.md. Environment: Windows, Python 3.11.15, pytest 9.1.1, uv worktree venv. Code head 2425506a03e9; uv.lock sha1 81818cd47301. Data/browser: none.

| Check | Command and scope | Result |
|---|---|---|
| unit modules unchanged | git diff 4b93d952 2425506a -- 4 unit src files + 2 unit test files | empty |
| conflict resolution | git show 97465d5d --cc | 1 file, both entries kept, count 24 |
| cli.py formatting only | ast.dump equality, cli.py at 97465d5d vs 2425506a | equal |
| nothing dropped | blob compare, 598 master-only + 10 branch-only files | 2 expected differences (SNAPSHOT, manifest) |
| tests | pytest -p no:xdist -o addopts= (8 files, abs paths) | 126 passed |
| lint / doctor | ruff check src tests scripts; autotester doctor | clean |
| falsification | copy via git archive, drop site entry / count 24->23 | green before, red on named assertions |
