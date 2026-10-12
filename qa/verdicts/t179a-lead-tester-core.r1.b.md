# Verdict: t179a-lead-tester-core, repair check, coordinator B (blind dual)

Cycle checked: 1
Verdict: FAIL (AL6, built subset). AL2 PASS. AL3 PASS (READ_ONLY now fails closed).
Branch wave/t179-lead-tester, head c489e201 (code 67a94fb1), Repair base 638d788a, Tier L, dual-trigger security, Policy-Version proportional-verification/2026-10-10.9.
EXECUTOR: claude-sonnet-subagent. Blind: no earlier verdict, checkpoint or evidence of this unit was opened. Evidence: qa/evidence/t179a-lead-tester-core-r1-B/ (labels only, fake fixture canaries).
SERIAL: sections 2-6 ran in the coordinator, 3 of 4 sub-checker spawns hit the concurrent-subagent limit and were not retried.

## Check plan (made before running)
Probes ran in C: copies of base (638d788a) and head (c489e201), real `tools.dispatch`, stage/session/judge spies, fresh data root per row; sections 1-7 of the brief. No full suite, no suite lock.

## Totals
| Section | Rows | Result at head | Exception rows |
|---|---|---|---|
| 1 run_case, 3 policies x all Action x corpus x position x login | 21,744 per copy (base, head, head again; head=head again) | READ_ONLY exec 3340 / ref 3908 (base 6688/560). TEST_ACCOUNT 6934/314 (base 7116/132). ALLOW_WRITES 6992/256 (base 7174/74). 0 escaped, 0 refused row with a session, call or file | 7 READ_ONLY rows: whitespace-only login FILL (see PI-3) |
| 2 NAVIGATE, 118 destinations x 3 policies | 354 | READ_ONLY exec 30 / ref 88. TEST_ACCOUNT and ALLOW_WRITES 66 / 52 each. 0 escaped. Refusals all class `destination`/`write_policy` | 4 READ_ONLY executes that an independent classifier calls not-plain-read: `/%252flogout`, `/users/1/destroy`, `/home?`, `/home?#x` |
| 3 login carve-out abuse | 176 (3 modes) | login mode exec 21 / ref 59; mode other exec 1 (reads only) and unset exec 1 (reads only), base 48 and 47. Cycle-0 hole closed (base ran 95 of the mutating rows in other/unset) | login-mode executes of blank FILL then submit, name-agnostic submit, query NAVIGATE (PI-3) |
| 4 dispatcher robustness | 138 | 135 typed results. 0 escapes from an `Exception` subclass, 0 stdout/stderr/log/warning leak of a canary spelling, worst 0.17 s (base: 70 rows escaped, worst 12.3 s on a 2 MB key) | 3: KeyboardInterrupt, SystemExit, GeneratorExit pass through (documented: dispatch catches `Exception` only). 3 more rows return a TAB-split canary in the summary (PI-1) |
| 5 secrets from stages, byte grep of data root (file bytes, JSON-decoded strings, file names) | 134 attack + 40 decoy | 110 of 134 clean (base 9). Decoys refused 0 of 40. Dict keys cannot be built (models are extra=forbid) | 24 rows leave a spelling on disk, 7 also in the returned summary: TAB split 16, newline split 4, `\uXXXX` escape 4 (PI-1, PI-2). Zero for raw, reversed, base64, base64url, base32, hex, percent, upper, spaced, dotted, zero-width, soft-hyphen, nested |
| 6 static | ruff clean, doctor clean | two files 131 passed. Importers of guards/tools/agent_layer 218 passed. Neighbours 71 passed. guards.py 161, tools.py 280, test file 260 lines | none |
| 7 benign READ_ONLY rows now refused (no decision) | 483 of 1,120 benign rows that base ran (35 distinct single-step non-login) | click 112, press_key 98, fill 70, select 70, upload 70, navigate 63. Examples: CLICK Home/Next/Products/Dashboard, FILL "Search box", PRESS_KEY Tab | HUMAN_GATE-REQUEST 1 |

