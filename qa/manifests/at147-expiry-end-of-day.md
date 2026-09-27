# Manifest — at147-expiry-end-of-day

**Unit:** implement option C of `qa/gates/at147-expiry-end-of-day.md` — a `--expires <date>` grant
means THROUGH THE END of that day, for approvals minted from 2026-09-26 on only. Existing
`approvals.jsonl` rows keep their instant (no retroactive widening).
**Contract:** `qa/contracts/consent.md` CN4, folded in commit d8da333.
**Gate:** `qa/gates/at147-expiry-end-of-day.md` — answered **C** by Umesh (D-048).
**Date:** 2026-09-26
**Fix cycle:** 1
**Dual check:** no
**Persona walk:** skip (CLI-only backend change; no UI surface touched — the UI grant form at
`ui/routes_crawl_approval.py` already collects an explicit datetime + timezone offset from the
browser and is unaffected by this unit, which is scoped to the CLI's bare-date `--expires`)
**Issues addressed:** AT-147, AT-150 (AT-151 unaffected in substance — see "What changed")
**Executor:** claude-opus-subagent

## The gate, restated

`RunApproval.is_expired` reads a bare `expires_at: "2026-09-09"` as **midnight — the START of the
9th**. AT-147/AT-150/AT-151 fixed `_validate_grant` to REFUSE `--expires <today>` at the grant
(matching that midnight semantics) rather than silently issue a doomed approval. The checker then
asked Umesh whether the *semantics itself* should move to end-of-day instead. Answer **C**: yes,
for new grants only, by storing an explicit end-of-day instant at grant time — no change to
`is_expired`'s bare-date reading, so nothing already on disk widens.

## What changed

- `src/autotester/cli_crawl.py`:
  - **New `_local_now() -> datetime`** (line 138): `datetime.now().astimezone()` — the operator's
    current local moment, offset-aware. This is the single seam a test monkeypatches instead of
    depending on the host clock or timezone.
  - **New `_end_of_day(day: date) -> datetime`** (line 143): `datetime.combine(day, time(23, 59,
    59), tzinfo=_local_now().tzinfo)` — the last local second of `day`, in the operator's own
    offset. Never naive: `RunApproval.is_expired` (schema/approval.py:135-136) reads a naive stamp
    as UTC, which would shift the boundary by the host's own offset (~5.5h on an IST host — this is
    the exact hazard the brief named, caught in review rather than shipped).
  - **`_validate_grant`** (line 149): `today` is now read from `_local_now().date()` instead of
    `date.today()` (same value on a real clock, but now the same seam as `_end_of_day`). The
    refusal condition changed from `expiry <= date.today()` to `expiry < today` — only a genuinely
    PAST day is refused; `--expires <today>` no longer triggers it (AT-147/AT-150 closed by
    construction, not by a stronger warning). The refusal's "usable date" is now `today.isoformat()`
    instead of tomorrow's date, since today itself is grantable. The two-arm "today vs past" `cause`
    branch collapsed to one arm (only "already in the past" remains), which is what let AT-151's own
    lesson — "one arm fixed, the other forgotten" — retire: there is only one arm left to forget.
  - **`approve_cmd`** (line 268-271): after `_validate_grant` passes, `expires_at =
    _end_of_day(date.fromisoformat(expires)).isoformat()` is computed and stored on the
    `RunApproval` (replacing the bare `expires_at=expires`), and the printed confirmation line now
    echoes the stored instant, not the bare input string.
  - Net effect on file size: 300 lines exactly (was 300; C2's cap), by shrinking new comments to fit
    since new functions were added — no pre-existing docstring was trimmed or reflowed, only my own
    new prose from this same edit.
- `tests/test_approve_cli.py`:
  - **New `test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later`**
    — the primary CN4 pin. Monkeypatches `autotester.cli_crawl._local_now` to a fixed
    `datetime(2026, 9, 26, 10, 0, 0, tzinfo=+05:30)`, grants `--expires 2026-09-26` through the
    real CLI, asserts the stored `expires_at == "2026-09-26T23:59:59+05:30"` (offset-aware, exact
    literal), then drives the real `require_approval` (the runtime gate) at `2026-09-26T23:59:59
    +05:30` (covers) and at `2026-09-27T00:00:00+05:30` (refused, `ApprovalRequired`) — the boundary
    pinned as an exact aware instant, independent of the host's real clock or timezone.
  - **`test_approve_refuses_an_expiry_of_today` renamed to `test_approve_grants_an_expiry_of_today`**
    — behaviour inverted per the gate answer: asserts `exit_code == 0` and that today's literal date
    appears in the output, using the REAL clock (no monkeypatch) as a plain end-to-end sanity check
    alongside the pinned test above. Original AT-147 docstring kept verbatim; an "Updated for CN4"
    paragraph appended, not a rewrite.
  - **`test_the_expiry_refusal_prints_a_usable_date` (AT-150)** — today is no longer refused, so
    this now drives `yesterday` instead of `date.today()` and asserts today's literal date (the new
    usable value) appears, instead of `TOMORROW`. Original docstring kept; "Updated for CN4"
    paragraph appended.
  - **`test_a_past_expiry_also_names_a_usable_date` (AT-151)** — same treatment: still drives
    `long_ago` (400 days back), now asserts today's literal date instead of `TOMORROW`. Kept as a
    second, more-distant-past instance alongside AT-150's one-day-back case, per AT-151's own
    lesson that one distance is not enough evidence an arm generalises.
  - `test_the_grant_and_the_runtime_agree_on_every_expiry_they_accept` (offsets 1/2/30 days) is
    UNCHANGED — still passes, since future-dated grants are unaffected by this change in substance
    (they are `>= today` either way; only the *stored format* of `expires_at` changed, from a bare
    date to an offset-aware end-of-day instant, and `is_expired`/`require_consent` handle both).
