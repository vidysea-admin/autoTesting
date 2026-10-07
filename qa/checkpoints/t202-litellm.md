# Checkpoint — t202-litellm (cycle 0, single checker)

Completed checks (evidence identity: tree = d5c200b7 + qa ledger rows only; lock hash ad191bacfcd0dae4 (sha256 prefix), pyproject hash 5a4c8969ae612f0a; env = Windows 11, CPython 3.11.15, litellm 1.104.0 from uv.lock, no network beyond loopback):

| Check | Command / scope | Result |
|---|---|---|
| falsification x20 | per-row throwaway copy, named nodes in tests/test_litellm_provider.py, test_litellm_guard.py, test_provider_factory.py; `ck-t202/fals.py` rows 0-19 | all green before, red after |
| lock | `uv lock --check`; loosened-pin copy | clean / red |
| lint | `ruff check src tests scripts` | passed |
| doctor | `autotester doctor`; 337-line copy | clean / red |
| real-SDK probe | litellm 1.104.0 vs loopback mock, `ck-t202/probe_real.py`, `probe_conn.py` | 1 request on 500, environ delta two flags, callbacks empty, loopback sockets only |
| probes | `ck-t202/x1`, `x2` (learn 500, short .env false refusal, vertex @, vendor-key echo) | AT-790..AT-796 |
| retargeted tests diff | `git diff 7782df41 d5c200b7` over the 12 files | no assertion weakened |

Not completed (pending for the repair checker): the one full `uv run pytest`, started 2026-10-07 18:50 (no -q, no -x), about 38% at 19:16, log `D:/autoTesting/.work/t202-suite.log`. Reason: shared RAM and CPU with other checkers' suites; `D:/autoTesting/.work/suite.lock` was held by t190-ux and the checker was denied stopping its own process. One `F` was seen near 20%; node unidentified. Run once on the repaired tree.

Repair checker should re-run: LL8 (AT-790 canary tests plus a falsification that empties the new withhold set), the affected tests for the fix diff, and the full suite.

## Cycle 1 (repair checker, tree 7b87b222; lock ad191bacfcd0dae4, pyproject 5a4c8969ae612f0a unchanged; Windows 11, CPython 3.11, fake SDK only)

| Check | Command / scope | Result |
|---|---|---|
| LL8 own probes | qa/evidence/t202-ll8-probe-cycle1.py.txt: 8 secret sources x 3 echo shapes over provider, learn page, CLI expand, run grader path and saved files | 50 passed, 1 skipped |
| single source | call-count probe and source read litellm_provider.py:183-203 | _guard and _failure each call _secret_values() once |
| falsification F1-F6 | one copy each (runner in qa/evidence) | all red, green before |
| affected tests | litellm_provider, litellm_guard, provider_factory, ui_learn, ingest_narration, providers | 87 passed |
| lock, ruff, doctor | uv lock --check, ruff check src tests scripts, autotester doctor | clean |
| other LL criteria | reused from cycle 0 (inputs unchanged) | kept |

Pending: the one full uv run pytest (deselect tests/test_crawl_inventory_live.py), queued 7th in the suite-lock order; lock not taken. The resume runs only that, then the PASS steps (manifest flip, merge, renumber AT-790..796 after master max, push).
