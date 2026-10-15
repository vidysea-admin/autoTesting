# Manifest — provider-policy

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** Owner-authorized Ollama-primary/Gemini fallback and narration contract amendment.
**Branch:** codex/provider-policy
**Base commit:** b2b175da
**Authorization:** explicit owner provider/narration policy amendment in this chat, 2026-10-15; recorded as D-101.

## What changed
- `docs/DECISIONS.md`: D-101 appended through existing append_decision.ps1 only.
- `qa/contracts/langchain-fallback.md`: OC3 configured Gemini fallback on Ollama key/auth/service unavailability; no privacy/global-budget fallback.
- `qa/contracts/providers-litellm.md`: corresponding narrow default/fallback-boundary amendment.
- `qa/contracts/ingest.md`: configured capability-verified Gemini visual fallback, actual payload/provenance/privacy/accounting unchanged.
- `qa/contracts/source-adapters.md`: SA8 supplied transcript first; bounded local extraction plus guarded Gemini audio when Ollama lacks audio; no automatic local ASR/download.
- `qa/manifests/provider-policy.md`: this packet and evidence scope.

## Acceptance and checks
Documentation-only tier under D-100: no runtime, schema, dependency, enforcement, credential or test change; no pytest/build or mutation duty introduced by this prose-only unit.
`powershell -ExecutionPolicy Bypass -File scripts/append_decision.ps1 -EntryFile .work/d101.md -RepoRoot .` exit 0, APPENDED D-101.
`git diff --check` exit 0.
`python .work/verify_policy.py`: structural check independently rerunnable by checker (five normalized historical prefixes retained; unique sequential D-101; amendments present).
No runtime/release correctness, provider availability, credentials or audio capability is certified. D-095/096/097/098 remain unchanged. Unknown provider consumption is never zero by assumption.

## Compact checker packet
Read exact candidate/base diff and these five amendments only, applicable D-100 docs-only policy and authoritative manifest identity. Verify no runtime/enforcement/credential paths; previous decision/contract prefixes preserved; fallback eligibility and prohibited boundaries align; no supplied-transcript overwrite or automatic local ASR; no claim of live acceptance. Write `qa/verdicts/provider-policy.md`, Cycle checked 1, Reviewed SHA exact candidate; no intended verdict supplied. Fresh context required.
Maker elapsed/token/cost measurements before phase instrumentation are unavailable (null); command count is 3 tool-command phases through initial verification. No efficiency-success claim. Use bounded bootstrap reviewer scope (180 seconds/6000 allocated tokens) with skill assessment before phases; required checks are scoped diff/structural only. Future runtime implementation and combined release gates remain separate.
