# Verdict (coordinator B) — land-integrate-combined

Cycle checked: 0 · Policy-Version: proportional-verification/2026-10-10.9 · Tier L · Dual check (coordinator B, blind)
Checked: wave/land-integrate-combined HEAD 23e694a9 (tree e7093149; code unchanged since f210ddc2) · base master 3a16616c (merge-base verified with git)
Date: 2026-10-11 · Resume: 0 of 2 · Retry: 0

## Plan
Diff `master...wave/land-integrate-combined` read in full (13 files). Checks: RC11/RC12/RC14 and C1/C2/C3 verify commands once; one own falsification per criterion (different from the builder's); security read of every path from reconcile content to a model; bypass probes of the PII masks. No UI surface, so no browser. No full suite (the other coordinator owns the single L suite). All runs in a `git archive 23e694a9` copy under the scratchpad; one pytest process at a time, `-p no:xdist`.

VERDICT: PASS
SCOREBOARD: 6/6 criteria met (RC11, RC12, RC14, C1, C2, C3), invariants none-touched
TIER: L (security: src/autotester/core/redact.py:173 and src/autotester/stages/reconcile.py:92; prompt PII masking)
FAILURES: none
CAPABILITY-COVERAGE: 8/8 own falsifications reproduced (one extra mutant survived, see RC11b; floor met)
LIVE-BROWSER: not-applicable (changed paths: core/redact.py, stages/reconcile.py, tests/, qa/, docs/SNAPSHOT.md; no ui/)
ISSUES-WRITTEN: none (dual check; PROPOSED-ISSUE lines below)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all re-run by me)
- Scoped tests: tests/test_redact_pii.py test_reconcile_pii.py test_reconcile.py test_redact_encoding_coverage.py test_redact_ignorable_perf.py test_redact_obfuscation.py test_redact_wrap_perf.py test_timing_scale.py test_schema.py -> 358 passed, 1 failed in 76.8 s. The one failure is `test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` (3.57 s vs 3 s bound) at host CPU load 100%; re-run alone: 18 passed in 11.5 s. A timing assertion, in code this diff only adds to (`contains_folded`/`assert_no_raw_secrets` unchanged), so `load-flake: tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus`.
- [RC11] test_rc11_* (3 tests in test_reconcile.py) green in the run above. Falsify: drop `sorted(new_f.values(), key=flow_rank)` in `_union` -> green in copy, RED on `test_rc11_same_inputs_give_byte_identical_output_in_any_input_order` (bytes differ at index 26885). Mutant RC11b (drop only the screen output sort) SURVIVED: input sort of `videos` still orders it; not a defect, input-sort redundancy.
- [RC12] test_rc12_* (4) + tests/test_reconcile_pii.py green. Falsify A: `"value": mask_name_value(s.target, s.value)` -> `s.value` in `build_judge_prompt`: green copy, RED (4 params of `test_name_field_value_is_masked`, "Rahul Sharma" in prompt). Falsify B: delete `text = _mask_emails(text)` in `mask_pii`: RED (`test_pii_values_are_masked_in_the_exact_prompt[jane.doe@example.com]`).
- [RC14] `autotester doctor` in copy: "doctor: clean"; reconcile.py = 300 lines; ruff "All checks passed!"; `git diff --name-only master...` matched against stages/review|test_review|ui|grade.py|qa/contracts = 0. Falsify: add `core/redact_v2.py` -> doctor RED `drift-filename`.
- [C1] tests/test_schema.py green. Falsify: `Screen` model_config `extra="forbid"` -> `"ignore"` -> RED `test_unknown_field_is_rejected_loudly` (DID NOT RAISE).
- [C2] doctor clean. Falsify: 53-line function appended to `core/excel.py` -> RED `function-too-long: excel.py:24 _big_fn is 53 lines > 50`.
- [C3] doctor clean. Falsify: `class Redactor` added to `core/excel.py` -> RED `duplicate-concept ... 'Redactor' also defined`.
- Step 4c diff scope: `stages/reconcile.py` changes are the import line, `build_judge_prompt` (mask_name_value on the value, `mask_pii_obj` over both dicts before `json.dumps`) and the docstring trim; no def/class/test removed, no file outside the manifest "What changed" list (qa/ ledgers and manifests, docs/SNAPSHOT.md, redact.py, two tests, reconcile.py). Nothing under ui/, review.py, grade.py or qa/contracts.

## Security read: does every reconcile -> model path go through the mask?
The only model call in reconcile.py is `_judged` -> `provider.judge(prompt, ...)` (line 120); `build_judge_prompt` is its only prompt source and has no other caller (grep of src). Order inside the prompt build: `mask_name_value` on step value, then `mask_pii_obj` over BOTH the video dict (name, route, cues, fields, actions incl. target/value/said) and the candidate dict (from, title, route, controls) just before `json.dumps`; then `_judged` adds `redactor.scrub` and `assert_no_raw_secrets`. No images or files are passed. So no path skips the mask. Out of this unit's scope and still open: grade.py:178 (AT-840), ux_advisory.py:140, relitigation.py:74.

Bypass attempts (probe, copy only), shapes that still reach the prompt unmasked: percent-encoded `%40` in a title or value (AT-830 filed, medium); full-width `@` (AT-832); `[at]` spelling; spaced single digits and Aadhaar (AT-839); names in narration, cues, titles (AT-838); `set` containers in `mask_pii_obj` (AT-836); label-less name fields such as "Who are you?" or "Account holder" (AT-833). NEW shapes I found that are not in the ledger rows I read: a zero-width space or U+180E inside a phone number (`98765​43210`), a non-breaking hyphen U+2011 phone separator (`98765‑43210`), an HTML entity `&#64;` email. Masking is declared heuristic in the redact.py comment ("they are guesses"); none of these is a regression against master (master sends the same text with no mask), and RC12's checked clause (seeded secret / step value replaced or refused) holds, so these are non-blocking.

PROPOSED-ISSUE: {"severity":"low","feature":"reconcile","title":"mask_pii misses phones with a zero-width space/U+180E or U+2011 non-breaking hyphen inside the digits, and emails written with the HTML entity &#64;","evidence":"src/autotester/core/redact.py:_PHONE_RES, _mask_emails; probe: mask_pii('98765\\u200b43210') and mask_pii('98765\\u201143210') and mask_pii('jane&#64;example.com') return the input unchanged","status":"open","found_by":"checker-unit","regression_check":null}
PROPOSED-ISSUE: {"severity":"low","feature":"reconcile","title":"No test pins that build_judge_prompt is the only prompt source for the judge: a second caller or a post-mask string edit would bypass mask_pii_obj","evidence":"src/autotester/stages/reconcile.py:108 _judged takes a prebuilt prompt string; masking lives only in build_judge_prompt (reconcile.py:103)","status":"open","found_by":"checker-unit","regression_check":null}

## Notes
- Builder claims reproduced: scoped tests green (my run differs only by the perf-bound load flake the manifest also reports), doctor clean, ruff clean, one falsification per criterion, no executable line changed in reconcile.py beyond the merge (diff read), nothing under ui/, review.py, grade.py, qa/contracts.
- full-suite trigger: none beyond L; the single L suite is the other coordinator's.
- Processes: only my own pytest/python children; all finished; my copies deleted after use.

Metrics: start=2026-10-11T01:03:35+05:30 end=2026-10-11T01:30:00+05:30 wall_min=26 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1585 mutants=1 defects_unit=0 defects_6c=0
