# Checkpoint (coordinator B) — t179a-lead-tester-core

Cycle checked: 0
Status: COMPLETE (verdict PASS written to qa/verdicts/t179a-lead-tester-core.b.md)
Head: 638d788a (code 90705dc0), branch wave/t179-lead-tester, base master 16aaa402
Work tree: `git archive 638d788a` extracted to a uniquely named folder on C: (temp), its own venv, never edited; `autotester.__file__` confirmed inside it. No checkout, worktree or venv on D:.
Policy-Version: proportional-verification/2026-10-10.9
Environment: Windows 11 10.0.26300, `uv --directory <copy> run`, scratch env file with fake canaries, fake `AUTOTESTER_APPROVAL_KEY`; no real `.env` read; no network; no browser.

## Evidence identity (all in qa/evidence/t179a-lead-tester-core-B/)
| Check | Command (script) | Result | Output file |
|---|---|---|---|
| Black-box attack matrix, 403 calls | `python attack.py <outdir>` (attack_cases.py defines S1-S6); spies on browser open, execute.run_case, explore.run_crawl, MockProvider prompts | 223 refused, 163 executed, 17 raised; leak scan: return 1 (contrived), exception 8, stored files 20 (encoded forms / seeded fixtures), logs 0, judge prompts 0 | attack-table.md, results.json |
| Gate differential | `python gate_probe.py` (bare assert_no_raw_secrets vs repr-wrapped gate, 9 spellings) | zero-width, soft hyphen, newline-split differ | gate_probe.py (output in verdict P4) |
| Diff scope | `git diff <merge-base>..638d788a --stat` | 6 src/test files + manifest, brief, MAP, SNAPSHOT, all declared | static/full.diff, static/docs.diff |
| Tests | `pytest tests/test_agent_tools.py` (no CLI -q) | 14 passed | static/pytest.txt, static/testnames.txt |
| ruff, doctor, sizes | `ruff check src tests scripts`, `autotester doctor`, line and function counts | clean; tools.py 184 lines; no function over 50 | (verdict Static) |
| Falsification x6 | throwaway copies on C:, green-before / red-after / restored | AL2, AL3a, AL3b, AL3c, AL6 (_release), AL6 (_scrubbed) all red after the edit | falsification/row_*.txt |

Script sha256 prefixes: attack.py 9d206fdf, attack_cases.py c309e238, gate_probe.py 6656d079, results.json c8216dd0.
Canaries are obviously fake strings defined in attack.py; results and tables use labels only (no raw or encoded canary text), `scratch.env` is not committed.

## Not run (by assignment)
Full suite, suite lock, browser, any `.a.md`/`-A` file. full-suite trigger: none from this seat (new package, no config/conftest change).

## Remaining
None. B wrote no issue rows, flipped no manifest, merged and pushed nothing.
