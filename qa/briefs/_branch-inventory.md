# Branch and worktree inventory (read-only pass, 2026-10-11)

Master = 4f8f5da1. `git branch --no-merged master` lists 30 branches; `git worktree list` lists 76 worktrees. Dirty = lines of `git status --short` in that worktree. D-080 item 1: dirty work in the three Codex worktrees (codex-ui-consistency, codex-live-product, codex-video-live) is not canonical; counts only, contents not read.

Path legend: `@/` means `D:/autoTesting/`.

Disposition words: LAND = holds a matching-cycle PASS and is not on master (see note for blockers); CONTINUE = unfinished work for a pending task; SUPERSEDED = its work is already on master by another route; UNKNOWN.

## Table 1: branches not merged into master

| Branch | Ahead | Behind | Last commit | Worktree | Dirty | Manifest / verdict, result, cycle | Disposition | Note |
|---|---|---|---|---|---|---|---|---|
| bk/master-pre-sync-1010 | 1 | 156 | 2026-10-07 | none | - | at113-crawl-completion cycle 4 PASS verdict is on master | SUPERSEDED | backup of pre-reset master; git cherry shows its 1 commit patch-equivalent on master and all 7 changed files are byte-identical on master |
| codex/at113-cycle1-preserved | 1 | 211 | 2026-09-30 | none | - | none (at113-crawl-completion is cycle 4 PASS on master) | SUPERSEDED | git cherry: its 1 commit is patch-equivalent to a commit on master (f9052150); name says cycle-1 snapshot |
| codex/at733-entry-cleanup | 1 | 183 | 2026-10-01 | C:/Users/Lenovo/.codex/worktrees/at733-entry-cleanup/autoTesting | 0 | at733-entry-cleanup, no verdict ever (superseded-by at733-bounded) | CONTINUE | task at733-bounded (qa/QUEUE.md:326); INPUT only. Private worktree clean. |
| codex/t153-completion | 4 | 9 | 2026-10-09 | @/.worktrees/codex-t153-completion | 9 | t153-completion manifest ready-for-check, fix cycle 1; no verdict | CONTINUE | task T-153 (pending); tier L, dual check required per its manifest |
| codex/t174-repair | 1 | 31 | 2026-10-07 | @/.worktrees/codex-t174-repair | 13 | t174-cli-mcp manifest ready-for-check, fix cycle 0; no verdict | CONTINUE | task T-174 (pending); same commit 7af87feb as branch t174 |
| codex/t202-completion | 3 | 12 | 2026-10-08 | @/.worktrees/codex-t202-completion | 1 | none for this branch; t202-litellm cycle 1 CONTINUE-NEEDED is the nearest | CONTINUE | task T-202 (pending); 123 files vs merge-base, so built on a stale base, re-land needed |
| integrate/combined | 8 | 13 | 2026-10-07 | @/.worktrees/combined | 0 | at780-pii a+b PASS cycle 0 @1856e5c4; at780-harden a+b PASS cycle 0 @84f3e522 | LAND | blocked: merged onto master it fails doctor (reconcile.py 302 lines) and qa/issues.jsonl conflicts; unit land-integrate-combined. The reviewed commits sit on base 7782df41, not on this merged head; the deferred full suite never ran on it |
| t152-153 | 2 | 31 | 2026-10-07 | @/.worktrees/t152-153 | 0 | t152-ai-check-registry (on master, T-152 done); t153-ai-behavioural-capture ready-for-check, no verdict | CONTINUE | task T-153; its T-152 commit is patch-equivalent on master (git cherry -), the one + commit is T-153 (97103cf3) |
| t174 | 1 | 31 | 2026-10-07 | @/.worktrees/t174 | 0 | t174-cli-mcp manifest ready-for-check, fix cycle 0; no verdict | CONTINUE | task T-174 (pending) |
| wave/at335-modal-determinism | 1 | 1033 | 2026-09-28 | @/.worktrees/at335-modal-determinism | 0 | at335-modal-determinism checked-PASS cycle 1 is on master (908c67d1) | SUPERSEDED | AT-335 status fixed; master has tests/test_explore_return_determinism.py; this branch is a wip that preserves the abandoned return-settle |
| wave/at758-759-security | 3 | 113 | 2026-10-07 | @/.worktrees/at758-759-security | 0 | at758-759-security a+b cycle 0 CONTINUE-NEEDED | CONTINUE | unit at758-759-security (AT-758 and AT-759 both open on master). Detached worktree @/.worktrees/at758-b-suite (b9ce7983, 5 dirty) is an earlier point of this branch |
| wave/at773-judge-rule | 3 | 44 | 2026-10-07 | @/.worktrees/at773-judge-rule | 0 | at773-judge-rule cycle 0 CONTINUE-NEEDED (single checker) | CONTINUE | issue AT-773 (open, high) |
| wave/at780-harden | 6 | 68 | 2026-10-07 | @/.worktrees/at780h | 0 | at780-harden a+b PASS cycle 0 @84f3e522 | LAND | contained in integrate/combined; lands with it, delete after |
| wave/at780-pii | 3 | 68 | 2026-10-07 | @/.worktrees/at780-pii | 0 | at780-pii a+b PASS cycle 0 @1856e5c4 | LAND | contained in integrate/combined; lands with it, delete after |
| wave/at787-bundle-wiring | 10 | 43 | 2026-10-07 | @/.worktrees/at787 | 0 | at787-bundle-wiring PASS cycle 1 @d06dcadd (cycle 0 PASS r0-1); manifest checked-PASS | LAND | blocked: stacked on wave/t177-agent-fallback (30 commits; manifest says merge T-177 first) and T-177 has an A FAIL at cycle 0; AT-787 still open on master |
| wave/g2-review-core | 3 | 56 | 2026-10-07 | @/.worktrees/g2-review-core | 0 | g2-review-core cycle 0 CONTINUE-NEEDED @f3587d5d; manifest now fix cycle 1 ready-for-check | CONTINUE | task T-197 (G2 video-review core) |
| wave/g3-zip-core | 1 | 56 | 2026-10-07 | @/.worktrees/g3-zip-core | 0 | g3-zip-core manifest ready-for-check cycle 0; no verdict | CONTINUE | task T-198 (G3 zip + Drive core), inferred from the G-numbering |
| wave/g5-schedule-core | 4 | 21 | 2026-10-07 | @/.worktrees/g5-schedule-core | 0 | g5-schedule-core manifest ready-for-check cycle 0; no verdict | CONTINUE | task T-200 (G5 schedule core), inferred |
| wave/g6-bug-core | 2 | 56 | 2026-10-07 | @/.worktrees/g6-bug-core | 0 | g6-bug-core cycle 0 CONTINUE-NEEDED; manifest ready-for-check | CONTINUE | task T-199 (G6 bug loop core), inferred |
| wave/pathlynks-exact-host | 1 | 179 | 2026-10-07 | @/.worktrees/pathlynks-exact-host | 0 | none | UNKNOWN | holds feat(secrets) 41ce907d: exact-host credential scope (not on master; master _host_matches is suffix match); no manifest or verdict names it; owner to say if wanted |
| wave/t125-catalog | 9 | 552 | 2026-09-27 | @/.worktrees/t125-catalog | 0 | t125-catalog cycle 3 FAIL/STALLED on branch; master has cycle 4 integration dual PASS | SUPERSEDED | T-125 is done; master carries it via 6c0d57a1 (merge of dual PASS cycle 4). Known by status, not by content (1 of 23 files identical) |
| wave/t177-agent-fallback | 6 | 68 | 2026-10-07 | @/.worktrees/t177 | 0 | t177-agent-fallback A FAIL / B PASS, cycle 0 | CONTINUE | task T-177 (pending) |
| wave/t177-followup | 7 | 68 | 2026-10-07 | @/.worktrees/t177f | 2 | t177-followup manifest ready-for-check, fix cycle 1; no cycle-1 verdict | CONTINUE | task T-177; dirty worktree @/.worktrees/t177f |
| wave/t196-citation-subjects | 5 | 43 | 2026-10-07 | @/.worktrees/t196-citation-subjects | 11 | t196-citation-subject-check Status BUILDING (same on master) | CONTINUE | task T-196 (pending); 11 dirty files |
| wave/t202-litellm | 5 | 65 | 2026-10-07 | @/.worktrees/t202-litellm | 0 | t202-litellm cycle 0 verdict (r0-1), then cycle 1 CONTINUE-NEEDED | CONTINUE | task T-202 (pending) |
| wave/t203-hosting | 6 | 68 | 2026-10-07 | @/.worktrees/t203-hosting | 0 | t203-hosting PASS (slice) cycle 1 @9a644597; cycle 0 FAIL | LAND | blocked per D-080: conflicts with master in ui/routes_runs.py and reuses AT-782..AT-793; unit land-t203-hosting. Verdict says the full suite was still running when written |
| wave/t204-auth | 4 | 68 | 2026-10-07 | @/.worktrees/t204-auth | 0 | t204-auth a+b FAIL cycle 0 | CONTINUE | task T-204 (pending) |
| wave/t204-auth-fix1 | 5 | 19 | 2026-10-07 | @/.worktrees/t204-fix1 | 0 | t204-auth manifest fix cycle 1 ready-for-check; verdict on branch is cycle 0 FAIL | CONTINUE | task T-204; same tip 886936ab as detached @/.worktrees/t204-b2 |
| worktree-agent-a6e53d091edaf9342 | 1 | 265 | 2026-09-28 | @/.claude/worktrees/agent-a6e53d091edaf9342 | 0 | at710-decision-citation-resolver HUMAN_GATE manifest (same Status text on master) | SUPERSEDED | AT-710 status fixed; gate new-module-authorization answered A 2026-09-29 (D-057); ledger/citations.py exists on master |
| worktree-agent-aca539b488be4c248 | 12 | 265 | 2026-09-28 | @/.claude/worktrees/agent-aca539b488be4c248 | 1 | t125-catalog cycle 3 FAIL; t125-test-catalog ready-for-check | SUPERSEDED | T-125 done on master (cycle 4 dual PASS, 6c0d57a1); this is the older build to recover |

