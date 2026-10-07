# Independent T-151 bounded fixture review — 2026-10-05

Status: PARTIAL-FINDINGS. Cycle checked: 1.
Bound project: D:/autoTesting; candidate .worktrees/t151-target-discovery.
Baseline bd2fe8f4; uncommitted maker source hashes below. This is NOT a Mode A
unit completion verdict: manifest remains verification-in-progress, source commit,
full adapter suite, doctor and exhaustive C7 guard coverage remain outstanding.
No PASS, goal close, merge, push, browser, real model, target endpoint or credential use.

## Reached findings — all C5, independently derived, >80% confidence

1. **High: recoverable encoded metadata escapes the context artifact.**
   `stages/read_context.py::_metadata:47` scrubs literal strings only; `read_context:140`
   returns the artifact without the existing widened `Redactor.assert_clean` gate.
   A filesystem Markdown frontmatter `title` containing base64 of the synthetic known
   value `checker-secret-longvalue` is emitted unchanged; `Redactor.contains_folded`
   independently recognizes the serialized returned Discovery as credential-bearing.
   `test_encoded_context_output_is_guarded` reached its named assertion and failed.
   Expected: refuse or otherwise prevent that recoverable credential leaving the
   read boundary. Plain literal scrubbing is not equivalent to the existing gate.

2. **High: recoverable encoded filesystem name escapes discovery evidence.**
   `stages/discover.py::scan:230,235` only literal-scrubs Signal.evidence_path, then
   returns without a widened output guard. A real `.py` filename containing the same
   synthetic base64 emits a serializable SDK Signal with that recoverable value.
   `test_encoded_evidence_path_is_guarded` failed its named folded-secret assertion.
   Input is a filesystem name, not a model output. Expected: an explicit safe refusal
   before credential-bearing provenance can leave the stage; never invent a valid citation.

3. **High: an approval refusal exposes raw secret-bearing root paths.**
   `stages/discover.py::approved_roots:42,50` calls the existing consent helper with
   unguarded filesystem roots. With no approval, its ApprovalRequired exception
   includes a raw secret-bearing external directory twice (target and grant command).
   `test_unapproved_secret_path_error_is_scrubbed` failed the exact raw-value absence
   assertion. This is the newly introduced caller boundary, not a claim that this
   unit wrote consent.py. Expected: safe refusal/error presentation while retaining
   exact-root consent identity; do not authorize a scrubbed target or soften approval.

4. **High: caller-supplied project identity escapes Source.project unchanged.**
   `stages/read_context.py::_source_reference:112` copies `scope.project` directly.
   Supplying a legal string identity equal to the synthetic known secret returns a
   Discovery whose Source.project carries it verbatim, even though metadata is benign.
   `test_source_project_identity_is_scrubbed` reached its raw-value absence assertion.
   This input is a caller-provided ID, not content extracted from the filesystem.
   Expected: reject credential-bearing IDs safely rather than corrupting identity or
   silently persisting the known secret. A final output gate also catches this bypass.

All probes use only synthetic values and local fixture directories. No real secret
was read. These are four concrete manifestations across output/error surfaces; the
repair may share an existing guard, but every manifestation needs a reached regression.

## Commands actually executed and native results

Candidate environment: PYTHONPATH=<candidate>/src;
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; PYTEST_CURRENT_TEST=t151-checker-local-no-env;
root .venv Python. No .env loader; no live Provider calls. Fixtures use synthetic keys.

`D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_discover.py tests/test_schema.py tests/test_consent.py tests/test_providers.py -o addopts= -p no:cacheprovider --basetemp=.work/t151-checker-baseline --junitxml=.work/t151-checker-baseline.xml`

Native exit 0: **77 passed in 0.94s**; XML 77 tests, 0 failures, 0 errors.

`D:/autoTesting/.venv/Scripts/python.exe -m pytest .work/t151_checker_probe.py -o addopts= -p no:cacheprovider --basetemp=.work/t151-checker-probes --junitxml=.work/t151-checker-probes.xml`

Native exit 1: **4 failed in 1.49s**; 0 collection errors; all four named assertions above.

`D:/autoTesting/.venv/Scripts/python.exe .work/t151_checker_mutations.py`

Native exit 0. This controller asserts its own baseline and exact mutation anchors,
changed bytes, named failure attribution and restore. Each child uses `python -B -m
pytest tests/test_discover.py -o addopts= -p no:cacheprovider` with unique scratch
basetemp/XML; complete command arrays/native exits are in results.json.
Cache-free source copy baseline **35 passed**; 10 separate single-hunk mutations:

