# Manifest — T196 citation subject checking

Contract: qa/contracts/living-ledger.md L10; preserve L9 and core invariants C2/C7/C12.
Goal task: T-196
Policy-Version: proportional-verification/2026-10-06.5
Protocol hashes: maker=3F5A021B27A04447C87726929BAB9FA6245C1251A36E28E9CF5CA91DCCB4063B checker=12C935F80B4344E1C7B43C7F2A3467B71D1923B8883A06D16B9D7E828CDB47E5
Adapter: codex-native/2026-10-05.3; project coding, qa/adapter.json.
Fix cycle: 0
Resumes: 0
Phase: BUILDING
Status: BUILDING
Tier: L — authority-claim governance validator; explicit L10 final dual-check requirement.
Dual check: required — two blind final coordinators, not intermediate helper reviews.
Base: bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf, master; shared dirty state preserved.
Manifest creation: Umesh approved this exact evidence path on 2026-10-06.
Audience: internal developer/operator CLI; no new UI or portal behavior in this feature.

## Scope and independent plan authority

Read approved pre-implementation plans and independent inventory receipts in
qa/feedback-inbox.md. Initial implementation approval begins at line2408;
later acceptance-gap approval has its own uniquely named heading. Numeric
references below the current inventory block can shift; use receipt headings
and actual reviewer Attribution/Reviewer labels, not a guessed shifted line.

Existing product files: src/autotester/ledger/citations.py (L9/L10 scanner);
src/autotester/schema/ledger.py (strict typed claims and reviews);
src/autotester/doctor.py::run (consumer wiring).
Existing test file: tests/test_citations.py. Every original L9 assertion retained.
Two approved citation-only migrations in docs/spec.md; scope refusal and
owner-held deferral preserved. No new product/test module.
Maker has not edited contracts, architecture prose or immutable history.
Two independently plan-approved gate migrations:at052's inaccurate decision-entry
status corrected,canonical closed-enum quotation added,remaining boundaries
unchanged; occurrence independently classified and mechanically rebound.
t191's kept-video exception now quotes the complete relevant What paragraph;
ordinary analogy,root-cause answer and checker-owned amendment requirement unchanged.
Current contract adoption is not product implementation PASS.

## Claimed implementation and unfinished acceptance

- Strict visible quotation plus agreeing JSON, whitespace-only textual comparison
  against one unambiguous full What body; separate L9 dangling resolution.
- Archive full-body comparison, fail-closed index-only/missing/ambiguous subjects.
- One current occurrence-bound review block in qa/feedback-inbox.md; exact path,
  line text, id, same-id ordinal and identical-line multiplicity, reviewer attribution.
- Per-occurrence exemptions, no whole-file allowance; marker contents cannot invent refs.
- Visible known identifiers retained in malformed-declaration diagnostics.
- Real-tree inventory is PARTIAL:877 adopted independently reviewed occurrences
  across68paths, not complete five-glob coverage. All35 contracts and the reviewed
  gates, immutable decision bodies through063, and generated/header checkpointH
  are included. CheckpointI added82 independently reviewed historical body rows:
  32ordinary,46authorization,4nonclaiming;28 exactWhat-supported authorization
  claims and18 unresolved historical claims, not invented quotations.
  Root fresh mechanical binding check across all877rows:zero errors, including
  exact line/id/ordinal/multiplicity, duplicate keys and review-reference presence.
  Mechanical binding is not semantic acceptance or complete coverage. Remaining
  manifest/verdict occurrences still require independent semantic review.
  Three generated snapshot authority claims
  remain unrestricted and require truthful source/generator migration.
- Mutable claim migration and disputed What-versus-Why/Changes-authorized
  attribution remain unfinished. Checker owns contract edits. Prior authorizing
  decisions are required before contract/architecture changes; this manifest
  grants no such authority or new operational permission.

## Exact development verification

Approved synthetic environment: PYTEST_CURRENT_TEST=governance-tests,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
AUTOTESTER_APPROVAL_KEY=synthetic-governance-key. Offline, mocked unit scope;
not native process/network containment and not real-account/browser acceptance.

