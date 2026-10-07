# Independent T-151 repair verification — 2026-10-05

Status: BOUNDED-REPAIRS-VERIFIED. Cycle checked: 1.
Bound root D:/autoTesting, candidate .worktrees/t151-target-discovery.
No unit PASS, full-suite result, committed source acceptance, goal close, merge or push.
This report is independent diagnostic verification, not a ready-for-check Mode A verdict.
Root explicitly granted the exclusive runtime lane after the maker released it.

## Repaired findings independently re-run

Original unchanged four probes now pass: encoded context metadata, encoded discovery
filename, approval-refusal secret path, and raw caller project identity. Their old
four reached failures are preserved in t151-target-discovery-scoped-cycle1.md and
the original independent evidence directory; no historical finding was rewritten.
Prior report remains SHA256 C6118DB464D224189E96DED04796BD22503F9DE27469FCDD8185DE7172BE1206.

Added ten independently derived local oracles, not copied from maker tests:

- Six raw/base64 missing-root/scan-open/context-open cases require the exact
  FileNotFoundError or PermissionError subtype, fixed `filesystem access refused`
  message, absent filename, suppressed context and clean formatted traceback.
- Secret-bearing binary-file refusal provenance must itself be guarded before
  returning a Discovery; this covers nested refusal rows, not only positive signals.
- Encoded caller project identity must be rejected before filesystem resolution:
  Path.resolve is a forbidden collaborator sentinel, not a timing measurement.
- Approval denial must retain ApprovalRequired, fixed read-refusal text, suppressed
  chain and clean formatted traceback, rather than allowing a scrubbed approval target.
- Benign project identity, real relative Source.path and evidence path remain exact;
  body text stays absent and normal context stays complete.

All these reached their intended assertions and passed. Filesystem sources and
caller IDs remain distinct in the oracles. No code or manifest was changed by checker.

## Native commands / terminal results

Candidate env: PYTHONPATH=<candidate>/src; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1;
PYTEST_CURRENT_TEST=t151-checker-repair-no-env. Root .venv Python, only synthetic
fixtures/MockProvider. No .env load, browser, network, external target or paid model.

`D:/autoTesting/.venv/Scripts/python.exe -B -m pytest tests/test_discover.py tests/test_schema.py tests/test_consent.py tests/test_providers.py tests/test_redact_obfuscation.py tests/test_redact_encoding_coverage.py .work/t151_checker_probe.py .work/t151_maker_filesystem_probe.py .work/t151_checker_repair_probe.py -o addopts= -p no:cacheprovider --basetemp=.work/t151-independent-repair-regression --junitxml=.work/t151-independent-repair-regression.xml`

Native exit 0: **218 passed in 2.73s**. Independently parsed XML: 218 tests,
0 failures, 0 errors, 0 skipped. Includes 63 discovery cases, unchanged original
four independent C5 probes, unchanged six maker diagnostic filesystem probes and
ten fresh independent oracles. This is a bounded subset, not the full adapter suite.

`D:/autoTesting/.venv/Scripts/python.exe .work/t151_checker_repair_mutations.py`

Native exit 0. Fresh source-only copy excluding all __pycache__/pyc; copied only
test_discover plus original four-probe and new ten-oracle files. Controller asserts
GREEN baseline before sabotage; AST function anchor unique, hunk exactly once within
that unique function, changed bytes on disk, native exit and expected failure name.
Each single-hunk sabotage affects only the scratch copy, never candidate source.
Full child command arrays/native exits/failure lists are in repair-results.json.

Baseline **77 passed**, native 0; seven attributable guard removals, each native 1,
77 tests collected and 0 errors:

| Removed guard / wrapper | Named independently derived defender | Failure count |
|---|---|---:|
| scan final artifact guard | test_encoded_evidence_path_is_guarded | 5 |
| context final artifact guard | test_encoded_context_output_is_guarded | 4 |
| project preflight guard | test_dirty_project_rejected_before_filesystem | 1 |
| approval exception sanitation | test_denial_class_and_formatted_chain_are_safe | 4 |
| root resolution exception sanitation | test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-missing] | 6 |
| scan read exception sanitation | test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-scan_open] | 6 |
| context read exception sanitation | test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-context_open] | 6 |

