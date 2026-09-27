# Verdict — at265-gemini-schema-allowlist

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent + orchestrator capability re-run

```
VERDICT: PASS
SCOREBOARD: AT-265 met: const→enum, tuple prefixItems dropped, oneOf→anyOf, N-member null collapse, additionalProperties still excluded; zero change for every schema shipped today
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced against the NAMED pytest tests (orchestrator copy c265-rows: baseline 6 passed; admit const → test_a_single_value_literal_becomes_enum_not_const red (plus the drift guard); admit prefixItems → test_a_tuple_drops_prefixItems_rather_than_leaking_it red (plus the drift guard); delete the oneOf branch → test_a_discriminated_union_becomes_anyOf_not_a_dropped_oneOf red only; restore the 2-member guard → test_a_three_way_union_with_none_collapses_the_null_branch red only; add additionalProperties → test_ALLOWED_KEYS_matches_the_installed_SDKs_actual_field_set red only; restored 6 passed). The manifest's own rows used scratch claim functions, so this re-run is what binds them to the tests.
LIVE-BROWSER: not-applicable (providers/gemini_schema.py, tests/test_gemini_schema_allowlist.py)
ISSUES-WRITTEN: none
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: Every production response schema (VideoObservation, Judgment, AgentFix, ExpandedSteps, RelitigationVerdict, GeminiTranscription) renders byte-identically under the base and branch sanitisers and validates as google.genai.types.Schema offline, so the change is purely latent-hazard coverage. ALLOWED_KEYS is a literal derived from google-genai 2.22.0, with a drift-detector test that fails loudly on an SDK upgrade. tests/test_gemini_schema.py is byte-identical to base.
```

Evidence: subagent: targeted 3 files 27 passed · ruff clean · doctor clean · diff vs bb4be39 = manifest, providers/gemini_schema.py, tests/test_gemini_schema_allowlist.py · 4 independent hazard probes: base emits const/prefixItems/oneOf → Schema.model_validate extra_forbidden; branch valid. Caveat: Schema validation is stricter than the fake client but is not the live endpoint (Type is a CaseInSensitiveEnum and accepts any string with a warning).