Command: uv run --offline pytest --noconftest -p no:cacheprovider tests/test_citations.py
Earlier actual:exit0,61passed27.03s on pre-strengthening test hash.
Additive foreign/historical strengthening:exit0,61passed31.82s on test hash
DB7C7AA597BFEE549803BB79EA78D727A99987926028DE3B2AB87521261ACF7F.
The foreign deletion mutant remained GREEN:the fixture had accidentally included
its own quote in the open What field. This result is INCONCLUSIVE, not a proof.
Independently approved Links-field boundary correction and protected controlled
doctor-negative-test correction replace the contingent assertion that the real
repository must remain incomplete. Real-tree clean acceptance remains mandatory.
First corrected-fixture run:exit1,1failed60passed68.00s; expected diagnostic order
was wrong (docs first versus actual qa first). Only expected order corrected;
exact two diagnostic locations/ids retained. Current-hash rerun:exit0,
61passed19.15s. The entire citation file,not a full suite,was actually rerun.
TDD known-id diagnostic: actual first-parse-error assertion RED before source fix,
exit1,9failed2passed48deselected3.99s. An earlier weaker added assertion passed
because a later diagnostic masked the missing id; stronger first-diagnostic
assertion and all previous assertions retained.

Command: uv run --offline pytest --noconftest -p no:cacheprovider tests/test_schema.py tests/test_ledger.py tests/test_ledger_checks.py tests/test_doctor.py tests/test_product_map.py tests/test_ui_product_map.py --tb=short
Actual:exit0,109passed,1Starlette deprecation warning,15.28s.
Combined prior focused/affected tests:170, not a full suite. The109 affected
consumer tests bind unchanged product code; the citation test file was corrected
afterward and requires its own current-identity evidence, not a blanket170PASS.

Command: uv run --offline ruff check src tests scripts
Actual:exit0,All checks passed!
Source/test caps verified:citations295lines,tests300lines,no function over50.
Scoped git diff --check:exit0; CRLF conversion warnings only.
Policy check:node C:/Users/Lenovo/.agents/skills/maker/tools/tick.mjs --policy-check
Actual:exit0,policy.5,targets2,drift0.

Command: uv run --offline autotester doctor
Last actual receipt BEFORE latest43+152 inventory adoption and final diagnostic
edit:exit1,1547coverage/89declaration/2root-clutter on260-reviewed-occurrence
identity. This is an older partial-build receipt, not current clean verification.
Two inaccessible pre-existing scratch directories remain untouched.

Earlier455-row identity check: uv run --offline autotester doctor,
same three synthetic environment values above. Actual exit1,1352coverage,
245declaration,2root-clutter;1599total violations. Root measured the actual
CLI output, grouping rule labels without discarding failures. No full-suite run.
Coverage findings decreased as independent reviews were adopted; declarations
increased because previously unreviewed authorization claims are now exposed.

Fresh768-row partial-inventory identity:command uv run --offline autotester doctor
with the same approved synthetic environment. Actual start09:24:51.643874Z,
end09:26:03.143976Z,exit1;1040coverage,365declaration,2root-clutter,
1407total. CURRENT block SHA256
B97AFFCCFB1EC407E99CF1FCC9130F6FF9B08AB8ED4B8497F9E6BD403A6E1693.
The later27-row adoption invalidates this as final current-tree clean evidence;
it remains an exact partial-build receipt,not a fullsuite or PASS.

## Relevant evidence identity

- citations.py SHA256 8A968A55FF4BBC9C112CD6A0873933860C46E6244E1E2244C62BE36AFA3D3A59
- test_citations.py SHA256 FDE194E9512684B270AC93F2CF41F34E06EB0422D0AAE5ABC0610226E3C4FDEC
- schema/ledger.py SHA256 61A763C6BB8D7AF85BF08555160D5FF0C6AA444E2E5596BDE1BCDE9C5E11AD14
- doctor.py SHA256 A1022B4655C1A6BCCEB5CA372BB483F147EC2210DE9E43083A97B9D607DAA865
- docs/spec.md SHA256 747FE75E0391E08E6F9C1B877C3CC15E530D26F77E97B18F9B5CC2E7CE3AAA9A
- living-ledger contract SHA256 DD252CA15862DA3983739B42618075673B0CDFCD3495A6C01340E0CD4DA77A75
- adapter SHA256 5CAF01B14CF8214DD4357B01FB38825CFBB7FE3E44DB05C1FCE0D0E90AF56BCF
- pyproject.toml SHA256 593084A9B30E8FAEF0B5D2EEE5FC4F9749EA5A0E035F9FF11F2895ED7C127CCA
- uv.lock SHA256 188681B3A300C36FB485C3979CCB735236E3073443D73015BBB3BACE34C86BA1

