# Mixed teaching — registered aggregate core

Status: checked-PASS
Fix cycle: 1
Root: C:/Users/product/Desktop/autoTesting/.work/wt-mixed-aggregate
Base SHA: 3eddfab6add8f41e50b73a0f30fada041931a18d
Code candidate SHA: d1064e85106ea71cf724475e81c054e7b10d8863
Review candidate: evidence-only wrapper HEAD containing this packet; all code/test blobs equal Code candidate SHA.
Unit: mixed-teaching-aggregate-core (bounded SA7 aggregate adapter; production callers deferred)
Risk: high (shared persistence, model dispatch, privacy, immutable resume).
Maker active seconds/tokens/cost: unknown; host accounting unavailable. Ratio unverified; checker must use explicit bounded bootstrap rather than claim measured compliance.

## Behavior and contract

D-099 source-adapters SA1-SA7, core C1-C7/C9, D-097 proposal reconciliation and D-100 scoped proof apply. Every registered source enters one sorted immutable snapshot before Provider creation. Text/email/document/PDF/supplied audio narration use checked teach_text/Provider.act; VIDEO alone uses existing visual ingest. No raw document enters video, invented timestamp, ASR, download, raw-audio image upload or implicit provider fallback.

Actual document bytes and typed page/method/confidence receipts, source/page/section/transcript citations and supplied transcripts determine material. Path-only DOC reuses the checked extractor. Drive uses registered resolved body/children, with unresolved metadata explicitly incomplete. EVAL/CONDITION/USE_CASE remain declared inputs. Missing/unreadable narration is unavailable, never proof of silence; missing audio is incomplete and video can be partial with visuals.

Raw source/receipt/sidecar bytes bind resume, including malformed readings. Semantic evidence ignores per-artifact envelope for dedupe. Supplied sidecar parsing cannot introduce transient timestamp drift. Changed source set/content/bytes/reading requires a new run before another model call. Source/project misattribution is refused. Outcomes persist before/after calls; successful, failed and uncertain interrupted calls cannot silently repeat on resume. Duplicate outcomes retain their own errors and failed canonical duplicates do not cause a second call. Merge preserves conflicts; proposal is run-local DRAFT/reconciled and never loads or overwrites canonical APPROVED truth. Input/output privacy guards run before transport/persistence.

One-place domain shapes: schema/teaching_run.py. source_material resolves material; teach_sources owns snapshot/dispatch/cache/merge. Existing checked teach_text, PDF extraction, merge/reconcile, video ingest and Provider boundary reused. Prompt remains existing checked prompt file. No schema/project or providers changes. RUN_AUX_FILES registers exactly the two root teaching artifacts so all existing result-reader consumers skip them; nested per-source receipts stay outside its nonrecursive glob.

Changed code/test paths (13):
- src/autotester/schema/teaching_run.py
- src/autotester/stages/source_material.py
- src/autotester/stages/teach_sources.py
- src/autotester/stages/ingest.py
- src/autotester/store/run_store.py
- tests/teaching_helpers.py
- tests/test_teach_sources.py
- tests/test_teaching_inputs.py
- tests/test_teaching_privacy.py
- tests/test_teaching_documents.py
- tests/test_teaching_media_dedupe.py
- tests/test_ingest_persist.py
- tests/test_ingest_real_cli.py

Tracked request: qa/manifests/mixed-teaching-aggregate-core.md. Ignored evidence/scripts only in .work/teaching-aggregate-evidence/, .work/aggregate_mutations.py, .work/scoped_aggregate_checks.py, .work/validate_aggregate_packet.py. No unrelated untracked feature paths.

## Verification and readable test scope

Retained interpreter C:/Users/product/Desktop/autoTesting/.venv/Scripts/python.exe (3.11.16), candidate/copy absolute src PYTHONPATH. Complete isolated src+tests+scripts copy, including tests_mutation_fixtures.py/regression_proof.py; cache files excluded. Preflight confirms interpreter/import containment and writable basetemp. Known ACL failures require authorized escalation; no new environment. No network/live API/browser/full suite.

Final receipts: .work/teaching-aggregate-evidence/attempt6/. baseline.json/log/xml contains exact command and all 39 passing test instances. mutations.json is the compact per-guard map: exact source anchor/replacement and named expected failure node IDs. Each red/restored receipt binds candidate/source hashes, interpreter/import root, lock/dependencies/config, execution result, observed timestamp, log/XML hashes and exact failures. Only one isolated subject changes; all other bytes preserved. Final candidate never mutated. harness.py preserves exact producer. scoped-checks.json binds exact-path ruff and applicable doctor size/function/duplicate/name/root rules. packet-validation.json seals all receipts and verifies complete copy, unchanged source/environment, named failures and restored bytes.

