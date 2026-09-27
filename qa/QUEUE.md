# qa/QUEUE.md — checker sweep queue (top-3 recommended next units)

Refreshed by `/checker sweep` **2026-09-18T01:41:32+05:30**. The stamp comes from the system clock
(`date`), not typed (AT-399). Bound strictly to `D:/autoTesting`. Single-agent sweep (measured
ceiling this tick: 2.3 GB free RAM, an at496 checker concurrently in flight — not sharded per
dispatch instruction). Window `246c026..130e0c7`, 20 commits. Supersedes the
`2026-09-17T23:30:00+05:30` queue — its top-3 (dispatch checker on at490-491 / AT-483 wave /
the three HUMAN_GATEs) resolved as follows inside or just after this window: AT-492 (at490-491
dispatch gap) closed via `992f03f`/`4d00d58` (checker PASS + close-out, both inside this window);
the AT-483 wave closed via `9e11559` (checked-PASS cycle 1, filed a narrower residual AT-497); the
three HUMAN_GATEs remain open, unchanged.

**Note on scope:** while this sweep ran, the live `at496-the-ledger-never-loses-a-row` checker
(explicitly out of scope for this dispatch — "do not judge, dispatch, or write anything for it")
closed cycle 2 `checked-PASS` at commits `d115c0a`/`a0155f2`, just past this window's `130e0c7`
end. No governance problem found in its handshake (manifest → FAIL → fix cycle 2 → PASS →
close-out, each with a matching-cycle verdict); not judged technically, per instruction.

## GRILL — human decision, not a build row

- GRILL: recurring vacuous-guard prevention policy (AT-218). Unanswered, carried.
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281). Carried.
- GRILL (AT-402): structure-before-code review of `visual_order.js`. Carried.

## Findings this sweep — FINDINGS: 1

| Issue | Sev | What |
|---|---|---|
| AT-502 | medium (structural-erosion signal, never a blocker) | `scripts/flake_probe.py` rewritten across 3 separate units in <24h (AT-335 build, AT-401 fix, AT-494 fix): 186→244 lines (+31%), each re-touching `run_once`'s subprocess-invocation core (bare `subprocess.run` → timeout-wrapped → `Popen`+file-log+shared `kill_tree`). Still under the 300-line cap and under `scripts/`'s existing zero-size-cap gap (AT-488/AT-419) either way — noted so the next touch considers whether the design has actually settled. |

**Not filed (dedupe):** `scripts/mutation_check.py`'s structural-erosion signal is unchanged in
size this window (still 416 lines; the one diff was a rename `_kill_tree`→`kill_tree` to make it
importable, +1 commit) — same signal `AT-488` already carries, numbers updated: **416 lines / 12
commits** (was 361/9 when filed, 416/11 last sweep).

**Non-findings confirmed, not re-filed:**
- **Bypass check (all 20 commits):** every commit touching `src/`, `tests/`, or `scripts/` traces
  to a manifest→verdict handshake (at401: `cf34933`→`9b5cbc5`→`05cc388`; at490-491:
  `176a89c`(prior window)→`992f03f`→`4d00d58`; at494: `0ed84a7`→`1688da3`→`f8f304d`; at496 cycle
  1-2: `385fec1`/`67a61ec`→`b437a85`(FAIL)→`0af3ad8`→`d115c0a`(PASS, just past window)→`a0155f2`)
  or is a correctly-scoped `chore(qa): stamp the … tick` commit. CLEAN.
