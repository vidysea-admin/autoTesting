# Manifest — reconcile (video knowledge graph → product knowledge graph, no human gate)

Status: checked-PASS
Fix cycle: 0
Resume: 0 of 2
Contract: qa/contracts/reconcile.md RC1–RC14 (commit 8b9bdb89 on wave/reconcile)
Goal task: T-166 (reconcile half) · D-070 part 2 · module authorized by D-073
Policy-Version: proportional-verification/2026-10-07.7
Tier: M. Additive, default-valued schema fields plus one new stage. No migration rewrites a stored FlowSpec: reconcile is a pure function and persists nothing. `stages/review.py` and `tests/test_review*.py` are untouched.
Dual check: not required (M; no consent, credential, approval, deletion or production-write boundary changes)
Source: 82ad6255 (code) + the manifest commit that follows (adds the RC9 direct tie test) on wave/reconcile (merged origin/master 6f351e11 first)

## What changed

- `schema/flowspec.py`: optional `Step.screen_id` / `narration` / `on_screen_text`; `Screen.video_only` (default False, left out of the dump when False so pre-unit files round-trip byte-identically under `exclude_none`); `Flow.kind` / `ideal_basis` / `variant_of` / `diverges_at` (Literal types, None by default); `Flow.source_id` property; report models `ScreenJudgement`, `ScreenMatch`, `StepRef`, `Possibility`, `ReconcileReport`. 255 lines. `enums.py` sits at the 300-line cap, so the kinds are Literals.
- `schema/observation.py`: `ObservedStep.screen` (optional). Its field description asks the model for the screen name. The ingest-video SKILL.md is deliberately **not** edited: `tests/fixtures/golden_prompts/ingest-video.md` pins it byte-for-byte (SK3), and a real re-ingest waits on Umesh (contract no-fire list).
- `schema/media.py`: `Transcript.quotes(text, scrub=)` checks a whitespace-normalised, case-folded verbatim quote (RC3).
- `stages/ingest.py` (≤300 lines): `_to_step` keeps narration, on-screen text and the step screen (resolved through the same name→id map as `entry_screen`; an unknown name gives None). `_to_flow` keeps `exit_screen`. `flow_id(name, source)` fixes RC8. `legacy_flow_id`. `flowspec_from_observation` is extracted from `ingest_video` and is pure.
- `stages/merge_flowspec.py::_new_flows`: a re-ingest of the same recording whose saved flow still has the legacy name-only id is recognised and not added twice. Saved ids are never rewritten.
- `stages/screen_identity.py`: gains `route_key`, `element_labels`/`screen_labels`, `match_signals`, `fold_routes` (RC4), `rewrite_screen_refs` and `dangling_references`. These were moved here to keep `reconcile.py` under 300 lines; the module job is restated as "when two screens are one".
- `stages/reconcile.py` (new, D-073): thresholds `MATCHED_AT` and `AMBIGUOUS_AT` are the only literals. It also holds `band`, `combined_score` (weights 2/4, 1/4, 1/4), `score_screen`, the judge seam (`_judged`: scrub, then `assert_no_raw_secrets`, then `Provider.judge`), `verify_narration`, `assign_kinds` (ideal/narrated/variant per normalised flow name; basis crawl, then modal, then only) and `reconcile()`, which returns `(FlowSpec, ReconcileReport)`. It never reads `review`.
- `skills/reconcile-screen/SKILL.md`: the judge prompt, loaded via `load_skill_prompt`.
- `tests/fixtures/reconcile/frozen_sample.json` (66 lines): derived from the 3 real ingests (3 sources, 38 screens, 4 real flows) plus 2 synthetic same-named "Sign in" flows, giving 6. It is sanitized: fill values become "sample", names are replaced, uploads are dropped. Two real crawl nodes (`/`, `/signup`) are included. Every synthetic part is listed in the fixture's `note`. Routes shared by videos include `/counsellor/dashboard` (3 sources).
- `docs/MAP.md` was regenerated with `autotester map` (the authorized path).

## Capability coverage (criterion → defender test → falsification)