| Mutation | Expected defender | Actual result |
|---|---|---|
| dirty signal guard | test_dirty_signal_is_refused_before_provider | KILLED, native 1 |
| non-AI root guard | test_non_ai_encoded_root_secret_is_refused | KILLED, native 1 |
| scope preflight | test_all_roots_are_preflighted_before_any_open | KILLED, native 1 |
| physical-byte accounting | test_rejected_files_still_consume_physical_read_budget | KILLED, native 1 |
| scan final deadline | test_final_parser_overrun_is_not_complete[False] | KILLED, native 1 |
| context final deadline | test_final_parser_overrun_is_not_complete[True] | KILLED, native 1 |
| YAML alias guard | noncyclic alias parameter | INCONCLUSIVE; different cyclic case failed |
| strict confidence | test_seeded_bad_classifier_output_is_never_overridden[string] | KILLED, native 1 |
| ProviderError sanitization | test_provider_error_never_echoes_raw_secret | KILLED, native 1 |
| metadata literal scrubbing | test_context_is_metadata_only_and_secrets_are_scrubbed | KILLED, native 1 |

Every child collected 35 tests with 0 errors. First alias probe's max_yaml_nodes=10
independently refuses the noncyclic fixture when AliasEvent detection is removed;
the run is therefore NOT credited to that designated case and NOT called vacuous.
Final original suite **35 passed**, native 0; all 175 copied source files hash-match
the initial bytes after restoration, zero mismatches. Candidate was never mutated.

`D:/autoTesting/.venv/Scripts/python.exe .work/t151_checker_yaml_proof.py`

Native exit 0. Independent default-budget noncyclic alias oracle asserts the exact
`yaml_alias` reason (not merely any refusal): baseline **1 passed**, native 0;
same isolated AliasEvent deletion **1 failed**, native 1, named
`test_noncyclic_alias_exact_refusal`, 0 errors; exact restore **1 passed**, native 0.
The supplemental proof does not rewrite or relabel the initial INCONCLUSIVE record.

## Bindings and persistence

Evidence copied byte-for-byte to `qa/evidence/t151-independent-cycle1-2026-10-05/`:
three checker-authored probe/controllers, baseline/probe XML, each mutation XML/log,
results.json and alias-independent-results.json. Scratch retained under
`.work/t151-checker-mutation-copy`, never copied to source or adopted as production code.

Hashes independently checked against maker freeze before and after all runtime work:

| Path | SHA256 |
|---|---|
| schema/ai_target.py | 0FECC124BB8657ADB3C535B7090D761CD9A126E5FAE892229ED7E45AD72221A6 |
| stages/discover.py | F82D548BB041818FDC3B5C83CDFC885607463A703A9CA190D8EBEC27830088D5 |
| stages/read_context.py | F9269FDBC89A08E937E0195BE4BD4DD7C5B4B8E13033252ED67B24FDD0E2AFC8 |
| providers/mock.py | FC293C107974A10D770671BB9E6DB432F976AE19050212C449DAC35244378CC5 |
| tests/test_discover.py | B8D071C37CD443AE3BFDFF66B7C458A3FC3ABC166961FFBB7CCFB19B60810033 |
| prompts/ai_target_classify_v1.md | A24F256D6F8A20391C3B4F0859989CAB83EC7DBC17734E36D7A0CC752EB4E3C4 |
| pyproject.toml | 95E41530CA190D9EDFF9154704E62F799F6E77CCF4835CEB5FB165D91BAAE6ED |
| uv.lock | 25A972903D45D319291BA0D0D56B7E688097B7CDEBC571F0018AD06E458AE601 |

Probe source SHA256: 05A4B8E75133BB4FA24F5D1BE28086AA2763A24030F7BA3E77A50C36EAAC6184.
77-baseline XML: A6CF0406EA64601EC4AB53652FB3A85F374E72CFE18053AF8F8E759321161D73.
4-failure XML: 3A01751DF0A92BF6E186B28BEC72065A1A4468F58EB2259B7AF447D5A3584638.
results.json: 0CAA0EF0E8414ADDA6E88030727B37D7044D32AB103B555C4C157D50087CD6EE.
alias-independent-results.json: FD4129442B1160EDC5AA9BFDB44FB8D7FCF2FB1DEF7A167D31A2F14DCE6D1117.

## Scope honesty / terminal handoff

AI1 and AI8 have fixture-level positive evidence only; C5 has reached failures.
C7 partial: targeted guards above are mutation-proven, not every added test/guard.
No claim is made about full-suite result, clean doctor, committed reviewed SHA,
live-browser acceptance, production readiness or any T152/T153 behavior.
LIVE-BROWSER: not-applicable to changed non-UI paths in this bounded review.
No canonical unit verdict, issues ledger IDs, contracts, manifests, goal or code were
modified. This diagnostic report/evidence is uncommitted for orchestrator narrow QA
persistence; it is not a substitute for required commit-before-Mode-A verification.
Runtime sessions 47387 and 72323 terminated native exit 0. Sole runtime lane RELEASED.