Base vs head under TEST_ACCOUNT and ALLOW_WRITES: 364 rows (182 each, identical sets) executed at base and refused at head, all NAVIGATE, all class `destination`; 0 non-destination differences; 0 rows head runs that base refused. Of the 13 distinct targets, base `BrowserSession.goto` already refused most; it would have navigated `ftp://app.test/`, `ws://app.test/`, URLs with TAB, LF, NUL or DEL, and `https://{{SECRET:APP_PASS}}/` when the secret value is the in-domain host. CLICK deny-list unchanged. No tool (crawl, run_case, get_persona, get_catalog, grade_case) writes the project, `login_case_id` or any case; case ids are content hashes.

## Falsifications (fresh `git archive c489e201` copy each; imported tree printed; green, red, restored green)
| Criterion | Edit | Test | Red on |
|---|---|---|---|
| AL3(c) | `_read_only_refusal` final `return f"{action.value} can change state"` becomes `return None` | test_read_only_refuses_each_state_changing_step 32 passed | 4 failed `assert not out.ok`, restored 32 passed |
| F2 | `_dispatch` `except Exception as exc` clause deleted | test_a_stage_session_or_judge_failure_is_a_scrubbed_typed_refusal | `assert "RuntimeError" in out.summary` ('the tool call failed'); the outer net in `dispatch` still returns a typed STAGE_ERROR, so only the detail assertion goes red |
| F3 | `_withhold_if_credential` made a no-op | test_a_folded_secret_in_a_stage_result_is_never_stored | `load_results == []` (a result was stored) |

## Findings
PROPOSED-ISSUE: PI-1 S2 security, BLOCKING (AL6): `_withhold_if_credential` (tools.py:86) and `_release` (tools.py:158) run the gate on `model_dump_json()`, where TAB and LF become the two characters `\t`/`\n`, which the fold does not strip. A stage result or error holding the credential split by TAB or newline is saved to disk and returned to the model with `ok=True`; the same string passed to `SecretStore.guard_prompt` raises (s5b: 6 of 6 rows, `ok=True` yet gate raises; space and zero-width controls are refused). AL6 requires the model-bound text to pass `assert_no_raw_secrets`; F4 already fixed this exact trap for call arguments but not for results. Repro: `RawResult(error="saw " + "\t".join(chunks of 4 of the secret))` through `dispatch("run_case")`, then grep the data root (s5-head.json rows tab_split/newline_split). Fix: gate decoded string values (walk like `_call_texts`), not the JSON text, in both places. The tab-split error also returned for crawl and get_catalog (s4 rows).
PROPOSED-ISSUE: PI-2 S3: `C`-style escape spelling and a literal-in-JSON variant are caught nowhere, even on raw text (beyond the required list; HTML entity is caught).
PROPOSED-ISSUE: PI-3 S3 login carve-out slack: `guards._declared_credential` accepts a whitespace-only FILL (empty placeholder list, `all()` is True) so it arms `credential_pending`; the submit CLICK is name-agnostic except the deny list ("Place order", "Save", blank or the secret literal run); the declared login case may NAVIGATE to a same-domain URL with a query. Only the operator-declared login case; mode other/unset is clean.
PROPOSED-ISSUE: PI-4 process: coordinator wall about 85 min against the L 45 min target, caused by the 21,744-row table run three times (about 12 min each) and the subagent limit forcing serial sections; no mandatory check left undone.
HUMAN_GATE-REQUEST: HG-1 (section 7) READ_ONLY now refuses every CLICK, PRESS_KEY, SELECT and UPLOAD, so no click-through navigation is possible under READ_ONLY: 483 of 1,120 benign rows. Owner to say whether that is the intended tier or whether a safe-click allow-list is wanted; not decided here.
HUMAN_GATE-REQUEST: HG-2 confirm that refusing control-character, non-http(s) and userinfo destinations at TEST_ACCOUNT and ALLOW_WRITES (364 rows) fits `write-policy-tier.md`, since the account's rights are the scope.

Metrics: start=2026-10-11T21:11:50Z end=2026-10-11T22:36:00Z wall_min=84 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=5040 mutants=3 defects_unit=1 defects_6c=0
slow: section 1 table 36 min (three 12 min runs), sections 2-6 serial 30 min
