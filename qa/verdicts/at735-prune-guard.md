# Verdict - at735-prune-guard

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 5993356238acdbc9bd737fc7e4c76222d5971e9d (base 3f081243; worktree clean at review)

## Scope
AT-735 / O5: prune_old_videos_safely (stages/video_retention.py), run_follow_ups (stages/run_launcher.py), ordering change in stages/orchestrate_downstream.py, tests/test_prune_guard.py.

## Independent checks
- pytest (PYTHONPATH=worktree src, import path confirmed in worktree): test_prune_guard, test_video_retention, test_run_launcher, _approval, _retired, test_team_run_launcher, test_orchestrate_downstream, _privacy: 51 passed, rc 0 (260 s).
- ruff check src tests scripts: clean, rc 0.
- autotester doctor: clean, rc 0. run_launcher.py is 250 lines (<=300).

## Findings
1. Race/need: the ask (ask_for_what_it_did_not_recognise -> queue_requests -> store.add_request) is a synchronous call, no thread/queue/async, so ordering is real, not nominal. It reads only EvidenceKind.URL evidence (coverage._seen_urls); prune removes only EvidenceKind.VIDEO rows. The ask raises requests for NEW videos and consumes no existing video. prune_old_videos has no kept/flagged concept; it drops the oldest beyond 20 (unchanged, gate D-048 value). Ask-before-prune plus failure-skip means a prune error or ordering cannot starve the ask.
2. Duplication: run_launcher.run_follow_ups (advise, ask, prune) vs orchestrate_downstream.make_report_stage (ask, prune; no advise). Not the same sequence, but the ask+prune pair is written at two call sites. Minor, non-blocking; consider folding into one helper later.
3. Error safety: `except Exception` only (BaseException/KeyboardInterrupt propagate), logs warning with exc_info, returns []. Correct.
4. Limits: no test pins the ordering in orchestrate_downstream (reviewed by diff only: ask line precedes prune_old_videos_safely). No mutation run (CPU/time budget); tests prove ordering and raise-survival for run_follow_ups.

## Remaining
Full suite is the post-merge gate. Checker time exceeded the 300 s target because the scoped pytest alone took 260 s on a saturated CPU; recorded, not waived. Token/time actuals for the checker are unknown (null).
