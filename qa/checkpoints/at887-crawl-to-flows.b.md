# Checkpoint B - at887-crawl-to-flows (cycle 0)

Environment: Windows, python 3.11 venv on C: (UV_PROJECT_ENVIRONMENT=scratchpad/venv-b2), tree = `git archive 6d70c0ec` extracted on C:. Lock: uv.lock at 6d70c0ec. Attribution: coordinator B, verdict qa/verdicts/at887-crawl-to-flows.b.md.

| Check | Command / scope | Code | Result |
|---|---|---|---|
| AT-887 data path | qa/evidence/at887-crawl-to-flows-B/data-path/probe_datapath.py (own fixture) | 6d70c0ec | pass |
| Three doors | probe_doors.py (AUTOTESTER_ALLOWED_HOSTS=testserver) | 6d70c0ec | pass, 0 provider calls |
| Dangling screen ids | probe_dangling.py | 6d70c0ec | FAIL (P1) |
| Falsifications AT-887 | falsify_887.py F1-F10 | 6d70c0ec | F1-F5, F7-F10 red; F6 survives (P4) |
| AT-890 spy | at890/probe1.py, probe2.py, t3.py | 6d70c0ec | secrets pass |
| AT-890 falsifications | at890/fz.py F6'-F9' | 6d70c0ec | all red |
| Phone prompt corruption | probe_phone.py | 6d70c0ec | FAIL (P2) |
| UI Generate catches only ProviderError | read ui/routes_learn.py:256-257, core/redact.py:254,258 | 6d70c0ec | FAIL (P3) |
| Targeted tests | pytest -p no:xdist -o addopts=: flows, doors, redaction, explore_merge (60); redact_pii 133; expand 15; expand_cli 10; eval_compiler 23 | 6d70c0ec | passed |
| ruff / doctor / map | review/ruff.txt, doctor.txt, regen.txt | 6d70c0ec | exit 0 / 0 / identical |
| Diff scope, D-082, gap rulings | review/ | 6d70c0ec | in verdict |

Full suite: not run (the other coordinator owns it). A repair checker (cycle 1) needs: P1, P2 and P3 re-run, the AT-890 redaction tests, the explore_flows and doors tests, and one falsification per repaired criterion.
