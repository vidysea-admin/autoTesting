# Verdict - sheet-sync-hardening (coordinator A, blind dual check)

Cycle checked: 0
Date: 2026-10-17
Bound to: D:/autoTesting/.worktrees/sheet-sync-hardening (HEAD ea65f9b5, code b3844a0d, base 69ebfae7 = git merge-base with master)
Policy-Version: proportional-verification/2026-10-15.12

## Check plan
Tier L dual (write barrier + redaction). Logic changed -> affected tests + one falsification per criterion (C1..C4 = AT-981..984) in a copy outside the worktree. Security read of the changed lines in sheet_write.py / sheet_plan.py. No UI, no persona walk, no live client. Lane: normal (quick lane is dual-excluded).

## Evidence (all produced by this checker)
- `uv run pytest tests/test_sheet_sync_hardening.py tests/test_sheet_plan.py tests/test_sheet_sync_tb12_tb14.py` -> 37 passed, 1 warning
- importer tests `tests/test_bug_wiring.py tests/test_tracker_page.py` + the three above -> 56 passed
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean
- Diff read in full (`git diff 69ebfae7 HEAD -- src tests`): nothing removed beyond the replaced lines; only files listed in the manifest changed; no live client added; `_WRITERS` empty in production (only tests/sheet_fake.py registers). The only src caller, stages/sheet_sync.py:39, passes through write_confirmed_plan, so it is now stricter, not looser.
- Security read: `isinstance(client, ())` is False, so an empty registry refuses every client; `getattr(client,"live",True)` makes a missing flag count as live; the barrier runs before read, after read and before each row write. Sheet-side text (`before`, `sheet_has`) is scrubbed before model, render and hash. `adopts` values come from the already-scrubbed `want`. No secret path found.

## Falsification (copy at scratchpad/chkA from `git archive HEAD`, PYTHONPATH on the copy; green before, red after, restored)
| Criterion | Edit | Green | Red |
|---|---|---|---|
| C1 AT-981 | `before=scrub(have)`->`have`, `sheet_has=scrub(have)`->`have` | 1 passed | `assert not True` (secret in plan text/hash input) |
| C2 AT-982 | `if new and last != new:` -> `if False:` | 1 passed | adopts `{}` vs `{'bug_..': {'Status': 'fixed'}}` |
| C3 AT-983a | `if not isinstance(client, tuple(_WRITERS)):` -> `if False:` | 1 passed | `DID NOT RAISE WriteRefused` |
| C3 AT-983b | both post-read and per-row `_assert_writable` removed | 1 passed | `DID NOT RAISE LiveWriteRefused` |
| C4 AT-984 | `unguard(have)==unguard(new)`->`have==new` (and last form) | 1 passed | extra `PlanRow(action='conflict' ... sheet_has='-5', we_last_wrote="'-5")` |
After restore: 6 passed. Worktree untouched.

## Criteria
- C1 AT-981 met: secret in a sheet cell is absent from model_dump_json, render_plan, repr and hash input (test + falsification).
- C2 AT-982 met: retry after a landed write adopts the equal cell into memory; a later change is an update, not a conflict.
- C3 AT-983 met as the issue states it: a structural registered-class check replaces the self-declared flag and `live` is re-checked after the read and before each write. A non-fake class claiming live=False is refused; a fake going live during the read is refused. (Hint applied: the module-level list is structural, not tamper-proof; the issue asks for a structural check, not tamper-proofing.)
- C4 AT-984 met: guarded value read back without the apostrophe is no conflict and converges.
Invariants: core-invariants touched = secrets/redaction, write barrier; hold.

PROPOSED-ISSUE: {"severity":"low","type":"security","title":"register_writer is a public mutable allow-list: any importer can register a live client class, and subclasses of a registered class are admitted; the barrier is structural, not tamper-proof. Acceptable while no live client exists; before the live slice make registration test-only or require the confirmed first-write record (t199-first-live-write gate).","evidence":"src/autotester/stages/sheet_write.py:51-58,95"}
PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"Manifest says order note 'fix written before tests' (honest) but Pre-check lines all cite the same single command; harmless, wording only.","evidence":"qa/manifests/sheet-sync-hardening.md:27,35-38"}

VERDICT: PASS
SCOREBOARD: 4/4 criteria met, invariants hold
TIER: L (outward-facing write barrier and secret redaction in changed src)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced (C1, C2, C3a, C3b, C4)
LIVE-BROWSER: not-applicable (no UI path changed)
ISSUES-WRITTEN: none (dual coordinator; 2 PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Re-ran the verify commands and each criterion's falsification in an isolated copy; every one went green then red on the named assertion and restored. Diff and security read found no defect in the changed lines.
Metrics: start=2026-10-17T10:50:00Z end=2026-10-17T11:20:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
