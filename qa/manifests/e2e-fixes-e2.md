# Manifest - e2e-fixes-e2

**Status:** checked-PASS (cycle 0, verdict a25593cf)
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E2 (E2.1-E2.7; AT-1413, AT-1414). **Criticality:** HIGH (the verdict path, core-invariants C12).
**Branch:** `feat/e2e-e2`, cut from master `dccc65e9` (contract commit). Not merged, not pushed.
**Base SHA:** `dccc65e9`. **Code SHA:** the commit carrying this manifest (`git log -1 feat/e2e-e2`).
**Edit in place:** no new `src/` module (so no D-entry needed); three new test files.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/providers/langchain_fallback.py` | E in place | `_make_ollama` `:47-58` (private helper, same file); `_default_chain` `:61`: ollama tier gated on `ollama_cloud.base_url()` `:76` (explicit `OLLAMA_BASE_URL`, else the cloud URL when `OLLAMA_API_KEY` is set) and placed ahead of gemini (`:77` vs `:87`); Bearer header `:55`; default model `ollama_cloud.GLM` minus prefix when a key is set, `llama3` for a bare local URL (unchanged), `OLLAMA_MODEL` overrides. Module docstring updated. |
| `src/autotester/schema/verdict.py` | E in place | `Judgment.judge_required` ClassVar `:99` and `Judgment.model_json_schema` override `:105-120`: the schema a model is given marks `defect_observed` required, boolean-only, no default. Construction stays tolerant (`bool \| None = None`, validator untouched). Field description reworded for the model (no "None = omitted" text). |
| `src/autotester/providers/litellm_schema.py` | E in place | `parse_answer :85` calls `_require_answered :94`: an absent or null `judge_required` field raises a pydantic `ValidationError` (field path only, never the input), which is the existing repair-retry path in `litellm_provider._structured`, then `ProviderError`. `litellm_provider.py` is NOT edited (299 lines, cap 300). |
| `src/autotester/skills/grade/SKILL.md` | E in place | one bullet (`:30-35`) after the `defect_observed` bullet: how to word a no-defect note (E2.6). |
| `tests/fixtures/golden_prompts/grade.md` | E in place | the same bullet (SK3 golden refresh, precedent `d1970464`); `test_sk3_rendered_prompt_is_byte_identical...[grade]` passes. |
| `tests/test_langchain_ollama_tier.py` | N | E2.1-E2.3 (11 tests) |
| `tests/test_judge_defect_required.py` | N | E2.4 (a)(b)(c)(d) (10 tests incl. params) |
| `tests/test_grade_e2e_notes.py` | N | E2.6 + E2.7 (13 tests) |
| `qa/evidence/e2e-fixes-e2/` | N | `mutations-{chain,schema,notes}.json` and run logs |

**Not touched (E2.5, mechanical):** `git diff dccc65e9 -- src/autotester/stages/` is empty. `stages/grade_note_guard.py` and `stages/grade.py` are unchanged, so `_DEFECT_LEXICON`, `_NEGATED_SUCCESS`, `_negated`, `_exemptible`, `_exempt`, `_EXPECTED_CUE`, `_CONTRARY`, `_defect_decision` are byte-identical. No existing test file was edited (additions only: three new test files plus the golden fixture).

## Criteria map

| Crit | Code | Test (falsifier) |
|---|---|---|
| E2.1 key alone adds `ollama` | `langchain_fallback.py:76`, `_make_ollama :47` | `test_langchain_ollama_tier.py`: `test_e2_1_a_cloud_key_alone_adds_the_ollama_tier`, `..._nothing_configured_adds_no_ollama_tier`, `..._a_base_url_alone_still_adds_it`, `..._the_factory_is_not_invoked_while_building_the_chain` (`langchain_ollama` blocked in `sys.modules`), `..._the_cloud_tier_targets_the_cloud_url_with_a_bearer_header_and_glm`, `..._ollama_model_overrides...`, `..._a_local_daemon_keeps_its_url_default_model_and_sends_no_header` |
| E2.2 order | `langchain_fallback.py:76-87` | `test_e2_2_the_order_is_anthropic_ollama_gemini_chatgpt`, `test_e2_2_ollama_precedes_gemini_without_anthropic` |
| E2.3 cap survived, winner named | `_call`/`_try_tier` unchanged (`:154-196`) | `test_e2_3_a_capped_gemini_falls_through_to_ollama_and_ollama_is_named`, `test_e2_3_a_failing_ollama_first_falls_through_to_gemini` (fake chain entries, `provider.id` asserted) |
| E2.4 (a) required + non-null in the sent schema | `verdict.py:99-120`; `litellm_schema.py` `json_mode_instruction` and `request_options` call `schema.model_json_schema()` unchanged | `test_a_the_json_mode_schema_requires_a_non_null_boolean`, `test_a_the_schema_and_tool_strategies_send_the_same_tightened_schema`, `test_a_the_ollama_judge_call_carries_the_required_schema` (schema text captured from the fake `litellm` call) |
| E2.4 (b) omitted/null -> 1 repair -> ProviderError -> INCONCLUSIVE | `litellm_schema.py:90,94-105`; repair loop `litellm_provider.py::_structured` untouched | `test_b_a_missing_or_null_answer_gets_one_repair_prompt_then_provider_error[omitted\|null]` (exactly 2 calls, repair text names `defect_observed`), `test_b_a_repair_that_supplies_the_field_is_accepted`, `test_b_the_unanswered_field_grades_inconclusive_with_the_reason_in_the_note` |
| E2.4 (c) `false` grades as before | - | `test_c_defect_observed_false_parses_and_grades_as_before`, `test_c_defect_observed_true_still_downgrades_a_pass` |
| E2.4 (d) `Judgment` tolerant to construct | `verdict.py` field unchanged | `test_d_judgment_without_the_field_still_constructs_and_keeps_the_none_fallback`; `tests/test_grade_defect_field.py` unchanged and green |
| E2.5 guard not loosened | no diff under `stages/` | the hold suites green unmodified (below); `test_the_a5ea_note_is_still_held_on_a_negative_case`, `test_the_cfa4_note_is_still_held_on_a_positive_case`, `test_a_bare_rejection_note_with_no_expected_cue_stays_held` |
| E2.6 prompt wording | `SKILL.md:30-35` | `test_the_grade_prompt_tells_the_judge_how_to_word_a_no_defect_note`, `..._keeps_its_placeholders_and_the_untrusted_evidence_paragraph`, `..._does_not_tell_the_judge_to_hide_a_real_defect`; SK3 golden test |
| E2.7 notes pinned both ways | - | `test_grade_e2e_notes.py`: verbatim a5ea + cfa4 held; reworded -> PASS; controls (positive-path rubric, `defect_observed=True` x2, genuine contrary marker x2) held |

## Things the checker should look at (judgement calls and deviations)

1. **E2.7's reworded a5ea text deviates from the contract's literal example, and the reason is evidence for a HUMAN_GATE.** The contract's note ("The **wrong-password** login was correctly rejected: ...") is NOT a PASS under the unchanged guard: `_CONTRARY` (`grade_note_guard.py:90-93`) contains `wrong`, and `_QUALIFIED_INPUT` strips only `wrong <input>` separated by whitespace, so the hyphenated `wrong-password` leaves a contrary marker and the note is held. I pinned the spaced form ("The login with a wrong password was correctly rejected: the 'Invalid credentials' assertion was met."), which does PASS. Fixing the hyphen is a guard change, outside E2.5; if wanted it is a separate human-gated decision. Consequence for E2.6: a judge that writes "wrong-password" is still held.
2. **`grade()` does not itself turn a `ProviderError` into INCONCLUSIVE** (contract E2.4(b) says "`grade()` returns INCONCLUSIVE"). It propagates; the conversion is the existing `run_case_pipeline.py::run_and_grade_case_resilient` (`:271-276`, AT-573; E4's file, untouched). The test goes through that function with a real `LiteLLMProvider` on a fake `litellm` and asserts INCONCLUSIVE with `ProviderError` and `defect_observed` in `note`. I did not add a catch to `grade()` (it would swallow `AvailabilityFailure`, which other code distinguishes).
3. **Model-chain enforcement is at reply-parse time (`litellm_schema.parse_answer`), not on the langchain path.** `langchain_fallback` uses `with_structured_output(Judgment)`: it receives the tightened schema (the override is on the class) but LangChain's parse is tolerant, so an omitted field still yields `defect_observed=None` and `_defect_decision` falls to the note guard (fail closed, unchanged). The contract names the "model-chain judge" / `litellm_provider`; say so if the legacy chain must be strict too.
4. **Effect of the reorder on `providers/agent_model.py::agent_chat_model`**, which takes `entries[0]`: with no Anthropic key and both Ollama and Gemini configured the agent layer now gets Ollama, not Gemini. That is the intended direction, not a separate edit.
5. **Root cause not closed by E2.4 alone** (as the contract says): the verbatim notes stay held; the remedy is E2.6 wording. Whether the prompt changes the real judge's wording is not measurable offline; the pinned reworded notes show what a prompted judge's output must look like to pass.
6. The ollama path validates `strict=True`; a string `"false"` from Ollama was already refused there. Unchanged.
7. **LC2 amendment owed** (`qa/contracts/langchain-fallback.md`: order and the OLLAMA_BASE_URL-only gate) belongs to the checker per the contract; `qa/contracts/` not edited. `tests/test_langchain_fallback.py` has no order assertion and passes unmodified.
8. Line endings: working tree is CRLF with `core.autocrlf=true`; edits preserved that.

## Verify (in `D:/autoTesting/.claude/worktrees/e2e-e2`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`, never the full suite: low memory)

