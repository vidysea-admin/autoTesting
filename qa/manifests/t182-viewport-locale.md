# Manifest — t182-viewport-locale

**Contract:** qa/contracts/execute.md E6 (D-045)
**Issues addressed:** AT-581
**Goal task:** T-182
**Date:** 2026-09-26
**Fix cycle:** 1 of 3
**Dual check:** no
**Executor:** claude-sonnet-subagent (maker build subagent)
**Branch/worktree:** `wave/t182-viewport-locale`, `D:/autoTesting/.worktrees/t182-viewport-locale`
**Base:** master `7913387`
**Commit:** `b7506f0` (code + test; this manifest lands in a second commit per the maker/checker
handshake — `Status: ready-for-check` is written last)

## The bug (AT-581)

`stages/expand.py` generates VIEWPORT_MOBILE and LOCALE_I18N cases (`stages/expand.py:29-30,46`),
but nothing enacted them: `browser/launch.py:30` hard-coded the persistent context's viewport to
`{"width": 1366, "height": 850}`, there was no locale override, and nothing in `execute.py` or
`browser/` ever read `case.case_class`. A "mobile viewport" or "non-default language" case ran at
desktop size in the default locale, so a PASS on one of these cases was false.

## What changed (file:line)

- **`src/autotester/browser/conditions.py` (new, 64 lines)** — the enactment seam.
  - `enact(session, case_class) -> str | None` (line 32): `VIEWPORT_MOBILE` calls
    `session.page.set_viewport_size(MOBILE_VIEWPORT)` (a 390x844 iPhone-12-class size, line 26) and
    returns `None` (enacted). `LOCALE_I18N` returns `LOCALE_NOT_ENACTABLE_REASON` (line 29) — see
    "Why LOCALE_I18N is not enacted" below. Any other class returns `None` untouched.
  - `reset(session, case_class)` (line 57): undoes the VIEWPORT_MOBILE resize back to
    `browser.launch.DEFAULT_VIEWPORT` after the case, best-effort (`contextlib.suppress`, same
    discipline as `BrowserSession.settle()`), so a reused session (AT-577's serial route shares one
    session across cases) never leaves a later, unrelated case running at the mobile size.
- **`src/autotester/browser/launch.py:17-19,32`** — pulled the previously-inline
  `{"width": 1366, "height": 850}` out to a module constant `DEFAULT_VIEWPORT`, so `conditions.py`'s
  `reset()` and the tests reference the one definition instead of a second hard-coded copy.
- **`src/autotester/schema/enums.py:122-123`** — new `Outcome.NOT_RUN`: "case_class named an
  execution condition that could not be enacted; the case did not run under it -- must never be
  judged PASS." (Two other docstrings in the file were reflowed by 1 line each, without changing
  their wording, to hold the file at the doctor's 300-line cap — see Gaps for the exact lines.)
- **`src/autotester/schema/run.py:47-52`** — `RawResult.not_run_reason: str | None`, set only when
  `outcome is NOT_RUN`; carries `conditions.enact`'s reason string.
- **`src/autotester/stages/execute.py`**:
  - `run_case` (line 138 in the final file) calls `conditions.enact(session, case.case_class)`
    before any step runs; if it returns a reason, `run_case` returns `Outcome.NOT_RUN` immediately
    — zero steps execute, zero evidence is recorded.
  - The step loop was extracted into `_run_steps` (new, line 105) so `run_case` could wrap it in a
    `try/finally` that always calls `conditions.reset(...)` — this also kept both functions under
    the doctor's 50-line-per-function cap (the combined body would have been ~60 lines).
  - `_result` gained a `not_run_reason` kwarg, scrubbed through `session.secrets.scrub_optional`
    like `error`/`hitl_prompt` already were (defense-in-depth; the reason is a static string today,
    never user input).
- **`src/autotester/stages/grade.py:133-138`** — `_outcome_verdict` gained a third deterministic
  short-circuit: `Outcome.NOT_RUN` → `Result.INCONCLUSIVE`, `note=result.not_run_reason`, before the
  judge is ever built or called — mirrors how `BLOCKED_HITL`/`ERRORED` already never reach the judge.
- **`docs/MAP.md`** — regenerated (`uv run autotester map`) for the new module.
- **`tests/test_viewport_locale_enact.py`** (new, 8 tests) — see below.

## Why LOCALE_I18N is not enacted (a real gap, not an oversight)

