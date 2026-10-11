# Checkpoint (coordinator B) — t205-g10-headroom

Cycle checked: 0
Status: COMPLETE (verdict PASS written to qa/verdicts/t205-g10-headroom.b.md)
Head: 0b8325b61bf89e2ed66d62ef02ec47f94c211733 (branch wave/t205-g10-headroom), product sha 3ebd2fca, base master 09828f2d
Worktree: D:/autoTesting/.worktrees/t205-g10-headroom (read-only for B; python = its .venv)
Policy-Version: proportional-verification/2026-10-10.9
Environment: Windows 11 10.0.26300, uv run --project <worktree>, temp data roots, fake keys, AUTOTESTER_ALLOWED_HOSTS=testserver for TestClient; no .env read; no network.
Master comparison tree: `git archive 09828f2d` extracted into the scratchpad, used via PYTHONPATH (not committed).

## Evidence identity (all in qa/evidence/t205-g10-headroom-B/)
| Check | Command (script) | Result | Output file |
|---|---|---|---|
| Refusal / status differential, master vs branch | diff_routes.py (TestClient, temp root) run on both trees | outputs identical; no secret/path/traceback leak | refusals-master.txt, refusals-branch.txt |
| Route table, middleware, handlers | routes_dump.py (flatten `original_router`) on both trees | 56 rows identical | route-table-master.txt, route-table-branch.txt |
| Names | names.py | refused/accepted lists as in verdict attack 5 | names-out.txt |
| Marker exclusivity | ts2.py | `nul:` True/True, `ab:stream` ADS | marker-out.txt |
| Policy merge | policy_chk.py | as in verdict attack 4 | policy-out.txt |
| Schema | schema_chk.py <master tree> <branch src> | 9/9 project.json load, run back-compat, forbids hold | schema-out.txt |
| Falsification F1 (+F2, F3, F3b, F3c) | falsify.py (copies of HEAD under scratchpad, deleted at end) | F1 21 passed -> 1 failed/20 passed; F2 21 passed; F3* 12 passed; `copies deleted: True` | falsify-out.txt |
| Builder's new tests (re-run for sanity) | 8 new test files, pytest | 87 passed in 4.5 s | (in verdict text) |

Script sha256 prefixes: diff_routes 7576700e, falsify b3f76c3b, names f9561ce7, policy_chk 5f81bf2f, routes_dump 3c7532b0, schema_chk 5d319015, ts2 35a5f28e.

## Not run (by assignment)
Full suite, any browser (seat A). full-suite trigger: router/CLI seam (for the 6c integration check).

## Remaining
None. B wrote no issue rows, merged nothing, closed no goal task, pushed nothing.
