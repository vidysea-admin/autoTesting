# Verdict B (adversarial, combined A+B seat) - hint-malformed-bounds

**Verdict:** PASS
**Cycle checked:** 1
**Branch / head checked:** fix/hint-malformed-bounds @ 21fe40de (off fix/cli-clamp-and-standing-help a8ef5392)
**Checker:** fresh context, read-only toward src and tests. Probes, the baseline copy (`git archive a8ef5392 src`) and the in-memory revert plugin live in the checker scratchpad (outside the repo). Every criterion C1-C6 was re-judged; no git stash, no merge, no push, main checkout untouched.

## Findings

### F1 (cycle 0, blocking) - CLOSED
`src/autotester/core/consent.py:174,176,178` now format the three request numbers through `_shown` (imported at `:26`); the `approval.max_*` side is unchanged (signed row numbers). Evidence:
- Own probe (`cmp.py`): 5 `ApprovalKind` x 3 bound slots x 9 bad values (-1, NaN, inf, True, 1e308, 10**13, 10**400, 10**5000, 1e13) with ONE signed narrower approval (150/100/900): new head `crashes 0, longs 0` (0 raised anything but `ApprovalRequired`; 0 digit runs of 14+; 0 texts over 700 chars; 0 `approve` / `Grant one with` / `--standing`). The same probe on a8ef5392 gives `crashes 16` (`ValueError: Exceeds the limit (4300 digits)`) and `longs 134` - so the probe does see the defect.
- Tests: `tests/test_grant_clamp_notes.py:268-299` (45 + 5 cases) pass.
- Falsification by in-memory revert (plugin monkeypatching `consent._shortfalls` back to the raw f-strings, no source edit): `pytest tests/test_grant_clamp_notes.py -p rev_short -k narrower` -> **45 failed, 5 passed**. The 45 are exactly the cap test; the 5 well-formed tests correctly stay green. The new tests are load-bearing.

### Byte-identity for well-formed requests (C4)
`cmp.py`: 5 kinds x {no approval, narrower approval, wide approval} x 12 well-formed requests (incl. 2500 actions over the ceiling, exactly 10**12, 86400.0004, 700.5, 3000/60000/90000 over every ceiling) = 180 results; compared with a8ef5392: **0 differences**, 65 `RETURNED` (covered) identical, 0 crashes.

### Other raw-number paths hunted (none found)
- `grep` of every f-string over actions/probes/wall in `src`: refusal builders are only `consent.py:174-178` (fixed) and `:266` (`_grant_advice` -> `invalid_bounds_message` / `grant_clamp_warning`, both capped via `_shown`, `schema/approval.py:106-136`). `explore_consent.py:72-77` only wraps the same text; `consent.py:292-300` appends a slug/row-id note, no request numbers. `cli_crawl.py:283`, `report_export.py:61` print an approved row's own bounds after success, not a refusal.
- Observation O2 (non-blocking, out of scope): `consent.py:63,65` (`check_grant_limits`, the NEW-grant cap shared by CLI `approve` and the UI) interpolates the raw `actions` / `wall_clock_s` into a `ValueError`; with 10**5000 `str()` would raise. It is the grant path, not the refusal text, `approve` is explicitly unchanged (C4) and `int()` of a 5000-digit CLI string fails earlier. Not charged to this unit.
- Observation O1 (carried, out of scope per brief): with an approval that does not reject on `>` (-1, NaN, True), malformed bounds return/ignore rather than refuse (45 `NO REFUSAL` rows = 5 kinds x 3 slots x {-1, NaN, True}, identical on a8ef5392). Recommend the issues ledger.

## Criteria
| # | Result | Evidence |
|---|---|---|
| C1 no pasteable command for a malformed bound, every kind | PASS | `consent.py:149-151` returns the note first; probe above 0 command strings across 5 kinds x with/without a narrower approval. |
| C2 each bad bound named, good one not | PASS | `test_every_malformed_bound_is_named_when_several_are_bad` in the 200-test run. |
| C3 no printed number over 13 digits, no crash, <700 chars, "implausibly large" | PASS | F1 closed; probe 0 longs / 0 crashes on both the no-approval and narrower-approval paths; `grant_clamp_warning` cap test passes. |
| C4 well-formed unchanged, `approve` strict | PASS | 180/180 byte-identical to a8ef5392; `test_approve_cli_bounds.py test_grant_bounds_caps.py` 17 passed. |
| C5 `explore demo --max-actions -1` exit 2, named, no command | PASS | `test_explore_with_a_negative_bound_...` in the 200-test run. |
| C6 design rules | PASS | `wc -l`: consent.py 300, approval.py 299, cli_crawl.py 300 (untouched), tests file 299; no new module; `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> `2 violation(s)`, both `decision-citation-known-disputed` (`docs/DECISIONS.md:80` D-000 K1, `:209` D-005 K2), advisory/non-blocking, files this unit does not touch. |

## Test runs (worktree, 2 files per call, `-o addopts=`, one pytest at a time)
- `test_grant_clamp_notes.py test_cli_advice_resolves.py` -> 200 passed
- `test_consent_followups.py test_cli_release.py` -> 86 passed
- `test_approve_cli_bounds.py test_grant_bounds_caps.py` -> 17 passed
- `test_consent.py test_auto_size_budget.py` -> 54 passed
- `test_explore_consent.py test_ui_crawl_approval.py` -> 11 passed

## Judgement
Cycle-0 judgement calls (bound above 10**12 treated as malformed; `hint_grant_bounds` removed) remain accepted. The unit meets C1-C6 at cycle 1. Maker may flip the manifest to `checked-PASS`; merge and push are left to the human (nothing pushed here).
