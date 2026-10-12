# Build brief: at733-bounded

Written 2026-10-11 by a read-only readiness pass.

**NOT DISPATCHABLE as of this writing: no contract criterion states the requirement.** `qa/contracts/ui-run.md` RU1 to RU4 say nothing about the entry-case profile wipe; the only trace of it is an amendment-log line (`ui-run.md:48-54`, 2026-09-04, at044) that records the wiped profile as an implementation fact and says "RU1-RU4 meaning unchanged". The queue row (`qa/QUEUE.md:332`) and the old manifest cite "RU1/RU3 (entry-profile amendment)", but no such amendment text exists. The nearest rule is the generic `core-invariants.md` C12(b), quoted in section 3. A checker judges against the contract, and the maker never edits `qa/contracts/` (CLAUDE.md), so the unit needs one step first: the checker adds criterion RU5 to `qa/contracts/ui-run.md` through its criticality-gated amendment path (proposed wording in section 3, not authoritative). Everything else in this brief is ready; the unit becomes dispatchable the moment RU5 (or an owner ruling that C12(b) alone is enough) is on disk.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier M.** Trigger: multi-file behaviour change in a shared module (`ui/run_execution.py`, used by both the serial path at `run_execution.py:100` and the parallel path at `run_execution.py:142`) plus a test file. Not L: it touches no security, auth, tenancy, data-write/migration, concurrency, config/hook/CI or dependency surface. The deleted directory is the gitignored scratch browser profile `profiles/<slug>-entry-test` (`core/paths.py:111`), and the defect is a verdict that can be wrong, not a credential or tenancy leak.
- **Dual check: no.** No `security|auth|tenancy|prod-write <path:line>` trigger exists. The old manifest said "Dual check: required (false-PASS prevention)" (`qa/manifests/at733-entry-cleanup.md`, line 6); false-PASS prevention is not one of the policy's trigger classes and it is part of why the old unit ran long. Owner decision if he wants it back: say so, and the trigger to cite would be `auth src/autotester/ui/run_execution.py:73` (the wipe that establishes the logged-out state).

## 2. Root and base

- Root: `D:/autoTesting`.
- Base: current `master` = `4f8f5da100931ebda1b26836304bfbd38460764b`. Re-read `git -C D:/autoTesting rev-parse master` at start.
- Build in a NEW branch `wave/at733-bounded`, worktree `D:/autoTesting/.worktrees/at733-bounded`, from master. Reason: the private branch `codex/at733-entry-cleanup` (1 commit, 6e0134b7) is 183 commits behind master, rewrites unrelated docstrings, and is INPUT only (D-080 item 1, `QUEUE.md:329`). Do not merge or cherry-pick it; its idea is reused, its diff is not.

## 3. Acceptance criteria

**Contract status: none exists for the entry-profile requirement (see the top of this brief).**

What the contract does say, verbatim, and which a checker could use meanwhile:
- `core-invariants.md:258` C12: "Every signal and every measurement this system reports must fail closed", and from clause (b), `core-invariants.md:371-375`: "The same rule, one surface out. A number this system **reports about a product or a participant** — a score, a rate, a duration, a coverage figure, a budget — must be **absent when its input is absent**, never substituted with the value most favourable to whatever is being measured. 'I did not measure this' and 'I measured this and it was fine' are different facts and must be different outputs." and `core-invariants.md:383-384`: "**Verify by construction, never by inspection:** build the object with the input missing and assert the report says unavailable. A test that exercises only the populated path cannot catch this class, because the unpopulated path IS the defect."
- `core-invariants.md:81` C7: "A unit is complete only when a check that someone else can re-run passes." plus "A sabotage must assert that it was applied."
- `ui-run.md:48-50` (amendment log, not a criterion): "`trigger_run` now gives an entry-screen case (`_is_entry_case`) a dedicated, wiped-before-every-run profile instead of the shared persistent session".

The expected behaviour exists only as the issue's own text (`qa/issues.jsonl`, AT-733, last row, status open, severity high): "After the wipe, assert the profile directory is absent (or empty) and on failure end the case ERRORED naming the profile path, never run it. Needs a manifest with a falsifying sabotage: hold a file open inside the profile dir, run the entry case, and assert ERRORED not PASS."

