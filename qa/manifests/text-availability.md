# Availability-only Gemini text fallback

Status: ready-for-check
Fix cycle: 1
Risk tier: high-risk (shared Provider boundary, secrets and attempt caps)
Base SHA: 40f5b4b20e91d3806ee313fb8e67af109b62b0ae
Immutable runtime/test SHA: 1ecf58cef26e96b713c005e1b089363e4a7fbc18
Policy-synchronized candidate SHA: aa7813ad20c6ead5012559d9f9961b2a15338d56
Root: C:/Users/product/Desktop/autoTesting/.work/provider-availability

## Scope and authorization

D-101/D-102, checked authoritative policy at Base SHA, permit configured Gemini
availability/capability fallback while Ollama remains primary. This unit implements
TEXT ONLY: GLM, DeepSeek, then `gemini/gemini-3.6-flash` through LiteLLM. The official
model list confirmed that stable endpoint on 2026-10-15:
https://ai.google.dev/gemini-api/docs/models.md . `AUTOTESTER_TEXT_FALLBACK_MODEL`
overrides the implicit final model; explicit model lists and
`AUTOTESTER_MODEL_ORDER` retain their exact order. Primary success makes one call.

Default image-bearing calls omit the implicit Gemini tier. Video/audio/narration,
Gemini SDK client generation/upload/poll, vision capability verification, and
default migrations are excluded; their bounded operation is NOT certified here.
The existing root .env and all credential values remain untouched. No browser,
live product/API/model request, installation, merge into master or push performed.
Only policy/docs master synchronization was merged into this isolated branch.

## Complete runtime/test surface and immediate consumers

- `providers/availability.py`: new single responsibility, payload-free transport
  taxonomy. Authentication401 or declared AuthenticationError; service502/503/504,
  builtin connection/timeout or declared APIConnectionError/ServiceUnavailableError/Timeout;
  explicit Provider Unsupported. No generic403/400/429/schema/refusal fallback.
- `providers/litellm_provider.py`: normalize only allowlisted physical failures;
  strict validation option; model-setting names excluded from secret-value scan.
- `providers/model_chain.py`: append default text fallback, skip unavailable keys,
  exclude default media fallback, preserve explicit order, terminal refusal/budget
  paths, thread-local safe fallback reasons and actual winner/usage attribution.
- `tests/test_text_availability.py`: 15 parametrized offline cases.
- `tests/test_model_chain.py`: defaults, eligible failures and safe logging aligned.
- `tests/test_provider_attempts.py`: repair/fallback budget fixture uses eligible timeout.

Immediate consumers are registry `for_role`, CLI defaults and all existing
LiteLLM agent/judge callers. No stage prompt or authorization contract changed.
Malformed output retains at most one in-tier JSON repair, then terminal failure;
an invalid answer never becomes an availability failure. No added prompt text.

## Criteria and evidence

OC2/OC3/D-102 and LL5/LL6/LL7: each Gemini TEXT physical call uses the existing
`reserve_attempt`, every enclosing count/deadline, remaining-time timeout and
`num_retries=0`. Unknown tokens stay null. No Gemini SDK call is reached.
C5/C8/C9/C12: privacy/policy/authorization/generic errors stop; unavailable key
skips are explicit; actual serving model, safe reason tuple/logs and failed usage
remain observable. Outer exhaustion propagates without trying another provider.
C1-C3/C11: no new domain shape or dependency; source caps35/156/294 lines and no
function over50. Independent grading and target write authorization are untouched.

`qa/evidence/text-availability/checks.json` binds exact commands, source fingerprints,
exit codes and output hashes. Selected immediate consumers: **100 passed**;
scoped lint: exit0; own-source candidate and scratch preflights: exit0.
`packet-bindings.json` pins interpreter, fixture/config/contracts and supplemental
receipts. `environment.json` pins Python3.11.16, dependencies and unchanged lock.
Missing Gemini credentials: offline probe yields unavailable after2 Ollama calls,
zero Gemini requests. Each outer cap/timeout remains enforced before transport.

Doctor's corrected command exits1 solely for stale generated MAP/SNAPSHOT; source
rules are clean. Initial `python -m autotester doctor` was an invalid entrypoint
(package has no __main__) and is preserved, not offered as behavioral evidence.
Earlier sandboxed test setups could not create temporary directories; they were
not counted as product failures or reused. Escalated local-temp runs supply the
claimed evidence. The exact combined integration candidate still needs generated
docs plus full pytest, full ruff and doctor. No integration/release PASS claimed.

## Falsification and compatibility

Complete cache-free scratch copy includes src/tests/scripts plus
tests/tests_mutation_fixtures.py, pyproject.toml and uv.lock; no pycache reused.
`mutations.json`, executed `run-proof.py`, `receipts.json` and every named output
record baseline30 green, all18 semantic mutations red (exit1 and named defending
test), each focused restoration green, and final30 restored green. Guard mapping:
auth/service/network/capability eligibility; terminal policy taxonomy/chain gate;
strict repair; global count/deadline; media exclusion; explicit order; missing
credentials/model override; secret guard; null usage; timeout; retries; visible reason.
The checker must independently probe every affected safety boundary; representative
mutation reuse does not replace those checks.

One new source file's scratch writer changed LF to CRLF. Raw hashes differ and are
preserved in `source-binding.json`; `canonical-source-binding.json` re-derives exact
canonical-text and AST equality for every runtime/test file. Existing files match
raw hashes. No semantic source difference is concealed by the normalization.
The100-test candidate run uses the actual candidate source, not the scratch tree.
The policy sync changed only docs/contracts/manifests/verdicts, not runtime/lock.

Maker active seconds/tokens/cost: unknown (null). Checker ratios: unverified.
Use D-100 fixed bootstrap with the high-risk checks; do not infer a denominator.
Candidate diff/complete file inventory derive from `git diff BaseSHA..HEAD`;
packet artifacts are evidence only. Historical checked-PASS units remain historical.
