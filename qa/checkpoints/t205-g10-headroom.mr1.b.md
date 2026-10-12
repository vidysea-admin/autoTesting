# Checkpoint — t205-g10-headroom, merge-reconcile 1, coordinator B
Policy-Version: proportional-verification/2026-10-10.9 · Verdict: PASS (qa/verdicts/t205-g10-headroom.mr1.b.md) · Cycle checked: 1 · Resume: 0 of 2
Attribution: claude-sonnet-subagent (coordinator B, blind; no `.mr1.a` / `-mr1-A` file opened)

## Evidence identity
- Bound code: branch `wave/t205-g10-headroom` head `ecaaf7e4`; product `39b42ca5`; merge `b841c232` (parents `fb93776b`, `1c52bf71`); master compared: `1c52bf71`.
- Head tree hash `b1ce9143ec8aa23d53804046b7bc0f944959780a`; lock: `uv.lock` blob `93f572eb...` (same in both copies).
- Environment: Python 3.11.15, uv 0.11.27, Windows 11; each copy has its own `.venv` on C: (`%TEMP%/at-mr1b-123619858/{head,master,mut-*,pt}`); `autotester.__file__` printed first in every probe output and is inside its copy.
- No `.env` value read; dummy signing key `probe-only-signing-key-not-real`; spies replace `BrowserSession`, `run_execution.run_and_grade_case_resilient`, `for_role`.

## Checks run (command and scope -> result)
| Check | Scope | Result |
|---|---|---|
| Route probe `probes/drive_routes.py`, head and master | 34 rows, TestClient, scratch `AUTOTESTER_ROOT` per row | `routes-head.json` == `routes-master.json` (all rows) |
| Door probe `probes/drive_doors.py` | head 99 rows, master 46 rows | no ungated door; refusals and executed sets equal per equivalent row |
| Origin probe `probes/drive_origin.py gen/load` | 3 real intake routes (upload, zip x2 members, Drive link) + stored samples + hostile shapes | master lines byte-exact after head re-save (4/4); hostile shapes refused as on master; bare enum accepted only on head |
| CLI `probes/cli_tree.py` + 8 `--help` subprocesses | 43 commands/groups; `tests/golden/cli_commands.json` | identical; golden == live listing |
| Enum identity `probes/enums_id.py` | 5 schedule enums, all modules | one definition each, `is` identity across paths |
| `ruff check src tests scripts` (head copy) | whole tree | All checks passed (`ruff-head.txt`) |
| `autotester doctor` (head copy, git-less) | design rules | `doctor: clean` (`doctor-head.txt`) |
| Falsification F1a, F1b, F2a, F2b, F3 (5 copies, `PYTHONPATH=<copy>/src`) | named tests in the verdict | green before, red after (`falsify/g-*.txt`, `falsify/r-*.txt`); bound copy untouched |

Not run (by instruction): full suite, suite lock, real browser, live site, real model call, any `qa/issues.jsonl` write, manifest flip, merge, push.
Out of scope for B (the other coordinator's): diff audit, test suite, TF4/TF7 detail, generated-doc checks that need git.

## Resume notes
Complete; nothing remaining. Slow steps: `uv sync` for the two copies and sequential `uv run` CLI subprocesses (45 min wall, 5 falsification copies in parallel).