- `tests/test_consent.py`:
  - **New `test_a_pre_existing_bare_date_row_still_lapses_at_the_start_of_its_day`** — the second
    required CN4 pin. Direct `RunApproval(expires_at="2026-09-26").is_expired(...)`, asserting
    `False` at `2026-09-26T00:00:00` and `True` at `2026-09-26T00:00:01` (the strict `>` in
    `is_expired` means the boundary is one second after midnight, not midnight itself — measured,
    not assumed; see "Gaps" below). Confirms old rows are genuinely unaffected: no change was made
    to `RunApproval.is_expired` or to how a bare date already on disk is read.

**Not changed:** `src/autotester/schema/approval.py` (`RunApproval.is_expired`) — deliberately.
Option C's whole point is that the runtime reading of a bare date is untouched; only what
`approve_cmd` writes for a NEW grant changed. `src/autotester/ui/routes_crawl_approval.py` — its
own `_future_iso` already takes an explicit datetime + browser timezone offset from the operator
and stores its own offset-aware instant; it was never part of the AT-147/AT-150 bug and is outside
this gate's scope.

## How to verify (commands + actual outputs)

```
$ uv run pytest tests/test_approve_cli.py tests/test_consent.py
..................................                                       [100%]
34 passed in 1.68s

$ uv run pytest tests/ -k "approval or consent or expir"
........................................................................ [ 98%]
.                                                                        [100%]
73 passed, 1879 deselected, 1 warning in 14.61s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean

$ git status --short
 (clean after commit e318fa6 — see below)
```

`tests/test_cli_advice_resolves.py` also re-run since `--expires`'s help text is unchanged but the
brief asked for it whenever CLI advice/help strings are touched:
```
$ uv run pytest tests/test_cli_advice_resolves.py
............................                                             [100%]
28 passed in 10.41s
```

Full suite (`uv run pytest`, no target) was **not** run this cycle — RAM-low standing instruction.
Only the two named files, the `approval or consent or expir` subset (73 tests, a superset of the
two files), the CLI-advice file, ruff, and doctor.

## Capability coverage (each claim -> its isolating falsification)

Falsified in a throwaway copy OUTSIDE the tracked worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at147-falsify/copy`,
`cp -r` of the tracked worktree, own `uv run`-managed `.venv` built fresh there — confirmed
34/34 green baseline before any mutation). Each edit is a single hunk, anchor-checked to match
exactly once, applied, run, then reverted. `git stash` was never used. The tracked worktree's
`git status --short` before and after this round showed only the same 3 files
(`src/autotester/cli_crawl.py`, `tests/test_approve_cli.py`, `tests/test_consent.py`) — see
"Actual outputs" below.

| row | claim | falsifying edit (single hunk, throwaway copy only) | check | observed |
|---|---|---|---|---|
| (a) | a NEW grant's `expires_at` is stored offset-aware, never naive | `src/autotester/cli_crawl.py:146` — `_end_of_day` drops `tzinfo=_local_now().tzinfo`: `datetime.combine(day, time(23, 59, 59), tzinfo=_local_now().tzinfo)` → `datetime.combine(day, time(23, 59, 59))` | `test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later` | PASS before. FAIL after, on the right assertion: `assert '2026-09-26T23:59:59' == '2026-09-26T23:59:59+05:30'` — the offset is missing, exactly the naive-stamp hazard the brief named |
| (b) | a NEW grant's `expires_at` is the end-of-day instant, not the bare start-of-day date | `src/autotester/cli_crawl.py:276` — `approve_cmd` reverted to the old storage: `expires_at=expires_at` → `expires_at=expires` (the pre-fix bare string) | same test | PASS before. FAIL after, on the same assertion: `assert '2026-09-26' == '2026-09-26T23:59:59+05:30'` — reproduces the exact AT-147 shape (a grant stored as a bare date) |
| (c) | a PRE-EXISTING bare-date row is unaffected — still lapses at the start of its day, not end-of-day | `src/autotester/schema/approval.py:132-134` — `is_expired` made bare dates inclusive too: inserted `if "T" not in self.expires_at: expiry = expiry.replace(hour=23, minute=59, second=59)` between the `fromisoformat` call and its `except` | `test_a_pre_existing_bare_date_row_still_lapses_at_the_start_of_its_day` | PASS before. FAIL after: `assert row.is_expired(datetime(2026, 9, 26, 0, 0, 1)) is True` → `False` — the mutation makes the old row survive past midnight, the retroactive-widening option B explicitly declined by the gate |

Anchor-match counts, each confirmed `1` before editing (`grep -c`): row (a)/(b) target lines unique
in `cli_crawl.py`; row (c)'s anchor (`fromisoformat(self.expires_at)\n        except ValueError:`)
unique in `approval.py`.

Actual outputs (abridged; full pytest tracebacks captured live during the run):

```
-- row (a) --
--- before ---
    return datetime.combine(day, time(23, 59, 59), tzinfo=_local_now().tzinfo)