Totals: SUPERSEDED 6, CONTINUE 18, LAND 5, UNKNOWN 1

- SUPERSEDED: bk/master-pre-sync-1010, codex/at113-cycle1-preserved, wave/at335-modal-determinism, wave/t125-catalog, worktree-agent-a6e53d091edaf9342, worktree-agent-aca539b488be4c248
- CONTINUE: codex/at733-entry-cleanup, codex/t153-completion, codex/t174-repair, codex/t202-completion, t152-153, t174, wave/at758-759-security, wave/at773-judge-rule, wave/g2-review-core, wave/g3-zip-core, wave/g5-schedule-core, wave/g6-bug-core, wave/t177-agent-fallback, wave/t177-followup, wave/t196-citation-subjects, wave/t202-litellm, wave/t204-auth, wave/t204-auth-fix1
- LAND: integrate/combined, wave/at780-harden, wave/at780-pii, wave/at787-bundle-wiring, wave/t203-hosting
- UNKNOWN: wave/pathlynks-exact-host

## Table 2: removal candidates (detached HEAD or merged branch, clean tree)

Only the owner or the maker removes these, later. A detached worktree whose SHA is held by a branch has no unique commits.

| Worktree | Branch / HEAD | State | Why it is a candidate |
|---|---|---|---|
| C:/Users/Lenovo/.codex/worktrees/goal-continuation/autoTesting | DETACHED ff7f4ff2 | clean | detached HEAD is an ancestor of master |
| C:/Users/Lenovo/.codex/worktrees/t174-verification/autoTesting | DETACHED 7af87feb | clean | detached HEAD, SHA also held by branch codex/t174-repair, t174 |
| @/.claude/worktrees/agent-a34c44eb5901959f8 | worktree-agent-a34c44eb5901959f8 | clean | branch is an ancestor of master |
| @/.worktrees/at-crawl-hang | wave/crawl-live-hang | clean | branch is an ancestor of master |
| @/.worktrees/at113-integrate | integrate/at113 | clean | branch is an ancestor of master |
| @/.worktrees/at757-timing | wave/at757-timing | clean | branch is an ancestor of master |
| @/.worktrees/at779 | wave/at779-ingest-narration | clean | branch is an ancestor of master |
| @/.worktrees/at784 | wave/at784-ingest-transcripts | clean | branch is an ancestor of master |
| @/.worktrees/bk-1007 | bk/ledger-reconcile-1007 | clean | branch is an ancestor of master |
| @/.worktrees/codex-t152-release | codex/t152-release | clean | branch is an ancestor of master |
| @/.worktrees/d-answers | docs/d-answers-1007 | clean | branch is an ancestor of master |
| @/.worktrees/d-tz | wave/d-tz | clean | branch is an ancestor of master |
| @/.worktrees/d063-grant-budget | wave/d063-grant-budget | clean | branch is an ancestor of master |
| @/.worktrees/d074-followups | wave/d074-followups | clean | branch is an ancestor of master |
| @/.worktrees/dockerignore-secrets | wave/dockerignore-secrets | clean | branch is an ancestor of master |
| @/.worktrees/g3-b | DETACHED ac7df298 | clean | detached HEAD, SHA also held by branch wave/g3-zip-core |
| @/.worktrees/g3-b-base | DETACHED c09debd1 | clean | detached HEAD is an ancestor of master |
| @/.worktrees/land-1010 | integrate/land-1010 | clean | branch is an ancestor of master |
| @/.worktrees/reconcile | wave/reconcile | clean | branch is an ancestor of master |
| @/.worktrees/t122-first-login-run | wave/t122-first-login-run | clean | branch is an ancestor of master |
| @/.worktrees/t122-first-run | wave/t122-first-run | clean | branch is an ancestor of master |
| @/.worktrees/t125-integrate | integrate/t125 | clean | branch is an ancestor of master |
| @/.worktrees/t136-bench | wave/t136-bench | clean | branch is an ancestor of master |
| @/.worktrees/t153-checkB | DETACHED 97103cf3 | clean | detached HEAD, SHA also held by branch t152-153 |
| @/.worktrees/t166 | wave/t166-eval-compiler | clean | branch is an ancestor of master |
| @/.worktrees/t174-checkB | DETACHED 7af87feb | clean | detached HEAD, SHA also held by branch codex/t174-repair, t174 |
| @/.worktrees/t176-script-replay | wave/t176-script-replay | clean | branch is an ancestor of master |
| @/.worktrees/t178 | wave/t178-failure-bundle | clean | branch is an ancestor of master |
| @/.worktrees/t190-ux | wave/t190-ux | clean | branch is an ancestor of master |
| @/.worktrees/t204-b2 | DETACHED 886936ab | clean | detached HEAD, SHA also held by branch wave/t204-auth-fix1 |

