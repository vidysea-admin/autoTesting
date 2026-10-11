# Verdict - at887-crawl-to-flows, repair check, coordinator A (blind dual check)

Cycle checked: 1
Bound to: D:/autoTesting. Head b3a365a1 (product 54dced40), Repair base 6d70c0ec (ancestor of head, verified with git), merge-base with master 3748cb83.
Policy-Version: proportional-verification/2026-10-10.9. Checkpoint: qa/checkpoints/at887-crawl-to-flows.r1.a.md. Evidence: qa/evidence/at887-crawl-to-flows-r1-A/.
Date: 2026-10-12. No earlier verdict, checkpoint or evidence of this unit was opened; no `.b` / `-B` file was read.

## Check plan
Tier L (dual trigger cited: security src/autotester/stages/expand.py:183). Repair-scoped: re-run F1..F3 plus criteria whose input files the repair diff touches (X13, X12, X6, C5, C2); read the repair diff in full (9 files, 270 insertions); scan the whole-unit diff for out-of-scope files; one falsification per repaired item; affected tests; one full suite (A owes 1).
Lane check not applicable (cycle 1; `--lane-check` says lane-disabled). No UI surface changed (the only UI file changes are an `except` clause and a message): no browser run, no persona walk. SERIAL: none needed, steps were independent copies.

## Block
VERDICT: PASS
SCOREBOARD: 3/3 repaired items met (F1, F2, F3), 4/4 added test gaps closed, 0 invariants broken (C2 files <= 300 and functions <= 50, ruff and doctor clean; C5 holds)
TIER: L (security trigger: new secret/PII gate before provider.act at expand.py:183)
FAILURES: none

## Per-item results
- F1 MET. `explore_merge.py::_rediscovered_ids` applies the same test as `merge_screens` (`incoming.id not in known`, same `by_pattern`, `_is_rediscovery`) and `merge_screens_and_flows` rewrites the proposed flows with `screen_identity.rewrite_screen_refs` after the flow id is computed from the crawl node ids. Probe (`f1-probe.txt`, `f1-ui-probe.txt`): with a spec seeded with matching human screens, `dangling_references == []` after the CLI door, the UI door and orchestrated DISCOVER+MODEL; CLI and UI flows are identical; flow ids equal the fresh-spec ids; flows with no rediscovery are byte-identical to the fresh-spec flows; a re-crawl under a new crawl id adds no flow and no version bump; version bumps once and review is DRAFT with by None.
- F2 MET. `routes_learn.py:255` catches `(ProviderError, ValueError)`; a guard refusal is a themed 400 (title and next-action link), no case written, provider spy saw no refused prompt, neither the secret nor its base64 spelling is in the page, and no file under the project root changed during the POST (`f2-f3-probe.txt`, before/after tree hash). With two flows the first flow's clean prompts (12) were already sent, which is the existing "partway through" behaviour; the refused prompt was not.
- F3 MET. `expand.py::build_expand_prompt` masks each step line, then joins; the flow name is masked separately. Full lines for steps 1..5 with a phone or email in the value, in the target and in a trailing position: ordinals 1..5 intact and each line starts with its own ordinal (`'4. fill note <phone> = see <phone>'`); header line `## Original flow: Phone <phone> / <email>`; `{{SECRET:ST_PASS}}` untouched. Forms masked: +91 spaced, bare 10-digit, (022) 2345 6789, +919876543210, 91-98765-43210, tel:+..., upper-case and plus-addressed emails, mailto:.
- Added tests: version bumps exactly once (m4 mutant red), flows-only merge is DRAFT with by/at empty, a real A-B-A cycle yields no flow, the `compile_evals` spy sees the scrubbed prompt only: all in the 340 passed.
- AT-887 stays OPEN: the manifest does not claim to close it ("AT-887 clause 2 ... NOT built", "stay open until the checker decides"). My ruling: clause 2 (pre-run reachability warning) is unbuilt, so AT-887 must not close on this unit. AT-890 can close once both coordinators PASS.