**Proposed RU5 for the checker to adopt (a proposal, not ground truth):**
"RU5 — an entry-screen case never runs on a profile that was not wiped. Before an entry-screen case's browser starts, its dedicated profile directory is removed and verified absent. If removal raises, or the directory is still present, or its presence cannot be determined, the case's result is ERRORED with an error naming the profile path, its verdict is graded through `grade_errored_result`, no `BrowserSession` is started for it, and every sibling case still runs and the Run is still saved. *Check:* with the removal stubbed to leave the directory (and separately to raise), a run containing the entry case and a sibling returns 303; the entry case is ERRORED with the path in its error and its verdict is INCONCLUSIVE; the entry case was never executed; the sibling is COMPLETED; with a healthy wipe the entry case runs and passes."

## 4. What exists and what is missing

The defect, on master `4f8f5da1`:
- `src/autotester/ui/run_execution.py:60-87` `_run_entry_case`. Line 72 builds `ProjectPaths(f"{slug}-entry-test")`; **line 73** `shutil.rmtree(entry_paths.profile_dir, ignore_errors=True)` swallows every failure; line 74 `BrowserSession(...)` and line 79 `session.start()` follow with no check that the directory is gone. On Windows a profile held by a lingering Chromium survives the wipe silently, the case runs logged in, and a case that expects a logged-out start can PASS. The docstring (lines 65-67) promises "genuinely logged-out state" and nothing asserts it. (The issue and the QUEUE row cite line 67; master has moved it to line 73.)
- Callers: `run_execution.py:100` (`_run_cases_serially`) and `run_execution.py:142` (`_run_entry_cases`, the entry leg of a parallel run). One function, so one fix covers both.
- Existing handling that already works and must be reused: the `try/except Exception` at lines 76-84 builds `RawResult(outcome=ERRORED, error=secrets.redactor().scrub(...))` and grades it with `grade_errored_result` (imported at line 29-31). The fix feeds that same path; no new result or grade path.
- Existing tests: `tests/test_ui_runs_serial_resilience.py` (217 lines; `test_an_entry_case_crash_still_saves_every_case_and_the_run` at line 174, helpers `_entry_case` line 49, `_patch_common` line 58, `_only_run_id` line 73); entry ordering and namespace tests in `tests/test_ui_runs_serial_entry_order.py` (300 lines, at the cap, do not edit), `test_ui_runs_serial_entry_screenshot_namespace.py`. No test makes the wipe fail. There is no test file named like `*run_execution*`.

What the private branch tried (`codex/at733-entry-cleanup`, worktree `C:/Users/Lenovo/.codex/worktrees/at733-entry-cleanup/autoTesting`, clean, 0 dirty lines): one commit `6e0134b7` (2026-10-01), 2 files, +124 -27. Source: replaced the `rmtree` line with a nested try that `lstat`s the profile, calls `shutil.rmtree` without `ignore_errors`, `lstat`s again, and returns ERRORED through `grade_errored_result` on any `OSError`; correct in principle, but it returns before the `try` block, so a failure in the post-wipe inspection and the session lifecycle are separate arms. Test: rewrote `tests/test_ui_runs_serial_resilience.py` (docstrings of three unrelated tests shortened) and added a 6-mode (`raising`, `leftover`, `inspection`, `post-inspection`, `healthy`, `absent`) by 2-width (serial, parallel) matrix = 12 parametrised nodes plus helpers, to 300 lines.

Why the earlier unit never converged (`qa/manifests/at733-entry-cleanup.md`, 289 lines; D-080 item 6: 208 of 549 ticks, no verdict):
1. The product change was finished and frozen on 2026-10-01 (manifest "Evidence pending", lines 203-215: two files, 13 then 15 focused tests green, source reviewer APPROVE, candidate 6e0134b7 committed). It never reached a verdict because of the verification path, not the code.
2. The full-suite gate on the candidate hit environment faults (a native `git clone` exit 128 `GitCommandFailure`, a `0xC0000005` access violation in `conhost.exe`), and the unit then expanded into building a diagnostic/retention harness for them (zero-OID `cat-file` mode, receipt hashes, stream-scrub and 16384/65536-byte bounds, launcher and validator reviews; manifest lines 15-56). The manifest itself says "AT733 product frozen/held" while those diagnostics ran.
3. It was entangled with T-125 cycle-4 planning in the same manifest (lines 15-56 carry T-125 plan/audit notes), so every tick advanced something else.
4. The test matrix itself grew (6 fault modes x 2 widths, plus stronger cause/note equality assertions on reviewer request) until the file sat at its 300-line cap, and a real "Windows locked-file sabotage" plus live-browser acceptance were added to scope.
The bounded unit therefore: one behaviour, one source function, a small fixed test set, and a rule that a gate command failing for a reason unrelated to those two files is recorded and stopped, never diagnosed inside this unit (section 11).

