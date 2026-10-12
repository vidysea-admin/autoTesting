# Checkpoint - t177-slice0-browser-seam - coordinator B - cycle 2

Checker: claude-sonnet-subagent (coordinator B). Verdict: qa/verdicts/t177-slice0-browser-seam.r2.b.md (PASS). Evidence dir: qa/evidence/t177-slice0-r2-B/.
Environment fingerprint: Windows 11 (10.0.26300), Python 3.11.15, Playwright chromium-1243 headless, uv-synced venv in a `git archive 1f4f0514` copy on C: (scratchpad r2b-3222928938/head); repair base copy `.../base`; `autotester.__file__` asserted inside the copy by every script. Host ~100% CPU, 20 cores, 2.8 GB free RAM.
Code identity: launch.py of 1f4f0514 (code SHA a8f2b9fb); lock: uv.lock of that commit (unchanged by the unit); data snapshot: not applicable.

## Completed checks (all result PASS)
| check | command / scope | result |
|---|---|---|
| 20 real rounds head | harness/rounds.py head 20 (expose_cdp=True) | start median 5.11 s, worst 7.72 s; probe median 1.031 s; 20/20 clean; rounds-head-1.jsonl |
| 20 real rounds base | harness/rounds.py base 20 (0a4859a1) | start median 4.97 s, worst 10.58 s; probe median 1.015 s; 20/20 clean; rounds-base-1.jsonl |
| substitution attacks | harness/attacks.py (15 variants a1..h) | all refused except f1 (right guid at 1.9 s, accepted by design); browser closed each refused time; attacks-1.jsonl, rest.log (c2) |
| extra hostile | harness/misc.py, misc2.py (race x300, header flood, 100-continue) | race 0/300 early success; header flood 6.1 MB in 0.05 s; 100-continue held 2.02 s |
| threads x5 | harness/conc_threads.py | 5/5 started, cross pairs true only on diagonal, clean close; run3.log |
| processes x5 | harness/conc_proc.py | cross_ok 5/5, clean close; proc*.json |
| interrupts | harness/interrupts.py | KeyboardInterrupt (injected and interrupt_main) propagates, browser closed; rest.log |
| _reaches_past_loopback | harness/misc.py, raw_wild.py | raw Chromium 0.0.0.0 still loopback -> False; 127.0.0.2 listener True; full-backlog listener False after 1.0 s |
| affected tests | pytest hostile + session_cdp + navigation_secrets + session_cdp_live (head copy) | 104 passed in 50.6 s |
| ruff / doctor | ruff check src tests scripts; autotester doctor | all passed / clean |
| falsification 1a | watchdog.start() -> pass; node ...cut_off_at_the_overall_deadline[drip_headers] | 1 pass / red `assert 5.1 < 2.0` / 1 pass |
| falsification 1b | both PROBE_MAX_BYTES checks removed; padded_declared + padded_undeclared | 2 pass / red DID NOT RAISE / 2 pass |
| falsification 2 | except Exception -> (OSError, ValueError, HTTPException); deeply_nested | 1 pass / red RecursionError / 1 pass |
| falsification 3 | _answers_as := repair-base urllib version; redirect_never_followed x2 | 2 pass / red DID NOT RAISE / 2 pass |

Each falsification ran in its own copy (fals-1a-*, fals-1b-*, fals-2-*, fals-3-*) with PYTHONPATH pointing to that copy's src and tests, using the head venv's python (not `uv --directory <copy> run`: no per-copy venv was built, to save time); the copy was restored (edit reverted) and re-run green. Raw blocks in run3.log.

## Not run / limits
- Headed Chrome (does it honour --remote-debugging-address) not run; no 0.0.0.0 listener bound (firewall-prompt risk).
- Second rounds pass (rounds-head-2.jsonl, rounds-base-2.jsonl, quieter host): head start median 2.60 s / worst 3.19 s, base 2.63 s / 5.02 s, probe median 1.016 s both, 40/40 clean.
- No full suite, no suite lock.