Candidates: 30.

## Dirty worktrees that are not candidates (count only)

| Worktree | Branch | Dirty |
|---|---|---|
| C:/Users/Lenovo/.codex/worktrees/live-product-integration/autoTesting | DETACHED | 172 |
| C:/Users/Lenovo/.codex/worktrees/t136-bench-provenance/autoTesting | DETACHED | 4 |
| @/.claude/worktrees/agent-aca539b488be4c248 | worktree-agent-aca539b488be4c248 | 1 |
| @/.worktrees/at113-crawl-completion | codex/at113-crawl-completion | 2 |
| @/.worktrees/at758-b-suite | DETACHED | 5 |
| @/.worktrees/codex-batch-foundation | codex/batch-foundation | 94 |
| @/.worktrees/codex-live-product | codex/live-product | 362 |
| @/.worktrees/codex-t152-check | DETACHED | 4 |
| @/.worktrees/codex-t153-completion | codex/t153-completion | 9 |
| @/.worktrees/codex-t174-check | DETACHED | 2 |
| @/.worktrees/codex-t174-final-a | DETACHED | 10 |
| @/.worktrees/codex-t174-final-b | DETACHED | 10 |
| @/.worktrees/codex-t174-repair | codex/t174-repair | 13 |
| @/.worktrees/codex-t178-completion | codex/t178-completion | 23 |
| @/.worktrees/codex-t196-completion | codex/t196-completion | 12 |
| @/.worktrees/codex-t202-completion | codex/t202-completion | 1 |
| @/.worktrees/codex-ui-consistency | codex/ui-consistency | 419 |
| @/.worktrees/codex-video-live | codex/video-live | 553 |
| @/.worktrees/t125-cycle4 | codex/t125-cycle4 | 5 |
| @/.worktrees/t151-target-discovery | codex/t151-target-discovery | 10 |
| @/.worktrees/t167 | wave/t167 | 24 |
| @/.worktrees/t177f | wave/t177-followup | 2 |
| @/.worktrees/t196-citation-subjects | wave/t196-citation-subjects | 11 |

Root D:/autoTesting is itself dirty (29 files, other agents working); not listed above.
