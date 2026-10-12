# AT-887 hostile attack, sub-checker A (commit 6d70c0ec, worktree check-at887-a)

Scripts (scratchpad .../scratchpad/at887/): h1_pure.py (37 pass / 2 fail), h2_merge.py (20 pass / 1 fail),
h3_doors.py (16 pass / 0 fail), h4_leak.py. Run as
`uv --directory D:/autoTesting/.worktrees/check-at887-a run python <script>` (module file confirmed = worktree).
Builder tests (test_explore_flows, _doors, test_explore_merge): 39 passed.

| Property | Result | Evidence |
|---|---|---|
| P1 deterministic | PASS | shuffle x20 of nodes+edges byte-identical incl. list order (h1); 3 PYTHONHASHSEEDs same sha1; module imports no clock/random/provider |
| P2 existing id never overwritten | PASS | h2: human-edited same-id flow byte-identical after merge that adds another flow |
| P3 DRAFT + version once | PASS | h2: screen+flow v7->8; only-screen v8 (not 9); only-flows v4; None spec v2; APPROVED/NEEDS_EDIT -> DRAFT, by/at None; nothing new -> SAME object, APPROVED, v7 |
| P3 byte-identical persisted | PASS | h3: CLI, UI, MODEL stage re-merge flowspec.json bytes equal |
| P4 skip, not guess | PASS | FILL/SELECT/BACK/HOVER/PRESS_KEY/UPLOAD/SCROLL/WAIT/ASSERT, 6 non-NAVIGATED outcomes, missing edge, missing parent, 2-cycle, self-loop all produce no flow ending at that node; 13-edge chain dropped, 12-edge kept |
| P5 merge_screens unchanged | PASS | diff vs 3748cb83 = only added blank lines; 30 random trials equal (created_at excluded) |
| P6 no case without approve | PASS | expand/propose_cases/expand_flow raise FlowSpecNotReviewed, provider calls = 0; after approve still ValueError "human approval of HAPPY proposal required"; after approve + stage_and_review expand yields 10 cases. Second gate (case-proposal approval) exists in the code |
| P7 three doors | PASS | CLI, UI POST (303), DISCOVER (+MODEL) each: 1 flow, Typed (FILL) path skipped, DRAFT, v6, re-run byte-identical. UI/CLI of APPROVED spec with nothing new stays APPROVED |
| Flow validity | PASS w/ DEFECT-1 | orders 1..n, extra=forbid roundtrip ok, entry/exit in spec.screens in normal case; FlowSpec has no validator for screen refs |

## DEFECTS
D1 (medium): dangling Flow.entry_screen / exit_screen / Step.screen_id. merge_screens skips a crawled screen as
`_is_rediscovery` (existing NON-structural screen, same url_pattern + same name, e.g. a video/human "Home" at /h),
but flows_from_crawl still uses the NODE id. Repro h2_merge.py "rediscovered human screen":
`DANGLING steps=[('crawl path: Home > T', 1, 'node_bf4873fbda6c'), ... 2 ...] entry=[(... 'node_bf4873fbda6c')]
screens=['human_home', 'node_c30168f34edb']`. Nothing validates it, so the dangling flow is saved as a DRAFT proposal.
Same-name-different-name case (conflict) is fine (screen added).
D2 (low): flows_from_crawl is input-order dependent when two nodes share an id with differing name, or two edges share an id with
differing outcome (h1: `['crawl path: D2']` vs reversed `['crawl path: D1']`; edge dup: `Home` vs `Home > T`). Not reachable via the
store (crawl_store.add_node is idempotent on id), only by direct calls.

## SURPRISES / reviewer notes
S1: Step.target for step 1 is the raw `url_example` incl. query string; Flow.name and click targets carry node names and edge selectors verbatim.
h1/h4: `?token=...SESSIONSECRET` reaches Step.target and the expand prompt text (mask_pii only masks emails/phones; guard_prompt only
declared .env secrets). Email in edge.target / node.name: verbatim in Step.target and Flow.name in stored spec (h1), masked to `<email>` in the
expand prompt (h3: prompts=9 leaks=0); happy Case keeps the raw email in stored steps. Crawl-derived text is NOT sent to a provider before
expand's mask. A `sk-ant-...`-looking edge.target is not masked (only declared secrets are).
S2: When a leaf is skipped (typed/failed/too long), its nearest valid ancestor becomes a leaf flow (typed edge: "crawl path: Home";
14-chain: ends at S12). Acceptable but it is a shorter proposal not an omission.
S3: A flow id already present wins forever: a later merge with login_case_id does not set requires_auth/preconditions on the existing
flow (h2: requires_auth stays False, nothing changes, v unchanged).
S4: Flow id ignores crawl id (same path in 2 crawls = same id, no duplicate, spec object returned) but step source_ref.locator differs per crawl (edge ids include crawl_id); first crawl's provenance is kept.
S5: Nodes with status QUEUED/ABORTED_ERROR are not filtered; a discovered-but-unexplored leaf still yields a flow.
S6: explore_flows.py docstring cites `explore_merge.merge_crawl`, which does not exist (the UI route is routes_crawls.merge_crawl; function is merge_screens_and_flows).
S7: MODEL stage (merge_flowspec) on an APPROVED spec with the same proposal re-run: stays APPROVED, bytes equal (nothing new); with new content it goes DRAFT.

## Other callers
`merge_screens(` callers in src/ and scripts/: only explore_merge.py:156 (def) and :195 (inside merge_screens_and_flows). No door skips flows.
Doors: cli_crawl.py:125/128 (merge_stored_crawl), ui/routes_crawls.py:30/279, orchestrate_runners.py:30/101 (live caller cli_orchestrate.py:110/149).
Other crawl->spec merges: none found (portal_persona.py merges nodes into the persona, a separate artifact; cli_video.py:161 merges video, not crawl).