**The one behaviour change.** In `_run_entry_case`, wipe the entry profile without `ignore_errors`, then verify it is absent; if the wipe raises `OSError`, or the directory is still present, or its presence cannot be determined, return the ERRORED result (error text names the profile path and the cause) through the existing `grade_errored_result` path and start no browser. Healthy wipe and "already absent" behave exactly as today.
Suggested shape (in place; the builder may differ if the checks above hold): a small private helper `_wipe_entry_profile(profile: Path) -> None` in `ui/run_execution.py` that calls `shutil.rmtree(profile)` treating `FileNotFoundError` as success, and raises `OSError(f"entry profile not removed: {profile}")` if `profile.exists()` is still true after the call (an inspection `OSError` propagates, which is the fail-closed reading). Call it inside the existing `try` (move `session = BrowserSession(...)` and the `evidence_prefix` line into the `try`, with `session = None` before it and `if session is not None` in the `finally`) so the existing `except Exception` produces the ERRORED result. Do not use `os.path.lexists`: it returns False on any OSError and would fail open.

## 5. Files the builder will touch

- `src/autotester/ui/run_execution.py` (existing, 195 lines; expected 205 to 215). One new private helper plus the edit at lines 72-87. Functions stay under 50 lines.
- `tests/test_ui_runs_serial_resilience.py` (existing, 217 lines; expected 260 to 280, cap 300). Append only; do not rewrite docstrings or touch the three existing tests.
- `qa/manifests/at733-bounded.md` (new, the maker's own manifest).
Nothing else. No new module, no schema, no contract (checker-owned), no `docs/MAP.md` change (no module added or described differently; run `uv run autotester map` and confirm no diff).

## 6. Test scope

Builder, exact nodes (the file is named, not the directory; one pytest process):
- `uv run pytest tests/test_ui_runs_serial_resilience.py` (the three existing tests plus the new ones).
- `uv run pytest tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py` (existing entry-case behaviour must not change).
- `uv run ruff check src tests scripts` and `uv run autotester doctor`.
Planned new nodes in `tests/test_ui_runs_serial_resilience.py`, at most four:
`test_an_entry_case_whose_profile_survives_the_wipe_is_errored_and_never_run` (stub leaves the directory), `..._whose_profile_wipe_raises_...` (stub raises `PermissionError`), `..._parallel_...` (the leftover mode with a width-2 plan, to exercise the second caller), `test_an_entry_case_with_a_healthy_wipe_still_runs` (control: a stale file in the profile is removed and the case executes).
The builder runs no full suite. The checker runs the one full suite (tier M gets one scoped run unless the checker says otherwise).

## 7. Reachable test cases

1. Happy path control: stale file in `scratch_root/profiles/demo-entry-test`, real `shutil.rmtree`; the route returns 303, the profile is gone, the entry case is executed and has a PASS verdict (fake `run_case`/`grade` as in line 191-203 of the existing test).
2. **Fails today, passes after:** stub `autotester.ui.run_execution.shutil.rmtree` to do nothing (the exact AT-733 repro: failed wipe, no error) with the directory present. Today: the entry case runs and the verdict is PASS (assertion on ERRORED fails). After: entry result ERRORED, error contains the profile path, verdict INCONCLUSIVE graded by the rule path, `fake_run_case` never saw the entry case id, no `BrowserSession` constructed for `demo-entry-test`, sibling case COMPLETED with PASS, Run saved, status 303. Use `scratch_root` (sets `AUTOTESTER_ROOT`, `tests/test_ui_runs_parallel_trace.py:36`) so `ProjectPaths("demo-entry-test").profile_dir` is under `tmp_path`.
3. Stub raises `PermissionError`: same expectations, and no 500 (today the exception escapes `_run_entry_case` outside its `try`, which is the AT-574 shape).
4. Parallel caller (width 2 via `plan_parallel_run` monkeypatch as in `6e0134b7`'s test): same as 2, through `_run_entry_cases` at `run_execution.py:142`.
5. Edge, no test: directory already absent behaves as today (`FileNotFoundError` is success), covered by the existing entry tests staying green.
6. Checker falsification (throwaway copy, anchor must match once and the file must change): restore `ignore_errors=True` with no check; case 2 must go red. On Windows the checker should also run the real sabotage the issue names (hold a file open inside the profile dir with no share-delete, run the entry case, expect ERRORED not PASS); on POSIX deleting an open file succeeds, so that probe applies to Windows only and is the checker's, not a builder test.

## 8. Gate answers

- `qa/gates/commit-before-verdict.md:60`: "Answered: 2026-09-26T22:34:22+05:30 — C — Umesh via AskUserQuestion in the checker session. Official rule: a unit is committed on its own branch (wave/<slug> worktree) before check, and reaches master only by merge after a checker PASS with a matching cycle. This ratifies the current practice."
- `qa/gates/plan-approved.md:13`: "Answered: 2026-09-27T08:43:48Z — plan APPROVED — same answer, same session; scope decisions recorded in docs/plan.md (max parallel; Track C through C3; T-154/T-155 held)"
- No gate file mentions AT-733 except `qa/gates/t125-fullsuite-browser-egress.md` (which concerns the full-suite sandbox, not this fix). The decision that scopes this unit is D-080 item 6 (a decision entry, not a gate). Approval to run: `qa/QUEUE.md:327` "approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)".

## 9. UI surface and persona walk

`Persona walk: skip (no visible UI change: the diff touches ui/run_execution.py and one test file only; checkable with git diff --name-only master, which must list no route, template or static file. The only user-visible effect is an ERRORED case row with an error string, rendered by the existing report path that tests/test_ui_runs*.py already cover)`

## 10. Dependencies and conflicts

- `after:` the checker adding RU5 to `qa/contracts/ui-run.md` (or an owner ruling that C12(b) suffices). No other unit gates it (`QUEUE.md:334` `after: none`).
- `ui/run_execution.py` is owned by this row (`QUEUE.md:335`). Two unmerged branches also edit it, textually away from line 73: `wave/t202-litellm` and `codex/t202-completion` change the `judge:` annotation (`LangChainFallbackProvider` to `Provider`) on the signatures of `_run_entry_case` (line 62) and other functions, and change two lines of `tests/test_ui_runs_serial_resilience.py` (the `_patch_common` provider patch). Land this unit first; T-202's re-land then rebases onto it. If the new test patches `routes_runs.LangChainFallbackProvider` as `_patch_common` does today, T-202 will have to adjust that line.
- `wave/t203-hosting` edits `ui/routes_runs.py` only; no overlap with this unit's files.
- `docs/MAP.md`: unchanged by this unit.

## 11. Budget and process rules

- Check budget: tier M, 10 minutes.
- **Hard cap: 2 fix cycles** (`QUEUE.md:336`). After the second FAIL the unit is STALLED to the owner; no third cycle, no new top-of-queue item. The old open-ended unit is not a precedent.
- Builder runs no full suite; the scoped files in section 6 only.
- Falsification only in a throwaway copy under the session scratchpad, never in the worktree under check (open issues AT-782 and AT-820 are exactly this and the PID kill below).
- Kill only PIDs you started; never `taskkill /IM` or `Stop-Process -Name`; give every child process a timeout.
- **Stop rule that bounds this unit:** if any gate command (`uv run pytest`, ruff, doctor, or a git operation inside a test) fails for a reason unrelated to the three files in section 5, record `BLOCKED-PROCESS: <command>, <exit code>, <first error line>` in the manifest, file an issue, and stop. Do not build diagnostic tooling, receipts or launchers inside this unit; that is what consumed the old one.
- Do not touch `qa/contracts/` or set any issue status (checker only). Do not read or merge from the Codex worktrees beyond the single commit `6e0134b7` for reference.
- Edit in place, no new module, no `*_v2`/`*_new` file. No push: the checker pushes on PASS (D-007). Use `git -C <dir>` and absolute paths; no `cd X && cmd`.