- **Handshake integrity:** no manifest sat `ready-for-check` with a missing/stale-cycle verdict
  at sweep time (AT-492's dispatch gap from the prior sweep closed inside this window). The only
  `ready-for-check` string match left on disk is the known phantom at
  `qa/manifests/at438-display-contents.md:385` (header says STALLED at line 8) — confirmed still
  live, this is **AT-485**, already open, not re-filed.
- **Ledger hygiene (AT-475/496 class):** `qa/issues.jsonl` is clean at HEAD (no working-tree
  divergence) as of this sweep — the very unit built to catch this class (AT-496,
  `check_qa_issue_rows` in `doctor.py`) closed `checked-PASS` while this sweep ran. AT-401/490/
  491/494/496/498/499 rows all verified present with correct terminal status, matching their
  verdicts field-by-field.
- **Data boundary (MC-003):** `python .../data_boundary.py D:/autoTesting` still exits 1, no
  `data_class` in `qa/adapter.json` — already **AT-365** (open, high), not re-filed.
- **Contract staleness:** none found; no criterion in `qa/contracts/*.md` contradicts what this
  window shipped (C10's ledger-handshake language is exactly what AT-496 implements).
- **Inbox:** `qa/feedback-inbox.md` (691 lines) has no entry dated after 2026-09-16, and every
  entry through that date already carries a `**FOLDED:**` line. CLEAN.
- **Gates:** 19 total (unchanged count — the 14→19 growth and the "most lack an Answered line"
  rot pattern is already **AT-415**, not re-filed). Of the 19, only 7 carry an `Answered:` field
  at all and every one of those 7 reads blank or `(pending)` — **zero of 19 gates are actually
  answered on disk**, same state as prior sweeps. The three blocking all further buildable work:
  `post-login-forms.md`, `live-crawl-target.md`, `erp-credentials.md` — all three still
  `Answered: (pending)` / no `Answered:` line.
- **Doctor + ruff, re-run at HEAD:** `uv run autotester doctor` → `doctor: clean`; `uv run ruff
  check src tests scripts` → `All checks passed!`.
- **Silent-failure hunt** over code touched by units PASSed since the last sweep (at401,
  at490-491, at494): none found. AT-490/AT-491/AT-494 were themselves exactly this class and are
  now closed with tested, non-swallowing exception handling (`kill_tree`'s `MutationError` on an
  unkilled survivor; `flake_probe.run_once`'s file-backed output with the kill failure surfaced
  in the run's `tail`, not discarded).

## Token spend (re-measured this sweep)

`opus_sub_share=0.22` over the last day (55 sub-agents) — **now UNDER the 25% diet threshold**,
continuing the fall from 0.624 → 0.539 → 0.299 → 0.22 across four consecutive re-reads. Same
ongoing day-window as `AT-486` (open, low) — left open rather than closed by this sweep: its
`expected` clause calls for an audit of the day's Opus dispatches for stated heavy-reasoning
justification, which this sweep did not perform; the number alone crossing the line is not that
audit.

## TOP-3 BUILDABLE NEXT UNITS (re-ranked — AT-492 and the AT-483 wave both closed this window)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-497** (low) — a crawl killed before its first action completes (during `_seed`, login bootstrap, or mid-first-action) never gets a heartbeat write and displays RUNNING forever. Disclosed residual, narrower scope than AT-483 (fixed). `src/autotester/stages/explore.py:277-287`, `explore_node.py:119-137,266-267`. | The only open, mechanically-buildable, non-gated defect left on the board this sweep found. |
| **2** | **The three open HUMAN_GATEs still block everything else buildable:** `qa/gates/post-login-forms.md` (X10/D-016, any post-login typing/select/upload), `qa/gates/live-crawl-target.md` (the live acceptance run of X17/X18/V7), `qa/gates/erp-credentials.md`. All three `Answered:` lines remain unfilled placeholders. | Unchanged from the last two sweeps — every mechanism buildable without a human call is built and fixture-proven; further progress on the product surface needs Umesh to answer one of these three. |
| **3** | **Structural-erosion signals, advisory only, never blockers:** `AT-488` (`scripts/mutation_check.py`, now 416 lines / 12 commits) and `AT-502` (new this sweep — `scripts/flake_probe.py`, 3 units / 186→244 lines). Neither needs a dedicated unit; both are a note for whoever next touches either file. | Named so a future maker doesn't grow either file past its natural stopping point without noticing. |

**Deprioritised (not cancelled):** `AT-460` (`explore.py` at the 300-line cap), `AT-464`,
`AT-456`.

**Explicitly NOT assigned:** `at438` / `AT-442…AT-454` (other session, STALLED + gate) · anything
under `.goal/`, `.codex/`, `AGENTS.md`, untracked `projects/*`.

## HUMAN_GATE — do not build as ordinary units (verified unanswered on disk unless noted)

| Gate | Blocks |
|---|---|
| `live-crawl-target.md` | The live post-login acceptance run of X17/X18/V7 (target, write_policy, bounds). |
| `post-login-forms.md` | Any crawler typing, selecting or uploading after login (X10, D-016). |
| `t162-contract-approval.md` | T-162…T-169 |
| `at438-u14b-baseline.md`, `commit-before-verdict.md` | Other session's AT-438; protocol departure. |
| `at416-clip-vs-reach-direction.md`, `at383-loop-status-consumer.md`, `at365-data-class-declaration.md` | Various |
| `at110-approval-forgery.md`, `erp-credentials.md`, `at147`, `at218`, `at253`, `t136-model-credentials.md` | Various |
| `at052-bfs-video-corpus-grill.md` | **Answered 2026-09-07** — kept in this table only as the record of what unblocked Tracks 0/A/B; not an open gate. |

**Terminal state: `FINDINGS: 1`** (AT-502 medium, structural-erosion signal; 0 new gates opened,
AT-488/AT-365/AT-485/AT-415/AT-486 dups avoided).

---

## Sweep refresh — 2026-09-22 (this sweep supersedes the top-3 above; full sweep report: qa/verdicts/sweep-2026-09-22.md)

**AT-539 confirm:** maker retarget (3da1f56) verified — `uv run pytest tests/test_approve_cli.py`
10 passed; FULL SUITE `uv run pytest` **1514 passed, 5 skipped, 32 xfailed, 0 failed, exit 0**
(831.61s, whole-log scan, .work/checker_sweep_full_suite.txt). AT-539 -> fixed.

**Inbox fold (2026-09-22 TestSprite audit):** 6 new ledger rows + 1 dup-resolution. New rows:
AT-540 high (dead assertion layer: ExpectedState's absent_text/dom_asserts/visual_signal/network
zero read sites, Action.ASSERT no-op), AT-541 medium (REGRESSION_ANCHOR unreachable),
AT-542 medium (F-039 ensemble claim vs models_agreeing:1 in all 3 erp rows), AT-543 medium
(bench duration_s=300.0 literal), AT-544 medium (feature ledger 12 days stale, last row F-043),
AT-545 low (orphaned running crawl), AT-546 low (contract staleness: explore.md/consent.md name
the removed stages/explore.py seam for require_consent; line anchors drifted). The
ARCHITECTURE.md script-first claim folds into existing high row AT-253 (duplicate — same greps
re-verified, not re-filed).

**Contract staleness (X17/X18-era references):** explore.md:266 names `require_consent` without
the new `stages/explore_consent.py` module; line anchors `explore.py:200-211` (X18) and
`:298-300` drifted (file now 285 lines; `_terminal_status` at :207, call site at :285). Filed
AT-546 low; the contract is NOT edited by this sweep (checker-owned but this sweep files, the
next contract-touching unit or amendment applies the re-point).

## TOP-3 BUILDABLE NEXT UNITS (2026-09-22 refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-540 (high)** — the dead assertion layer: wire `absent_text`/`dom_asserts` into `_poll_for_expected` so a settled-but-unmet expectation records a failure instead of returning normally, and give `Action.ASSERT` a real evaluator; DECISIONS entry first (ARCHITECTURE.md Execution-model prose correction is its prerequisite per the inbox). Umesh approved assertions-first order. | Highest-leverage open product defect; the sweep's re-derivation confirms it blocks the oracle-quality north-star axis. |
| **2** | **AT-529 (high, HUMAN_GATE)** — PATHLYNKS_USER_* dev credentials 401; only Umesh can supply valid test-account values in the env editor, then re-run the stage-1 crawl to reach the post-login surface. | Unchanged; blocks the entire live-crawl-target acceptance run and X17/X18 Mode-D proof. |
| **3** | **AT-546 (low) + AT-253 (high, DECISIONS-gated):** AT-546 is the checker's own one-amendment re-point of require_consent references + line anchors in explore.md/consent.md (routine, this checker next contract touch); AT-253's resolution is the D-entry correcting the Execution-model prose (human-approved, bundled with AT-540's design decision). | Cheap checker-owned housekeeping + the human gate the assertions work must pass through first. |

**Deprioritised (not cancelled):** AT-497 (orphaned running crawl heartbeat — now AT-545 joins it as
a second on-disk instance, same fix unit can close both), AT-460, AT-488, AT-502 signals.

## HUMAN_GATE — do not build as ordinary units (verified unanswered on disk)

| Gate | Blocks |
|---|---|
| `live-crawl-target.md` | The live post-login acceptance run of X17/X18/V7. |
| `post-login-forms.md` | Any crawler typing, selecting or uploading after login (X10, D-016). |
| `erp-credentials.md` / AT-529 | Valid Pathlynks test-account values. |
| `t162-contract-approval.md` | T-162–T-169. |
| `at438-u14b-baseline.md`, `commit-before-verdict.md` | Other session's AT-438; protocol departure. |
| `at416-clip-vs-reach-direction.md`, `at383-loop-status-consumer.md`, `at365-data-class-declaration.md` | Various |
| `at110-approval-forgery.md`, `at147`, `at218`, `at253` (ARCHITECTURE Execution-model D-entry), `t136-model-credentials.md` | Various |

**Terminal state: `FINDINGS: 7`** (AT-540 high; AT-541/542/543/544 medium; AT-545/546 low;
AT-539 flipped fixed; 0 new gates opened; ARCHITECTURE.md fold deduped onto AT-253).

---

## Sweep refresh — 2026-09-22b (sharded Mode B; consolidation of 3 read-only shards; full report: qa/verdicts/sweep-2026-09-22b.md)

Window `3833218..00e36a8` (7 commits) + working tree. Full suite at this tree: **1521 passed, 5 skipped, 32 xfailed, 0 failed, exit 0** (1113.89s, `.work/full-suite-2026-09-22-1549.txt`); doctor + ruff CLEAN at 00e36a8 (shard 3). The **at540-assertion-layer Mode A checker is IN FLIGHT** (dispatched 15:38; no verdict on disk at 16:10) — expected pending handshake, not a finding; its files untouched.

**GRILL — human decision, not a build row (carried):**
- GRILL: recurring vacuous-guard prevention policy (AT-218). Unanswered, carried.
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281). Carried.
- GRILL (AT-402): structure-before-code review of `visual_order.js`. Carried.

### Findings this sweep — FINDINGS: 6

| Issue | Sev | What |
|---|---|---|
| AT-547 | high | **Bypass:** AT-541+AT-542 fixes (df529f2) and AT-543 (a5e5b81) landed as bare commits — no manifest, no verdict; all three ledger rows stay open (a flip needs a verdict). Remediation: retro-manifests + Mode A checks. |
| AT-548 | medium | df529f2's message claims "+ F-044 ledger correction appended" — no F-044 row exists in docs/FEATURES.jsonl and the commit never touches the file (shards 1+2 deduped to one row). |
| AT-549 | medium | x10b-form-typing terminal-STALLED (manifest :230) at cycle 3 of 3 with FAIL verdict and NO qa/debug/x10b-form-typing* diagnosis — its sole FAIL cause (AT-539) is since fixed; stall without diagnosis. |
| AT-550 | medium | AT-542's ensemble wiring silently shrinks: routes_sources.py:237-241 drops uncredentialed providers with no recorded signal; project.py:61-70 substitutes ["gemini"] for empty config (extends open AT-542). |
| AT-551 | medium | browser/assertions.py met() swallows probe errors into True and body_text() returns "" on a broken page — absent_text-only expectation on a crashed page records met and completes clean; visible_text/dom_asserts fail safe. Ruled defect-not-contract vs D-032's Result (no-raise is satisfiable failing-safe). |
| AT-552 | low | Inbox residual: umesh's 2026-09-06 home-page-dashboard ask never filed (the two sibling 2026-09-07 asks were delivered — Status lines annotated, entry folded onto this row). |

**Deduped / not filed:** opus_sub_share — shard 3 measured **0.289 (over the 0.25 line)** at 15:54:51; consolidation re-read **0.153 (UNDER)** at 16:10:25 — volatile around the threshold; scan line appended to `qa/token-ledger.jsonl` and open **AT-486** extended with both numbers (its Opus-dispatch audit is still not performed; no new row). grade.md **G2** ("Only Outcome.COMPLETED results are sent to the judge") + execute.md **E1** — both D-032-wave staleness, folded into the in-flight at540 checker's contract touch (no row; the next sweep files if its verdict lands without them). AT-541/542/543 got evidence notes (fixes in-tree, UNVERIFIED) — **no flips this sweep**; AT-253 NOT flipped (D-031 prose landed, wiring question still gated); AT-415 re-confirmed; AT-488/AT-502 unchanged in window (no refile); data-boundary gate still fires (no `data_class`) — standing **AT-365**; no graph.json → blast radius NOT-APPLICABLE.

### TOP-3 BUILDABLE NEXT UNITS (2026-09-22b)

| # | Unit | Why |
|---|---|---|
| **1** | **at540-assertion-layer Mode A check** — in flight (dispatched 15:38), not to be raced. Its contract touch (execute.md E1 per D-032) should also absorb the grade.md G2 line and, if convenient, the AT-546 require_consent re-point. | The pending handshake the board waits on; its verdict lets AT-540 close. |
| **2** | **AT-547 (high) bypass remediation** — retro-manifests + Mode A checks for AT-541/AT-542/AT-543. | The only high row filed this sweep; three open rows carry real in-tree fixes awaiting a check. |
| **3** | **The buildable tail:** AT-529 (high, HUMAN_GATE — Umesh's test-account credentials) · AT-546 checker re-point (bundle with the at540 contract touch if its verdict allows) · AT-544 via the F-044 remediation (AT-548) · AT-545+AT-497 heartbeat unit · T-123 medium batch · AT-550/AT-551 as natural follow-ons to at540. | Ordered by severity + unblocking value. |

### HUMAN_GATE — do not build as ordinary units (carried from the 2026-09-22 refresh, verified unchanged)

live-crawl-target · post-login-forms · erp-credentials/AT-529 · t162-contract-approval · at438-u14b-baseline + commit-before-verdict · at416-clip-vs-reach-direction · at383-loop-status-consumer · at365-data-class-declaration · at110-approval-forgery · at147 · at218 · at253 (ARCHITECTURE Execution-model D-entry) · t136-model-credentials.

**Terminal state: `FINDINGS: 6`** (AT-547 high; AT-548/549/550/551 medium; AT-552 low; 0 flips; AT-486 extended with the token reading; sweep report: qa/verdicts/sweep-2026-09-22b.md).

---

## Sweep refresh — 2026-09-22c (sharded Mode B; consolidation of 3 read-only shards, HEAD `93fad7b`)

Window `00e36a8..93fad7b`. The at540-assertion-layer Mode A check landed **cycle-2 checked-PASS**
(`d7d8405` fix, `41ff0e1` close-out) since the prior sweep — AT-547/548/549/550/552 (checker-unit
set, its own cycle-1 findings) flipped `fixed`; AT-551 (sweep set, met()/body_text fail-unsafe)
also flipped `fixed`. `target.md` milestone tracker landed (`93fad7b`), routed at `CLAUDE.md:24`.

**GRILL — human decision, not a build row (carried):**
- GRILL: recurring vacuous-guard prevention policy (AT-218). Unanswered, carried.
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281). Carried.
- GRILL (AT-402): structure-before-code review of `visual_order.js`. Carried.

### Findings this sweep — FINDINGS: 3 new + 1 reconciled (no renumber) + aging restatement

| Issue | Sev | What |
|---|---|---|
| AT-555 | medium | `assertions.py::met()`'s url branch stays fail-UNSAFE (blanket `contextlib.suppress` → `return True` on a `page.url` read failure) — the AT-540 fix closed the `body_text`/`absent_text` half of AT-551 but not this one; disclosed as "row 11" debt in `qa/verdicts/at540-assertion-layer.md:21-23` but carried no issue id until now. |
| AT-556 | low | One `ScheduleWakeup` call blocked today by a `glm-5.3-flash` classifier outage (6 outages total) — same failure shape as AT-368's multi-day dead loop; loop did not visibly stall this time, leading-indicator only. |
| AT-557 | low | `uv run autotester doctor` not clean: `docs/SNAPSHOT.md` stale vs its own regeneration — likely the `target.md` commit or at540's landing not re-running `autotester snapshot`. |

**AT-553 (dup-id pattern) — reconciled by judgment, NOT renumbered.** Evaluated the dispatch's
preferred renumber (keep at540-set AT-547..552 `found_by=checker-unit`, renumber sweep-set
AT-547..552 `found_by=checker-sweep` to fresh ids) and rejected it: the sweep-set AT-551 content
(met()/body_text fail-unsafe) is cited by id inside `src/autotester/browser/assertions.py` and two
test files — files this role is barred from editing — so a clean renumber isn't achievable without
orphaning permanent code comments. Every one of the twelve colliding rows (AT-547..552 ×2,
AT-288..291 ×2) already carries a `found_by`/`checker` discriminator, mirroring the precedent
AT-293 (2026-09-11, verified) already set for the AT-288..291 case — that ruling stands, not
re-litigated. Full reasoning recorded in AT-553's own `evidence` field. Old→new id mapping: **none
— no renumber performed.**

**Non-findings confirmed, not re-filed:** AT-541/542/543 (bypass-fixed-but-unverified) re-derived
independently by shard 3 as still legitimately OPEN — no manifest/verdict exists for any of the
three; AT-550 (ensemble silent-shrink) confirmed still reproduces in code, unchanged. Gate-answered-
off-disk sweep over all 21 `qa/gates/*.md` found zero violations (one cosmetic stray placeholder at
`t136-model-credentials.md:44`, not filed). `target.md`'s north-star framing is not literally
covered by check 6's trigger (goal.json's `north_star` field itself is unedited) but is
un-reconciled with a second, higher-visibility statement of the goal — noted, not filed as a new
row this sweep (informational only, folded into the TOP-3 below instead). Data-boundary (AT-365),
loop.md agreement, and structural erosion (session.py at 299/300 lines, watch-item) all re-confirmed
unchanged.

### TOP-3 BUILDABLE NEXT UNITS (2026-09-22c refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-541/542/543 retro-remediation** — verify-or-revert the bare commits `df529f2`/`a5e5b81` (no manifest, no verdict, per AT-547) through the maker-checker pair properly: retro-manifest the three fixes (What changed + verify commands), dispatch Mode A, let the rows flip only on a real verdict. Bundle the **AT-550** fix (silent ensemble-shrink at `routes_sources.py:236-244` / `schema/project.py:70` — record which provider was skipped instead of a silent drop; refuse or note the empty-config `["gemini"]` default) into the same unit since it extends the same AT-542 surface. | The only high-severity row with real in-tree fixes still awaiting a check; unblocks three open ledger rows plus AT-550 in one pass. |
| **2** | **AT-529 (high, HUMAN_GATE)** — PATHLYNKS_USER_* dev credentials 401; only Umesh can supply valid test-account values. | Unchanged; blocks the entire live-crawl-target acceptance run. |
| **3** | **AT-555 (medium, new)** — guard `met()`'s url-read the same way `body_text()`/`selector_exists()` are now guarded, with a falsifying test that a raising `page.url` does not leave `met()` returning `True`. Cheap, same file already touched by at540. | Closes the last disclosed gap from the at540 fix cycle; small, isolated, well-scoped. |

**Aging (not new, restated for priority):** AT-110 (14d, high, RunApproval tamper-check defeat) is
the oldest untouched high-severity row on the board — no code change this sweep, still needs a
build slot. AT-218/AT-281 (GRILL rows, 13d/12d) remain HUMAN_GATE, not buildable.

**Deprioritised (not cancelled):** AT-544 (feature-ledger stale, via the F-044 remediation AT-548,
already fixed by at540's cycle-2 close-out — re-check on next ledger touch) · AT-545/AT-497
(orphaned-running-crawl heartbeat) · AT-488/AT-502 structural-erosion signals · AT-556/AT-557 (low,
no urgency).

### HUMAN_GATE — do not build as ordinary units (carried, verified unanswered on disk)

live-crawl-target · post-login-forms · erp-credentials/AT-529 · t162-contract-approval ·
at438-u14b-baseline + commit-before-verdict · at416-clip-vs-reach-direction ·
at383-loop-status-consumer · at365-data-class-declaration · at110-approval-forgery · at147 · at218 ·
at253 (ARCHITECTURE Execution-model D-entry) · t136-model-credentials.

**Terminal state: `FINDINGS: 3`** (AT-555 medium; AT-556/557 low; AT-553 dup-id pattern reconciled
by judgment, no renumber; 0 new gates opened; sweep report: this consolidation, shards at
`qa/sweeps/shard-{1,2,3}-2026-09-22c.md`).

---

## Sweep refresh — 2026-09-22d (focused reconcile; not a full sweep — delta since 18:56/6b0e744,
now HEAD `370a017`)

Targeted reconcile of the 4 checker-verified units merged since the last full sweep (`93fad7b`
onward): the ledger already carried the correct flips from those units' own verdicts —
re-verified rather than re-derived from scratch, per the dispatch's bounds.

**Ledger state re-confirmed against `qa/verdicts/`:**
- **AT-541, AT-542, AT-543, AT-547** — `qa/verdicts/at541-543-ensemble-honesty.md` = PASS (cycle 1).
  Already `status: fixed` on disk with the verdict's own retro-coverage notes; confirmed, not
  re-flipped to `verified` (this checker's convention: `fixed` now, `verified` only on a later
  independent re-check, per the checker protocol — not this reconcile).
- **AT-550** (the `checker-sweep` ensemble-shrink row, line 547) — confirmed **OPEN**, partial-fix
  note intact: record-the-shrink half fixed+verified in `7c3626b`
  (`schema/analysis.py:59-93` → `adjudicate()` → `routes_sources.py:252`, mutation-tested 3/3 in
  the verdict), the empty-config half (`schema/project.py:70` `return seen or ["gemini"]`) still
  untouched. Left open, not closed.
- **AT-555** — `qa/verdicts/at555-url-guard.md` = PASS (cycle 1). Already `status: fixed` on disk
  (`met()`'s url branch now guarded via `_page_url()`, independently falsified in a throwaway copy).
- **AT-557** (docs/SNAPSHOT.md stale) — `uv run autotester doctor` re-run at HEAD `370a017` →
  **`doctor: clean`**. Flipped `open → fixed` this reconcile (evidence: "doctor clean at 370a017,
  SNAPSHOT regenerated" — the ensemble unit's landing evidently re-ran `autotester snapshot`).
- **AT-556** (ScheduleWakeup blocked by classifier outage) — loop-resilience observation, not a
  code defect. Left **open, low**; annotated that this session's tick survived via
  subagent-notification + heartbeat (no dead loop observed).

No other rows touched. `qa/issues.jsonl` re-validated line-by-line as valid JSON after edits (560
lines, unchanged count).

### TOP-3 BUILDABLE NEXT UNITS (2026-09-22d refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-110 (high)** — RunApproval tamper-check defeat, now the oldest untouched high-severity row on the board (~14 days). | No mechanical blocker; the highest-severity buildable defect with no human gate in front of it. |
| **2** | **AT-550 empty-config remainder** — make `schema/project.py:70`'s `return seen or ["gemini"]` explicit (refuse, or default-with-note) instead of a silent substitution; the record-the-shrink half is already done and verified, this is the narrow remainder. | Small, well-scoped, closes the last disclosed gap on a row already half-fixed. |
| **3** | **AT-554 (HUMAN_GATE, not a buildable unit)** — `/settings/providers` + env editor serve the real credential VALUE in the HTTP response/DOM, contradicting `browser-and-secrets.md:59`/`core-invariants.md:47`; CRITICAL-class (weakening a credential boundary needs Umesh + a D-entry). Noted here as a gate row so it stays visible, not picked up as ordinary work. | Blocks nothing else buildable but is high-severity and needs a human decision before any code touches it. |

**GRILL — human decision, not a build row (carried, unanswered):**
- GRILL: recurring vacuous-guard prevention policy (AT-218).
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281).
- GRILL (AT-402): structure-before-code review of `visual_order.js`.

**Terminal state: `focused reconcile — 0 new findings, 6 rows reconciled`** (AT-541/542/543/547/555
confirmed `fixed`; AT-550 confirmed `open`/partial; AT-557 flipped `open → fixed` on a clean
doctor; AT-556 annotated, left `open`/low; HEAD `370a017`).

---

## Sweep refresh — 2026-09-23 (Mode B safety-net, reconcile after T-162/T-163/D-037 merge burst)

Window `370a017..24043b8` (48 commits): T-162 fast-follow phases AUDIO/EMAIL/DRIVE landed and
closed (F-044, `checked-PASS` each, dual-checked), T-163 resumable orchestrator landed and closed
(D-036, F-045, dual-checked cycle 1), the `EnterWorktree`/`ExitWorktree` allowlist fix landed
(D-037, `Approved-by: Umesh`), and a `test_goal_done_checks.py` registration guard was corrected
twice (`bfb8c48`, `b8c2297`) to match the widened T-162 `done_check` and the actual T-163 test
file names.

**Bypass detection — CLEAN, no new bypasses.** Every `feat`/`fix` commit in the window traces to a
manifest→verdict handshake: t162-source-adapters-1a (`5e243b7`→`14b6830`/`fb18d13`→`f2f2f9a`),
t162-audio-1b (`efbb17e`→`994d698`/`54a2935`→`3b32871`), t162-email-2a (`53adcc8`→`e22df4f`/
`d8d4c9c`→`f4a8c54`), t162-drive-2b (`2485ca2`→`46a7094`→FAIL`f4ec8c0`→cycle-2`b602226`→
`d650eaf`→`15804a1`), t163-orchestrator (`6cad8e0`+merged-in `4f84b45`/`bfb8c48`/`b8c2297`→
`71badf2`/`00036af`→`75bad93`). `4f84b45` (settings.json allowlist) is the one config change with
no manifest of its own — correctly so: it is an **enforcement-path** change authorized by
`D-037` with `Approved-by: Umesh` per the Lab Protocol's own rule (a DECISIONS entry, not a
maker-checker unit, is the gate for `.claude/settings.json`). `bfb8c48`/`b8c2297` (test registration
+ `.goal/goal.json` done_check strings) were committed straight to master, then merged into
`wave/t163-orchestrator` at `daafba4` *before* the dual check ran — both checkers' diff-scope step
(step 4c) explicitly inspected them and recorded them as "changed only outside judged scope …
confirmed by inspection" (`qa/verdicts/t163-orchestrator.b.md:69-70`), i.e. reviewed and
consciously scoped, not silently skipped. No unreviewed code/schema/contract change found.

**Ledger reconciliation:**
- **`ISS-t162-drive-2b-1`** (T-162 done_check too narrow) → **CLOSED, `open → fixed`.**
  `.goal/goal.json` T-162.done_check.cmd is now the 4-file form
  (`tests/test_source_adapters.py tests/test_source_adapters_audio.py
  tests/test_source_adapters_email.py tests/test_source_adapters_drive.py`, via `b8c2297`), and
  `tests/test_goal_done_checks.py::test_revised_goal_contract_is_registered` expects the identical
  string (via `bfb8c48`) — read directly, both match byte-for-byte.
- **`ISS-t163-1`** (stale `docs/SNAPSHOT.md`) → **CLOSED, `open → fixed`.** `uv run autotester
  doctor` at HEAD `24043b8` → `doctor: clean`; `docs/SNAPSHOT.md`'s "Last decisions" list now
  reads through `D-037` (grep-confirmed).
- No other open row references T-162/T-163/adapters/orchestrator as stale — `AT-420`/`AT-447`
  (the older `t162-contract-approval.md` gate-premise pair) are unrelated to this burst and still
  legitimately open, left untouched.

**Contract staleness/liveness — CLEAN.** `qa/contracts/source-adapters.md` header reads ACTIVE,
finalized by /checker under D-035, phase-1a + phase-2a/2b all cite their real verdict files —
matches shipped code (adapters seam + TEXT/DOC/AUDIO/EMAIL/DRIVE all present under
`src/autotester/sources/`). `qa/contracts/orchestrator.md` header reads ACTIVE (was DRAFT,
authorized by D-036, taken ACTIVE by /checker on T-163 cycle-1 PASS) with OR1-OR6 each carrying a
falsifying-edit row in its own amendment log — matches `stages/orchestrate.py` +
`schema/run_state.py` on disk.

**Enforcement liveness — CLEAN.** `.claude/settings.json` `permissions.allow` contains both
`"EnterWorktree"` and `"ExitWorktree"` (D-037's fix is actually installed, not just decided).
SessionStart/PreToolUse/Stop hook files it references
(`qa/hooks/mc-sessionstart.ps1`, `.claude/hooks/lab-session-start.ps1`,
`qa/hooks/mc-precommit.ps1`, `.claude/hooks/decisions-append-guard.ps1`,
`.claude/hooks/lab-session-end.ps1`) all exist on disk. Repo has commits (HEAD `24043b8`, not an
empty-history gate). `uv run ruff check src tests scripts` → `All checks passed!`.

**Goal-coverage gap — no drift.** `.goal/goal.json` progress = **37/55 done (67%)**, matching the
dispatch's stated 37/55. T-164 (Portal Persona, deps `["T-163"]` ✓) and T-165 (deps
`["T-163","T-144"]`, both ✓) are now mechanically ready — no dependency gap. `qa/.regrill-due`
absent, `qa/.paused` absent, `qa/.last-tick` fresh (`2026-09-23T00:59:10Z`, names this exact
reconcile + the T-164/T-165 fork) — no re-grill trigger fired (north star unedited this window, no
requirement newly `missing` with no source, no unit re-PASSed twice on the same evidence).

**Doctor — CLEAN.** `uv run autotester doctor` → `doctor: clean` at HEAD `24043b8`. Full-suite
`pytest` not re-run per dispatch (already green at 1568 passed on master).

### TOP-3 BUILDABLE NEXT UNITS (2026-09-23 refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **T-164 — Portal Persona** (deps `T-163` ✓, `done_check`: `uv run pytest tests/test_portal_persona.py`) | Newly unblocked this window; the next roadmap milestone unit with no mechanical or human blocker. T-165 (deps `T-163`+`T-144`, both ✓) is equally ready as an alternative/parallel pick. |
| **2** | **AT-110 (high)** — RunApproval tamper-check defeat; oldest untouched high-severity row on the board (~15 days), no human gate in front of it. | Carried unchanged from the 2026-09-22d refresh; still the highest-severity buildable defect. |
| **3** | **AT-529 (high, HUMAN_GATE)** — PATHLYNKS_USER_* dev credentials 401; only Umesh can supply valid test-account values, then re-run the stage-1 crawl. | Unchanged; blocks the entire live-crawl-target acceptance run (X17/X18/V7 Mode-D proof) — named here so it stays visible, not picked up as ordinary work. |

**Deprioritised (not cancelled):** AT-497/AT-545 (orphaned running-crawl heartbeat, same fix unit
closes both) · AT-488/AT-502 (structural-erosion signals, advisory only) · AT-556 (loop-liveness
observation, low) · AT-546 (checker-owned `require_consent` contract re-point, routine, next
contract touch).

**GRILL — human decision, not a build row (carried, unanswered):**
- GRILL: recurring vacuous-guard prevention policy (AT-218).
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281).
- GRILL (AT-402): structure-before-code review of `visual_order.js`.

### HUMAN_GATE — do not build as ordinary units (carried, verified unanswered on disk)

live-crawl-target · post-login-forms · erp-credentials/AT-529 · t162-contract-approval ·
at438-u14b-baseline + commit-before-verdict · at416-clip-vs-reach-direction ·
at383-loop-status-consumer · at365-data-class-declaration · at110-approval-forgery · at147 ·
at218 · at253 (ARCHITECTURE Execution-model D-entry) · t136-model-credentials.

**Terminal state: `FINDINGS: 0`** (no new issues opened; 2 closed — `ISS-t162-drive-2b-1`,
`ISS-t163-1`, both `open → fixed`; 0 bypasses; contracts + enforcement + goal-coverage all CLEAN;
HEAD `24043b8`).

---

## Sweep refresh — 2026-09-24 (sharded Mode B; consolidation of 3 read-only shards; full report:
`qa/verdicts/sweep-2026-09-24.md`)

