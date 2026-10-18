# Verdict - fix6c-r4-routeword (coordinator A, dual check)

Date: 2026-10-19 · Cycle checked: 0 · Base 58e13d6b (git merge-base HEAD int/1017, verified) · Head 3045e909 · Code 58c0361e
Policy-Version: proportional-verification/2026-10-18.15

## Check plan
Logic changed in a security path (schema/leak_evidence.py:22-37 ROUTE_WORDS, :46-53 segment_is_id_like) -> affected tests + 1 falsification per criterion (F1, F2, F3) + security probes (id/PII/tenant leak, test-edit weakening). No UI (no browser walk), no LLM output, no data artifact. Dual check: no lane check (step 0a n/a). No full suite (pre-push covers it).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (F1, F2, F3), core-invariants touched: none broken
TIER: L (dual-trigger src/autotester/schema/leak_evidence.py:53 read in this check; protected T-209 test files edited additively)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no capability rows)
LIVE-BROWSER: not-applicable (changed paths: schema/leak_evidence.py, 3 test files)
ISSUES-WRITTEN: none (dual coordinator; findings as PROPOSED-ISSUE below)
EXECUTOR: claude-sonnet-subagent (maker: claude-sonnet-subagent; checker: claude-sonnet-subagent)

## Evidence (all produced by me in this check)
- Scope: `git diff 58e13d6b..3045e909 --stat` = 5 files (1 src +2 lines, 3 tests, manifest). No core/image_privacy.py, no qa/contracts.
- Affected tests, worktree head: `uv run --directory <wt> pytest` over test_oracle_state_after, test_state_probe_schema, test_oracle_answer_key, test_oracle_copy_lint, test_network_oracles, test_leak_evidence, test_oracle_responsive, test_leak_url_ids, test_leak_repro_replay, test_role_session_port, test_platform_links, test_image_privacy, test_multi_role_schema -> 334 passed (95 s). Includes the 38 r4 reds and the two no-OCR nodes.
- ruff on the 4 changed py files: All checks passed. File sizes: leak_evidence.py 104, tests <= 190 lines.
- F1 falsification (own copy `scratchpad/check-routeword-a/m1`, 11 words removed, PYTHONPATH to copy; module path confirmed to resolve to the copy): test_state_probe_schema + test_oracle_answer_key + test_network_oracles + test_leak_url_ids -> 26 failed, 120 passed; real tree green. Red on ValueError "id-like segment" / collapsed endpoints, not an import error.
- F3 falsification: same copy: the new test `test_ordinary_route_words_other_units_use_are_kept_but_names_still_are_not` is among the 26 reds (keep half). Name-slug half: probe below.
- F2 falsification (copy `m2`: base-version `git show 58e13d6b:tests/...` of the two files, current src): 2 failed (exactly test_unmaskable_screenshot_is_withheld_never_written_raw and test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw), 17 passed. Fixed versions in the real tree: 2 passed. Root cause confirmed: image_privacy.py:48-65 also reads AUTOTESTER_TESSERACT, repo .env and WINDOWS_TESSERACT (:37), which exist on this machine.

## Security probes (qa/evidence/fix6c-r4-routeword/probe-a.py, run against the head)
1. Real identifiers next to an added word stay refused (ValueError): /inbox/alice, /inbox/Alice, /ME/Alice, /inbox/bob, /inbox/zorblax-quimby, /mail/jane.doe, /me/<hex>, /status/<JWT>, /items/12345, /quiz/<ObjectId>, /mail/<UUID>, /cart/cus_*, /status/acme-corp, /users/me/alice, /me-alice, /inbox/<26-letter run>, /mail/+14155550123, and any path containing `@` or `%40`. Note the predicate rejects the segment AFTER the word because that name is not in the closed set; the closed set stays closed (the 11 words are the only change).
2. `templatise_url` (stages/leak_evidence.py:82, platform_links.py:209, the writers): /inbox/alice?token=abc&q=Zorblax -> /inbox/{id}?token={value}&q={value}; /status/acme-corp/members/42 -> /status/{id}/{id}/{id}; /mail/alice@x.com -> /mail/{id}; /quiz/Zx9secret?next=/inbox/bob -> /quiz/{id}?next={value}. Query values never survive.
3. Added word as a literal tenant/user value: a tenant, user or slug literally named `me`, `status`, `mail`, `cart`, `inbox` etc. would now survive as that literal when it is the whole segment (e.g. /t/status/...). Same residual as the pre-existing words `admin`, `test`, `user`, `school`, `help`, `home`, `new` in the closed list; the 11 words carry no entropy of a person (no name, email, phone, token). Non-blocking, see P1.
4. Test edits: diff is additive (+4/+4/+8 lines, no `-` lines in tests). No assertion removed or changed, no skip/xfail, no threshold. The F2 patches only isolate tesseract discovery (WINDOWS_TESSERACT, env key, repo_root) so the no-engine path is really exercised; the assertions (`screenshot_path is None`, reason `local_ocr_unavailable`, no .png written) still pin the "withhold, never write raw" behaviour. Protected change justified: hermeticity only.

## Findings (non-blocking)
PROPOSED-ISSUE: {"severity":"low","kind":"security-hardening","title":"ROUTE_WORDS holds common single words (me, status, mail, cart...) that can equal a real tenant/user slug; a slug named exactly like a route word survives literally in a leak url_template","evidence":"src/autotester/schema/leak_evidence.py:34-35 and :53; probe-a.py items 3","fix":"AT-1033 per-project route vocabulary (or require the segment after a collection word to be {id}); already open, link rather than duplicate","unit":"fix6c-r4-routeword"}

EXPLANATION: The 11 added words are ordinary route vocabulary and nothing else in the predicate changed; probes show ids, emails, tokens, name slugs and query values still collapse to {id}/{value}, and the two test edits only isolate the OCR environment. All 334 affected tests pass, and each criterion was falsified red in an isolated copy.

Metrics: start=2026-10-19T03:40:00Z end=2026-10-19T04:05:00Z wall_min=25 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