```
tests/test_langchain_ollama_tier.py tests/test_judge_defect_required.py      -> 21 passed
tests/test_grade_e2e_notes.py tests/test_grade_note_guard.py                -> 90 passed
tests/test_grade_defect_field.py tests/test_grade_negative_path.py          -> 130 passed
tests/test_grade.py tests/test_grade_negative_path.py                       -> 42 passed
tests/test_langchain_fallback.py tests/test_prompt_skills.py                -> 29 passed
tests/test_litellm_provider.py tests/test_judge_defect_required.py          -> 28 passed
tests/test_gemini_schema.py tests/test_litellm_guard.py                     -> 34 passed
tests/test_grade_injection.py tests/test_grade_assertion_rule.py            ->  8 passed
tests/test_run_teardown_stall_wiring.py tests/test_langchain_ollama_tier.py -> 19 passed
tests/test_agent_model.py tests/test_video_evidence.py                      ->  4 passed
tests/test_user_persona.py tests/test_mutation_check_judgement.py           -> 27 passed
ruff check src tests scripts                                                -> All checks passed!
autotester doctor (redirected to .work/e2-doctor.txt, rc 0)                 -> doctor: clean
```

**Mutation evidence (C7), `scripts/mutation_check.py`, specs and logs in `qa/evidence/e2e-fixes-e2/`: 23/23 killed.**
- `mutations-chain.json` -> 8/8 (E2.1-E2.3: gate, order, Bearer header, default model, `OLLAMA_MODEL`, base url, narrowed `except`, winner id). Log: `mutation-run.txt` (first section).
- `mutations-schema.json` -> 8/8 (E2.4: required list, null alternative, default, reply check, null-vs-absent, repair path, `defect_observed=True` hold). Log: `mutation-run-2.txt`. The first run (in `mutation-run.txt`, 6/8) had two spec defects of mine, not test gaps: s3 deleted a block body (collection error, not a kill) and s2's textual replacement was not a clean mutant; both re-specified and re-run.
- `mutations-notes.json` -> 7/7 (E2.5/E2.6/E2.7: dropping `leak` from the lexicon, a bare-`rejected` cue, three SKILL.md deletions, the `{{FORMAT}}` placeholder, the `defect_observed=True` hold). Log: `mutation-run-3.txt`. The earlier notes run (`mutation-run-2.txt`, 5/7) exposed a wrong kill claim (n1 named a test that `_CONTRARY` also covers) and a missing control (n2 survived: no test held a bare rejection note); fixed by correcting the claim and adding `test_a_bare_rejection_note_with_no_expected_cue_stays_held`.
