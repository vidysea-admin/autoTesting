# at233-score-near-miss

Fix cycle: 1 of 3
Dual check: no
Issues addressed: AT-233

## What changed

- `src/autotester/stages/score.py:250-266` (`score()`): the branch that used to
  read `if best is None or best[0] < threshold: matches.append(Match(truth=row)); continue`
  now splits the two cases. `best is None` (nothing shares the recording and
  window at all) still appends a bare `Match(truth=row)` — genuinely nothing
  to report. `best[0] < threshold` (a real candidate that was rejected) now
  appends `Match(truth=row, similarity=ratio, seconds_apart=apart)` —
  `issue_id`/`issue_title` stay unset so `Match.found` is still `False`, but
  the similarity and time-gap the scorer actually computed are kept instead of
  being discarded down to the same `0.0`/`None` a truly-empty row gets. No new
  `Match` field: `similarity`/`seconds_apart` already existed on the dataclass
  (`src/autotester/stages/score.py:70-81`) and were previously write-only for
  the matched case.
- `src/autotester/stages/score.py:209-227` (new `_best_candidate()`, extracted
  from `score()`): the candidate list-comprehension + AT-221 total-tie-break
  sort moved out of `score()` verbatim (comment and all) so `score()` stays
  under the 50-line function cap after the AT-233 branch (`autotester doctor`
  flagged `function-too-long: score is 64 lines > 50` before this split).
- `tests/test_score_near_miss.py` (new file, 91 lines): three tests —
  a rejected-but-real candidate keeps its similarity/seconds_apart on the
  `Match`; a row with no candidate in range at all stays at similarity=0.0/
  seconds_apart=None (the two cases must stay distinguishable); and the same
  near-miss numbers reach `Scorecard.as_dict()["per_row"]`, which is what a
  human actually reads when tuning `--threshold`. Not added to
  `tests/test_score.py` because that file was already at the 300-line cap
  (`autotester doctor: file-too-long`) before this unit touched it.

`tests/test_score.py` and `tests/test_score_cli.py` are byte-identical to
`HEAD~1` (`git diff tests/test_score.py` is empty) — nothing in the CLI
output shape changed. `Scorecard.as_dict()`'s `per_row` dict already had
`similarity`/`seconds_apart` keys; only their VALUE changed for near-miss
rows (real numbers instead of `0.0`/`None`), so the score CLI stays backward
compatible with no explicit flag needed.

## Capability coverage

| Claim | Single-hunk falsifying edit | Check that goes red |
|---|---|---|
| A rejected-but-real candidate's similarity/seconds_apart survive onto the Match | Revert `score()`'s `if ratio < threshold:` branch back to `matches.append(Match(truth=row)); continue` (the pre-fix line) | `tests/test_score_near_miss.py::test_a_rejected_best_candidate_keeps_its_similarity_and_seconds_apart` |
| A row with no candidate at all still reads as 0.0/None, not confused with a near-miss | Same revert as above — collapses both branches back to the same bare `Match(truth=row)` | `tests/test_score_near_miss.py::test_no_candidate_at_all_still_reads_as_zero_and_none` (passes on both old and new code by itself; paired with the row above it proves the two cases are now distinct) |
| The near-miss numbers reach the CLI's `per_row` JSON, not just the in-process `Match` | Same revert as above | `tests/test_score_near_miss.py::test_the_near_miss_score_reaches_per_row_json` |
| `score()` still claims each truth row at most once, and the AT-221 total tie-break still holds after the `_best_candidate()` extraction | Revert the extraction (inline `_best_candidate()`'s body back into `score()`, unchanged logic) | `tests/test_score.py::test_recall_does_not_move_when_the_issue_list_is_permuted`, `tests/test_score.py::test_one_issue_cannot_claim_two_truth_rows` (both still pass — extraction is behaviour-preserving, included as a sanity check, not itself proof of AT-233) |

Red-first was run in a throwaway copy at
`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at233-redcheck`
(a `git archive HEAD` of the worktree's pre-fix tree, its own `uv sync`'d
venv, deleted after the red run) — never in this tracked worktree. On that
unmodified code, `test_a_rejected_best_candidate_keeps_its_similarity_and_seconds_apart`
failed (`assert 0.0 > 0.0`) while `test_no_candidate_at_all_still_reads_as_zero_and_none`
already passed, confirming the fix's scope was exactly the rejected-candidate
branch.

LIVE-BROWSER: not-applicable (pure scoring logic, no browser, no provider).

## Runner output (this worktree, post-fix)

```
$ uv run pytest tests/test_score.py tests/test_score_cli.py tests/test_similarity_score.py tests/test_score_near_miss.py
ss.......................................................                [100%]
55 passed, 2 skipped in 18.21s
```

(2 skipped = `test_score.py`'s two real-corpus tests,
`@pytest.mark.skipif(not TRAINERS.exists(), ...)` — the real workbooks live
on `C:/Users/Lenovo/Videos/Screen Recordings`, not on this host. Pre-existing,
unrelated to AT-233.)

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

## Gaps

- **Full suite not run.** Free RAM was ~1.1 GB at the start of this unit
  (`Get-CimInstance Win32_OperatingSystem`: `FreePhysicalMemory` 1138472 KB /
  `TotalVisibleMemorySize` 24866680 KB), under the 3.5 GB bar for a full-suite
  run per this unit's brief. Ran targeted: `test_score.py`, `test_score_cli.py`,
  `test_similarity_score.py` (the score stage's own suite) plus the new
  `test_score_near_miss.py`, not the whole `tests/` tree.
- **docs/MAP.md not regenerated.** `tests/test_score_near_miss.py` is a test
  file, not a `src/autotester/` module — `docs/MAP.md`'s generated directory
  map only covers `src/`, confirmed by `grep -n "test_score" docs/MAP.md`
  (no hits) and by `autotester doctor` staying clean without a regen.
- **No browser / no live product involved** — pure function over in-memory
  `TruthRow`/`Issue` objects and a fixture workbook; not a gap specific to
  this unit, stated per the manifest contract.
- Did not touch `qa/contracts/`, `qa/issues.jsonl`, `docs/FEATURES.jsonl`, or
  `.env`, and did not dispatch a checker or merge/push, per this unit's brief.

Status: checked-PASS (cycle 1, 13c341f)