Window `761982d..087ab84` (12 commits: D-038 T-164 build → checked-PASS → close-out → reuse spike →
D-039 gate write). HEAD at consolidation `2263e9a` (tick stamp only). T-123 build
(`.worktrees/t123-medium-batch`) and the AT-483 re-land (fix cycle 2,
`.worktrees/at483-reland`, branch `wave/at483-reland`) both running concurrently — out of scope,
not judged or touched.

**GRILL — human decision, not a build row (carried, unanswered):**
- GRILL: recurring vacuous-guard prevention policy (AT-218).
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281).
- GRILL (AT-402): structure-before-code review of `visual_order.js`.

### Findings this sweep — FINDINGS: 0 new · 1 reopened · 1 evidence-refresh

| Issue | Sev | What |
|---|---|---|
| **AT-483** | low (reopen) | Its 2026-09-18 checked-PASS (`9e11559`) certified a fix that never reached master — `git merge-base --is-ancestor 9673f6b master` = NOT-ANCESTOR, `grep heartbeat src/autotester/stages/explore_status.py` on master = no match. Reopened `fixed → open` with `reopen_reason`; re-land already in progress on `wave/at483-reland` (not touched by this sweep); `.work/wave-at483` left unpruned. |
| **AT-415** | medium (evidence refresh, no flip) | Gate-rot count re-derived: `qa/gates/` now 24 files (was 14 at filing), only 6 carry an `Answered:` line, only 1 (`at554`, D-034) is truly answered. `checker_note` appended; row stays open. |

