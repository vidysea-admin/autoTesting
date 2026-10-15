# Mixed teaching — guarded text proposal core

Status: checked-PASS
Fix cycle: 1
Root: C:/Users/product/Desktop/autoTesting/.work/wt-mixed
Base SHA: f5da2cd9d81f530e47a209654e448294c79734c8
Code candidate SHA: 4e3e94c97c52be5d867812492893ec77665e4ec9
Review candidate: the evidence-only wrapper HEAD containing this canonical packet; code blobs equal Code candidate SHA.
Unit: mixed-teaching-text-core (bounded first subunit of SA7; no full mixed-source completion claim)
Risk tier: high-risk (shared structured schema and secret/PII boundary).
Maker tokens/cost/active seconds: unknown (host does not expose task accounting; do not infer from wall time).

## Scope and acceptance

D-099 / source-adapters.md SA3, SA4, SA6 and SA7: text-role teaching uses Provider.act,
credentials and PII scrubbed and guarded before call and before return; output cites exact supplied
section/page locators and the registered source ID; no synthetic video timestamps; adapter never
selects product checks or persists/approves existing truth. Core C1-C7/C9 apply. D-097 eligibility
is deliberately deferred to the aggregate caller: this stage returns an unreconciled DRAFT.
It must refuse wrong-project/video inputs, missing/duplicate/oversize units, unknown model locator
or screen references and duplicate/unordered steps. Returned output is a proposal only.

New modules have separate jobs: schema/teaching.py owns extracted units and text-role response
family; stages/teach_text.py owns guarded prompt/model-to-FlowSpec conversion, independent of
store/dispatch/cache/reconciliation; prompt file owns instructions; test module owns fake-provider
boundary verification. No existing module is duplicated; video mapping uses a timestamp-dependent
schema and cannot represent text evidence without inventing time.

Changed tracked paths (only these four code/test paths in candidate):
- src/autotester/schema/teaching.py
- src/autotester/stages/teach_text.py
- src/autotester/prompts/teach_text_v1.md
- tests/test_teach_text.py

Canonical tracked review request: qa/manifests/mixed-teaching-text-core.md (this file).
Ignored raw evidence: .work/teach-text-evidence/, .work/teach_text_mutations.py,
.work/validate_teach_text_packet.py. No unrelated untracked files.
Immediate consumers: none in this first core unit. CLI/UI dispatch is next unit, explicitly not shipped here.

## Evidence and commands

Existing retained interpreter: C:/Users/product/Desktop/autoTesting/.venv/Scripts/python.exe
Set PYTHONPATH to the candidate's absolute src directory; PYTHONDONTWRITEBYTECODE=1.
No browser, network, provider/API call or full suite was used.
Normal preflight temp writability failed WinError5; authorized escalation passed. Persisted
preflight receipt: .work/teach-text-evidence/preflight.log (3.11.16, correct import containment).

Selected nodes and coverage rationale (all 11 passed):
- tests/test_teach_text.py::test_text_proposal_retains_locator_expectation_and_stays_unreconciled —
  source/locator mapping, null timestamps, expectations, draft/kind and deterministic fingerprint.
- tests/test_teach_text.py::test_invalid_model_references_are_refused[locator]
- tests/test_teach_text.py::test_invalid_model_references_are_refused[screen]
- tests/test_teach_text.py::test_invalid_model_references_are_refused[orders]
- tests/test_teach_text.py::test_invalid_model_references_are_refused[duplicates]
  — distinct unknown-citation/screen/order/duplicate-name rejection paths.
- tests/test_teach_text.py::test_input_and_model_output_secrets_and_pii_are_scrubbed[input]
- tests/test_teach_text.py::test_input_and_model_output_secrets_and_pii_are_scrubbed[output]
  — independent prompt and returned-artifact privacy boundaries with actual stage execution.
- tests/test_teach_text.py::test_invalid_input_never_calls_provider[empty]
- tests/test_teach_text.py::test_invalid_input_never_calls_provider[duplicate]
- tests/test_teach_text.py::test_invalid_input_never_calls_provider[project]
- tests/test_teach_text.py::test_invalid_input_never_calls_provider[video]
  — empty/duplicate evidence and scope/type refusal before the fake provider.

Each execution uses -m pytest <nodes> --basetemp .work/teach-text-evidence/<name>-temp
--junitxml .work/teach-text-evidence/<name>.xml (no extra CLI -q).
The harness initially ran the explicitly scoped 11-case module as one batch; a fresh checker should
select node IDs for the claims being independently checked rather than expanding the scope blindly.
Final green: green-repeat2.{json,log,xml}; six applied mutations: red-{model-refs,privacy,inputs,
units-empty,units-duplicate,provenance-repeat2}.{json,log,xml}; matching restored-*.json/log/xml.
Every mutation matched one anchor, changed real source, yielded exit1 with the specified test names
in XML failures, restored source and yielded exit0. The initial provenance mutation receipts are
preserved but superseded by repeat2 because source newline normalization changed physical hashes.
All later guards already used the normalized source identity. The failed pip-freeze collector
attempt occurred before any mutation; dependency capture uses importlib.metadata on the same venv.

Contemporaneous receipts contain all four file hashes, Python version/path, uv.lock hash, installed
package versions, per-command timing/exit and full log hash. Packet validation recomputes current
file/log hashes, before/after identity, dependency/lock compatibility and named XML failures:
C:/Users/product/Desktop/autoTesting/.work/wt-mixed/.work/validate_teach_text_packet.py
Result: .work/teach-text-evidence/packet-validation.json = READY.

Scoped lint exit0: -m ruff check src/autotester/schema/teaching.py src/autotester/stages/teach_text.py
tests/test_teach_text.py; .work/teach-text-evidence/lint.log.
Applicable doctor file/function/duplicate/filename checks on changed surfaces exit0:
.work/teach-text-evidence/doctor.log. Full doctor/generated docs and full combined pytest/ruff are
integration obligations, not certified by this unit.

## Remaining obligations and limits

No source gathering, PDF receipt/transcript adapter, source-set snapshot/resume/cache, multi-source
aggregation/conflicts/dedupe, configured-role resolution, production CLI/UI caller or D-097 kind
reconciliation is implemented by this core unit. Do not report complete SA7 or no-CLI teaching.
Citation validation proves locator membership/referential consistency, not semantic truth of a model
claim. Existing human review remains available. No approved FlowSpec bytes are read or written.
Fresh independent checker alone owns the verdict. No self-PASS or push performed.

