# Verdict B (adversarial, combined A+B seat) - hint-malformed-bounds

**Verdict:** FAIL
**Cycle checked:** 0
**Branch / head checked:** fix/hint-malformed-bounds @ c95c22bf (off fix/cli-clamp-and-standing-help a8ef5392)
**Checker:** fresh context, read-only toward src and tests. Probes, the revert plugin and the baseline copy are in `.work/` (gitignored) and the checker scratchpad. Every criterion C1-C6 was re-judged.

## Findings (numbered)

### F1 (blocking, C3) - the refusal still crashes / prints full digits when a narrower approval row exists
The change caps the numbers it prints itself (`schema/approval.py::_shown`, `invalid_bounds_message`, `grant_clamp_warning`) but not the "approvals that exist do not cover it" detail that `require_approval` puts BEFORE `_grant_advice`: `core/consent.py:173-177` (`_shortfalls`) interpolates the raw request, `f"actions {actions} > approved ..."`. With one signed, unexpired, in-scope approval (150 actions) and a malformed/absurd request:

- `require_approval([ap], kind=CRAWL, actions=10**5000)` raises `ValueError: Exceeds the limit (4300 digits) for integer string conversion` (not `ApprovalRequired`). Same for probes and wall clock, and for every one of the 5 `ApprovalKind`s (`.work/probe_hm.py`: 15 crashes, 5 kinds x 3 positions).
- `actions=10**13` prints `actions 10000000000000 > approved 150` (14 digits) and, in the same message, `--max-actions is over 1000000000000: implausibly large`. `10**400` and `1e13` (float) print every digit / `10000000000000.0`. 30 more "LONG NUMBER" hits in the same probe.
- The refusal text for these still contains no `approve` command (C1 holds), so this is only the C3 half: "No printed number exceeds 13 digits" and "10**5000 ... refuse cleanly".