**Inbox:** `qa/feedback-inbox.md`'s 2026-09-23T07:30:10 Umesh entry got a missing `**Status:**`
line added — GATED at `qa/gates/t165-d039-traversal-scope.md` (D-039), T-164 portion folded to
`portal-persona.md` (PASS `05fc732`).

**Non-findings confirmed, not re-filed:** 0 bypasses (t164-portal-persona manifest/verdict
reconcile clean, cycle 1 PASS `05fc732`, closed `3ceb7b9`); delegation health n=1 external unit
(`at119-vocab`), below the ≥10-unit sample threshold, no finding; contracts not stale; data
boundary still fires — standing **AT-365**, not re-filed; enforcement liveness CLEAN (`doctor:
clean`, ruff `All checks passed!`, `.last-tick` fresh, no `.paused`); goal-coverage **38/55
(69%)**, up from 37/55 (T-164 closed), no drift; silent-failure hunt over T-164's new code — none
found. Token scan re-run: `opus_sub_share=0.0`, 8 sub-agents, 0 compactions — well under the 25%
diet threshold; no unit at fix cycle 3 this window. Line appended to `qa/token-ledger.jsonl`.
Worktrees `checker-at540/row1..row10`, `.work/t161-primary-4c09990`,
`.claude/worktrees/agent-a6095f6e2fc40863a` confirmed merged/content-identical, safe to prune —
**report only, not pruned** this sweep.

