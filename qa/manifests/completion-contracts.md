# Manifest — completion-contracts

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** Checker-owned foundational contract amendments for the approved Ollama-first completion plan.
**Branch:** codex/completion-contracts
**Base commit:** 4c7a9efd
**Owner authorization:** Umesh explicitly approved the full plan in this chat on 2026-10-15 and requested implementation through checker PASS.

## What changed
- `docs/DECISIONS.md`: D-099, appended only through the existing append_decision.ps1 script; no prior decision rewritten.
- `qa/contracts/langchain-fallback.md`: OC1-OC2, default model-chain versus explicit legacy providers, bounded physical attempts and validated JSON.
- `qa/contracts/ingest.md`: I4 amendment, real timestamped sampled image transport and behavioral vision capability.
- `qa/contracts/source-adapters.md`: SA7, all registered source kinds and searchable/scanned PDF extraction with provenance.
- `qa/contracts/orchestrator.md`: OR7, full CLI continuation with durable checkpoints and existing eligibility/approval boundaries.
- `qa/contracts/browser-and-secrets.md`: B11, fail-closed external image privacy and honest incomplete coverage for conservative text removal.
- `qa/contracts/providers-litellm.md`: current default examples, cloud JSON expectations and provider-neutral vision ownership.
- `qa/contracts/agent-fallback.md`: AF7, explicitly enabled production fallback only after deterministic failure.
- `qa/contracts/persona-ux-advisory.md`: PU10, production caller, actual execution conditions, retry accounting and functional-result preservation.
- `qa/contracts/run-case-pipeline.md`: RP4 amendment, script replay retains current-run evidence and independent grading.
- `qa/contracts/failure-bundle.md`: historical absence notes qualified, FB6 production integration, D-097 generation exception, explicit visual incompleteness.

## Verification and limitations
- Append script returned exit 0: `APPENDED: D-099 | type: decision | status: ACTIVE -> .\docs\DECISIONS.md`.
- `git diff --check` exit 0, no output.
- Diff is documentation-only; no runtime source, tests, dependency, schema, enforcement, credential or architecture file changed.
- No runtime tests/guards were added or rewritten; no mutation proof is claimed or required for these prose clauses. Future implementation units must prove their own guards per C7.
- Full pytest/Ruff/doctor were not run in this lightweight foundation pass; independent checker must record required validation or identify the limitation explicitly. No runtime/release PASS is claimed.
- Existing contract text remains historical evidence; effective new clauses name their narrow precedence. D-095/096/097/098 remain expressly protected.

## Checker request
Independently review this immutable branch commit for owner-approval fidelity, narrow amendments, historical append preservation, no accidental credential/enforcement changes and cross-contract consistency. Author verdict at `qa/verdicts/completion-contracts.md` with `Cycle checked: 1`; do not infer an implementation PASS from contract publication.