All seven named defenders actually appear in their XML failure lists. Final exact
restore **77 passed**, native 0. All 175 copied source files match their pre-mutation
SHA256 hashes, zero mismatches. Candidate freeze also rechecked unchanged afterward.
No zero-failure mutation, collection error or instrument failure was credited as a kill.

`D:/autoTesting/.venv/Scripts/ruff.exe check src tests scripts`

Native exit 0: **All checks passed!** Entire declared lint scope, not just changed files.

With PYTHONPATH=<candidate>/src, AUTOTESTER_ROOT=<candidate>,
PYTEST_CURRENT_TEST=t151-checker-doctor-no-env:

`D:/autoTesting/.venv/Scripts/python.exe -B -c "from autotester import main; main()" doctor`

Native exit 0: **doctor: clean**. Working-tree design/generated freshness evidence only;
committed-vs-fresh acceptance remains unproven and no commit is inferred from this result.

Fresh-process import binding command (native 0):

`D:/autoTesting/.venv/Scripts/python.exe -B -c "from pathlib import Path; from autotester.stages import discover, read_context; from autotester.schema import ai_target; root=Path.cwd().resolve(); modules=[discover,read_context,ai_target]; assert all(Path(m.__file__).resolve().is_relative_to(root/'src') for m in modules); print('\n'.join(m.__file__ for m in modules))"`

Actual imports all resolve under candidate src: stages/discover.py,
stages/read_context.py and schema/ai_target.py. Mutation children's PYTHONPATH points
only to scratch/src; their failure traceback paths independently identify that copy.

## Source and evidence bindings

These hashes matched root's explicit lane grant before and after all checks:

| Path | SHA256 |
|---|---|
| stages/discover.py | 7A1221BA2AA7B63B0C6A05EFD3FCCCD39B86B74C3B69E9B4B42E1872CC577C0F |
| stages/read_context.py | 27E6C7EFF266E15C87152B6E08CCB2A89B6A432B57C2BA5D7CC71B0C8666797A |
| tests/test_discover.py | 051F1035B6BCB1EF3129AADE9AC011D4C5C4392D05D489D7936DD9BBF70B2D63 |

Other authorized product/prompt/dependency hashes still match original freeze:
ai_target0FECC124BB8657ADB3C535B7090D761CD9A126E5FAE892229ED7E45AD72221A6;
mockFC293C107974A10D770671BB9E6DB432F976AE19050212C449DAC35244378CC5;
promptA24F256D6F8A20391C3B4F0859989CAB83EC7DBC17734E36D7A0CC752EB4E3C4;
pyproject95E41530CA190D9EDFF9154704E62F799F6E77CCF4835CEB5FB165D91BAAE6ED;
uv.lock25A972903D45D319291BA0D0D56B7E688097B7CDEBC571F0018AD06E458AE601.

New probe AFAE4F744CB13B5F0A7F184AF512EE78C945D40CA3B24E44CD74C317BADEAAA5;
218 XML251D4D161A291DFE0692E8149B1235D7ECFE315BBBCCB3C52202024EDF328EAA;
mutation controller8B8B0F241C91A911CAECE0BE6F5568324B717EE267A025AEE26BDA3149F3303C;
repair-resultsA3C0C2E649DEE3F57501174B07CAA7A17FA63C4B9D348BCFA1A0CB084AA714A5.

Exact controllers/oracle/XML/each mutation log and result JSON copied to
qa/evidence/t151-independent-repair-cycle1-2026-10-05. Scratch retained under
.work/t151-checker-repair-copy. No previous receipt overwritten.

## Remaining / terminal handoff