**Bypass-detection gap noted (not filed as a row):** a checker-PASS + close-out on a wave branch
that never merges to master is currently invisible to the bypass check, which reads handshake
existence rather than master-ancestry. AT-483 is the live example; folded into that row's own
evidence rather than filed separately.

### TOP-3 BUILDABLE NEXT UNITS (2026-09-24 refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-483 re-land (fix cycle 2)** — in progress on `wave/at483-reland`; the next Mode A check re-verifies the heartbeat/liveness fix actually reaches master (same ancestor + grep check used this sweep) before flipping the row back to `fixed`. | The false-fixed claim is the highest-severity live governance issue on the board; re-land already started, needs its check dispatched when ready. |
| **2** | **T-165 HUMAN_GATE (D-039)** — `qa/gates/t165-d039-traversal-scope.md`, 4 spike questions awaiting Umesh (traversal strategy, permission-surface scope, Playwright Healer, API-capture ordering). | Blocks T-165/T-166/T-167/T-168/T-169 downstream; highest-leverage open gate. |
| **3** | **AT-110 (high)** — RunApproval tamper-check defeat, oldest untouched high-severity row with no human gate in front of it. | Carried unchanged across multiple prior sweeps; still the highest-severity buildable defect. |

**Deprioritised (not cancelled):** AT-497/AT-545 (orphaned-running-crawl heartbeat — folds into
the AT-483 re-land, same fix class) · AT-488/AT-502 (structural-erosion signals, advisory only) ·
AT-556 (loop-liveness observation, low) · AT-546 (checker-owned `require_consent` contract
re-point) · AT-529 (HUMAN_GATE, Pathlynks test-account credentials).