Environment:Windows,existing .venv; exact runtime fingerprint must be refreshed at
readiness. No service/build deploy id:CLI-only BUILDING, no deployment performed.
Inventory/manifest/docs mutation invalidates older real-tree evidence. Final
checker brief must bind current inputs/conftest/fixtures/dependency hashes.

## Falsification and final handoff remaining

Three earlier isolated green/red/byte-identical-restored proofs exist under
.work/t196-subject-falsification-20261006:unrelated-id swap,What→Why movement,
missing-review enforcement removed. They PRE-DATE the final code/test hashes;
intermediate evidence only. Helper /root/build_t196_citation_checks reported its
bounded final-identity floor checkpoint complete at2026-10-06T08:50:13Z,
11m48s elapsed:18 isolated copies byte-restored, selected controls GREEN,
four bound code/test/model/doctor hashes unchanged, sole Python slot released.
Evidence:.work/t196-subject-falsification-20261006/final-identity-20261006/
with per-case baseline.txt,mutant.txt,restored.txt. Root has not independently
rerun this checkpoint; it is maker-helper evidence, not a checker verdict.

Reported RED cases cover id swap,What-to-Why movement,missing review,empty log,
normalization/comparison/ambiguity,archive full-body versus index-only,
canonical parsing,marker enumeration,known-id diagnostics,exemption neighbor,
review coverage reporting,historical quote,doctor caller,and newly appended claim.
Those18 proofs now precede test strengthening; product identity unchanged.
Eight additional isolated proofs (4m01s) under remaining-final-floors-20261006
close duplicate canonical declaration,foreign entry scope,historical ordinal,
seven resolving wrong subjects,review text,multiplicity,conflict and attribution
gaps on that prior test identity. Each reached its named assertion and restored.
The four review-binding mutations remove substantive guards, unlike the earlier
17 output-suppression probes. No broad final-hash campaign is claimed.
Under strengthened-fixtures-final-20261006,the exact historical output assertion
on DB7C7AA test identity detected four mismatches versus the expected two;
the older any assertion passed. Baseline2PASS,mutant1FAIL1PASS,restored2PASS.
Foreign deletion remained GREEN for the fixture-contamination reason above.
Current corrected foreign and doctor-caller proofs completed on FDE194 test
identity under links-doctor-final-20261006. Foreign baseline1PASS0.34s,
deletion1FAIL4.39s at test266 (extra decision-history:4),restored1PASS2.65s.
Doctor baseline1PASS1.27s,caller deletion1FAIL2.93s at test273 (marker absent),
restored1PASS2.27s. Five-file copies restored;helper terminal61940exit0,
Python slot released. Maker-helper evidence,not an independent final verdict.
Historical exact-output test normalized function fingerprint
C449BD104557AC1958BC8B8A8F00531C1823AA27D8D67DFE228CD7984A4B242E
and relevant helper/product/model/config dependencies unchanged; its old
whole-file proof is still labeled intermediate,not a new whole-file campaign.
No mutation of bound product/test files and no full-suite or readiness claim.

Mandatory before readiness:complete independently reviewed occurrence inventory;
canonical migration of current mutable authorization claims with correct authority;
immutable-history attribution and all seven historical write-policy examples;
remaining acceptance-capability falsifiers; required full pytest suite plus exact
lint/doctor gates; fresh senior review at completed feature boundary; both blind
final checker verdicts. Partial slices and fixture green never close T196.

Owner decision requested once on immutable historical reconciliation:two early
claims cannot truthfully satisfy the What-only boundary while remaining unchanged.
One qualifies the appender's Changes-authorized field; another overattributes
BACK to a decision that did not name it. Both remain authorization claims and
reported, never nonclaiming or convenient-subset quotes. Existing contract has
no addressed-historical-finding disposition. No contract/source change implementing
an exception is authorized or performed while the owner choice is outstanding.

Browser:not applicable to this CLI-only touched flow; this does not waive the
original goal's separate real Pathlynks/ERP browser and human-comparison obligations.
No model/provider call, real credentials, live write, product PASS, closure,
commit, push or deployment claimed. Goal remains58done/24pending.

Metrics: start=2026-10-06T08:20:24Z end=2026-10-06T08:43:18Z wall_min=22.9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.5
Metrics window above is an earlier historical continuation; three mutations are older
intermediate identities, not completed final-identity floor coverage.

## 2026-10-06 T196 checkpoint K — first 100 unreviewed verdict occurrences

Attribution: /root/build_t196_citation_checks