No further concrete failure was found within this agreed bounded repair scope.
Four prior C5 manifestations and planned filesystem exception wrappers have
independent fixture and targeted mutation evidence. This does not exhaust C7's
every-test/every-guard matrix, full adapter suite, commit-before-check, committed
generated freshness, actual Mode A acceptance or product end-to-end validation.
LIVE-BROWSER: not-applicable to this non-UI scoped repair; no browser was launched.
Only checker diagnostic evidence/report files were written. No source, manifests,
contracts, issues IDs, canonical unit verdict or goal state was changed.
Report/evidence remains uncommitted for orchestrator narrow QA persistence, not a
substitute for reviewed-source commit and required formal checker completion.
Session 54005 terminated exit 0; Ruff/doctor/import checks also terminal native 0.
Exclusive runtime lane RELEASED.

## Read-only C7 completion matrix — appended 2026-10-05, no runtime

This appendix inventories actual test functions and guard branches against actual
receipts. It is not a completion verdict or permission to waive a missing proof.
Current frozen discovery test source has **19 functions / 63 collected cases**.
Definitions: **FINAL** = attributable mutation on the current granted source freeze;
**CARRY** = attributable historical mutation on earlier same-cycle hashes, same
guard still present but not mutation-rebound to the final freeze; **PARTIAL** = some
claims/parameters mutation-evidenced, others not; **UNPROVEN** = green test only.
Historical CARRY evidence cannot be called a final-source mutation receipt merely
because the branch looks unchanged. A final bounded rerun can rebind it cheaply.

Receipt abbreviations:
- O: original independent evidence directory/results.json (old discover F82D548,
  reader F9269FD, test B8D071C hashes), 9 attributable kills plus one INCONCLUSIVE.
- A: that directory/alias-independent-results.json, isolated exact-reason alias
  baseline1/RED1/restore1 on old reader hash; not a rewrite of the original fixture.
- R: repair evidence directory/repair-results.json, seven attributable kills on
  final discover7A1221B/reader27E6C7E hashes, baseline77/restore77.
- G: final independent 218-green receipt; green-only is functional evidence, not
  mutation evidence. The maker's 208-green receipt is not independent C7 sabotage.

### Every newly introduced discovery test function