### HUMAN_GATE — do not build as ordinary units (carried, verified unanswered on disk unless noted)

live-crawl-target · post-login-forms · erp-credentials/AT-529 · t162-contract-approval ·
at438-u14b-baseline + commit-before-verdict · at416-clip-vs-reach-direction ·
at383-loop-status-consumer · at365-data-class-declaration · at110-approval-forgery · at147 ·
at218 · at253 (ARCHITECTURE Execution-model D-entry) · t136-model-credentials ·
**t165-d039-traversal-scope** (new this window — D-039, 4 spike questions).

**Terminal state: `FINDINGS: 0`** (0 new issue ids; 1 reopened — AT-483 high-severity governance
finding on a low-severity defect row; 1 evidence-refresh — AT-415; 1 inbox status line added; 0
bypasses; contracts + enforcement CLEAN; goal-coverage 38/55, no drift; HEAD `2263e9a`).

---

## Sweep refresh — 2026-09-24b (single-agent Mode B, not sharded — RAM tight, per dispatch;
full report: `qa/verdicts/sweep-2026-09-24b.md`)

Window `2263e9a..f1b8569` (26 commits: T-123/AT-483-reland merges + PASS, gate answers `b8d14bd`,
D-039/D-040/D-041 appended + T-170..T-178 registered, six DRAFT contracts authored, tick stamps).
**Out of scope, not judged/touched:** `.worktrees/t170-network-assertions`,
`.worktrees/at110-approval-signing`, `.worktrees/at335-modal-determinism`.

**GRILL — human decision, not a build row (carried, unanswered):**
- GRILL: recurring vacuous-guard prevention policy (AT-218).
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281).
- GRILL (AT-402): structure-before-code review of `visual_order.js`.

### Findings this sweep — FINDINGS: 0 new · 1 closed (wontfix) · 3 annotated

| Issue | Sev | What |
|---|---|---|
| **AT-365** | high → **wontfix** | Gate answer (`qa/gates/at365-data-class-declaration.md`, 2026-09-24) not yet reflected on the ledger row. Closed `open → wontfix`: Umesh declined both a shared `data_boundary.py` fix and a `.work/` purge — a tester-supplied test account's own data exposure is that account provider's responsibility, not this repo's own scratch-boundary gate. `data_class` stays undeclared by design; MC-003 will keep firing (expected, not a new finding each sweep). Folded → `qa/contracts/core-invariants.md` amendment log + No-fire list; `qa/feedback-inbox.md` 2026-09-24T16:33 entry partially folded. |
| AT-110 | high (unchanged, open) | `checker_note` appended: gate answered 2026-09-24 (option 1, HMAC keyed from `.env`); build already dispatched to `.worktrees/at110-approval-signing` (out of scope this sweep). Row correctly stays open — design decided, fix not yet merged. No inconsistency found. |
| AT-086 | medium (unchanged, open) | `checker_note` set: gate answered 2026-09-24 ("go with the best" → option a, explicit declared `.env` public-key allowlist). Not yet built; queued. No inconsistency found. |
| AT-087 | medium (unchanged, open) | `checker_note` set: gate answered 2026-09-24 (option a, per-field exemption kept in the concatenation join). Not yet built; queued. No inconsistency found. |

**AT-483-class gap re-check (per dispatch item c) — CLEAN, no new findings.** Sampled 24 distinct
commit SHAs cited as evidence across 18 `fixed`/`verified` rows closed since 2026-09-17 (AT-216,
AT-401, AT-461, AT-478, AT-483, AT-495, AT-539, AT-541, AT-555, `ISS-t162-drive-2b-1`,
`ISS-t163-1`, plus AT-065/AT-085 via `18ff2a9` already visible in this window's own log) —
`git merge-base --is-ancestor <sha> master` returned **ANCESTOR for all 24**, including AT-483's
own `9673f6b` (now merged via the `wave/at483-reland` re-land, `2d58215`). The class of bug this
check hunts (a close-out that flips the ledger without the merge reaching master) is not present
elsewhere in the sampled window; AT-483 itself is the one known instance and it is now resolved.

**Non-findings confirmed, not re-filed:**
- **Bypass check (26 commits):** only two touch `src/`/`tests/` — `d5db88b` (T-123: AT-085
  `/healthz` + AT-065 rubric-stamp migration; manifest `qa/manifests/t123-medium-batch.md` →
  verdict `97d74d7` → close-out `17a8a3d` → merge `18ff2a9`) and `9673f6b` (AT-483, already
  reconciled by the prior sweep and re-landed `87e247b`/`2d58215`). Both trace to a proper
  manifest→verdict handshake. All other commits are decisions (`ea6b7c3`/`310e7c1`, both
  `Approved-by: Umesh` per the Lab Protocol), contract DRAFTs (checker-owned surface), gate/inbox
  writes, or tick stamps. CLEAN.
- **Pair-state reconciliation:** no manifest on master sits at `Status: ready-for-check` (both
  in-flight units live in their own worktrees, out of scope). `qa/.last-tick` fresh
  (`2026-09-24T21:50:55+05:30`, this session). No `qa/.paused`. CLEAN.
- **Delegation health:** `qa/delegation-ledger.jsonl` — no run-dispatch gap (the one external
  `ollama/deepseek-v4.1-flash` unit, `at119-vocab`, carries a matching `run` row); weak-executor
  check `n=1` for that `(task_class, executor)` pair, below the ≥10-unit sample floor — no finding.
- **Gate-answered-off-disk:** all five gates touched this window
  (`t125-d039-entry-draft`, `t165-d039-traversal-scope`, `at086-at087-credential-exemption-scope`,
  `at365-data-class-declaration`, `at110-approval-forgery`) carry a real `Answered:` line dated
  2026-09-24T16:32:17+05:30. Zero found answered-off-disk.
- **Contract staleness:** the six new DRAFT contracts (`catalog.md`, `network-assertions.md`,
  `crawl-traversal.md`, `run-trace.md`, `parallel-run.md`, `skills.md`) are correctly `DRAFT` —
  authored this window, no unit has built against any yet. No stale criterion found elsewhere.
- **Enforcement liveness:** `.claude/settings.json` hooks (`SessionStart`, `PreToolUse`,
  `SessionEnd`) all resolve to files on disk (`qa/hooks/mc-sessionstart.ps1`,
  `.claude/hooks/lab-session-start.ps1`, `qa/hooks/mc-precommit.ps1`,
  `.claude/hooks/decisions-append-guard.ps1`, `.claude/hooks/lab-session-end.ps1`); `qa/loop.md`'s
  Stop/Human-gate lines uncontradicted by `qa/adapter.json`; repo has commits (HEAD `f1b8569`).
  CLEAN.
- **Data-boundary (MC-003):** still fires — `qa/adapter.json` has no `data_class`, by design now
  (see AT-365 close-out above). Not re-filed as a fresh finding; codified in the contract's No-fire
  list.
- **Goal-coverage:** `.goal/goal.json` = **38/64 done (59%)** — done count unchanged (T-164 last
  closed it), total rose 55→64 via D-041's T-172..T-178 registration (+9, all `pending`, deps
  satisfied or `[]`). No drift: no requirement newly `missing` with no source, north star unedited.
