# Verdict - e2e-fixes-e2 (E2.1-E2.7; AT-1413, AT-1414)

**Verdict: PASS**
**Cycle checked:** 0
**Checked:** `feat/e2e-e2` head `6d630ed5` (base `dccc65e9`), worktree `D:/autoTesting/.claude/worktrees/e2e-e2`. Fresh context; read-only toward `src/` and `tests/`. Fakes only: no network, no `.env` value read or printed.
**Contract:** `qa/contracts/e2e-fixes.md` unit E2. **Manifest:** `qa/manifests/e2e-fixes-e2.md`.

## Commands re-run by the checker (2 files per call, `env -u ANTHROPIC_BASE_URL uv run pytest <files> -o addopts= -q`)

| Files | Result |
|---|---|
| test_langchain_ollama_tier + test_judge_defect_required | 21 passed |
| test_grade_e2e_notes + test_grade_note_guard | 90 passed |
| test_grade_defect_field + test_grade_negative_path | 130 passed |
| test_langchain_fallback + test_litellm_provider | 31 passed |
| test_prompt_skills + test_gemini_schema | 29 passed |
| test_litellm_guard + test_grade | 34 passed |
| test_agent_model + test_grade_injection | 4 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor` (to `.work/e2-chk-doctor.txt`) | rc 0, `doctor: clean` |

Full suite not run (machine low on memory, per the brief); the touched surfaces and every hold suite named by E2.5 were run.

## Per-criterion findings

1. **E2.1 PASS.** `providers/langchain_fallback.py:76` gates on `ollama_cloud.base_url()` (explicit `OLLAMA_BASE_URL`, else cloud URL when `OLLAMA_API_KEY` set); `_make_ollama` `:47-58` sends the Bearer header only with a key, model = GLM minus prefix, `OLLAMA_MODEL` overrides, `llama3` for a bare local URL. Own probe (`.work/chk-schema.py`): env `{}` -> `[]`; `{OLLAMA_API_KEY}` -> `['ollama']`; `{OLLAMA_BASE_URL}` -> `['ollama']`. Factory not invoked while building the chain (test blocks `langchain_ollama` in `sys.modules`).
2. **E2.2 PASS.** Own probe with all four credentials: `['anthropic', 'ollama', 'gemini', 'chatgpt']`.
3. **E2.3 PASS.** `test_e2_3_*` (fake chain entries both orders, `provider.id` asserted); `_call`/`_try_tier` unchanged in the diff. Mutants m7 (narrowed except) and m8 (winner id) killed.
4. **E2.4 PASS.** (a) own probe: `Judgment.model_json_schema()` -> `required: ['result','defect_observed']`, `defect_observed` is `{"type":"boolean"}`, no anyOf/null/default (`schema/verdict.py:99-120`); the Gemini path (`litellm_schema.json_schema_for`) carries the same required list. (b) `litellm_schema.py:90,94-105` raises a pydantic `ValidationError` for absent/null (field path, `input: None`, so no reply text enters the repair prompt), taking the existing repair retry in `litellm_provider._structured` (untouched), then `ProviderError`; test asserts exactly 2 calls, then `run_and_grade_case_resilient` -> INCONCLUSIVE with `ProviderError`/`defect_observed` in `note`. (c) `false` parses and grades as before; `true` still downgrades a PASS. (d) `Judgment(...)` without the field constructs (own probe: `construct ok`); `tests/test_grade_defect_field.py` green unmodified.
5. **E2.5 PASS (mechanical).** `git diff --name-status dccc65e9 HEAD -- tests src/autotester/stages` shows no change under `stages/` and no existing test edited; the only modified test-tree file is `tests/fixtures/golden_prompts/grade.md` (SK3 golden refresh for the E2.6 bullet; `test_prompt_skills` green). Hold suites (note_guard, defect_field, negative_path) pass unmodified: 90 + 130 passed.
6. **E2.6 PASS.** `skills/grade/SKILL.md` gains one bullet after the `defect_observed` bullet: "correctly rejected" / "as expected" for an expected rejection, positive-terms PASS notes, no defect vocabulary even inside a negation; ends "This is wording only: a real defect is still reported as a defect". It does not name the guard. Placeholders and untrusted-evidence paragraph intact (tests green).
7. **E2.7 PASS, with a contract correction (see ruling 1).** Verbatim a5ea and cfa4 notes held (INCONCLUSIVE), reworded notes PASS, controls (positive-path rubric, `defect_observed=True` x2, genuine contrary marker x2) held.

## Mutation evidence (C7), run by the checker with `scripts/mutation_check.py`

- Maker specs re-run in full: chain 8/8 killed, schema 8/8 killed, notes 7/7 killed (23/23). Every mutant killed by the test it claimed (schema s5 and s7 also failed extra tests, which is fine).
- Checker's own spec `.work/chk-mut.json` (4/4 killed, worktree clean afterwards):
  - c1 Ollama gated on `OLLAMA_API_KEY` only -> killed by `test_e2_1_a_base_url_alone_still_adds_it` (and the local-daemon test).
  - c2 Bearer header sent with no key -> killed by `test_e2_1_a_local_daemon_keeps_its_url_default_model_and_sends_no_header`.
  - c3 `required` marking never appended -> killed by 3 schema tests (json-mode, tool/schema parity, Ollama call).
  - c4 reply check rejects absence only, so null is accepted (the spec label wrongly says "list") -> killed by `..._provider_error[null]`.

## Rulings on the five maker deviations

1. **`wrong-password` stays held: the CONTRACT wording was wrong; no guard change is authorized or needed for this unit.** Checker-run (`.work/chk-hyphen.py`, MockProvider via the maker's `_grade`): the contract's literal "The wrong-password login was correctly rejected: ..." -> INCONCLUSIVE; the spaced form -> PASS. Cause: `_CONTRARY` contains `wrong` (`stages/grade_note_guard.py:90-93`) and `_QUALIFIED_INPUT` (`:102-103`) strips only whitespace-separated "wrong <input>". E2.5 forbids the guard change, so the maker's spaced pin is correct. I amended the contract (`e2e-fixes.md` amendment log) so the pinned example is the spaced form. **Residual (WARNING, not blocking):** the real a5ea note used "wrong-password" (criterion c1) and the SKILL.md bullet does not steer the judge off the hyphen form, so a prompted judge may still be held on that exact phrasing. Closing it means widening `_QUALIFIED_INPUT` to accept a hyphen after `wrong`/`incorrect` in `grade_note_guard.py`: a separate Umesh-gated decision (HUMAN_GATE), with the verbatim hold tests updated deliberately. Not authorized here; E2's own deliverables (prompt wording + required field) are met.
2. **`ProviderError` -> INCONCLUSIVE only via `run_and_grade_case_resilient`: accepted.** `grade()` has no ProviderError handler (`stages/grade.py` only `except ValueError` at `:157`); the conversion is `stages/run_case_pipeline.py:271-276` (AT-573), the production path. Adding a catch to `grade()` would swallow `AvailabilityFailure`. The contract's "grade() returns INCONCLUSIVE" was loose; clarified in the amendment log.
3. **Legacy langchain parse stays tolerant of an omitted field: accepted.** Contract E2.4 names the model-chain judge (`litellm_provider`, `json_mode_instruction`, `request_options`). On the langchain path the model still receives the tightened schema (class-level override); an omitted value yields `None` and falls to the note guard, i.e. fail closed, unchanged (C12). Not a loosening.
4. **`agent_chat_model` now gets Ollama first: accepted, intended direction.** `agent_model.py:22-26` takes `entries[0]` of `_default_chain()`; with no Anthropic key and Ollama + Gemini configured it now gets Ollama (matching `autotester providers`). Observation (low, no action): with BOTH `OLLAMA_API_KEY` and an explicit local `OLLAMA_BASE_URL` set, `_make_ollama` sends the key to that URL and defaults the model to the cloud GLM id; a mixed config is unusual and `OLLAMA_MODEL` overrides it.
5. **LC2 amendment: written** (`qa/contracts/langchain-fallback.md`, sections LC2a order Anthropic -> Ollama -> Gemini -> ChatGPT and LC2b Ollama gated on `OLLAMA_API_KEY` or `OLLAMA_BASE_URL`), and the corrections of rulings 1 and 2 are logged in `qa/contracts/e2e-fixes.md`.

## Not verified / limits

- Whether the amended judge prompt changes the real model's wording is not measurable offline (the maker said the same); the pinned reworded notes show what a passing note looks like. Re-measure on the next live Pathlynks run (a5ea/cfa4-style cases).
- Full suite not run (memory); no cross-run of unrelated test files beyond those listed.

## Ledger / next

- Worth a HUMAN_GATE row for the hyphen residual above (guard widening); not filed by this pass.
- Maker: close out the manifest (`checked-PASS`). Per D-007 the push happens after the merge to `master`; this pass pushes nothing.
