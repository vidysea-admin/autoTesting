# Checkpoint A - at758-759-host-allowlist (cycle 0, coordinator A)

Commit checked: c642dcb5 (product 2e9b3bf8; the only diff between them is the manifest). Policy-Version: proportional-verification/2026-10-10.9.
Checker attribution: coordinator A (claude-sonnet-subagent), verdict qa/verdicts/at758-759-host-allowlist.a.md, evidence qa/evidence/at758-759-host-allowlist-a/.
Environment: Windows 11, python 3.11.15 (D:/autoTesting/.venv), copies are `git archive` extractions in uniquely named scratch dirs (A758fresh = c642dcb5, A758master = 16efd426), PYTHONPATH=<copy>/src for in-process runs.

Code hashes (blob): ui/helpers.py 1cee1c72 · stages/explore_consent.py 2de6550f · tests/conftest.py 6e574e96 · tests/test_ui_origin_guard.py dfad606b · tests/test_credential_run_approval.py 3dff0010 · uv.lock e9bfb886.

| Check | Command / scope | Result |
|---|---|---|
| C1-C4 affected tests | pytest tests/test_ui_origin_guard.py tests/test_credential_run_approval.py tests/test_consent.py tests/test_hosting_deploy.py (158 collected) | 157 passed, 1 failed (test_env_example_documents_every_key_the_code_reads, also red on master 16efd426) |
| C1 attack | evidence attack_host.py: 39 hostile Host values x 75 route/method probes (2,850 sent), plus ASGI-level cases and env-list matrix | 0 non-403/non-empty, 0 leaks (master 16efd426: 2,850 not-403, 1,026 leaking) |
| C4 attack | evidence attack_approval.py: CRAWL, LIVE_CASE, READ x {.env removed, domain re-scoped, declaration dropped, value blanked}; ADVERSARIAL; human row | tree c642dcb5: all REFUSED; master: all COVERS (differential) |
| Falsification | evidence falsify.py, one isolated copy per row, green-before / red-after / restored | C1a C1b C1c C2 C3a C3b C3c C4a C4b all green->red->green; C5 (helpers.py +12 lines) doctor clean->1 violation |
| ruff / doctor | in A758fresh | clean / clean |
| Full suite | shard_suite --shards 4 --ref c642dcb5 -o addopts= (collect proof ok, 3,107 = 3,107) | 3,084 passed, 19 skipped, 4 failed (none new, see verdict) |

Reuse: none of the builder's Pre-check output was reused; every command was re-run.
