# Manifest — ollama-only-defaults

**Status:** checked-PASS
**Fix cycle:** 1
**Root:** C:/Users/product/.codex/worktrees/ollama-provider/autoTesting
**Branch:** codex/ollama-provider
**Base SHA:** abc4a0ef
**Candidate code SHA:** 003dc974f87b64ce0a084a5bfe6c91c9515ba4b5
**Unit:** Ollama-only agent/judge defaults and cloud JSON validation, authorized by Umesh's completion-plan approval and D-099. This is a bounded subunit, not all of OC1/OC2.

## Acceptance and actual behavior
- qa/contracts/langchain-fallback.md OC1: shipped chain is GLM then DeepSeek, no implicit Gemini. Explicit project/server model-order overrides remain. Vision default remains a following unit.
- qa/contracts/providers-litellm.md LL amendment, OC2 JSON subset: Ollama uses schema-bearing prompt JSON, sends no native response-format or forced tools, strictly validates typed JSON, and repairs at most once. Other vendors retain prior strategy selection. Failure accounting, total attempt budgets, vision transport/probes and agent adapter remain following units; no complete OC2 claim.
- Core C5 credential boundary and C7 mutation discipline remain. No secrets were printed or changed; no live inference/browser used.

## Declared changes and consumers
Source/test changes: providers/model_chain.py, providers/litellm_provider.py, providers/litellm_schema.py; tests/test_model_chain.py and tests/test_litellm_provider.py. No new production module. Evidence resides qa/evidence/ollama-only-defaults/. No other untracked implementation paths; .work scratch is excluded.
Immediate consumers: providers.for_role defaults (registry), chain act/judge fallback, CLI's existing DEFAULT_SPEC, grading through LiteLLM. No stage, schema or CLI interface changed. parse_answer gains optional strict flag. Existing vision config untouched intentionally.

## Maker checks and rationale
Python C:/Users/product/Desktop/autoTesting/.venv/Scripts/python.exe, Python3.11.16; PYTHONPATH=<Root>/src; no separate venv. Preflight import identity and writable .work passed; history.json records receipt. checks.json contains exact command, lock hash and timings; check-0.log/check-1.log contain complete output.
- pytest tests/test_model_chain.py tests/test_litellm_provider.py tests/test_litellm_guard.py -k 'not real_sdk' --tb=short: 50 passed in29.71s (39.015s command wall), no deselections. The expression matches no existing name: all tests, including no-network SDK refusal, ran.
- Scoped Ruff for the five changed files: exit0,0.250s.
- Scoped AST cap check: all five files <=300lines, functions <=50lines.
Relevant node IDs: tests/test_model_chain.py::test_default_order_is_ollama_only_and_schema_default_uses_it (default/factory); ::test_falls_back_in_order_on_error_and_timeout (timeout fallback); ::test_unconfigured_tier_is_skipped (explicit legacy override); ::test_secret_in_prompt_is_refused_once_and_never_sent (secret boundary); tests/test_litellm_provider.py::test_ollama_cloud_uses_json_even_when_sdk_advertises_schema (JSON repair/no native format); ::test_ollama_answer_rejects_coerced_types (strict values). Remaining file tests cover existing image, errors, guards, usage and strategy consumers.

## Mutation proof
mutations.json: green asserted baseline, six named attributable kills: defaults, fallback_order, explicit_override, cloud_json, cloud_no_native_format, strict_types. prove.py contains exact single-hunk edits, unique-anchor assertions, applied-byte assertion, per-command90s timeout and finally restoration. Copy excludes __pycache__ and disables bytecode. Run from Root with the same Python; set PROVIDER_PROOF_OUTPUT to a fresh evidence directory to preserve original receipts. Re-run uses .work/provider-mutation-copy, never modifies bound production source.
Earlier isolated-copy missing-fixture errors and zero-failure availability-filter mutation are retained honestly in history.json; neither counted as proof. Strengthened explicit-override mutation kills its intended test.

## Review budget and remaining gates
Read C:/Users/product/.agents/skills/checker/SKILL.md. review-metrics-dispatch.json and review-assessment-dispatch.json authorize BOOTSTRAP_REVIEW, finite180active seconds/6000allocated tokens. Maker total active time/tokens unavailable (null); ratio unverified. Measured command times above are not inflated into maker denominator. Initial invalid budget-shape attempt retained separately; no reviewer has run yet. Parent dispatches independent reviewer, no self-PASS.
Full combined pytest/Ruff/doctor release gates remain due once on integrated candidate under D-100; no blanket per-unit omission. Later vision/defaults, failed-attempt accounting, image privacy and live capability evidence remain unimplemented by this subunit. No push authorized here while remote reconciliation is pending.