- **Goal-drift / re-grill:** `qa/.regrill-due` absent. No new GRILL trigger.
- **Silent-failure hunt** over `d5db88b`'s new code (`ui/routes_live.py::healthz`,
  `_newest_source_mtime`): none found — the one fallback (`if not mtimes: return
  _PROCESS_STARTED_AT`) is a benign empty-directory case, not an error swallow.
- **Doctor + ruff, re-run at HEAD `f1b8569`:** `uv run autotester doctor` → `doctor: clean`;
  `uv run ruff check src tests scripts` → `All checks passed!`. Full `pytest` NOT run per dispatch
  (RAM; a build running).
- **Token ledger:** re-measured, `opus_sub_share=0.0` (0/250,154,319 sub-agent tokens are Opus; 16
  sub-agents, all `claude-sonnet-5`), 0 compactions, no unit at fix cycle 3 this window — under the
  25% diet threshold, no finding. Line appended to `qa/token-ledger.jsonl`.
- **Structural erosion:** no new signal — only `ui/routes_live.py` (first touch) and the already
  known `explore_*` files (AT-483 saga, unchanged this window) were edited; `AT-488`/`AT-502`
  carried, numbers unchanged.

### TOP-3 BUILDABLE NEXT UNITS (2026-09-24b refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **T-172 — Run trace** (`trace.jsonl` per run: stage + LLM spans, model/tokens/latency/cost/fallback/verdict + UI panel; D-041, deps `T-163` ✓) | Newly registered, dependency satisfied, no human gate; contract `run-trace.md` (DRAFT) already authored this window. |
| **2** | **T-173 — Parallel case execution** (N isolated browser contexts bounded by measured RAM/CPU + `project.max_parallel`; write-policy cases serial; D-041, deps `T-163` ✓) | Same readiness as T-172; contract `parallel-run.md` (DRAFT) already authored this window. |
| **3** | **AT-086/AT-087 (medium×2)** — both gate-answered ("go with the best": AT-087 per-field exemption kept in the join; AT-086 explicit declared `.env` public-key allowlist), deferred by T-123, not yet built. | Decision no longer blocks; smallest well-scoped buildable unit left with a resolved gate. |

**Queued after top-3, per the standing build-order plan:** T-175 (Prompts as SKILL.md, deps `[]`,
no contract yet), T-126 (adapter allowlist, gate-answered "allow krr dee"), AT-335 (modal crawl
determinism — worktree already prepared at `.worktrees/at335-modal-determinism`). **In flight,
not re-queued:** T-170 (network-assertions, `.worktrees/t170-network-assertions`), AT-110
(approval signing, `.worktrees/at110-approval-signing`).

**Deprioritised (not cancelled):** AT-497/AT-545 (orphaned-running-crawl heartbeat, folded into
the now-merged AT-483 fix) · AT-488/AT-502 (structural-erosion signals, advisory only) · AT-556
(loop-liveness observation, low) · AT-546 (checker-owned `require_consent` contract re-point) ·
AT-529 (HUMAN_GATE, Pathlynks test-account credentials).

### HUMAN_GATE — do not build as ordinary units (re-verified on disk this sweep)

| Gate | Status |
|---|---|
| `live-crawl-target.md`, `post-login-forms.md`, `erp-credentials.md`/AT-529 | Still unanswered — blocks the live post-login acceptance run. |
| `t162-contract-approval.md` | Still unanswered (T-162…T-169 umbrella; individual chains since split and separately gated/answered). |
| `at438-u14b-baseline.md`, `commit-before-verdict.md` | Other session's AT-438; protocol departure. Unchanged. |
| `at416-clip-vs-reach-direction.md`, `at383-loop-status-consumer.md` | Still unanswered. |
| `at147-expiry-end-of-day.md`, `at218-vacuous-guard-class.md`, `t136-model-credentials.md` | Still unanswered. |
| `at253-agent-fallback-wiring.md` | Still unanswered (ARCHITECTURE Execution-model D-entry). |
| ~~`t165-d039-traversal-scope.md`~~ | **Answered 2026-09-24** (D-040 approved) — removed from this table. |
| ~~`t125-d039-entry-draft.md`~~ | **Answered 2026-09-24** (D-039 appended) — removed from this table. |
| ~~`at365-data-class-declaration.md`~~ | **Answered 2026-09-24** — AT-365 closed wontfix, removed from this table. |
| ~~`at110-approval-forgery.md`~~ | **Answered 2026-09-24** (option 1) — build dispatched; removed from this table (no longer a *decision* blocker, tracked as an in-flight unit instead). |
| ~~`at086-at087-credential-exemption-scope.md`~~ | **Answered 2026-09-24** ("go with the best") — removed; tracked as TOP-3 #3 above instead. |

**Terminal state: `FINDINGS: 0`** (0 new issue ids; 1 closed `open → wontfix` — AT-365; 3 rows
annotated — AT-110/AT-086/AT-087 gate-answered notes; 0 bypasses; AT-483-class ancestry re-check
CLEAN across 24 sampled SHAs; contracts + enforcement + delegation health CLEAN; goal-coverage
38/64, no drift; 5 gates newly answered and removed from the open-HUMAN_GATE table; HEAD
`f1b8569`).


## Sweep refresh — 2026-09-25 (sharded Mode B; 3 read-only shards + consolidation, single writer)

Refreshed **2026-09-25T06:07:48+05:30** (system clock, AT-399). Window `f1b8569..8a97eca`, 103
commits (master moved on during the sweep: the T-172 close-out `d03fdfb` and this sweep's own writes).
**This section supersedes every TOP-3 and HUMAN_GATE table above it.** The 2026-09-24b sweep stamped
`.last-sweep` without appending a queue section — that drift was T-126's "QUEUE drift" item, closed here.

**GRILL — human decision, not a build row (carried, unanswered):**
- GRILL: recurring vacuous-guard prevention policy (AT-218). Two fresh instances this window —
  AT-561's empty-redactor gate and AT-565's unguarded session factory — both caught by checks.
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281).
- GRILL (AT-402): structure-before-code review of `visual_order.js`.

### Findings this sweep — FINDINGS: 3

| Issue | Sev | What |
|---|---|---|
| **AT-565** | high | PR6 crash isolation covers `run_fn` only: `stages/parallel_run.py::_run_one` calls `session_factory(case)` outside its try, so one case's context-launch failure aborts `run_cases` and discards every sibling's result. Missed by the t173 checker PASS (its PR6 row only mutated the `run_fn` except-clause). **T-173 reopened**; fix folded into at562-564-live-wiring. |
| AT-566 | medium | `qa/loop.md:53` — `BLOCKED` re-arms `ScheduleWakeup 300s` with no cap, unlike HUMAN_GATE (max 8) / STALLED (3 cycles) / EXHAUSTED (stop): "can it spin" = yes. |
| AT-567 | medium (erosion signal, never a blocker) | `ui/helpers.py` (223→300 over 6 credential-guard commits in 14 days) and `stages/explore_node.py` (9 commits in 14 days) both at the C2 300-line cap. |

**Extended, not re-filed:** AT-564 now also names T-163 — the resumable orchestrator has no CLI/UI
caller, and unlike T-172/T-173 this is undisclosed (FEATURES F-045 is `live`, target.md M8 ticks T-163
with no caveat). Maker to add the caveat until at562-564 lands.

**Applied this sweep (checker-owned surfaces):** reverify sample 8/8 VERIFIED → `verified` (AT-528,
AT-531, AT-532, AT-540, at540-cycle1 rows of AT-547..AT-550; AT-532's pin stays weak, pre-existing
note) · contracts `parallel-run.md`, `run-trace.md`, `skills.md` DRAFT→ACTIVE (each pre-authorized by
its own status line) · inbox 2026-09-24T23:00 D-042 entry folded → `agent-layer.md` AL2/AL3/AL4 ·
`at110-approval-forgery.md` header closed · token ledger appended (opus sub-agent share 0.0, no unit at
fix cycle 3) · **T-126 closed** (allowlist, SNAPSHOT drift, ledger backfill, QUEUE drift all met).