| Test function (test_discover.py line) | Actual mutation evidence | Still missing under its claims |
|---|---|---|
| signals_match_real_lines_without_importing_target (20) | G only, UNPROVEN | exact line/path attribution, SDK/framework emission, no target execution, overlap pruning each need falsification |
| context_is_metadata_only_and_secrets_are_scrubbed (32) | O metadata-secret named kill, CARRY/PARTIAL | metadata preservation, hashtags, no body/backlink/Dataview leakage, Source.text/path semantics not credited by scrub removal |
| unsafe_or_excessively_nested_yaml_is_refused (49), 5 parameters | O alias removal killed cyclic case but designated noncyclic case INCONCLUSIVE; A isolates alias capability, CARRY/PARTIAL | independent depth/node/tag guard deletions and final-freeze rebind; original noncyclic fixture's node-cap overlap remains |
| credentials_and_oversize_files_are_never_returned (55) | G only, UNPROVEN | credential exclusion, per-file byte guard, binary guard separately |
| file_bound_is_visible (64), files/entries/time | O scan-final-deadline incidentally also killed wall-clock case, CARRY/PARTIAL | max_files, global max_entries/iteration stop, and the named traversal/read deadline guards separately |
| symlink_escape_is_refused (91), symlink/junction | G actual local Windows fixtures, UNPROVEN | resolved containment versus reparse refusal branches separately; no escape content-read sentinel receipt |
| rejected_files_still_consume_physical_read_budget (107) | O physical-budget named kill, CARRY | final hash rebind; remaining<=0 terminal cap and truncation attribution are separate guard branches |
| all_roots_are_preflighted_before_any_open (129), 2 params | O scope-preflight CARRY; R approval-exception also kills both final params, PARTIAL/FINAL | exact scope/expiry/signature/kind/budget delegation mutation at new caller; final preflight-bypass kill rather than only sanitation |
| secret_keys_tags_and_paths_are_scrubbed (156), 28 params | R output/wrapper removals kill encoded metadata/filename and all raw/base64/hex/folded filesystem params, FINAL/PARTIAL; O metadata-secret CARRY | literal keys/values/tags/label/path subguards and current-classifier-free input provenance; repeated literal cases are not four different capabilities |
| discovery_never_calls_provider (191) | G only, UNPROVEN | a safe injected Provider seam call must hit its sentinel; current spy patches base Provider.act only, not every possible subclass override |
| classification_uses_mock_seam_without_paths (201), 4 kinds | G only, UNPROVEN | each kind rule, counts-only projection/no paths, evidence preservation, usage/prompt accounting and exact-schema fallback scope |
| non_ai_calls_no_provider_and_unrelated_mock_still_refuses (210) | G only, UNPROVEN | positive-signal predicate/non-AI no-call, comments/identifier negatives, unrelated-schema error boundary |
| seeded_bad_classifier_output_is_never_overridden (225), 6 params | O classifier-strict named string kill plus bool failure, CARRY/PARTIAL | unknown kind, extra key, numeric bound, NaN and seeded response precedence need their own named behavior-changing probes |
| model_reason_is_redacted_and_scanner_evidence_is_preserved (237) | G only, UNPROVEN | reason literal scrub, final reason/output assertion and original evidence retention independently |
| dirty_signal_is_refused_before_provider (246) | O dirty-signal named kill, CARRY | final-source rebind; guard of complete Signal payload already historically hit |
| all_detector_families_have_exact_line_oracles (254) | G only, UNPROVEN | retrieval/tool/async/sync/endpoint/prompt/ground-truth families and line attribution; one missing-family mutation can prove this test notices, not every detector branch |
| non_ai_encoded_root_secret_is_refused (265) | O nonai-root named kill, CARRY | final-source rebind, retain actual zero model calls |
| provider_error_never_echoes_raw_secret (272) | O provider-error named kill, CARRY | final-source rebind; malformed model schema error path is separately exercised but not mutation-proven for trace sanitation |
| final_parser_overrun_is_not_complete (284), scan/context | O scan-final-deadline/context-final-deadline named kills, CARRY | final-source rebind of both final-check guards, not just an earlier traversal clock |

### Guard inventory beyond a test-name count

| Source guard / capability | Evidence disposition |
|---|---|
| approved_roots project credential gate | FINAL R project-preflight; own forbidden Path.resolve sentinel is the named defender |
| root missing/access wrapper; approval-denial class/suppressed cause | FINAL R root-filesystem and approval-exception |
| scan/context traversal access wrappers | FINAL R scan-filesystem/context-filesystem |
| scan/context complete artifact gates, including refusal provenance | FINAL R scan-output/context-output, original C5 probes and refusal-path oracle |
| exact signed READ project/kind/target/time approval before any content | delegated helper has existing consent greens; new caller is CARRY scope bypass, not yet final end-to-end mutation-bound |
| require root directory; prune overlapping approved roots | UNPROVEN guard removal on final source |
| entry iteration islice; entry-cap checks in _candidates and across roots | UNPROVEN. Some checks are redundant (`entries>max` after capped iteration); removal may yield zero failures. That would be INCONCLUSIVE, not proof of vacuity or a waiver. Try a caller-bound perturbation and record actual null/reached outcome |
| filesystem resolved containment and reparse flags | UNPROVEN separately; current test uses outside-target links, so either remaining half may independently refuse |
| excluded vendor/cache directories; max tree depth | UNPROVEN and no dedicated discovery fixture currently names these branches |
| credential filename/extension exclusion | UNPROVEN; existing credential test covers .env only, not every named suffix/path form |
| max files; max file bytes; binary NUL; non-UTF8 refusal | UNPROVEN on final hash; non-UTF8 is not named by existing new tests |
| physical total read accounting | CARRY O physical-budget; final rebind required |
| max-total exhausted/truncated branches; traversal/read wall-clock guards | UNPROVEN individually; final parser deadline is CARRY only |
| invalid Python refusal and deterministic AST/no execution | UNPROVEN named invalid-Python guard; positive AST test alone does not mutation-certify no execution |
| YAML node count, collection depth, alias, explicit tags, mapping/string-key validation | alias capability CARRY A; remaining guards UNPROVEN. Existing max_nodes10 can hide alias/depth failures. safe_load also rejects executable tags without explicit-tag guard; exact reason/caller evidence is needed to isolate it |
| tags must be strings; fenced body hashtag exclusion; metadata-only Source/text/path | UNPROVEN except literal value scrub CARRY. No invalid-tag/mapping dedicated oracle yet |
| metadata key/value/tag/label literal scrubbing | CARRY value scrub; distinct key/tag/label guards not separately removed. Final widened gate can reject a leak without proving the literal scrub's successful output behavior |
| classifier original Signal guard; non-AI root guard; provider/schema exception sanitation | CARRY O, final rebind required |
| classifier counts-only prompt + pre-call prompt guard; non-AI gate | UNPROVEN mutation on final source |
| classifier reason scrub, widened reason and final output guards | UNPROVEN separately; redundancy can hide a single guard removal |
| Mock exact Classification schema/no queued agent gate, closed four-kind rules, queue/usage behavior | G only, UNPROVEN new-branch falsification; unchanged neighbors do not certify the new fallback |
| Classification extra=forbid, closed kind, reason strict/nonblank/length, confidence strict/range/finite | strict type CARRY; other validators UNPROVEN. AiTarget repeats some range/kind guards; direct validator proof alone does not replace caller mutation |
| Signal closed kind/positive line; ScanLimits all lower/upper finite bounds; other new extra=forbid models | UNPROVEN explicit guard rows and caller mutation. test_schema.py's pre-existing corpus does not automatically enumerate new AI models |
| Discovery.complete derives from refusals | G positive/negative cases, UNPROVEN changed implementation falsification |

