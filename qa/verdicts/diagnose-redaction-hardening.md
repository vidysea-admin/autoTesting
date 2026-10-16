# Verdict — diagnose-redaction-hardening

Verdict: PASS

Cycle checked: 2
Reviewed SHA: 49b386e63b804a10bb307a56c859fcce1602fba7
Base SHA: 3f081243
Prior verdicts: cycle 0 FAIL (edca4583, candidate 4bdb3437), cycle 1 FAIL (4d8f239e, candidate ba5735e7)

## Why PASS

The cycle 1 blocker is fixed. The awk `.env` reader leaked `KEY=val # comment`, `KEY = val` and
`KEY="val" # c`. All three are now masked on the python-dotenv path and on the awk-only path. No
regression was found in the earlier shapes.

## Verified (independent, evidence under .work/checker-diagnose-redaction-hardening/c2/)

1. Dotenv forms (`probe.env`, ground truth from python-dotenv `dotenv_values` in `truth.tsv`).
   The fixture covers 23 lines and 22 value lines: the 3 cycle-1 leak forms, `export K=v`,
   `export K = "v"`, double- and single-quoted multiline, `K=`, single quotes,
   `K='a # b'` (the `#` is kept as part of the value), escaped `\"`, three CRLF lines
   (plain, quoted, commented), a tab before `#`, padded values, UTF-8 and sed-special characters.
   - python path (venv python, PYMODE confirmed): 0 leaks (`out_py.txt`).
   - awk-only path (python removed from PATH and AUTOTESTER_PYTHON set to a nonexistent path,
     PYMODE=none): 0 leaks (`out_nopy.txt`). Both outputs are byte-identical.
   - `K=` does not over-mask a benign line.
   - Probe artifact noted, not a product defect: the first run's ground truth was cp1252 because
     `-I` ignores PYTHONIOENCODING. It was rerun with `-X utf8`.
2. Regression: all 72 cycle-0 shapes through `leak_probe.sh` give 72 ok and 0 LEAK. The output
   is byte-identical to the cycle-1 candidate ba5735e7 (`leak_diff.txt` is empty). The cycle-1
   `dotenv_shapes.sh` now masks all 5 values (cycle 1 leaked 3).
3. Split is behaviour-identical. A 37-line fixture log (diag_raw.txt plus the probe text) was run
   through redact + diagnose on ba5735e7 and on the candidate, with and without python. The only
   diff is the 13 previously leaked values, which are now `<redacted>`. The DIAGNOSIS output and
   rc are identical. The workflow `paths` lists `scripts/container_diagnose_lib.sh` under both
   push and pull_request.
4. Argv check (code inspection): values travel only through pipes and the value file. Argv
   carries only paths: `--values-from-env FILE`, `redact_cli VALUES_FILE`, `sed -f vf.sed`. The
   static `_REDACT_SED` holds no values. main runs `umask 077`, `mktemp -d` and `chmod 700`, and
   `_redact_load`/`redact` subshells run `umask 077`. `ps` was not sampled. The modes 0700/0600
   cannot be verified on NTFS, so they are left as a CI-verifiable item.
5. redact_cli failure (a `fakepy` that passes the import probe but fails `-m`): both NOTICEs go to
   stderr, plus an in-log `[NOTICE: python redaction failed ...]` line. None of the 5 secrets
   appears in the output. Kept lines that contain a value are value-masked, and 3 lines were
   withheld.
6. Commands (each exit code in its own `.rc` file): `bash -n` on both scripts gave 0/0. pytest
   (no -q) on tests/test_container_redaction.py and tests/test_container_ci_workflow.py, using the
   main .venv python with PYTHONPATH=worktree/src (import root confirmed in the worktree): 95
   passed, 1 skipped, rc 0. `ruff check src tests scripts` gave 0. doctor reported clean, rc 0.
   File sizes: 153, 253 and 58 lines (all under 300).

## Findings (non-blocking)

- When python-dotenv fails, a non-UTF-8 log byte becomes U+FFFD on the python path (the decode
  uses errors=replace). This changes readability only. It is not a leak.
- `diagnose` echoes PREFLIGHT lines from the file it is given. main passes it the already
  redacted LOG, so this does not leak today.

## Remaining gates

- A real docker or CI run to confirm the 0700/0600 modes and real Cloud Run log shapes.
- The full suite runs post-merge.

## Metrics

- Cycle 2 checker: about 600 s active wall time from start to verdict, including the 103 s pytest.
  This is at the 600 s approved finite escalation, which the orchestrator approved for this one
  cycle. Tokens: runtime actual_total unknown (null), roughly 70k context observed. Cumulative
  checker time and tokens exceed the 1.0x cap and the 10% target. This ratio miss is recorded,
  not waived. The review_budget.py assess phase files were not produced this cycle (time cap).
