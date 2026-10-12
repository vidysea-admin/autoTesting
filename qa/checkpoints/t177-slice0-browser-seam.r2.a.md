# Checkpoint - t177-slice0-browser-seam - repair checker coordinator A, cycle 2

Attribution: claude-sonnet-subagent, coordinator A (blind dual). Verdict: qa/verdicts/t177-slice0-browser-seam.r2.a.md. Policy-Version: proportional-verification/2026-10-10.9.

Common identity fields for every row below:
- code: launch.py blob c94951d84410, tests/test_browser_cdp_probe_hostile.py blob 9ad42d143786 (git rev-parse 1f4f0514:<path>); head 1f4f0514, code SHA a8f2b9fb
- lock: uv.lock blob 4882ef560a75; pyproject.toml blob 72a83bd9e4af
- environment: Windows 11, Python 3.11.15, venv synced from the archive in a C: copy (`uv sync`), pytest 9.1.1 `-p no:xdist -p no:cacheprovider -o addopts=`; loaded host (sibling checker pythons)
- browser/live: headless Chromium via tests/test_browser_session_cdp_live.py; no data snapshot

| check | command / scope | result | evidence |
|---|---|---|---|
| hostile listeners (56 x 3) | own raw-socket battery against `_answers_as` and `verified_cdp_url` | max 2.156 s public, 2.11 s direct; all refusals; cap+1 bytes | qa/evidence/t177-slice0-r2-A/hostile/ |
| start() path | fake launch, cases 01/02/04/09a/11a/11b | CdpEndpointError, context closed, port file removed | hostile/session.json |
| interrupts | own test, KeyboardInterrupt/SystemExit via start() and inside read1 | propagate, cleanup ran, no Timer left (4 passed) | interrupt/output.txt |
| watchdog races | 2000 fast replies; 200 near-deadline; 1800 boundary | no truncated acceptance, no leftover thread/socket | hostile/race_*.json, amp_*.json |
| falsification x4 + 6 probes | own copies, venv python + PYTHONPATH | 1a, 1b, 2, 3 red for the named reason; 4 probes survive | falsify/results.md |
| wildcard full-queue probe | wildcard_fullbacklog.py | wildcard + full queue -> False | loopback/output.txt |
| affected tests | hostile 11, session_cdp 23, settle 10, browser 15, secrets 68, live 2 | all passed | gates/affected-output.txt |
| ruff / doctor / sizes | ruff check src tests scripts; autotester doctor; ast | clean; max file 299, max function 49 | verdict |
| trial merge | clone on C:, master d42e9445, merge --no-commit | 1 conflict: docs/SNAPSHOT.md (generated) | verdict |
| full suite | shard_suite.py --repo D:/autoTesting --ref 1f4f0514 --shards 4 -- -o addopts= | 3533 passed, 20 skipped, 6 failed (2 known load, 3 same on base, 1 harness-venv artifact); collect proof ok | suite/shard_suite.out, suite/base-run.txt, suite/healthz-compare.txt |