This is a capabilities inventory, not a numeric coverage percentage: one kill may
defend several cases, while one function may contain several independent guards.
No model schema's existence or doctor's clean result implies its validators were
falsified. No scheduled T152 mapping/capture guard is counted as missing T151 work.

### Minimal next scratch-proof selection (proposal only; no runtime)

1. **Rebind carried receipts to final source**, with fresh green baseline and exact
   restored bytes: dirty Signal/root, physical-byte accounting, exact preflight,
   both final deadlines, ProviderError, strict confidence, metadata scrub and the
   isolated alias oracle. Retain old receipts as history rather than editing hashes.
2. **AI1 provenance/determinism cluster:** separate citation-line shift, overlap
   pruning removal, AST execution sabotage against the raising fixture, safe Provider
   seam injection, and per-family detector deletions with named line-set defenders.
3. **Read-boundary cluster:** credential, binary, UTF8, per-file/files/entries/tree
   depth/excluded-tree and exhausted-total guards; independent high-other-limit
   fixtures isolate each bound. Exercise containment/reparse halves with distinct
   sentinels, never relying on one outside link to prove both.
4. **AI8 structure cluster:** isolated node/depth/alias/tag and mapping/tags-shape
   exact-refusal oracles; body/Source.text/backlink/Dataview exclusion sabotage;
   metadata key/tag/label/path scrub sabotage. Do not raise parser budgets globally
   or weaken production criteria to make a mutant run.
5. **Classifier/mock/schema cluster:** force wrong kind rules, broaden mock schema
   gate, overwrite a queued malicious response, inject path/detail into payload,
   remove non-AI no-call predicate, reason/evidence alterations, then table-driven
   new-model invalid/extra/bounds assertions with at least one caller mutation per
   validator capability family. Redundant schema/final-output guards need named
   attempted single-hunk mutants; an unchanged outcome is explicitly INCONCLUSIVE.

These are the smallest independent capability groups, not a promise that five
mutations discharge C7: the one-hunk guard branches above still need actual rows.
Some missing fixture oracles may require maker edits within the existing test
module after fresh plan review; the checker must not add production test code.
No full suite/browser/model/network/source/manifests/contracts changes are needed
for this diagnostic matrix. No runtime was launched for it. Formal Mode A should
not treat this outstanding matrix as complete, even if the current source is
locally committed for a later reviewed freeze.

