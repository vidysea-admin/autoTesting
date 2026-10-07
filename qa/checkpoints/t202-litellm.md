# Checkpoint — t202-litellm (cycle 0, single checker)

Completed checks (evidence identity: tree = d5c200b7 + qa ledger rows only; lock hash ad191bacfcd0dae4 (sha256 prefix), pyproject hash 5a4c8969ae612f0a; env = Windows 11, CPython 3.11.15, litellm 1.104.0 from uv.lock, no network beyond loopback):

| Check | Command / scope | Result |
|---|---|---|
| falsification x20 | per-row throwaway copy, named nodes in tests/test_litellm_provider.py, test_litellm_guard.py, test_provider_factory.py; `ck-t202/fals.py` rows 0-19 | all green before, red after |
| lock | `uv lock --check`; loosened-pin copy | clean / red |
| lint | `ruff check src tests scripts` | passed |
| doctor | `autotester doctor`; 337-line copy | clean / red |
| real-SDK probe | litellm 1.104.0 vs loopback mock, `ck-t202/probe_real.py`, `probe_conn.py` | 1 request on 500, environ delta two flags, callbacks empty, loopback sockets only |
| probes | `ck-t202/x1`, `x2` (learn 500, short .env false refusal, vertex @, vendor-key echo) | AT-782..AT-788 |
| retargeted tests diff | `git diff 7782df41 d5c200b7` over the 12 files | no assertion weakened |

Not completed (pending for the repair checker): the one full `uv run pytest`, started 2026-10-07 18:50 (no -q, no -x), about 38% at 19:16, log `D:/autoTesting/.work/t202-suite.log`. Reason: shared RAM and CPU with other checkers' suites; `D:/autoTesting/.work/suite.lock` was held by t190-ux and the checker was denied stopping its own process. One `F` was seen near 20%; node unidentified. Run once on the repaired tree.

Repair checker should re-run: LL8 (AT-782 canary tests plus a falsification that empties the new withhold set), the affected tests for the fix diff, and the full suite.