BUILDING data-only classification receipt, not an acceptance verdict. Selection:
first 100 alphabetically ordered unreviewed occurrence bindings in qa/verdicts/*.md
against the CURRENT block snapshot below; repeated identical physical lines bind
through multiplicity. All selected multiplicities are 1. Whole source lines and
their surrounding context were reviewed; no automatic prose classification.
Full What bodies of all seven referenced entries were read in docs/DECISIONS.md;
no archive body was needed. Ordinary references below identify the specific
non-authorizing role of each occurrence; authorization claims remain explicit
migration-needed, with no optional historical What bypass for verdict files.
No past verdict, history, source, contract, goal or CURRENT inventory was edited.
The JSONL is documentary inventory metadata, not a grant of operational authority;
its visible manifest citations still require separate complete-inventory coverage.

Input SHA256 bindings:
- CURRENT body (LF-joined between exact standalone delimiters, excluding delimiters): 9AE4AD6019A01965C328679A9217CDFA103A3E013CD953EE74153E39E7BB763F
- qa/verdicts/at011-loop-md.md: 4FA5A88DC2044DE64B7A28F7D60287806438870971E7A226B9691D836CC8A73E
- qa/verdicts/at015-at028-hook-adapter-fix.md: C67838EE0157E8FFB0813CA74BC0AC9C27C5EDA77015C78EA74F381C7C2AEE0A
- qa/verdicts/at097-session-start-hook-regression.md: 541788AC01DA78207ABA52E8A82498154E89D9520981577311A194D1B400FEAB
- docs/DECISIONS.md: 797B17358F8D51369DA2EB8BCF50C65B8D1060CEA2220CA996CC62E259159445
- qa/contracts/living-ledger.md: DD252CA15862DA3983739B42618075673B0CDFCD3495A6C01340E0CD4DA77A75
- src/autotester/ledger/citations.py: 8A968A55FF4BBC9C112CD6A0873933860C46E6244E1E2244C62BE36AFA3D3A59
- src/autotester/schema/ledger.py: 61A763C6BB8D7AF85BF08555160D5FF0C6AA444E2E5596BDE1BCDE9C5E11AD14

Checkpoint K classification rows follow. Review-reference availability establishes
attribution only; an independent final checker must still challenge these reasons.

```jsonl
{"path":"qa/verdicts/at011-loop-md.md","line_text":"  ops with D-007's push exception scoped narrowly, and a `GRILL:` finding.","id":"D-007","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: asserts the standing push exception's operational scope; raw verdict prose is not a canonical full-What declaration.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"This unit hit its 3-cycle fix budget and STALLED (cycle-3 FAIL, `AT-031`: D-010's `Approved-by`","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"References the earlier defective Approved-by attribution as a finding/comparison, not as permission to perform the cap change.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"named the recovery: append a new D-011 that directly quotes the real approval exchange verbatim.","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the append-only recovery entry as historical work being verified; this occurrence does not assert operational authorization scope.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"## 1. D-011 form check","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Section label for a form check, not a decision-entry structural header or an authorization grant.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"Read `docs/DECISIONS.md` D-011 in full (lines 166-190). It has all required fields: **What**,","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Checks required record fields and append-only form; does not claim this cited entry authorizes a product action.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"per `append_decision.ps1`'s V1-V7 gates, and it correctly does NOT re-litigate or edit D-010","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the older entry as the target of the correction/non-editing discussion, not the source of the corrective authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"(append-only respected; D-011 explicitly says \"D-010's code/text is otherwise accurate and is NOT","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: quotes the corrective entry's claimed non-relitigation boundary; partial multiline raw prose is not a canonical full-What declaration.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"(append-only respected; D-011 explicitly says \"D-010's code/text is otherwise accurate and is NOT","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the older entry as the target of the correction/non-editing discussion, not the source of the corrective authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"rather than restate/infer an extension the way D-010's did? Yes:","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"References the earlier defective Approved-by attribution as a finding/comparison, not as permission to perform the cap change.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"This is categorically different from D-010's defect: D-010's Approved-by cited the *old*","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"References the earlier defective Approved-by attribution as a finding/comparison, not as permission to perform the cap change.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"This is categorically different from D-010's defect: D-010's Approved-by cited the *old*","id":"D-010","ordinal":2,"multiplicity":1,"kind":"ordinary-reference","reason":"References the earlier defective Approved-by attribution as a finding/comparison, not as permission to perform the cap change.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"AT-015/AT-028 batch quote and asserted an extension; D-011's Approved-by cites *this* entry's own","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Reports the corrected Approved-by field's quotation form; the occurrence is record-quality evidence rather than an operational scope grant.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"(D-008-D-011), `qa/loop.md`, `docs/SNAPSHOT.md`, `qa/manifests/at015-at028-hook-adapter-fix.md`,","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies decision entries included in a committed file/path inventory, not authority for an operation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"(D-008-D-011), `qa/loop.md`, `docs/SNAPSHOT.md`, `qa/manifests/at015-at028-hook-adapter-fix.md`,","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies decision entries included in a committed file/path inventory, not authority for an operation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"- **AT-030**: `open` -> `fixed` (D-010's authorization gap is superseded in effect by D-011, which","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the older entry as the target of the correction/non-editing discussion, not the source of the corrective authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"- **AT-030**: `open` -> `fixed` (D-010's authorization gap is superseded in effect by D-011, which","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: asserts that the corrective entry supplies the authorization gap's remedy; raw verdict prose is not canonical.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"  supplies the missing verbatim citation without editing D-010, per the Lab Protocol's","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the older entry as the target of the correction/non-editing discussion, not the source of the corrective authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"- **AT-031**: `open` -> `fixed` (D-011's Approved-by now directly quotes a specific approval","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Reports the corrected Approved-by field's quotation form; the occurrence is record-quality evidence rather than an operational scope grant.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"EXPLANATION: The named recovery (append D-011 quoting the real approval exchange verbatim) was","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the append-only recovery entry as historical work being verified; this occurrence does not assert operational authorization scope.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"applied correctly — D-011 has all required fields, does not re-litigate D-010, and its","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Checks required record fields and append-only form; does not claim this cited entry authorizes a product action.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"applied correctly — D-011 has all required fields, does not re-litigate D-010, and its","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the older entry as the target of the correction/non-editing discussion, not the source of the corrective authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"DECISIONS.md D-008-D-011, manifest, debug report, issues.jsonl, verdict) have now been committed","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies decision entries included in a committed file/path inventory, not authority for an operation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at015-at028-hook-adapter-fix.md","line_text":"DECISIONS.md D-008-D-011, manifest, debug report, issues.jsonl, verdict) have now been committed","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies decision entries included in a committed file/path inventory, not authority for an operation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"**Unit:** commit `b9fa94b` (closes AT-097 high, AT-029 medium; authorized by D-019)","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly calls this entry the authorization for the listed unit/commits; no canonical visible What quotation is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"I was asked to judge this adversarially and not to wave it through. I read D-008, D-010, D-011,","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Enumerates entries the checker read as evidence; this occurrence itself does not state what any entry authorizes.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"I was asked to judge this adversarially and not to wave it through. I read D-008, D-010, D-011,","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Enumerates entries the checker read as evidence; this occurrence itself does not state what any entry authorizes.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"I was asked to judge this adversarially and not to wave it through. I read D-008, D-010, D-011,","id":"D-011","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Enumerates entries the checker read as evidence; this occurrence itself does not state what any entry authorizes.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-013 and D-019 myself. **The reasoning holds on all three sub-questions.** This is *not* where","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Enumerates entries the checker read as evidence; this occurrence itself does not state what any entry authorizes.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-013 and D-019 myself. **The reasoning holds on all three sub-questions.** This is *not* where","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Enumerates entries the checker read as evidence; this occurrence itself does not state what any entry authorizes.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"### (a) Do D-008 and D-010 authorize these exact two values? — YES","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: the heading explicitly answers that these entries authorize the two restored values; no canonical What declaration is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"### (a) Do D-008 and D-010 authorize these exact two values? — YES","id":"D-010","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: the heading explicitly answers that these entries authorize the two restored values; no canonical What declaration is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **D-008** (ACTIVE, `Approved-by: Umesh` — batch answer \"Yes, approve both\", 2026-09-03).","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: names the active approval as support for the following filter-scope assertion; approval metadata alone is not a canonical What declaration.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **D-010** (ACTIVE, `Approved-by: Umesh`) authorizes the cap `-ge 100` → `-ge 150` and the label","id":"D-010","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: claims specific filter/cap authority from the cited entry; raw prose or an approval exchange is not a canonical What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  text, naming the specific line. **D-011** (ACTIVE) then supplies the *verbatim, cap-specific,","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: claims specific filter/cap authority from the cited entry; raw prose or an approval exchange is not a canonical What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"the authorization **name the specific change** rather than be assumed. D-008 names the filter;","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: claims specific filter/cap authority from the cited entry; raw prose or an approval exchange is not a canonical What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-011 names the cap verbatim. D-019 is not stretching an approval onto a value Umesh never saw; it","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: claims specific filter/cap authority from the cited entry; raw prose or an approval exchange is not a canonical What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-011 names the cap verbatim. D-019 is not stretching an approval onto a value Umesh never saw; it","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: claims the restoration entry relies only on already-approved exact values; attribution to its full What remains declarationally unresolved.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"### (b) Was 051303e's revert unintended, or does D-013 legitimately supersede? — UNINTENDED","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: uses this entry's stated unchanged-behavior boundary to deny superseding authority; the scoped attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-013's own text disclaims the effect:","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: uses this entry's stated unchanged-behavior boundary to deny superseding authority; the scoped attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- No `Supersedes:` line for D-008 or D-010.","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names potential supersession targets absent from a Supersedes field; does not derive permission from those targets.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- No `Supersedes:` line for D-008 or D-010.","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names potential supersession targets absent from a Supersedes field; does not derive permission from those targets.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"Nowhere does D-013 argue that the numbered-heading allowlist is *desirable* — an allowlist D-008","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: uses this entry's stated unchanged-behavior boundary to deny superseding authority; the scoped attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"Nowhere does D-013 argue that the numbered-heading allowlist is *desirable* — an allowlist D-008","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"References the prior filter diagnosis of zero matching headings, an empirical defect statement rather than an operational approval.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"had already proven matches zero headings in this repo. Reading D-013 as a legitimate supersession","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: uses this entry's stated unchanged-behavior boundary to deny superseding authority; the scoped attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"**Therefore restoring D-008/D-010's values creates no new authority and needs no fresh human gate.**","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly uses the cited values as standing authority to restore without a fresh human gate; no canonical full-What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"**Therefore restoring D-008/D-010's values creates no new authority and needs no fresh human gate.**","id":"D-010","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly uses the cited values as standing authority to restore without a fresh human gate; no canonical full-What quotation.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"### (c) Was declining `Supersedes: D-013` correct? — YES","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the candidate supersession/non-editing target when discussing protocol mechanics; this occurrence is not the source of permission.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"injected at every session start. Marking D-013 SUPERSEDED would print, in every future session,","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the candidate supersession/non-editing target when discussing protocol mechanics; this occurrence is not the source of permission.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"primitive, and D-013 cannot be edited (append-only).","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the candidate supersession/non-editing target when discussing protocol mechanics; this occurrence is not the source of permission.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"This repo also already has the correct, checker-endorsed pattern for exactly this: **D-011** narrows","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: invokes the corrective entry as the operative precedent for partial correction without supersession; raw authorization reasoning is not canonical.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"and corrects D-010's authorization record while stating \"D-010 itself is never edited\" and \"is NOT","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the corrected old entry inside the quoted non-editing statement; it is the correction target, not an authorization source.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"and corrects D-010's authorization record while stating \"D-010 itself is never edited\" and \"is NOT","id":"D-010","ordinal":2,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the corrected old entry inside the quoted non-editing statement; it is the correction target, not an authorization source.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"re-litigated\" — with no `Supersedes` line. D-019 follows that precedent, states the narrowing","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: asserts the restoration entry's narrowing follows an authorized precedent; raw prose is not a canonical What declaration.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"explicitly in both `What` and `Why`, and links D-013. **The protocol does not require the line","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the entry linked by the restoration record; the occurrence is a link target, not a source of authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"**One accuracy note (not a failure):** D-019's claim that it \"creates NO new authority\" is slightly","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: attributes a standing template-divergence policy to the entry while questioning its no-new-authority claim; disputed scope remains explicit.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"to the AIOS template — narrows a clause of D-013's `Changes-authorized` that Umesh did approve.","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: asserts that this entry's approved byte-identical clause is narrowed by the later policy; scope is not canonically attributed to What.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"That is a small new policy, not covered by D-008/D-010. It is documented prominently and was","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Explicitly excludes these older approvals from the new template-divergence policy; does not present them as authority for that policy.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"That is a small new policy, not covered by D-008/D-010. It is documented prominently and was","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Explicitly excludes these older approvals from the new template-divergence policy; does not present them as authority for that policy.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"whole filter block — the code D-008, D-010 and now D-019 have changed three times — **has never","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"whole filter block — the code D-008, D-010 and now D-019 have changed three times — **has never","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"whole filter block — the code D-008, D-010 and now D-019 have changed three times — **has never","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **AT-097** — the record/disk divergence is repaired and D-019 is a correct authorizing entry. But","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly declares the entry a correct authorizing record; no canonical visible What quotation is supplied.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- The manifest's \"Design rules, Commands and Status now reach the session\" and D-019's Result \"the","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Challenges the cited entry's Result as false in execution, not its What as an operational authorization.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"OLD filter (051303e / D-013 state, cap 100): kept 1 line, 0 '## ' headings","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Labels old/new measured filter states in recorded diagnostic output; this version label does not grant operational authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"NEW filter (b9fa94b / D-019 state, cap 150): kept 140 lines, 10 '## ' headings","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Labels old/new measured filter states in recorded diagnostic output; this version label does not grant operational authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"### 4. D-013's ASCII-escaping half — UNTOUCHED ✓","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the ASCII-escaping behavior as untouched regression evidence; this occurrence reports preservation, not permission to modify it.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  D-008/D-010/D-019, so it needs its own authorizing entry with a fresh Approved-by. · issue: AT-106","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Explicitly says the path value is outside these entries' authority and requires its own approval; no authority is claimed from these excluded entries.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  D-008/D-010/D-019, so it needs its own authorizing entry with a fresh Approved-by. · issue: AT-106","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Explicitly says the path value is outside these entries' authority and requires its own approval; no authority is claimed from these excluded entries.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  D-008/D-010/D-019, so it needs its own authorizing entry with a fresh Approved-by. · issue: AT-106","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Explicitly says the path value is outside these entries' authority and requires its own approval; no authority is claimed from these excluded entries.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> repo's genesis commit — not since 2026-09-05. The filter that D-008, D-010 and D-019 all fixed","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> repo's genesis commit — not since 2026-09-05. The filter that D-008, D-010 and D-019 all fixed","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> repo's genesis commit — not since 2026-09-05. The filter that D-008, D-010 and D-019 all fixed","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names historical filter edits in a diagnostic account of code that never ran; no operational permission is asserted at this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> further from the AIOS Lab template (already recorded as deliberate by D-019 item 4).","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: invokes this entry's item 4 as standing deliberate template divergence while proposing the new path fix; the policy attribution remains noncanonical.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> approval request for D-019, whose reasoning I judged sound above.**","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the earlier entry as not the subject of the new approval request; the gate still requires its own fresh approval.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"The approval judgement the maker asked me to make is **sound and I uphold it**: D-008 and D-010","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly upholds these entries as authorizing precisely the restored filter/cap; full-What attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"The approval judgement the maker asked me to make is **sound and I uphold it**: D-008 and D-010","id":"D-010","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly upholds these entries as authorizing precisely the restored filter/cap; full-What attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"(with D-011's verbatim exchange) authorize precisely the filter and the cap that were restored;","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly upholds these entries as authorizing precisely the restored filter/cap; full-What attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-013's revert was a side effect its own text disclaims rather than a decision that supersedes","id":"D-013","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: uses this entry's stated unchanged-behavior boundary to deny superseding authority; the scoped attribution is not canonically declared.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"them; and declining `Supersedes: D-013` was right, because the supersession marker is computed into","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the candidate supersession/non-editing target when discussing protocol mechanics; this occurrence is not the source of permission.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"every session's decision index and would misreport a live ASCII-escaping fix — with D-011 standing","id":"D-011","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: invokes the corrective entry as the operative precedent for partial correction without supersession; raw authorization reasoning is not canonical.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"verify commands all reproduce exactly (555 passed / 1 skipped, ruff clean, doctor clean), D-013's","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the ASCII-escaping behavior as untouched regression evidence; this occurrence reports preservation, not permission to modify it.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"AT-107 high; authorized by D-019 + D-020)","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly calls this entry the authorization for the listed unit/commits; no canonical visible What quotation is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"AT-107 high; authorized by D-019 + D-020)","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly calls this entry the authorization for the listed unit/commits; no canonical visible What quotation is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"> before any file was touched, per the gate-record rule. Authorizing entry: **D-020**.","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: quoted gate answer explicitly identifies the authorizing entry for the path fix; quotation context is not an example exemption.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"*within* `5d99520`, because the `Answered:` line, D-020 and the code edit all land in that one","id":"D-020","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names an entry among same-commit artifacts when stating a temporal-ordering evidence limitation; no authorization scope is asserted.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"**D-020 exists, is its own entry, and does not stretch an approval.** Verified by reading it in","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: endorses this separate entry as an unstretched approval for the fix; raw approval reasoning is not canonical.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- `**Changes-authorized:** .claude/hooks/lab-session-start.ps1 (the $archPath value only; the D-013","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names neighboring prior behaviors as explicitly untouched in the new entry's Changes-authorized quotation; these are excluded subjects, not sources of the new path authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  ASCII-escaping and the D-008/D-010 filter and cap are untouched); tests/test_session_start_hook.py.`","id":"D-008","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names neighboring prior behaviors as explicitly untouched in the new entry's Changes-authorized quotation; these are excluded subjects, not sources of the new path authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"  ASCII-escaping and the D-008/D-010 filter and cap are untouched); tests/test_session_start_hook.py.`","id":"D-010","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names neighboring prior behaviors as explicitly untouched in the new entry's Changes-authorized quotation; these are excluded subjects, not sources of the new path authority.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"text. Nothing in the authorization is stretched, and D-019 was correctly **not** extended — which is","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the old approval as deliberately not extended to the path; permission comes from a different entry, not this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"summary` is the only `## ` section dropped, which is exactly D-008's rule.","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: presents the cited filter/cap rule as the exact approved operational value reproduced by the code; no canonical What quotation is supplied.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"D-020 itself*, quoting the old warning. The maker reported \"actual [WARN] lines: none\", which is the","id":"D-020","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names injected decision text as the location of a quoted old warning, distinguishing text from an emitted runtime warning.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **D-013's ASCII escaping — untouched.** `lab-session-start.ps1:191` still carries","id":"D-013","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Names the ASCII-escaping behavior as untouched regression evidence; this occurrence reports preservation, not permission to modify it.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **D-008's filter — in place.** Line 125: `$inKeep = ($line -notmatch '^## Directory map and schema summary')`.","id":"D-008","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: presents the cited filter/cap rule as the exact approved operational value reproduced by the code; no canonical What quotation is supplied.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"- **D-010's cap — in place.** Line 128: `if ($keep.Count -ge 150) { ... \"capped at 150 lines\" ... }`.","id":"D-010","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: presents the cited filter/cap rule as the exact approved operational value reproduced by the code; no canonical What quotation is supplied.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"| **AT-097** (high) | **CLOSABLE → fixed.** Both halves are now real: the record/disk divergence is repaired under D-019, and the ground-truth block actually reaches the session (0 → 10 headings, verified by running the hook). |","id":"D-019","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly states that the repair/change is under or within this entry's authorization; no canonical visible full-What attribution is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"| **AT-106** (high) | **CLOSABLE → fixed.** Path corrected under its own gate + D-020; the else-branch `[WARN]` no longer fires. |","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly states that the repair/change is under or within this entry's authorization; no canonical visible full-What attribution is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"   enforcement diff inside it is exactly the two authorized lines, so nothing is smuggled and D-020","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly states that the repair/change is under or within this entry's authorization; no canonical visible full-What attribution is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"not extend D-019 to cover the path, it raised a gate, got Umesh's answer, wrote it to disk, and","id":"D-019","ordinal":1,"multiplicity":1,"kind":"ordinary-reference","reason":"Identifies the old approval as deliberately not extended to the path; permission comes from a different entry, not this occurrence.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
{"path":"qa/verdicts/at097-session-start-hook-regression.md","line_text":"authorized the change with its own narrowly-scoped D-020 whose `Changes-authorized` explicitly","id":"D-020","ordinal":1,"multiplicity":1,"kind":"authorization-claim","reason":"Migration-needed: explicitly states that the repair/change is under or within this entry's authorization; no canonical visible full-What attribution is present.","reviewer":"/root/build_t196_citation_checks","review_ref":"qa/manifests/t196-citation-subject-check.md:208"}
```

Checkpoint K terminal counts: 100 complete bound rows; 60 ordinary-reference;
40 authorization-claim, all migration-needed; 0 structural-header, foreign-entry
or nonclaiming. All original sources remain untouched. These are classification
evidence, not proof of complete real-tree coverage, migration, readiness or PASS.
The input-snapshot hashes above bind this receipt; integrations must revalidate
current exact lines/ordinals/multiplicity and must not treat stale rows as coverage.