Why it matters: a refusal against a project that already has a narrower approval is the COMMON state (the gate says "the approvals that exist do not cover it"), and the unit's own risk list is "the refusal never crashes (... 10**5000 ...)". Every test in `tests/test_grant_clamp_notes.py` passes `[]` as the approvals (`_refusal`, line 190-194; `test_require_approval_with_malformed_bounds_refuses_cleanly_for_every_kind`), so the suite cannot see this path. The crash is pre-existing on a8ef5392 (baseline probe: identical `ValueError`, identical 14-digit line), so this is a gap in the fix, not a regression.
Reproduce: `.work/probe_hm2.py` (last two lines), or `PYTHONPATH=.work uv run python .work/probe_hm.py` (look at `with_ap=True`).
Suggested fix (maker's call): format `_shortfalls`' three request numbers with `schema.approval._shown` (same module import already in `consent.py`), keeping `consent.py` at <= 300 lines (it is exactly 300 now, so offset by dropping a docstring line), and add a test that passes a narrower approval row with `10**5000` / `10**13`.

### Observation O1 (not blocking, pre-existing, out of this unit)
With a COVERING approval, malformed bounds are not refused at all: `-1`, `nan`, `-inf`, `True`, `-1e308` and `-10**5000` all return the approval (`_reject_reason` -> `_shortfalls` compares with `>`, which is False for those). Probe: 60 `NO REFUSAL` rows in `with_ap=True`, kinds read and crawl shown, same on a8ef5392. This is a gate-side question, not the hint text; recorded for the checker's issues ledger, not charged to this unit.

## Criteria
| # | Result | Evidence |
|---|---|---|
| C1 no pasteable command for a malformed bound | PASS | `core/consent.py:150-151` returns the note before any command is built. Probe `.work/probe_hm.py`: 5 kinds x {no approval, one narrower approval} x 3 positions x 12 values (-1, nan, inf, -inf, True, 1e308, -1e308, 10**13, 10**400, 10**5000, -10**5000, 1e13): 0 occurrences of `uv run autotester approve`, `Grant one with` or `--standing`. `invalid_bounds_message` covers a superset of `_is_valid_bounds`'s rejections (bool, negative, NaN, inf), so the `derive_grant_bounds` call at consent.py:152 cannot raise. |
| C2 every bad bound named, good one not | PASS | `invalid_bounds_message(-1, nan, 1e308)` names `--max-actions`, `--wall-clock` and `--max-probes` is absent in the test (`test_every_malformed_bound_is_named_when_several_are_bad`, passes). |
| C3 printed numbers capped, no crash | FAIL | F1. The no-approval path is clean (0 failures, all texts < 700 chars, "implausibly large" present); the narrower-approval path is not. `grant_clamp_warning` < 400 chars: PASS (`test_the_clamp_warning_caps_...` passes). |
| C4 well-formed unchanged, approve strict | PASS | 5 kinds x 9 well-formed requests (incl. 2500 actions over the ceiling, 10**12 exactly, 86400.0004, production) x {no approval, narrower approval} = 75 refusal texts, byte-identical to a8ef5392 (`.work/old.json` vs `.work/new.json`, 0 diffs). `derive_grant_bounds` body untouched (`git diff`: docstring only). `tests/test_approve_cli_bounds.py` + `test_grant_bounds_caps.py`: 17 passed. |
| C5 CLI `explore demo --max-actions -1` | PASS | `test_explore_with_a_negative_bound_names_it_and_prints_no_approve_command` passes inside the 150-test run (exit 2, names `--max-actions is -1`, no approve command). |
| C6 design rules | PASS | `wc -l`: consent.py 300, approval.py 299, cli_crawl.py 300 (unchanged), tests file 257; no new module; `uv run ruff check src tests scripts`: All checks passed; `autotester doctor`: "2 violation(s)", matching the manifest's pre-existing SNAPSHOT pair. `hint_grant_bounds` / `_whole_seconds` / `_grant_command` have no remaining caller in `src`, `tests`, `scripts` (grep). |

## Judgement calls confirmed
1. Treating a bound above 10**12 as malformed for every kind: ACCEPTED. The largest legitimate value is the 86400 s ceiling / 2000 actions / 40000 probes; 10**12 requests round-trip as well-formed (probe row `(10**12,0,0.0)` and `(5,5,10.0**12)` unchanged vs baseline). No legitimate plan is refused.
2. Removing `hint_grant_bounds`: ACCEPTED (no caller; grep clean). `routes_crawls.py:46` splits on "Grant one with:" and so shows the whole invalid-bounds note for a malformed request, which is the intended text.

## Falsification by in-memory revert (`.work/revert_plugin.py`, `-p revert_plugin`)
- REVERT=note (`consent.invalid_bounds_message` -> `""`): `tests/test_grant_clamp_notes.py` 86 failed, 23 passed (matches the maker's number).
- REVERT=cap (`approval._shown` -> uncapped `str`): 21 failed, 88 passed (unreverted 109 passed within the 150-test pair).
Both fixes are load-bearing for the cases the suite covers; the suite has no case for F1.

## Test runs (worktree, 2 files per call, `-o addopts=`, one pytest at a time)
- `test_consent_followups.py test_cli_release.py` 86 passed; `test_approve_cli_bounds.py test_grant_bounds_caps.py` 17 passed (the two pairs the maker had not repeated after the last edit).
- `test_grant_clamp_notes.py test_cli_advice_resolves.py` 150 passed.
- Neighbours: `test_explore_consent.py test_ui_crawl_approval.py` 11 passed; `test_run_launcher_approval.py test_ui_runs_live_case_approval.py` 25 passed.

## To close (cycle 1)
Fix F1 in place (`core/consent.py::_shortfalls`, use `_shown`), add a red-first test with a signed narrower approval row for `10**5000` and `10**13` across the kinds; the rest of the unit needs no change.