| RC | Defender test(s) | Falsification (scratch copy; green → red → green) |
|---|---|---|
| RC1 | test_reconcile_schema.py::test_rc1_* (5) | F1: `_to_step` sets `screen_id=None` |
| RC2 | ::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen, ::test_rc2_absent_evidence_is_none_not_empty_or_invented | F2: narration dropped · F2b: `""` kept instead of None |
| RC3 | test_reconcile.py::test_rc3_narration_not_in_transcript_is_rejected_and_the_step_kept, ::test_rc3_narration_is_scrubbed_before_it_is_stored | F3: quote check skipped · F3b: narration stored unscrubbed |
| RC4 | ::test_rc4_three_ids_for_one_route_fold_to_one_and_every_reference_follows, ::test_rc4_screens_without_a_route_are_never_folded_on_route_alone | F4: no folding · F4b: route-less screens folded by name |
| RC5 | ::test_rc5_boundaries_land_in_the_fixed_bands (0.80/0.79/0.50/0.49), ::test_rc5_thresholds_have_exactly_one_literal_each, ::test_rc5_every_row_records_three_signals_total_band_and_decider | F5: `>=` → `>` · F5b: a second `0.8` literal |
| RC6 | ::test_rc6_judge_is_called_once_per_ambiguous_row_and_never_for_rule_rows, ::test_rc6_decoy_low_confidence_and_errors_stay_ambiguous (0.79 / ProviderError / no judge), ::test_rc6_unsupported_judge_stays_ambiguous_and_a_confident_judge_matches | F6: confidence bar removed (0.79 promotes) · F6b: judge called for rule rows · F6c: judge error becomes `new` |
| RC7 | ::test_rc7_every_video_screen_lands_in_exactly_one_band_and_new_ones_survive | F7: `video_only` never set |
| RC8 | test_reconcile_schema.py::test_rc8_* (5) | F8: name-only flow id · F8b: one flow dropped from output |
| RC9 | ::test_rc9_the_crawl_path_is_ideal_even_when_a_video_path_is_more_common, ::test_rc9_without_a_crawl_the_modal_path_is_ideal, ::test_rc9_a_tie_resolves_to_the_earliest_source_every_time (5 runs), ::test_rc9_rc10_every_flow_has_one_kind_and_the_counts_balance | F9: crawl basis skipped · F9b: grouping in input order (defended by ::test_rc9_assign_kinds_breaks_a_tie_by_source_whatever_the_input_order) |
| RC10 | ::test_rc10_each_variant_is_an_another_possibility_with_step_second_and_quote, ::test_rc10_review_status_changes_nothing_and_is_never_read, balance test above | F10: possibilities not recorded · F10b: reconcile reads `review.status` · F8b: balance red |
| RC11 | test_reconcile.py::test_rc11_same_inputs_give_byte_identical_output_in_any_input_order, ::test_rc11_reconciling_its_own_output_changes_nothing_and_calls_no_judge | F11: new flows kept in input order · F11b: no-op run returns a new object |
| RC12 | ::test_rc12_no_raw_secret_reaches_the_judge_prompt (secret in field/signal, step value, narration), ::test_rc12_an_unscrubbable_spelling_refuses_the_call, ::test_rc12_module_uses_the_seam_and_a_prompt_file | F12: prompt not scrubbed · F12b: `assert_no_raw_secrets` skipped |
| RC13 | ::test_rc13_runs_with_sockets_blocked_and_no_keys, ::test_rc13_reconcile_tests_import_no_real_provider | F13: reconcile opens a socket · F13b: fakes import `providers.gemini` |
| RC14 | `uv run autotester doctor` | F14: reconcile.py padded past 300 lines → doctor exit≠0 |

Sabotage lines for RC6, RC11 and RC12 (C7) are F6/F6b/F6c, F11/F11b and F12/F12b above. Harness: scratchpad `fals.py`, run against a copy at `.../scratchpad/reconcile-fals/` with `PYTHONPATH=<copy>/src`. Result: **26/26 OK**. Three cases needed a second run, and the runs are recorded as they happened: (a) F3b first sabotaged only the step-level scrub and stayed green, because `_assemble` scrubs the whole output again (`scrub_obj`, defence in depth); with both layers removed it goes red. (b) F9b stayed green against the reconcile-level tie test because `_union` already orders flows; I added a direct `assign_kinds` test with reversed input, and it goes red. (c) F14's first baseline failed on a stale `docs/SNAPSHOT.md` in the copy; I regenerated it there, the baseline was clean, a 307-line pad gave `file-too-long` (exit 1), and the restore was clean.

## Verify (the checker re-runs)

- `uv run pytest tests/test_reconcile.py tests/test_reconcile_schema.py tests/test_ingest.py tests/test_merge_flowspec.py tests/test_schema.py` → 74 passed
- `uv run ruff check src tests scripts` → All checks passed!
- `uv run autotester doctor` → doctor: clean
- Importers of the changed modules (36 files: ingest/merge/screen_identity/media/observation/prompt-skills/explore/ui-learn/video, …): 1 failed, 405 passed in 1391.96s. The one failure, `tests/test_video_evidence.py::test_video_is_recorded_and_kept_only_for_fail_and_inconclusive_never_pass`, is a real-browser pipeline test that does not import a changed module directly. Re-run alone, it gave 2 passed in 56.94s, so it is load-sensitive timing and not this unit.

## Frozen-sample outcome (mock judge, same_screen=True @0.9)

27 canonical screens (11 folded). Bands: matched 2 (`/` and `/signup` against the crawl, both judge-decided from the ambiguous band at 0.61 and 0.55), ambiguous 0, new/video_only 25. 2 judge calls. Flows: 6 in and 6 out; kinds are ideal 5, narrated 0, variant 1 ("Sign in" from src_3f9c diverges at step 1 from the crawl-basis ideal in src_a2d6). Unresolved steps: 1 (the synthetic unlisted screen). Narrations were verified against the synthetic transcripts.

## Open for the checker

- `ObservedStep.screen` is requested through the response-schema field description, not the ingest prompt body (golden pin, SK3). If the checker reads RC1's "the vision prompt asks for" as the SKILL.md body, that is a golden-prompt change for Umesh to approve.
- Narration verification lives in reconcile, not ingest: ingest keeps the raw narration (RC2) and reconcile drops unverified quotes (RC3).

Metrics: 13 files / +1175 −21 in the code commit · 1 new module (D-073) + 1 prompt file · 37 new tests (18 + 19) · 26 falsifications OK · the frozen sample reaches 2 judge calls · reconcile.py 292 lines, ingest.py ≈299 · fix cycle 0