## C7 phase 1 — carried guard final-source rebind, 2026-10-05

Root explicitly granted this bounded phase only. No groups 2–5 were executed.
The read-only matrix above remains history; this addendum supplies new FINAL
receipts for the previously CARRY guard rows, without rewriting any old result.

Actual native command from candidate cwd:

`D:/autoTesting/.venv/Scripts/python.exe .work/t151_checker_rebind_mutations.py`

Native exit 0. Fresh .work/t151-checker-rebind-copy contains the final 175 source
files, excluding all __pycache__/pyc, current test_discover.py (63 cases) and the
unchanged previously isolated exact-reason alias oracle (one case). No candidate
code/tests/manifests/contracts changed. Child command shape, with unique label
basetemp/XML and scratch-only PYTHONPATH:

`D:/autoTesting/.venv/Scripts/python.exe -B -m pytest tests/test_discover.py tests/test_checker_yaml.py -o addopts= -p no:cacheprovider --basetemp=<scratch>/<label>-temp --junitxml=<scratch>/<label>.xml`

Credential-loader guard and synthetic approval key set; no real credentials,
browser, model, endpoint or network. Baseline asserted **64 passed**, native 0.
Each one-hunk edit asserts unique anchor, changed bytes, actual named defender
in XML failures, native exit 1 and zero errors. All ten were attributable kills:

| Final-source mutation | Actual defender | Failure count |
|---|---|---:|
| dirty-signal | test_dirty_signal_is_refused_before_provider | 1 |
| nonai-root | test_non_ai_encoded_root_secret_is_refused | 1 |
| scope-preflight | test_all_roots_are_preflighted_before_any_open[secret-token] | 2 |
| physical-budget | test_rejected_files_still_consume_physical_read_budget | 1 |
| scan-final-deadline | test_final_parser_overrun_is_not_complete[False] | 2 |
| context-final-deadline | test_final_parser_overrun_is_not_complete[True] | 1 |
| yaml-alias | test_noncyclic_alias_exact_refusal | 2 |
| classifier-strict | test_seeded_bad_classifier_output_is_never_overridden[string] | 2 |
| provider-error | test_provider_error_never_echoes_raw_secret | 1 |
| metadata-secret | test_context_is_metadata_only_and_secrets_are_scrubbed | 6 |

The preflight defender intentionally names the current parameterized node, not
the old unparameterized historical name. The alias defender is the isolated
default-budget exact-reason oracle; the original noncyclic fixture still has
its node-cap overlap and is not retroactively called an alias-specific kill.
Confidence kill also catches bool, but does not certify kind/extra/range/NaN.
Metadata kill proves successful literal-value scrubbing, not body/graph exclusion.

Final exact restoration **64 passed**, native 0, 0 errors. Controller checks all
175 source SHA256 identities against their initial copy, zero mismatches. Original
candidate discover7A1221BA2AA7B63B0C6A05EFD3FCCCD39B86B74C3B69E9B4B42E1872CC577C0F,
reader27E6C7EFF266E15C87152B6E08CCB2A89B6A432B57C2BA5D7CC71B0C8666797A,
tests051F1035B6BCB1EF3129AADE9AC011D4C5C4392D05D489D7936DD9BBF70B2D63
were independently checked before and after; no source change occurred.

Exact controller, alias oracle, every baseline/mutation/restoration XML/log and
results.json copied to qa/evidence/t151-independent-rebind-cycle1-2026-10-05.
Full command arrays, actual failed-test lists, before/mutated source hashes and
native child exits are preserved there. No existing evidence was overwritten.

Remaining matrix groups 2–5 stay pending; this phase does not claim all 19 tests,
all 63 parameters or every schema/runtime guard mutation-complete. No unit PASS,
full-suite result, committed freshness, goal close, merge or push is recorded.
Session 32821 terminated native exit 0. Exclusive runtime lane RELEASED.