## Rulings asked for
- Orchestrated door: SAFE, not merely untested. DISCOVER calls `merge_screens_and_flows(None, ...)`, so there is nothing to rediscover and no alias; the MODEL fold (`merge_flowspec._new_screens`) then adds the node-id screens the flows cite. Probe G: dangling == [], and a second orchestrated run is a no-op. The builder's door test passes with and without the fix (mutant fz1 leaves it green), so it guards the door and does not prove the fix; the three other tests that go red prove it. Side effect, pre-existing and untouched: that fold leaves a same-name node-id screen beside the human one at one pattern (`G: screens in folded`).
- Two crawl nodes mapping to the SAME existing screen: no collapse, no duplicate steps. Home > Items(A) > Items(B) with Items(A) and Items(B) both aliased to `scr_items` gives 3 steps with orders 1..3 and the targets unchanged, entry `scr_home`, exit `scr_items`; flow id unchanged. A flow landing on Items(A) and clicking to Items(B) would get entry == exit == `scr_items` with its steps intact, which is a valid screen-level self-edge, not a collapse.
- A rediscovered node that is a flow's entry AND exit (single-node crawl): entry, exit and the one step all cite `scr_home`; no dangling; version +1 once; DRAFT.
- F2 breadth: YES, `except (ProviderError, ValueError)` swallows unrelated ValueErrors (pydantic ValidationError is one) and labels them "a prompt was refused unsent", with nothing logged (probe: an injected `ValueError("programming error...")` returns 400 with that text). Before the repair they were raw 500s. Not a FAIL: X6 asks for a themed page not a 500, no secret or prompt is echoed, nothing is written, and the reachable ValueErrors in `expand` are the proposal-staging checks already tested before this call. PROPOSED-ISSUE P1.
- F3 `%40`: the criterion as written (AT-890 expected: "Expand prompts pass mask_pii_obj (and guard_prompt) before provider.act, pinned by a test") does not require URL-encoded emails; `ada%40example.org` and `ada [at] example.org` pass through unmasked, as the builder disclosed. Not a FAIL. P2.
- Limits: routes_learn.py 300, cli_crawl.py 300, explore_merge.py 246, expand.py 219, explore_flows.py 92, tests <= 247; ruff and `autotester doctor` clean. Out-of-scope scan of `3748cb83..b3a365a1`: all 14 files are named in the manifest; nothing deleted or renamed.
- Manifest wording: it says the falsification copy was deleted while the caller reports it remains on C:. Low wording finding, not a FAIL (P3).

## Falsifications (each in its own copy of the archive, PYTHONPATH at the copy, import path confirmed, green before then red after)
- X13c drop `rewrite_screen_refs`: 31 passed -> 4 failed (CLI door, UI door, flow-id test, model-level rediscovery test).
- X6 narrow the except to ProviderError: 1 passed -> 1 failed (`test_a_guard_refusal_is_a_themed_400...`).
- PII2 mask the joined text: 23 passed -> 1 failed (`test_a_phone_at_the_end_of_a_step_does_not_swallow_the_next_step_number`).
- Beyond the floor (cap 10 at L): m4 always bump version -> 1 failed (bumps exactly once); m5 negate the rediscovery condition -> 4 failed.

## Full suite (A owes 1): `shard_suite.py --ref b3a365a1 --shards 4`
3563 collected (collect proof ok), 3539 passed, 4 failed, 20 skipped. Failures:
- test_redact_wrap_perf (...500kb_corpus) and test_mc_sessionstart_loop_status (...healthy_log): on the load-sensitive list.
- test_hosting_deploy::test_env_example_documents_every_key_the_code_reads: also red on the merge base 3748cb83 with the same message (undocumented AUTOTESTER_SCHEDULE_GRACE_MINUTES, AUTOTESTER_TICK_INTERVAL_S), so not new. P4.
- test_hosting_config::test_healthz_source_root_is_the_package...: under the sharded runner the spawned interpreter imported `D:/autoTesting/src/autotester` (the editable install in the D venv) while pytest imported the shard copy; it passes in a self-contained copy of the same ref, and neither routes_live.py nor anything it imports from the unit changed. A merge-base shard run to show it red there was BLOCKED-PROCESS: suite lock held 15 min by another session (pid 46492, not ours; never touched). Judged environmental, not attributable to this unit. P5.
No other failure. suite_runs=1.

