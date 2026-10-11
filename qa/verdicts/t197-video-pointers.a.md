# Verdict - t197-video-pointers - coordinator A (dual check)

Cycle checked: 0
Head checked: 3d0be650 (wave/t197-video-pointers; product sha 5032cfa1; the only change between them is the manifest). Base master 09828f2d.
Policy-Version: proportional-verification/2026-10-10.9 · Date: 2026-10-11
Checkpoint: qa/checkpoints/t197-video-pointers.a.md · Evidence: qa/evidence/t197-video-pointers-a/falsification.md

## Plan (step 0)
Tier L (egress to an external model, TV7/TV8 CRITICAL; dual-trigger line verified: `require_approval(` is at cli_video_review.py:62).
Checks: (1) every BUILT criterion by its own command; (2) one falsification per criterion in throwaway copies; (3) whole diff 09828f2d..3d0be650 read, including the g2 code; (4) HELD audit against master; (5) new-module list; (6) ruff + doctor; (7) full suite: NOT RUN, see below.
No live model call, no network, no browser (no UI surface changed). Sonnet sub-checkers ran in parallel; I re-read cli_video_review.py:90-220 and re-ran `git check-ignore` myself.

VERDICT: FAIL
SCOREBOARD: TV1-TV6 and TV8 met; TV7 (parts 2-4) and TV10 (built part) met with findings; 2 evidenced FAILs (P1, P2); HELD parts open and not claimed.
TIER: L (security/data egress; cli_video_review.py:62, stages/video_review.py:221, media/redacted.py)

FAILURES:
- [CLI contract / TV7 exit 3] sev: medium · `--output json` is not a valid document on stdout for exit 3 (approval or permission missing) nor for the exit-1 usage errors. Contract cross-cutting "CLI contract": "`--output json` is a valid document on stdout with logs on stderr". · cli_video_review.py:183-185 (read by me): `except ReviewRefused as exc: _say(str(exc), ...); raise typer.Exit(EXIT_REFUSED)` writes nothing to stdout; same at :110-117, :127, :136, :140. Pointer errors (:97), unreadable (:196) and the review (:103) do emit JSON, so the gap is only the refusal paths. · Emit `{"status":"refused","reason":...}` through `_doc` on those paths and add a json-mode test per exit code. · issue: P1
- [TV10 "never in the repo" / data egress] sev: high · the review work dir `projects/<slug>/reviews/<rid>/` holds `redacted.mp4` and every extracted PNG frame, is never cleaned up, and is not git-ignored. Command: `git -C <worktree> check-ignore -v projects/x/reviews/rv-1.json projects/x/reviews/rv-1/frames/a.png` prints nothing, exit 1 (sibling `projects/*/sources/*/frames/` and `recording.*` ARE ignored, .gitignore:31-35). Persistence: stages/video_review.py:241 `frames_fn(video, paths.review_work_dir(rid), wins)`, media/redacted.py:123,127; grep finds no unlink/rmtree of the dir. Pathlynks frames sit in a PUBLIC repo path one `git add -A` away. · Add `projects/*/reviews/*/` to .gitignore and delete or ignore the work dir after the run (owner call on whether `reviews/<rid>.json` is tracked). · issue: P2