Playwright's `locale` (and the `Accept-Language` header it drives) is a `launch_persistent_context()`
-time-only option (`browser/launch.py::launch_options`). `BrowserSession.start()` launches that
context once per session; by the time `run_case` reaches a LOCALE_I18N case, the context is already
running in the project's default locale, and there is no live Playwright API to change it. The two
ways to actually enact it are both larger than this unit:
1. Recreate the context per LOCALE_I18N case — loses the persistent login state `BrowserSession`
   exists to keep (browser-and-secrets.md B5), and the serial route depends on that continuity
   across cases.
2. Launch every LOCALE_I18N case on a dedicated, freshly-launched context up front (closer to how
   `stages/parallel_run.py::default_session_factory` already gives each case its own context) — a
   session-lifecycle change touching the serial run path, not just the executor.
E6 explicitly allows this: "If the executor cannot enact it, the case is recorded as not run, with
the reason." That is what this unit does. Enacting LOCALE_I18N for real is left as a follow-on (not
filed as a new issue by this subagent per the brief — the checker owns `qa/issues.jsonl`).

## New tests (TDD, red first on unfixed code)

All 8 in `tests/test_viewport_locale_enact.py`:
1. `test_viewport_mobile_case_enacts_mobile_size_before_its_steps_run`
2. `test_viewport_resets_to_default_after_the_case_for_a_reused_session`
3. `test_locale_i18n_case_is_reported_not_run_and_no_step_executes`
4. `test_locale_i18n_never_reaches_the_judge_and_is_never_pass`
5. `test_happy_case_is_unaffected_by_the_condition_seam`
6. `test_enact_returns_none_and_resizes_for_viewport_mobile`
7. `test_enact_returns_a_reason_for_locale_i18n_and_touches_nothing`
8. `test_enact_is_a_no_op_for_a_class_with_no_condition`

### Red on unfixed code (throwaway worktree, own uv-synced venv — no tracked worktree file touched)

