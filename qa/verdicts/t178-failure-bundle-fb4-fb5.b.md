# Verdict, coordinator B (blind dual check), t178-failure-bundle-fb4-fb5
Cycle checked: 0 · Commit: a7d3fa6c (product bb76275f) · Policy-Version: proportional-verification/2026-10-10.9 · Date: 2026-10-11
Dispatch: resumed after a session-limit cut (Resume: 1); judged the same commit in git-archive copies.

## Plan
Tier L via the cited trigger `security src/autotester/stages/failure_bundle.py:211` (dual check). Checks: FB4 and FB5 end to end;
one falsification each in its own copy plus two for containment; own adversarial pass (path containment, secrets, priority filter);
step 4c full-diff read (21 src files, delegated to a read-only sub-checker, findings spot-checked); affected tests, ruff, doctor.
No full suite and no browser or persona walk here (coordinator A owns both).

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (FB4, FB5), containment amendment holds, invariants C2 (doctor clean) and C5 (no new bundle writer) hold
TIER: L (security: line-211 path containment in load_bundle; queue plumbing for QueueEntry.priorities)
FAILURES: none
CAPABILITY-COVERAGE: 4/4 falsification rows reproduced in own copies (FB4, FB5, containment x2), each red on its named assertion
LIVE-BROWSER: not-applicable here (coordinator A owns the browser and persona walk for the Learn page and ?priority=)
ISSUES-WRITTEN: none (dual check, PASS has no side effects)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## FB4 (met)
60 tests green (test_schema, test_store, test_pinned_regression, test_ui_runs). Four fixture cases, one per priority: `list_cases(["p0"])` returns the p0 case plus pinned, count asserted;
`delete_case` on a pinned case raises PinnedCaseError; a row saved without `priority` loads as `p2` with an unchanged id; `p4` is rejected (`extra="forbid"`, Literal).
Falsify: filter forced `if True` -> test_store priority node and both test_ui_runs priority nodes red (3 passed -> 3 failed, id-list inequality).

## FB5 (met)
61 tests green (test_expand, test_expand_cli, test_ui_learn, test_eval_compiler). Counting fake provider: 5 non-HAPPY proposals, 3 pruned -> exactly 2 prompts; all pruned -> 0; no approval recorded -> 0 and ValueError.
Only one production path reaches `provider.act(... ExpandedSteps)` (expand.py:146), and it is reached only through `_reviewed_batch` / `preflight_case_proposals` (grep over src and scripts). No auto-approve path exists: `review_case_proposal` is called only from the CLI `--approve/--prune` door.
Falsify: `approved_batch` lets pruned rows through -> `assert 5 == 2` and `assert 5 == 0`.

## Containment (holds)
87 tests green. Own mutants: dropping `is_relative_to(root)` -> "escaped file reached hashing/read"; dropping `".."` from the validator -> `[../outside]` red.
Adversarial results (evidence dir): 33 hostile names, 5 absolute/UNC/drive spellings of a hash-matching decoy, NTFS junctions (parent, decoy, mixed case, chained), a junction and an 8.3 short name onto a `.partial` bundle,
a run id with separators: none read or hashed outside the bundle, none wrote outside out_dir. Names that load (`CASE.JSON`, `case.json.`) resolve to the in-bundle file.
Priority filter: 10 malformed `?priority=` forms all 422 with no run created; absent filter = every case; four presses with four filters each ran exactly their own set; an old queue row loads with `priorities=None`.

## Step 4c
Whole diff 3d8f7d5a..a7d3fa6c read: nothing deleted or renamed besides non-code section banners and docstring compaction in project_store.py (299 lines). No assertion removed or weakened in the eight extended test files (edits add `tmp_path` / `store=` arguments only).
The AT-239, AT-260, AT-264 rationale edits are comments; the cli.py `expand` message wording, the review gate running before the credentials check and the merged `except` are behaviour changes inside this unit's FB5 scope, and the CLI tests still assert the phrases they need. `with_fixed_step` now keeps pinned/priority/issue trace (supports FB4). Doctor and ruff clean.

## Findings (none blocks; none in FB4/FB5 code paths)
PROPOSED-ISSUE: {"severity":"medium","feature":"failure-bundle","type":"security","title":"trace.jsonl keeps a secret containing a control character in JSON-escaped form","evidence":"stages/failure_bundle.py:_write_parts scrubs the text of sp.model_dump_json() after serialising; a secret with a newline or tab appears as `ab\\ncd1234` in trace.jsonl and assert_clean does not catch the escaped form. Repro: tests/test_attack_b.py::test_trace_leak_minimal[ab\\ncd1234] prints LEAK ['trace.jsonl'] (evidence dir). Quote and backslash secrets fail closed, plain and <&> secrets are clean. Pre-existing FB3 code, unchanged by this unit; build_failure_bundle has no production caller yet (wave/at787-bundle-wiring), so it is latent.","fix":"scrub_obj on the span dict before json.dumps, as _dump does; fix before the wiring lands"}
PROPOSED-ISSUE: {"severity":"low","feature":"eval-compiler","type":"fb5-spend","title":"compile_evals preflights per flow, so approved flows spend before a later pending flow refuses","evidence":"eval_compiler.py:107 calls expand_flow per flow (flow_id preflight only); with flow A approved and B pending, test_compile_evals_partial_spend counts 12 provider calls then ValueError and no result. No unapproved proposal reaches the provider, so FB5 as written holds; expand() preflights all flows first and compile_evals has no production caller.","fix":"preflight every traced flow before the first expand_flow call"}
PROPOSED-ISSUE: {"severity":"low","feature":"failure-bundle","type":"secret-in-filename","title":"a secret in a screenshot source suffix becomes an on-disk file name","evidence":"_write_parts uses src.path.suffix for `screenshots/N-n<suffix>`; the manifest is scrubbed so load_bundle then refuses with 'invalid bundle manifest', but the file name on disk holds the secret (tests/test_attack_b.py::test_suffix_load). Runner-generated names make it unreachable today.","fix":"derive the suffix from an allow-list (.png, .jpg, .webp)"}
PROPOSED-ISSUE: {"severity":"low","feature":"failure-bundle","type":"approval-integrity","title":"proposal approval is attribution only","evidence":"CaseProposal.reviewed accepts any non-blank name and case_proposals.jsonl rows carry no signature (RunApproval uses an HMAC); a hand-edited row with a recomputed id passes. Same trust level as editing cases.jsonl; no code path forges one.","fix":"decide with the owner whether proposal rows need the RunApproval HMAC"}
Builder-proposed issues (zero-match filter says "no cases", priority not editable in the UI, three files at the 300 cap) are accepted as written. Nothing assigns a non-p2 priority to generated cases yet, so `?priority=p0` runs only pinned cases.

EXPLANATION: FB4 and FB5 are evidenced by my own runs and falsified in separate copies; the load_bundle containment holds against every traversal, absolute, UNC, junction and 8.3 variant tried, and the priority filter cannot run cases it should not. The one security-class finding (P1) sits in unchanged FB3 code that is not yet wired to production, so it is a PROPOSED-ISSUE the maker should schedule before the at787 wiring, not a reason to fail this unit.
Metrics: start=2026-10-11T02:18:04+05:30 end=2026-10-11T05:34:00+05:30 wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