CRITERIA (each by its own command; I re-ran all of them, the pre-check lines were not relied on. Form: `uv run --project <wt> pytest -p no:xdist -o addopts= -rs --rootdir <wt> <files>`):
- TV1 met: test_video_pointers.py + test_cli_video_review.py -> 47 passed, 0 skipped. Exit 2 lists every error, provider.calls == 0. `ingest run --pointers` HELD.
- TV2 met: test_video_review_gates.py + test_video_review_guards.py -> 28 passed (superset, depth 12 > 4, exact partition, plain-language not_reviewed).
- TV3, TV4, TV5, TV6, TV8 met: test_video_review.py -> 28 passed. CLI exit 4 comes before the approval check.
- TV7.2 approval, TV7.3 redaction, TV7.4 cap and dry-run met: test_video_review_redaction.py 9 passed (real ffmpeg, luma of real PNGs), gates and CLI green. TV7.1 `authorize()` HELD.
- TV9 "no baseline" line met (guards test); the flow half is HELD.
- TV10 id, idempotence, human status (built half) met: 5 gates tests + the CLI second-run test. Routes HELD.
- F6, F8, exit codes 0/1/2/3/4 met (guards and CLI tests). test_cli_advice_resolves + test_approve_cli + test_cli_surface -> 89 passed. Totals 92 and 109 match the manifest; 0 skipped, the real-ffmpeg files RAN.
- ruff check src tests scripts: All checks passed (exit 0). `autotester doctor`: clean (exit 0) with core/paths.py, schema/enums.py, cli_crawl.py at exactly 300.
- CAPABILITY-COVERAGE: 21 falsification rows reproduced in copies (evidence file); 3 survivors below.