--- after ---
    return datetime.combine(day, time(23, 59, 59))
F                                                                          [100%]
FAILED tests/test_approve_cli.py::test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later
AssertionError: must be offset-aware end-of-day local time, never a naive stamp
assert '2026-09-26T23:59:59' == '2026-09-26T23:59:59+05:30'
1 failed, 10 deselected in 1.42s
```
Reverted; re-ran the pair (`test_approve_cli.py tests/test_consent.py`) -> `34 passed`.

```
-- row (b) --
--- before ---
        granted_at=date.today().isoformat(), expires_at=expires_at,
--- after ---
        granted_at=date.today().isoformat(), expires_at=expires,
FAILED tests/test_approve_cli.py::test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later
AssertionError: must be offset-aware end-of-day local time, never a naive stamp
assert '2026-09-26' == '2026-09-26T23:59:59+05:30'
1 failed, 10 deselected in 1.75s
```
Reverted; re-ran the pair -> `34 passed`.

```
-- row (c) --
--- before ---
            expiry = datetime.fromisoformat(self.expires_at)
        except ValueError:
--- after ---
            expiry = datetime.fromisoformat(self.expires_at)
            if "T" not in self.expires_at:
                expiry = expiry.replace(hour=23, minute=59, second=59)
        except ValueError:
F                                                                          [100%]
FAILED tests/test_consent.py::test_a_pre_existing_bare_date_row_still_lapses_at_the_start_of_its_day
AssertionError: assert False is True
 +  where False = is_expired(datetime.datetime(2026, 9, 26, 0, 0, 1))
1 failed, 22 deselected in 0.85s
```
Reverted; re-ran the pair -> `34 passed`.

Tracked worktree `git status --short` immediately after this round, confirming it was never
touched by the falsification copy's `uv` venv build or any mutation:
```
M src/autotester/cli_crawl.py
M tests/test_approve_cli.py
M tests/test_consent.py
```
(exactly the 3 files this unit changed — the falsification copy and its own `.venv` live entirely
under the scratchpad temp directory and were diffed content-identically, modulo CRLF, against the
tracked worktree's files before mutation: `diff --strip-trailing-cr` reported no difference.)

## Live browser evidence

Not UI-touching — CLI-only change (`cli_crawl.py`, plus tests). No browser, no crawl, no
screenshot directory involved.

## Known limits / gaps (disclosed, not claimed)

- `is_expired`'s comparison is strict `>`, not `>=` — so the actual boundary a NEW grant is honoured
  through is "the last local second of the day, inclusive" and the first REFUSED instant is
  `day+1 00:00:00` exactly (one second after `23:59:59`, not `23:59:59` itself and not some later
  point). Both pinned tests use this exact boundary; stated here so a reader does not assume `>=`
  from the contract's prose ("through the end of that day") without checking the operator.
- Full suite not re-run this cycle (RAM-low standing instruction) — see "How to verify" for the
  exact subset run instead (73 tests via `-k "approval or consent or expir"`, a superset of the two
  changed test files, plus the CLI-advice file, ruff and doctor).
- `granted_at` is unchanged — still `date.today().isoformat()` (a bare date), not run through
  `_local_now`/`_end_of_day`. CN4 only governs `expires_at`; `granted_at` was out of scope for this
  gate and is not touched.
- The gate's own recommended shape ("costs one line in `approve_cmd`") ended up costing two new
  small functions (`_local_now`, `_end_of_day`) rather than one inline line, because the brief
  additionally required the timestamp to be injectable/testable without depending on the host clock
  or timezone — a single `datetime.now().astimezone()` call inlined at the call site would have had
  no seam for `monkeypatch` to attach to. Flagged in case the checker judges this scope creep beyond
  the gate's own estimate; the two functions are 3 and 4 lines respectively, and `cli_crawl.py`
  still lands at exactly 300 lines (C2's cap), unchanged from before this unit.
- AT-151 is not "fixed" by a code change here in the sense of AT-147/AT-150 (those were about the
  refusal message; AT-151 was about the SAME message's second arm being forgotten once). This unit
  collapses the two-arm condition to one arm as a side effect of the gate's real change (today is no
  longer refused), which is why AT-151's own lesson has nothing left to re-forget — recorded rather
  than claimed as a fix of a distinct defect.

## Status: checked-PASS (cycle 1, qa/verdicts/at147-expiry-end-of-day.md 8819662)