Per the hard rule against falsifying a tracked worktree file, the red run happened against a
**separate git worktree checked out at the pre-fix base commit** (`.worktrees/_t182-redcheck`,
`git worktree add .worktrees/_t182-redcheck 7913387 --detach`, its own `uv sync`'d `.venv`), with
only the new test file copied in — nothing in that checkout's tracked files was edited:

```
$ cd D:/autoTesting/.worktrees/_t182-redcheck
$ uv run pytest tests/test_viewport_locale_enact.py
...
ImportError: cannot import name 'conditions' from 'autotester.browser'
1 error in 0.72s
```

Green on the real (fixed) worktree, same file:

```
$ cd D:/autoTesting/.worktrees/t182-viewport-locale
$ uv run pytest tests/test_viewport_locale_enact.py -v
...
8 passed in 0.16s
```

Both throwaway worktrees (`_t182-redcheck` and `_t182-mutcheck`, the latter used for the
capability-coverage mutations below) were removed after use (`git worktree remove --force`) —
neither is present in the final `git worktree list`.

## Capability coverage (mutation, single-hunk, throwaway worktree)

A third throwaway worktree, `.worktrees/_t182-mutcheck`, was checked out at the real fix commit
(`b7506f0`, its own `uv sync`'d venv, baseline confirmed `8 passed in 0.23s`). Each mutation below
was applied via an anchored `text.count(old) == 1` script, the named test re-run to confirm it goes
red, then reverted by the exact inverse replace and the file diffed (`diff -u --strip-trailing-cr`,
to ignore the checkout's CRLF normalization) byte-identical against the real worktree's file before
moving to the next mutation. No `git stash` was used anywhere.

| # | Mutation (file, single-hunk) | Reverted behaviour | Kills (named, re-run confirmed) | Survives |
|---|---|---|---|---|
| A | `execute.py`: `not_run_reason = conditions.enact(...)` replaced with `not_run_reason = None` | `run_case` never calls the enactment seam at all (the AT-581 bug shape) | `test_viewport_mobile_case_enacts_mobile_size_before_its_steps_run` — real pytest run, `1 failed`, `viewport_calls[0]` is the hard-coded desktop default `{'width': 1366, 'height': 850}` (from `reset()`'s own call, since only `enact` was neutralized) instead of `MOBILE_VIEWPORT` | not run separately — isolated single-mutation run |
| B | `conditions.py`: `LOCALE_I18N` branch returns `None` instead of `LOCALE_NOT_ENACTABLE_REASON` | LOCALE_I18N is (wrongly) treated as enactable and runs its steps like HAPPY | `test_locale_i18n_case_is_reported_not_run_and_no_step_executes` (`1 failed`, outcome came back `COMPLETED` instead of `NOT_RUN`) and `test_enact_returns_a_reason_for_locale_i18n_and_touches_nothing` (`1 failed`, `reason` is `None`) — both, same run | 6 others in the suite |
| C | `grade.py`: the `Outcome.NOT_RUN` branch removed from `_outcome_verdict` | A NOT_RUN result falls through to the judge like a normal COMPLETED run | `test_locale_i18n_never_reaches_the_judge_and_is_never_pass` (`1 failed`, `ProviderError: mock provider has no queued response for role=judge` — proves the judge really would have been called and could have returned PASS) | not run separately — isolated single-mutation run |
| D | `execute.py`: `run_case`'s `finally: conditions.reset(...)` body replaced with `pass` | A VIEWPORT_MOBILE case's resize leaks into the next case on a reused session | `test_viewport_resets_to_default_after_the_case_for_a_reused_session` (`1 failed`, `viewport_calls` after the HAPPY case still only has the mobile size, missing the `DEFAULT_VIEWPORT` reset entry) | not run separately — isolated single-mutation run |

Each mutation was applied, tested, and reverted one at a time (never two mutations live together),
so every kill is attributable to its own named test.

## Verify

```
$ uv run pytest tests/test_viewport_locale_enact.py
8 passed in 0.16s   (done_check for T-182 — exact command)

$ uv run pytest tests/test_execute.py tests/test_execute_assertions.py tests/test_execute_new_actions.py \
    tests/test_execute_serial_evidence_scope.py tests/test_grade.py tests/test_grade_evidence.py \
    tests/test_parallel_run_session_crash.py tests/test_session_start_hook.py
50 passed in 2.72s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

Full suite (`uv run pytest` with no path filter) and real-Chromium live evidence were **RAM-gated**
— see Gaps.

## Live browser evidence

Not run — **UNVERIFIED**, a gap. Free RAM was measured at the start of this cycle's verify pass at
~3.06 GB, below the 3.5 GB floor this brief sets for a real-Chromium run (host shared with several
concurrent maker/checker worktrees — `git worktree list` showed 12 active worktrees at the time).
A background poll (every 300s, 20-minute cap) was run to catch the threshold if transiently crossed:

```
free=0.32GB at 07:53:31
free=2.28GB at 07:58:31
free=0.86GB at 08:03:32
free=3.62GB at 08:08:33
RESULT: RAM_AVAILABLE
```

The threshold was crossed for one 300s sample (08:08:33), but a re-check immediately on the poll's
return already read 3.02 GB again — the host oscillated between ~0.3 GB and ~3.6 GB across the
20-minute window, driven by other concurrent worktrees' own `uv sync`/test runs. Launching a real
Chromium context needs RAM held stable for the run's duration, not a single passing instant, and
this host had already dipped to 0.32 GB minutes earlier — attempting a live launch on that read
risked starving the concurrent checker process the RAM budget is explicitly shared with. Not
attempted. **UNVERIFIED**: `MOBILE_VIEWPORT`'s actual effect on a real page (that a VIEWPORT_MOBILE
case's screenshot is genuinely mobile-sized in a real browser, not just that `page.set_viewport_size`
was called with the right argument on a fake page) was not observed live this cycle.

## Gaps

1. **LOCALE_I18N is reported not-run, never enacted** — by design this cycle (E6 explicitly permits
   this fallback); see "Why LOCALE_I18N is not enacted" above for the two real options to close it
   and why each is a larger change than this unit.
2. **No real-Chromium evidence** — RAM oscillated between ~0.3 GB and ~3.6 GB across a 20-minute
   poll and was not stably above the 3.5 GB floor (see Live browser evidence). The mobile-viewport
   resize is proven against a fake page (`ViewportFakePage` in the new test file) that records the
   exact call, not against a real rendered mobile layout.
3. **Full test suite not run** — same RAM constraint; only the targeted execute/grade/parallel-run/
   session tests plus the new file were run (58 tests total, all green).
4. `src/autotester/schema/enums.py` was at the doctor's exact 300-line cap before this change. Adding
   `Outcome.NOT_RUN` required reflowing two unrelated docstrings (`Outcome.ASSERTION_FAILED` and
   `IssueKind.EVIDENCE`, each 1 line shorter, same wording) and later `IssueKind.OVERLAY` (also 1
   line shorter, same wording) to hold the file at exactly 300 lines. No semantic change to those
   three docstrings — confirmed by re-reading them post-edit — but flagging the edit since it
   touched code outside this unit's direct concern, for the checker to double check independently.

## Status

checked-PASS (cycle 1, 4c6b7f6)