FALSIFICATIONS: every criterion has an on-criterion red (TV1 11 failed, TV2 4, TV3 1, TV4 1, TV5 3, TV6 1, TV7.2 1, TV7.3 3/5/1/1, TV8 b 2, TV10 1 to 4). I ran the TV7.3 redaction mutations the builder did not: blackout verification disabled and a no-op blackout both go red. Survivors:
- TV8 quote scrub only (the builder's survivor). Ruling: TV8 IS properly tested at the leak surface. `_finish` re-scrubs the whole review, no output carries pre-`_finish` items, and removing `_finish`'s scrub or the prompt scrubs goes red on canaries in json, md, html, caplog, stdout and stderr. The contract's literal mutation ("skip the scrub on quotes -> fails") is unmet, and the scrubbed-quote branch (video_review_items.py:53) is untested. Not a FAIL. P5.
- TV10 plain (non-refresh) re-run resetting human status (video_review.py:235) survives; the only mark-survival test uses refresh=True. Code is correct, test gap. P3.
- TV7.3 "original path handed over" (redacted.py:123-124) is red only on the internal `frames.origin` attribute and the `redacted.mp4` exists check; frames inside a window are never requested, so no pixel test can tell. The contract mutation is met. P4.

HELD AUDIT (checked against master 09828f2d and master HEAD; the manifest claims none of them as met): `authorize()` absent (no `def authorize`, no auth package, T-204 pending); `ui/routers.py` absent (T-205 pending), so TV10 routes and HTTP 422 wait; TV9 flows: `expand()` calls `require_reviewed` (review.py:43-48), which refuses non-APPROVED, D-073 forbids changing it, and the review path emits no flows; `stages/ingest.py` is exactly 300 lines so `ingest run --pointers` cannot be added; live acceptance needs an approval no file records; no Linux run exists to reuse (T-204 not landed). The unit has no code or test for any of them; `local_operator_permission()` is a no-op seam (cli_video_review.py:48-51) and the manifest says so. The contract does NOT carve these out of T-197 (its Out-of-scope section omits them), so the full T-197 cannot PASS or close on this cut; only the built subset is judged here. TV9 is self-contradictory (contract :108 vs :111).

NEW FILES (src): cli_video_review.py 220, schema/video_pointer.py 46, schema/video_review.py 157, stages/video_pointers.py 107, stages/video_review.py 289 (all five named by D-072 item 2 and contract :170). NO entry: stages/video_review_plan.py 129, video_review_items.py 150, video_review_prompt.py 111, video_review_render.py 70, media/redacted.py 130; prompts/video_review_v1.md 43. `ApprovalKind.VIDEO_REVIEW` (schema/enums.py) also has no entry. Fold candidates within 300: redacted.py into media/frames.py (88+130=218); video_review_plan.py into video_pointers.py (107+129=236). Render, prompt and items have no natural host; video_review.py (289) is full. Different jobs, so folding is a design call.
HUMAN_GATE-REQUEST: approve the 5 helper modules and ApprovalKind.VIDEO_REVIEW with a D-entry, or direct the folds above.

DIFF SCOPE (4c): nothing deleted or renamed. The only removed lines are cli_crawl.py:212 and :237 (non-URL target note, help text), the enums.py docstring and EXPECTED_SITE_COUNT 21 -> 22 in test_cli_advice_resolves.py, all listed in the manifest. Unlisted but harmless: core/pricing.py (+15), core/paths.py (+6), prompts/video_review_v1.md.

FULL SUITE: not run at cycle 0 by maker instruction; owed at the repair check. My queued shard_suite was stopped while still waiting on the lock (held by another pid); no pytest or shard_suite process of mine remains.

PROPOSED-ISSUE: {"severity":"medium","feature":"team-video-review","title":"--output json emits nothing on stdout for exit 3 and exit 1","evidence":"src/autotester/cli_video_review.py:183-185,110-117,127,136,140"}  (P1, FAIL)
PROPOSED-ISSUE: {"severity":"high","feature":"team-video-review","title":"projects/*/reviews/<rid>/ (redacted.mp4 + PNG frames) persists and is not gitignored","evidence":"git check-ignore -v projects/x/reviews/rv-1/frames/a.png exit 1; stages/video_review.py:241; media/redacted.py:123,127"}  (P2, FAIL)
PROPOSED-ISSUE: {"severity":"medium","title":"no test for human status surviving a plain (non-refresh) re-run","evidence":"mutant video_review.py:235 survives, 40 passed"}  (P3)
PROPOSED-ISSUE: {"severity":"low","title":"TV7.3 original-path mutation caught only by the frames.origin attribute assertion","evidence":"media/redacted.py:123-124 mutant, 1 failed"}  (P4)
PROPOSED-ISSUE: {"severity":"medium","title":"TV8 quote scrub has no direct test; scrubbed-quote branch items.py:53 unprotected","evidence":"qa/evidence/t197-video-pointers-a/falsification.md rows TV8 a, TV8 g"}  (P5)
PROPOSED-ISSUE: {"severity":"medium","title":"redaction windows exist only as a CLI flag; Source stores none; no _original_unredacted guard in product code (test fake only)","evidence":"cli_video_review.py:149; grep src _original_unredacted empty"}  (P6)
PROPOSED-ISSUE: {"severity":"low","title":"no test plants a script tag in a pointer note or model reply for the HTML export (escaping exists at video_review_render.py:60-70); the markdown export does not escape HTML","evidence":"grep tests"}  (P7)
PROPOSED-ISSUE: {"severity":"low","title":"cost cap is soft by one batch; a provider with no usage data never binds it; --dry-run exits 1 without credentials","evidence":"stages/video_review.py:152; cli_video_review.py:137-140"}  (P8)
PROPOSED-ISSUE: {"severity":"medium","title":"contract amendment owed: TV9 :108 vs :111 contradict; TV7.1 gates on video.upload while spec.md:169 says project.edit + video.view; no carve-out for HELD parts","evidence":"qa/contracts/team-video-review.md:107-114,34-37"}  (P9)
PROPOSED-ISSUE: {"severity":"low","title":"manifest wording: core/pricing.py, core/paths.py, prompts/video_review_v1.md missing from What changed","evidence":"git diff --stat 09828f2d..3d0be650"}  (P10)

ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The built criteria pass on the maker's tests and on 21 falsifications, but two evidenced defects block: the JSON contract breaks on the refusal exits, and a run leaves redacted video and frames in a non-ignored in-repo path. Both are small fixes. slow: mutant copies 23 min.
Metrics: start=2026-10-11T08:21:22+05:30 end=2026-10-11T08:52:00+05:30 wall_min=26 agent_min=unavailable blocked_min=5 suite_runs=0 repeat_runs=0 mutations=23 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1840 mutants=13 defects_unit=2 defects_6c=0
