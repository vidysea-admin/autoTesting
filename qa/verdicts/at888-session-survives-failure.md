# Verdict - at888-session-survives-failure (AT-888)

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Head eea903d8 (code 9286a25d, parent 55816796), branch wave/at888-session-survives-failure, merge base master 3748cb83. Checked from detached checkout `.worktrees/check-at888`; base reproduction from a `git archive` on C: with its own venv.
Date: 2026-10-11. Checkpoint: qa/checkpoints/at888-session-survives-failure.md. Evidence: qa/evidence/at888-session-survives-failure/.

## Check plan
Tier L (browser process lifetime, restart between cases). Plan: (1) reproduce on base and head in headed Chromium; (2) real-pipeline probes through `_run_and_grade_resilient` with kills, own-page close, latch and budget; (3) evidence integrity (mask, per-case video, `session-restart` placement); (4) whole-diff scope and design rules; (5) one falsification per criterion.

VERDICT: PASS
SCOREBOARD: 5/5 criteria met (C1-C5). Four non-blocking findings (PROPOSED-ISSUE below).
TIER: L. Dual check: no. Ruling: "no" is right. The diff adds no auth, tenancy or production-write code; the mask line `self._page.add_init_script(_MASK_INIT_SCRIPT)` is byte-unchanged (video.py:50 on head, `_MASK_INIT_SCRIPT` definition unchanged in the diff).

## Per-criterion
- C1 MET. Headed repro (`AUTOTESTER_HEADED_TESTS=1`) passes on head and fails on the base with `TargetClosedError` at the second case. Matrix probe, headed, real pipeline: case 1 pass, case 2 refused host, case 3 closed its own page; case 4 then ran on a live page and PASSED. Floor F1 (spare page removed) red at test_session_survives_failure.py:148.
- C2 MET. The restart is one `self.start()` call, recorded as `session-restart` on the RawResult of the case that began after the death (matrix c4, killbetween k2, both pipeline paths pinned by test). Floors F2 (no restart), F2b (no event), F6 (events not attached) red.
- C3 MET. A mid-case hard kill ended ERRORED / INCONCLUSIVE (c5), never PASS. When the headed relaunch timed out (180 s) the session latched; the remaining cases failed in 0.0 s with `SessionRestoreError: browser session died (...) and could not be restarted: TimeoutError ...`; the start count stayed at 2, so no relaunch loop. Floor F3 (latch check removed) red ("DID NOT RAISE"). Gaps: see findings 1 and 2.
- C4 MET. Every case in the probes got its own non-empty .webm (3.6-23.6 KB), including cases after a restart; the spare page's temp video differs from the case's in every row and is not returned. Floor F7 (`temp_path.replace(final_path)` removed) red: 2 failed of 2 live tests. Video/mask regression 5 passed.
- C5 MET. On every page that ran after a restart the mask style element was present and `webkitTextSecurity` computed to `disc` (probe notes). Floor F5 (init script removed) red.

## Falsifications (throwaway copies on C:, deleted; green before, red after)
F1 spare page -> C1 red; F2 restart removed -> C2 red; F2b event removed -> C2 red; F3 latch removed -> C3 red; F5 mask removed -> C5 red; F6 events not attached -> C2 red; F7 video move removed -> C4 red. Survived: F3b (`_scrubbed` returns raw text), so the secret scrub of the restore error has no test (finding 2).

## Brief items
- Budget and consent: `_restart_session` relaunches only through `start()`, which calls `RunBudget.check_start()` (session.py:93). Probe: with the budget exhausted `begin_case_video` raised `RunBudgetExceeded: max_actions` and `start` was called 0 times. A restart does not use up an action, so the number of relaunches is bounded by the budget clock and by one per case, not by a count.
- Mid-case death: ERRORED, never PASS (c5). Headless hard kill between cases restarted and passed in 54 s (killbetween-headless). Headed hard-kill relaunch exceeded 180 s here; plain Playwright with no product code shows the same slowness after `taskkill /F /T` (exp-plain-playwright-kill.txt), so it is the environment, and the failure was reported honestly.
- Diff: 5 files (video.py, run_case_pipeline.py, 2 tests, manifest); 0 removed test lines; ruff clean; doctor shows only the inherited `stale-generated: docs/SNAPSHOT.md` (also on base). Sizes within limits (video.py 224, pipeline 243, longest function 36 lines).
- Merge note (not a defect): branch `wave/t177-slice0-browser-seam` also edits `browser/session.py` and `browser/video.py` (7 lines). A trial `git merge-tree` of the two branches reported no conflict. After T-177 lands, `_restart_session` must also republish the DevTools port if that step is outside `start()`, as the manifest says.

## Executor
claude-sonnet-subagent (maker build); checker coordinator on claude-sonnet-5-5.

## PROPOSED-ISSUE (none blocks; the maker or coordinator files them)
- PROPOSED-ISSUE: sev low, video.py `_restart_session` / `_open_case_page` - a failed headed relaunch costs the batch one full launch timeout (181-244 s for one case) before the latch makes the rest fail at once. Consider a shorter restart launch timeout. Evidence: probe-killbetween-headed.json (k2 244.1 s).
- PROPOSED-ISSUE: sev low, test gap - nothing pins `VideoMixin._scrubbed` (floor F3b survived: 18 passed with the scrub removed). Add a test that a planted secret in the restart failure text is absent from the SessionRestoreError message.
- PROPOSED-ISSUE: sev low, video.py `_scrubbed` / `_one_line` - the profile directory path is not removed from the restore error text when the message is short (scrub-probe.txt: "profile path leaked: True", secret redacted). The path is local and holds no credential, but it reaches the case result.
- PROPOSED-ISSUE: sev low, browser/session.py `close()` (unchanged by this diff) raises `TargetClosedError` when the context is dead and was not restarted (probe-budget.json `close`). Every batch caller wraps it in `contextlib.suppress(Exception)` (ui/run_execution.py:106 and :147); `stages/manual_login.py:48` does not.

## Metrics
checks=14 criteria=5/5 falsifications=7 red=7 survived=1(F3b, extra row) findings=4 low, 0 blocking, cycle=0 tier=L wall~7h (machine under heavy load, real-browser runs 190-570 s each).
