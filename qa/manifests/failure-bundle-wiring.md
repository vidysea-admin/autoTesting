# Manifest — post-run failure bundles and report links

- Status: ready-for-check
- Fix cycle: 1
- Base: f5da2cd9
- Candidate: exact scoped commit SHA is recorded in the post-commit checker packet
  `.work/failure-bundle-evidence/checker-packet.md`.
- Authorization: approved completion plan, D-099; bounded production bundle/report wiring.
- Contracts: failure-bundle FB1–FB3, FB6; browser-and-secrets B11; report-export RE1/RE5;
  core-invariants C1–C8/C10/C12; D-100 unit review policy.
- Tier: high_risk (privacy/secrets, persisted schema, production launcher).

## Changed behavior and ownership

`run_launcher.save_tracked_run` invokes bundle assembly after saving the functional Run and
tracking its bugs. FAIL, INCONCLUSIVE and BLOCKED verdicts receive one existing atomic-writer
bundle each; PASS is excluded. RawResult, Verdict and Run bytes are never rewritten by assembly.

`schema/failure_bundle.py` adds typed assembly outcomes and the run-local index. New
`stages/run_artifacts.py` owns production assembly and validated report lookup, keeping this
separate responsibility out of the already capped launcher/report modules. It reuses the existing
`ProjectPaths.bundles_dir`, writer/loader, SecretStore/Redactor and trace reader. The nested
`bundles/index.json` cannot enter the run-level RawResult glob.

Original screenshot paths resolve within the correct run before sanitation reads them. Copies
remain inside `sanitized_images` contexts until the bundle writer finishes. Uncertain, unsafe or
unattributed screenshots are withheld; sanitized images have unreadable text, recorded explicitly
with image counts and value-free reasons. LLM trace entries are case-filtered; all retained trace
spans must share the run. A bundle failure records `assembly_failed`; an index-storage fault logs
the fixed `failure_bundle_index_unavailable` diagnostic and leaves the completed run available.

`report_export.py` adds HTML and Excel links only after loading the typed same-run index and
validating the complete bundle, content hashes and case/run/bundle identity. Links are relative
to the export destination. Corrupt, partial and unavailable bundles receive honest labels.
No UI routes, provider interfaces, CLI continuation or UX/fallback behavior changed.

## Evidence and check scope

Evidence: `qa/evidence/failure-bundle-wiring/`; compact exact candidate packet remains in `.work/`.
The four new focused tests run the real `launch_run`, real ProjectStore and real HTML/Excel
exporters; only preflight/execution and local OCR output are substituted. Actual sanitation,
pixel masking/copying, atomic bundle writing/loading, run tracking and reporting execute.

The final checker packet lists selected existing node IDs and their risk coverage. The maker's
12 byte-preserving mutation triples assert green baseline, one matching anchor, exact changed
bytes, named defending failures and exact restoration. Every command receipt binds source/test,
lock/dependencies, interpreter, import root, environment and complete output hashes before test
execution. `packet-self-audit.json` validates these against the frozen candidate bytes.

Final measured results: **11 passed** in the focused regression command; scoped Ruff clean;
source doctor caps/functions/names/duplicate-definition checks clean; self-audit validated all
12 attributable byte-preserving mutation triples against the final code/test fingerprints.

Early fixture/API setup failures, invalid mutation-copy import setup and text-based restoration
attempts are retained as failed/inconclusive preparation. Only the `v4-*` byte-preserving proofs
are claimed. No browser, model call, full pytest suite or live product action ran.

Full combined pytest/Ruff/doctor remains the parent's exact combined integration gate under
D-100. Initial full doctor reported own line caps (corrected before frozen proofs) and stale
generated MAP/SNAPSHOT. Final scoped source checks cover caps, filenames and duplicate concepts;
generated documentation regeneration belongs to combined integration. Do not report full doctor
PASS from this unit.

Maker active time/tokens/cost are unavailable and remain null. Individual command durations are
measured in receipts, including retries. Efficiency ratios remain unverified. Only an independent
checker can issue this unit's verdict; this manifest does not certify PASS or release readiness.
