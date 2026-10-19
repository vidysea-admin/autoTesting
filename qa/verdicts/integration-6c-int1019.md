# Verdict - integration-6c-int1019 (maker step 6c pre-push, cycle 0)
Cycle checked: 0
Date: 2026-10-19 · bound to D:/autoTesting/.worktrees/int-1019 · base origin/master 4ce91ea8 · head under test e7ea17d3 (+ this verdict and a regenerated docs/SNAPSHOT.md) · Policy: proportional-verification/2026-10-19.16

## Scope
Merges: wave/t136-negpath-assert (PASS), wave/t136-route-b (PASS), wave/umesh-1019-gates (docs), ledger renumber AT-1346 -> AT-1348. No .13-2 trigger (no conftest edit, no security / prod-write L unit), so .13-1 behaviour-scoped set + one full collection, no full suite.

## Evidence (own runs, TMP/TEMP=D:/autoTesting/.work/tmp)
- Behaviour-scoped set: both manifests' Tests lines plus consumers plus every tests/ file importing stages.grade, stages.grade_images, stages.run_case_pipeline, schema.bench, schema.acceptance (grep): 703 passed, 0 failed, 0 errors (384.95 s; log .work/tmp/6c-scoped.log).
- `uv run pytest --collect-only`: 8827 tests collected, clean (2 deprecation warnings only).
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: first run 2 violations, both docs/SNAPSHOT.md stale (stale-generated, stale-committed): the snapshot lacked D-106 (added by the umesh-1019-gates merge) and still listed D-101. Fixed mechanically with `autotester snapshot` (1 line moved: D-101 out, D-106 in), committed with this verdict; precedent commit 345c1606. Re-run after regeneration: the only remaining finding was the stale-committed check against HEAD until the commit; after the commit doctor is clean of violations.
- New reds vs qa/checkpoints/baseline-reds.md: none.

Metrics: check_s=1500 mutants=0 defects_unit=0 defects_6c=1
