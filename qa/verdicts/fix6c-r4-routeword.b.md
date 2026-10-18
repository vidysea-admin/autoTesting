# Verdict - fix6c-r4-routeword (coordinator B, dual check)

**Verdict:** PASS
**Cycle checked:** 0
**Checked state:** Head 3045e909 (code 58c0361e), base 58e13d6b, branch wave/fix6c-r4-routeword
Policy-Version: proportional-verification/2026-10-18.15 · Tier L (dual-trigger security src/autotester/schema/leak_evidence.py:53, line read: `segment_is_id_like` returns True unless the segment is a placeholder or in ROUTE_WORDS)
Lane: normal (Lane exit: none claimed; quick lane off) · Invariants: [MPI1] checked, [I*] none other touched
SERIAL: affected run, three mutant copies and probe ran one after another (no shared-resource parallelism needed; run took 21 s).

## Plan (step 0)
Diff = 1 src (+2 lines, 11 words), 3 test files (additive), 1 manifest. Checks: (1) read full diff vs base; (2) security probes on the predicate; (3) affected tests; (4) one falsification per criterion F1/F2/F3; (5) protected-test-change review; (6) ruff + doctor.

## Diff scope (4c)
`git diff 58e13d6b 3045e909 --name-only` = leak_evidence.py, test_leak_evidence.py, test_leak_url_ids.py, test_oracle_responsive.py, the manifest. No core/image_privacy.py, no qa/contracts, no stages/unified_report.py (A3 held), no schema/multi_role_enums.py (MPI3 held). Test diffs are pure additions (+4, +4, +8, no `-` lines): no assertion removed or weakened, no skip/xfail, no threshold. Protected-change justification: the two patches only isolate the environment (WINDOWS_TESSERACT, TESSERACT_ENV, repo_root; all three names exist in core/image_privacy.py:36-38, :25 and are the exact inputs `_find_tesseract` at :59-65 reads). The new test adds scrutiny.

## Security probes (evidence: qa/evidence/fix6c-r4-routeword.b/probe.py, run in a copy of 3045e909)
- Leak never un-reported: the predicate is used only to template or refuse a URL (stages/leak_evidence.py:82, stages/platform_links.py:209, validate_url_template :63); it decides no finding. Adding words can only turn a previous refusal/`{id}` into a kept literal, never suppress a finding. A planted canary sweep (tests/test_leak_evidence.py, test_leak_url_ids.py) stays green.
- Real values stay templated or refused: `/inbox/alice`, `/inbox/zorblax-quimby`, `/inbox/jsmith`, `/inbox/alice.smith`, `/mail/alice@x.com`, `/mail/4821`, uuid-like `/mail/9f8a...`, ObjectId `/quiz/507f...`, `/cart/sk_live_abc`, `/me/john.doe`, `/item/jsmith`, `/inbox/%61lice`, `/mail%2Falice`, `/inbox;alice`, `/api/status/ab12`: all become `{id}` in templatise_url and all are REFUSED by validate_url_template; query values stay `{value}`. Matching is whole-segment, so `status.x`, `me@x` or `me123` never match a word.
- Residual (non-blocking): a segment that is exactly one of the 11 words is now kept literally: `/users/me`, `/users/Me/orders`, `/status`, `/ME`, `/status/me/mail/cart`. A tenant slug or username literally spelled `me`, `mail`, `status`, `inbox`, `cart`, `quiz`, `item` would be kept in a URL template. This is the same exposure the existing list already accepts for `test`, `user`, `school`, `career`, `task`, and such a word names a role/route, not a person; `me` is the standard current-user alias. Not a defect in the changed code, so no FAIL (reviewer scope). Filed as a low PROPOSED-ISSUE; AT-1033 (per-project route vocabulary) is the fix.
- Pre-existing, unchanged by this diff (same on base): `//inbox` has no scheme so urlsplit takes `inbox` as host and the template becomes `''`; harmless for MPI1 (drops, never keeps).

## Criteria
- F1 PASS. Affected run on 3045e909: `uv run --directory <wt> pytest tests/test_oracle_state_after.py test_state_probe_schema test_oracle_answer_key test_oracle_copy_lint test_network_oracles test_leak_evidence test_oracle_responsive test_leak_url_ids test_leak_repro_replay test_platform_links test_oracle_credential_policy test_multi_role_schema test_negative_input_oracle test_image_privacy test_image_privacy_engine` -> 376 passed (evidence: affected-run.txt). Falsification[F1]: copy with the 11 words removed (autotester imported from the copy, verified by `__file__`) -> 39 failed, 139 passed across the 6 named files; green before, red after, restored (HEAD copy not touched).
- F2 PASS. The two named tests pass on this machine (Tesseract installed at the Windows path) in the affected run. Falsification[F2]: base versions (git show 58e13d6b) of the two test files, run against the HEAD source in a copy -> exactly the two named tests FAIL (OCR ran), 17 passed. So the base tests were non-hermetic and the patches are the whole fix; `core/image_privacy.py` untouched.
- F3 PASS. test_leak_url_ids.py: 42 pass on HEAD. Falsification[F3]: copy with `"alice", "zorblax-quimby"` added to ROUTE_WORDS -> the new test and the 3 `[unknown-word]` id-format cases go red (4 failed, 38 passed), i.e. the refuse half is held by tests, as is the keep half by F1's mutant.
- MP7-MP10, A3, MPI1-MPI6: MP9/MPI1 (no third-party PII on disk) untouched in kind: canary tests green, evidence fields unchanged; MP7/MP8/MP10 files not in diff; A3/MPI3 held by the name-only diff.
- Lint: `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> clean (2 advisory known-disputed D-087 notes, non-blocking). leak_evidence.py is 104 lines (<=300).

## Findings
PROPOSED-ISSUE: {"severity":"low","kind":"hardening","feature":"fix6c-r4-routeword","title":"ROUTE_WORDS keeps a segment literally when a tenant slug or username equals a route word (me, mail, status, inbox, cart, quiz, item); per-project vocabulary (AT-1033) would let a project decline words that name its tenants","evidence":"qa/evidence/fix6c-r4-routeword.b/probe.py: /users/me, /status/me/mail/cart templated literally","file":"src/autotester/schema/leak_evidence.py:34-35"}

Metrics: start=2026-10-18T23:05:00Z end=2026-10-18T23:20:00Z wall_min=15 agent_min=15 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=900 mutants=3 defects_unit=0 defects_6c=0