Selected test functions (parameter IDs remain in XML and mutation map; no generic group required):
- test_teach_sources.py: test_every_registered_type_is_consumed_with_citations_and_resume_cache (all types/provenance/cache); test_partial_pdf_keeps_readable_pages_and_reports_incomplete (reading/page/note); test_missing_audio_or_resolved_content_is_explicit_without_model (audio/Drive/URL); test_duplicate_evidence_is_one_model_call_and_conflicts_remain_visible (dedupe/conflict/own errors); test_failed_provider_is_redacted_and_cached_without_repeat (failed canonical duplicate/cache); test_invalid_or_interrupted_receipt_never_repeats_a_model_call (fingerprint/proposal/running); test_aggregate_never_rewrites_approved_canonical_bytes (literal persistence bytes); test_empty_registered_set_is_incomplete_without_model.
- test_teaching_inputs.py: test_changed_actual_input_requires_new_run_before_model (set/text/bytes/transcript/receipt); test_stale_or_misattributed_content_never_reaches_provider (bytes/video_bytes/receipt_source/transcript_source/project).
- test_teaching_privacy.py: test_video_prompt_and_returned_artifact_cross_privacy_guard (input/output); test_encoded_teaching_secrets_fail_closed_at_their_boundary (label/model); test_video_without_supplied_narration_is_partial_without_transcription.
- test_teaching_documents.py: test_lazy_pdf_retains_page_method_confidence_and_freezes_its_reading; test_corrupt_receipt_edit_requires_new_run_without_a_provider (DOC/AUDIO malformed actual receipt bytes).
- test_teaching_media_dedupe.py: test_duplicate_media_uses_transcript_content_not_its_envelope; test_supplied_sidecar_resume_is_stable_but_changed_bytes_require_new_run (both AUDIO/VIDEO).
- Immediate existing ingest consumers: test_ingest_persist.py::test_absent_narration_is_unavailable_instead_of_claiming_silence; test_ingest_real_cli.py::test_a_recording_without_a_sidecar_reports_unavailable_narration. Old names intentionally replaced; no tracked evidence reference found to old names.

Bounded immediate-consumer review: run artifact enumeration centralizes in ProjectStore.load_results; reports, UX, retention, bench and run service delegate there. Source sidecars and cache-resume are covered below; this core never invokes canonical merge/persistence.

Prior attempts retained: initial focused20/final24; root attempt1 failed missing fixture collection; attempt2 failed auth fixture setup; attempt3 baseline31 and partial mutation proof stopped on overly broad expected-failure attribution; attempt4 complete baseline33/31 mutations but superseded by media fixes. media-regression red2 established envelope defect, media-green passed2; sidecar-regression red2 established transient sidecar drift, final-focus passed6. Attempt5 baseline38/partial proof stopped for direct reader compatibility; consumer-red reproduced teaching-inputs.json parsed as RawResult, consumer-green passed1. test_teach_sources.py::test_teaching_artifacts_do_not_enter_case_results guards both registrations with separate mutations. These are maker attempts, never hidden or claimed as current candidate proof. No checker work charged as maker.

## Deliberate boundary and required follow-on

This unit's production consumer is not yet wired: CLI INGEST/MODEL and UI sources teaching must call the same aggregate stage in a later reviewed unit. No all-source end-user completion claim. That caller must prepare authorized narration before freeze, retain per-source outcomes, use configured role callback, return run-local proposal artifact and preserve canonical APPROVED bytes plus NEEDS_EDIT blocking status through the existing merge/reconcile/generatability gate. Current legacy MODEL behavior is not excused by this core test; direct caller persistence fix remains required.

Future guarded Gemini narration SDK/caller integration belongs to narration owner; this core reads supplied transcripts offline and truthfully marks missing narration incomplete. Full downstream CLI execution/generation and production-call integration tests are separate ownership. Parent must run combined mandatory integration/release suite and provider/security gates at integration; scoped evidence does not replace those. Independent checker alone may issue verdict. No self-PASS or push.

Final readiness: READY; 39 green cases, 35 named RED/restored-GREEN guard mutations, scoped lint/design clean.
Packet-validation SHA256: 9c523f44553fd3817e0da6a6ca19a381580e557ca133bd80798aecad17910cc8
Sealed receipt count: 87. No code/test changes after d1064; wrapper is evidence only.