**Non-findings (not re-filed):** bypass CLEAN across all 103 commits (every src/tests/scripts commit
traces to a manifest → matching-cycle PASS: t172 c2, at110 c2, at560, t173, at086-087, t175,
d042-registration, t170, fix-t175-criticality) · pair state CLEAN (building worktrees at335,
at562-564, t125-catalog correctly have no manifest yet; `.last-tick` fresh; not paused) · delegation
CLEAN (all `claude-sonnet-subagent`; no pair at the 10-unit floor) · data boundary = the accepted
AT-365 signal only · enforcement CLEAN (5 hooks present, D-037-authorized; `qa/loop.md` Stop lists the
seven states) · goal drift CLEAN (no `.regrill-due`, north star unedited since the last amendment,
every STALLED stamp has its `qa/debug/` report, no gate answered off-disk) · **proposed, not applied:**
orchestrator contract OR7 "reachable from a real entry point (CLI command or UI route), not
test-only" — the remedy for loop-design "can it Goodhart the verifier" (AT-562/AT-564/F-045); a new
criterion needs an authorizing D-entry.

### TOP-3 BUILDABLE NEXT UNITS (2026-09-25 refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **at562-564-live-wiring** (in build) — CLI/UI run entry points through `StageContext(secrets=...)` and `run_cases`, **plus the AT-565 PR6 fix** | Closes AT-562, AT-564, AT-565 and re-closes T-173; must land before parallel execution reaches real runs. Checker bar: every non-browser test file green; real Mode D (UI entry points change); a PR6 test in which the FACTORY raises. |
| **2** | **AT-566** — cap `BLOCKED` in `qa/loop.md` like HUMAN_GATE | Small; stops the loop spinning on a persistent environment block. |
| **3** | **AT-567** — split `ui/helpers.py` by responsibility before the next credential-guard fix (then `stages/explore_node.py`) | Zero headroom under the 300-line cap; a split under deadline pressure is how guards get dropped. |

**In flight, not re-queued:** at335-modal-determinism, t125-catalog. **Deprioritised (unchanged):**
AT-497/AT-545 · AT-488/AT-502 (erosion, advisory) · AT-556 · AT-546.

### HUMAN_GATE — do not build as ordinary units (re-derived on disk this sweep)

Re-derived strictly: a gate is open only if it has **no line beginning `Answered:` + a date** (a plain
grep for "Answered:" also matches each gate's own how-to-answer text and wrongly reads every gate as
answered).

| Open gate (11) | Blocks |
|---|---|
| `erp-credentials.md` / AT-529 | the live logged-in ERP runs (T-122, T-136, T-145) |
| `at147-expiry-end-of-day.md` | whether a bare-date approval expiry means start or end of day (CN4) |
| `at218-vacuous-guard-class.md` | the vacuous-guard prevention policy (GRILL above) |
| `at253-agent-fallback-wiring.md` | the ARCHITECTURE execution-model D-entry for the agent fallback |
| `at383-loop-status-consumer.md`, `at416-clip-vs-reach-direction.md` | carried |
| `at438-u14b-baseline.md`, `commit-before-verdict.md` | the other session's AT-438; protocol departure |
| `at516-evidence-spec-splitting-policy.md`, `at520-scripts-line-cap.md` | carried |
| `t135-url-pattern-data-migration.md` | the one-off url_pattern backfill |

**Correction to the tables above:** `live-crawl-target.md`, `post-login-forms.md` (both answered
2026-09-21), `t136-model-credentials.md` (answered 2026-09-09) and `t162-contract-approval.md`
(answered 2026-09-21) were still listed as "unanswered" by the 2026-09-24b table. They carry dated
`Answered:` lines and are **not** blockers. Also closed since that table: `d042-deep-agents.md`
(2026-09-24).

**Terminal state: `FINDINGS: 3`** (AT-565 high, AT-566, AT-567; AT-564 extended; T-173 reopened;
T-126 closed; 8/8 sampled fixed rows verified; bypass CLEAN; HEAD at stamp `8a97eca`-window, commit
`89f5b3a` + this correction).


## Meeting-input refresh — 2026-09-26 (checker goal-coverage review of the 2026-09-25 counselor-tool meeting)

Source: Umesh shared the transcript of the counselor-tool meeting. It asks for exactly AutoTester's job: a tester agent
separate from the builder, testing "as a tier-2 counselor", happy AND negative paths on every release, a reviewable
video, "run the 50 cases", and written checklists so a known bug never comes back. The checker mapped each ask against
the repo with file:line evidence and filed **AT-581..AT-589**. Contracts were tightened by **D-045**: execute.md E6 and
report-export.md RE6.

### TOP-3 BUILDABLE NEXT UNITS (meeting refresh)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-581** — enact VIEWPORT_MOBILE / LOCALE_I18N (per-case viewport/locale), or report not-run | High. These cases pass today at desktop size in the default locale, a false-pass class the north star counts. Closes execute.md E6. |
| **2** | **AT-582** — show each failure's reason, fix_hint and repro steps in both exports | Medium and cheap. The judge already writes these; the developer report drops them. Closes report-export.md RE6. |
| **3** | **AT-585** — known bug -> pinned p0 regression case in every release run | High. Answers "why does this bug keep coming back" (e.g. Google sign-in dropping signup data). |

**Extend existing tasks rather than creating new ones:** T-166 += structured scenario variants (AT-586); T-125 += standard
packs for OAuth sign-up carry-over, month/year pickers and Excel column-mapping upload (AT-588); T-180 += an explicit
judge vendor with a warning when judge == agent (AT-589).

### HUMAN_GATE (new, open)

| Gate | Blocks |
|---|---|
| `meeting-user-persona-ux-judging.md` | AT-583 user personas, AT-584 advisory UX/comprehension judging |
| `meeting-run-video-scope.md` | AT-587 run video recording (always vs on-FAIL, retention, secret masking) |

**Out of scope for this repo (noted only):** the seminar-capture agent, audio-first counselor UX, and removing the Gemini
dependency from VTC belong to other Vidysea projects.

## Sweep 2026-09-26

Mode B, sharded (3 shards + consolidation), window `a49c3b8..HEAD`. Full report:
`qa/verdicts/sweep-2026-09-26.md`. 4 new rows filed (AT-613..AT-616), 0 fixed→verified flips, 1
instrument gap (shard 1 returned empty — checks 1/2/3/1c did not run this cycle).

### TOP-3 NEXT UNITS (this sweep)

| # | Unit | Why |
|---|---|---|
| **1** | **AT-616** — reproduce the AT-608/AT-609 regression-check red/green split cleanly, then flip both `fixed -> verified` | Blocks closing out two already-fixed secret-leak rows; the discrepancy itself (real-path pytest run stays green with the fix reverted) is worth a second pair of eyes before it's dismissed as tooling noise. |
| **2** | **AT-614** — split `src/autotester/core/redact_fold.py` off the 300-line cap | Same remedy AT-567 already proved out for helpers.py/session.py/routes_runs.py; do it before the next redact fix has to work in a file with zero headroom. |
| **3** | **AT-613** — re-run the real `autotester snapshot` generator over `docs/SNAPSHOT.md` | The file every SessionStart hook injects is currently missing F-057/058/059 and T-182/183/184; cheap, high-leverage fix. |

### GRILL: (carried, unchanged by this sweep)

- AT-218, AT-281, AT-402 — untouched this window, out of scope for shards 2/3 (check 6 owns them,
  ran but did not re-verify; still open, not re-litigated here).

### Proposed folds for the standing checker (not applied by this sweep)

- **AT-582**: stale — its named fix shipped via T-183 (checker-PASSed) and is confirmed live in
  `stages/report_export.py`. Flip to `fixed`/`fixed_by: T-183`, or narrow the title to the
  still-open must-fix/suggestion split noted in `docs/FEATURES.jsonl` F-057.