## PROPOSED-ISSUEs
PROPOSED-ISSUE: {"severity":"low","feature":"expand","title":"routes_learn.py:255 except (ProviderError, ValueError) labels any ValueError (incl. pydantic ValidationError) 'a prompt was refused unsent' and logs nothing","evidence":"qa/evidence/at887-crawl-to-flows-r1-A/f2-f3-probe.txt UNRELATED-VALUEERROR; src/autotester/ui/routes_learn.py:255","fix_direction":"raise a dedicated PromptRefused(ValueError) from guard_expand_prompt and catch that; log the rest"}
PROPOSED-ISSUE: {"severity":"low","feature":"expand","title":"mask_pii leaves URL-encoded (%40) and '[at]' spelled emails unmasked in expand prompts","evidence":"f2-f3-probe.txt F3-FORM lines; core/redact.py mask_pii","fix_direction":"decode percent-escapes before masking in build_expand_prompt, or extend _mask_emails"}
PROPOSED-ISSUE: {"severity":"low","feature":"at887-crawl-to-flows","title":"wording: manifest says the falsification copy was deleted but it remains on C:; manifest Metrics line lacks the .9 fields and the Pre-check lines carry no t=/blobs= (not reusable under .9-5, all re-run)","evidence":"qa/manifests/at887-crawl-to-flows.md","fix_direction":"amend the wording; add t= and blobs= to pre-check lines"}
PROPOSED-ISSUE: {"severity":"low","feature":"hosting","title":"test_env_example_documents_every_key_the_code_reads red on master base: AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S missing from .env.example","evidence":"qa/evidence/at887-crawl-to-flows-r1-A/suite-reds-on-mergebase.txt (red at 3748cb83)","fix_direction":"document both keys in .env.example"}
PROPOSED-ISSUE: {"severity":"low","feature":"checker-tooling","title":"test_healthz_source_root_is_the_package fails under shard_suite because the child interpreter imports the D venv editable install, not the shard copy","evidence":"suite-summary.json failed list; shard-0.log assertion D:/autoTesting/src/autotester vs shard-0/src/autotester","fix_direction":"have shard_suite export PYTHONPATH to the shard copy src, or xfail the test under the runner"}
PROPOSED-ISSUE: {"severity":"low","feature":"explore","title":"orchestrated MODEL fold leaves a same-name node-id screen beside the human screen at one url_pattern (AT-102 duplicate), pre-existing and not changed by this unit","evidence":"f1-probe.txt G: screens in folded","fix_direction":"apply _is_rediscovery in merge_flowspec._new_screens"}

CAPABILITY-COVERAGE: 5/5 falsifications reproduced (3 floor, 2 extra)
LIVE-BROWSER: not-applicable (changed UI path is an except clause and message in ui/routes_learn.py; exercised through TestClient)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All three cycle-0 failures are fixed and each has a test that goes red when the fix is reverted. The orchestrated door is safe by construction, the unit leaves AT-887 open, and the four suite reds are load-sensitive (2), pre-existing on the merge base (1) or a shard-runner environment artifact (1). Two flagged limits (broad ValueError catch, %40) are non-blocking.
Metrics: start=2026-10-12T01:06:57+05:30 end=2026-10-12T01:58:00+05:30 wall_min=36 agent_min=unavailable blocked_min=15 suite_runs=1 repeat_runs=0 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3060 mutants=2 defects_unit=0 defects_6c=0
