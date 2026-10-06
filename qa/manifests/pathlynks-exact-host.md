# Manifest — Pathlynks exact-host credential scope

Contract: qa/contracts/browser-and-secrets.md B2/B3; core-invariants C1-C7
Goal task: T-122 prerequisite; AT-651 credential-scope component only
Policy-Version: proportional-verification/2026-10-06.5
Protocol hashes: maker 3F5A021B27A04447C87726929BAB9FA6245C1251A36E28E9CF5CA91DCCB4063B;
checker 12C935F80B4344E1C7B43C7F2A3467B71D1923B8883A06D16B9D7E828CDB47E5
Fix cycle: 0 of 2
Resumes: 0 of 2
Phase: BUILDING
Status: BUILDING
Tier: L — auth/security credential scope
Dual check: required — credential security
Base: bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf
Root: D:/autoTesting; adapter: coding; inline single owned build

## Plan approval

/root/approve_exact_host_slice approved product plan and existing navigation-test
location amendment before code edits; records in qa/feedback-inbox.md, 2026-10-06.
Umesh explicitly approved this manifest's creation. No contract amendment needed
for the tighter scope. No new product or test module was created.

## Acceptance

1. Both SecretStore.resolve and resolve_for_navigation honor an exact-host mode:
   equality succeeds, child/sibling/parent/lookalike hosts refuse, while omitted
   or true flags retain legacy subdomain behavior.
2. Strict boolean configuration rejects strings, integers, null and collections;
   JSON roundtrips retain false rather than defaulting it to true.
3. Saved Pathlynks USER references allow only pathlynks.vidysea.com; COUNSELLOR
   references only dev-new.vidysea.com. The four flags are false. Project-wide
   navigation allowance, masking, write policy and actual credential values stay
   unchanged. Synthetic values prove role separation; no real account run here.
4. Existing ambiguity refusal, prompt gate, redaction, persistence and affected
   callers retain behavior. Required full-suite/lint/doctor evidence and two blind
   checker verdicts are mandatory before this slice can claim PASS.

## Owned files / current SHA256

- src/autotester/schema/project.py::SecretRef —
  93654FBB0B8D8A92F2B911178DF1BF099195E678F9B70755ED65E5035FF33614
- src/autotester/browser/secrets.py::_host_matches, resolve_for_navigation, _value_for —
  7382DE8ADAF8F943A8BB669EC01307CAA29AD6A04AFB9C0B9046736AFED461EB
- tests/test_browser_navigation_secrets.py —
  A7DA4D29751E90EC3F26B98E72DCDD80CDB06F312031B2F6A0EC925607A8786F
- projects/pathlynks/project.json —
  49247E82606FD6CE62A5894DC533E53E682873A16F2F49D327CA2CB8857FF95A

## Actual builder verification

Commands used uv run --offline; pytest ran with plugin autoload disabled and
PYTEST_CURRENT_TEST marker. Scoped secret checks additionally used --noconftest
and -p no:cacheprovider. These are trusted mocked tests, not an OS sandbox claim.

- New 48 in-memory checks: pre-edit 40 failed/8 passed/5 deselected; post-edit
  48 passed/5 deselected in 1.16s. Baseline failures include missing schema field,
  not a falsification claim.
- pytest tests/test_secrets.py tests/test_browser_navigation_secrets.py --tb=short:
  83 passed in 2.80s (with scoped options above).
- pytest tests/test_schema.py tests/test_core.py tests/test_store.py
  tests/test_onboard_pathlynks.py tests/test_ui_env_editor.py
  tests/test_ui_secrets_declaration.py tests/test_ui_project_intake.py --tb=short:
  73 passed/1 skipped/1 Starlette deprecation warning in 3.94s.
- ruff check src tests scripts: exit0, All checks passed!
- autotester doctor: exit1, root-clutter at113-fixture-wn6g4n_e and pytest-of-unknown,
  missing T-171 ledger row, stale snapshot. Existing snapshot regenerated afterward
  by autotester snapshot (exit0, 44 lines); no fresh doctor receipt yet.
- git diff --check for owned product/test/config paths and feedback: exit0.

Maker isolated falsification: .work/exact-host-falsification-20261006. Copied
baseline 48 passed; separate copy per mutation. Ignore flag: 6 assertion failures;
drop strict validation: 4; false legacy default: 12; broaden USER password domain:
1. Every pytest exit1 reached intended assertions, no import/collection error.
All changed product/config files restored byte-identical to copied baseline;
each restored run 48 passed (2.59/1.85/1.92/1.96s). No bound-source mutation.

## Outstanding / no completion claim

Broader browser/UI affected union, L full suite, completed-boundary senior review,
two blind independent checker coordinators, narrow PASS commit/push. Runtime
containment remains a distinct prerequisite: approved viewer needs 4GiB headroom;
actual FreePhysicalMemory 1602344 KiB. Docker engine/image present; no container
launched, no unrelated process killed. Docker is not a product dependency.

This slice does not close T-122 or all of AT-651 (environment modeling separate).
T-122 still needs the USER-account end-to-end run and account-derived signed-grant
and aggregate execution-budget changes. Current canonical count 58 done/24 pending.
No independent feature verdict, commit, push or live-validation claim.

Metrics: start=2026-10-06 end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.5

## Authorized continuation — account-run prerequisites (still BUILDING)

Umesh approved this file and .work/pathlynks-consent-decision-entry.md explicitly.
The entry was appended using scripts/append_decision.ps1: exit0 APPENDED D-063 ACTIVE.
Independent checker maintenance adopted CN11 in qa/contracts/consent.md; CN1-CN10
normalized comparison remained identical. No acceptance PASS was claimed.

Fresh independent implementation plans approved in qa/feedback-inbox.md:
/root/approve_signed_grant_plan (key/env/fresh grant),
/root/approve_aggregate_budget_plan (one shared execution budget), plus its trace
stop-reason amendment. Two owned build workers execute in parallel; root owns
ui/routes_runs.py and core/trace.py/schema/trace.py integration and existing
test_ui_runs_parallel_trace.py/test_run_trace.py regression checks. No new product
or test module. Existing-file plan scopes and mandatory corrections remain binding.

Root implementation: referenced case credential keys alone gate account runs;
unused role declarations do not. Before any run/browser creation, validate scope
and positive derived brakes, prepare a signing key explicitly with deferred typed
repository-wide history under the env writer lock, and verify/store one NEW exact
grant. Human-grant route remains for cases without account references. One budget
instance is passed to serial/entry/parallel helpers. Failed EXECUTE spans preserve
the named brake through the SAME redacted TraceWriter; optional StageSpan.error
keeps legacy rows parseable.

Actual root regression receipt:
uv run --offline pytest tests/test_ui_runs_parallel_trace.py tests/test_run_trace.py
--tb=short, PYTEST_CURRENT_TEST set, plugin autoload disabled: 18 passed, 6 warnings
in 6.92s. Warnings: existing Starlette deprecation and expected synthetic no-secrets
StageContext warnings. Covers fresh scoped grant, unused missing role, trace failure
at widths1/2, synthetic error redaction, legacy missing-error parsing. Earlier new
trace assertions were red (3failed/5passed); one fixture lacked declared host scope,
and two proved missing writer/schema error propagation. Fixture corrected without
weakening the exact scope; independently approved trace propagation implemented.
This is builder evidence, not a checker verdict or live account success.

Other completed affected exact-host consumer run:
pytest --noconftest -p no:cacheprovider tests/test_browser.py
tests/test_browser_actions.py tests/test_browser_settle.py tests/test_execute.py
-k 'not real_headless_launch' --tb=short: 36 passed,1deselected in6.77s.
The real browser case was deliberately excluded; not full-suite evidence.

Historical bookkeeping only: T-171 already-done cycle2 checked-PASS row missing
from FEATURES was appended via authorized ledger CLI as F-067 live
permission-surface-coverage with existing verdict reference and already-prefilled
reason under Umesh's standing approval. No T-171 recheck or new task closure.
Current canonical 58done/24pending unchanged.

Current dependency: CIM FreePhysicalMemory21396KiB (~21MiB) on2026-10-06.
Heavy/native/full-suite validation must not launch into that headroom. User asked
to free>=4GiB; no unrelated processes killed. Even escalated read-only enumeration
of existing root-clutter dirs at113-fixture-wn6g4n_e and pytest-of-unknown is denied;
no ACL takeover, deletion or relocation attempted. Receipt prior-field accountability
amendment is under independent plan review; completed feature readiness awaits its
implementation, worker results/falsification, affected closure, L full suite/doctor,
completed-boundary senior review, two fresh blind final checkers and narrow PASS
commit/push. No intermediate checker dispatched while BUILDING.

### Parallel worker checkpoint (not final current-source acceptance)

Signed-key/grant worker completed its seven owned existing files:
core/ids.py, core/consent.py, ui/env_editor.py, cli_crawl.py,
tests/test_core.py, tests/test_consent.py, tests/test_ui_env_editor.py.
Actual affected8module run:100passed,1POSIXskip,1Starlettewarning49.93s;
expanded guard subset22passed9.95s; isolated baseline21passed10.72s.
Two safety edits after that run loaded (bounded child-startup reader and huge
integer wall-clock refusal/test) need focused rerun. Seven separate mutation
copies prepared, no mutants applied because of critically low RAM. No child
process remains running. Owned worker lint/cap checks green before those final
test edits; current final closeout must rerun, not substitute this checkpoint.

Worker hashes at handoff:
core/ids.py E667C641247DB1B1940B5F109D3591B705DEF3084370E9B35618CBD92BD35098
core/consent.py B46EC9BC85486FF936722E3A9038241E8F881AD551AA943FA55CFF34F0926BD5
ui/env_editor.py 3B588E3B71C79EDA92E920A3E419DDD53CC6ECFAB7B4144B7310145D85D7FD36
cli_crawl.py ED985EFACC0CF66CFAFB25DF7C701D650E6CC4B942ECC12D915CF951748FDABA
tests/test_core.py 9CAC47CCB948016C57D6F0E2A5E7FE635595E3C4BEE9E8C374337A1921EC9FF5
tests/test_consent.py C8EC87CFE28E04249E50E975A60755A22BB11F77BD32D1F6817BE65638CE30AE
tests/test_ui_env_editor.py 03EEBC345CA79BA1B90F7E392DDB543762DEEAEC677E3C59A130D4F2CA686BA7

Aggregate worker earlier fake-only affected checks:68passed12.17s; later UI
startup batch21passed/2failed from fixture API incompatibility (timeout keyword,
immutable fake session binding), originals assertions preserved for fixture repair.
Another downstream batch39passed/1setup-error: real video parallel-sweep fixture
excluded by --noconftest, not a behavior acceptance or browser launch.
CN11 field receipt amendment independently approved and being implemented by
the same owner in session.py/evidence.py and existingtest_browser_actions.py;
successful fill must retain receipt even when after-read triggers deadline.
Never read secret/password/tagged/unclassified prior values. This late change
and atomic sticky-brake race fix need tests/falsification before readiness.

Latest measured RAM550740KiB (~538MiB), still below approved4GiB native acceptance
headroom. Lightweight static check during BUILDING reported pending worker
session.py306line cap and one test signature lint finding; root fixed its two
long lines. Doctor also reports generatedMAPstale and two inaccessible rootclutter
dirs; no longer reports missingT171ledger or staleSNAPSHOT. These are outstanding
findings, not a clean doctor receipt. No fullsuite/mutation/realbrowser launch.

### Final text checkpoint and scoped cleanup audit

Aggregate worker completed approved receipt/atomic/startup code and existing
tests, including preserved UI fake assertions. No owned process remains.
New field receipt/atomic sticky brake/startup cleanup/test changes have NOT run
on the final tree; prior green runs are scoped checkpoints, not final acceptance.
Session299lines, other ownedfiles<=300; final function AST/lint still needs rerun.
Source hashes supplied by worker:
stages/run_budget.py F980FF2644F82C1DCB58BE32A67491A440A90152B9E7AFC93D62AF3E4AB51D45
stages/parallel_run.py 818F446AD5A32A6384E0FEA8A6ED2284E374DAA6941CF98E11E068FAF8578A2E
stages/execute.py 7033186AB6602DE4E3023B52867FB1FF7F20ADE599CEA230B80B8A2C7648DF69
ui/run_execution.py C04A99A49CD14520BB4AC588873C2BBE036EDD4CC4DB0B45DE242C26A17B602D
browser/session.py EE0DEC8B6EB0ED8F84EF5576641B3A2F6AAD3E70B2F177D22DFB72EC6C82572F
browser/assertions.py 4D99ABED034EF1BF5C1C986E7F918839F63AD125B45176C78C5BEA2F11B23E04
browser/evidence.py 39A13D06A4C268AC8099E858C906D603CBC8A3460B9A37BC600E0812B15E54B8
browser/video.py C038430BCE99512D5B0377CCE19FEF74AE8CDB2878F82E12F851DE46B4A891E6

Root regenerated docs/MAP.md via autotester map:exit0. Not a clean doctor claim;
native/fullsuite and rootclutter obligations remain. Landplane release verification
is REFUSED/incomplete: no checked-PASS, no fullsuite receipt, no commit/push.
All source and test work retained; goal remains active, not complete or paused.

Umesh requested cleanup of unused processes from past5hours. Read-only exactPID
ownership/age/container/activity audit found no running old AutoTesting viewer/
browser/test runtime to terminate. No process closed or container stopped.
Current Codex/ChatGPT, recent Pythonjobs and recently created Chromerenderers
remain active/ownership unknown. Docker holds other projects, not stale AutoTesting:
deepinterview-agent-worker measured272.91%CPU; deepinterview-kokoro about1.014GiB,
and whatsapp-msg-mongo/KnowledgeBase work container also active. Their start-age
is not proof of5hour inactivity. No blanket Docker/WSL shutdown or database stop.
Latest measured freeRAM259512KiB (~253MiB). Exact app shutdown targets remain
a user choice if reclaim requires closing Chrome/VSCode beyond proven idle jobs.

### Final-tree focused verification (serial, 2026-10-06 continuation)

Environment for both pytest commands: PYTEST_CURRENT_TEST=budget-tests,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, AUTOTESTER_APPROVAL_KEY=synthetic-budget-test-key.
These are mocked builder checks, not live-browser or OS-containment evidence.

Command: uv run --offline pytest --noconftest -p no:cacheprovider
tests/test_parallel_run.py tests/test_parallel_run_approval.py
tests/test_parallel_run_session_crash.py tests/test_parallel_run_evidence_namespace.py
tests/test_execute.py tests/test_execute_assertions.py tests/test_browser_actions.py
tests/test_browser_settle.py tests/test_ui_runs.py tests/test_ui_runs_serial_resilience.py
tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py
tests/test_ui_runs_parallel_crash_recovery.py --tb=short
Result: exit0; 103 passed, 1 Starlette deprecation warning in 12.06s.
Covers final field receipts, secret-value non-reading, exact deadline propagation,
aggregate execution/probe brakes, browser startup mocks and repaired UI fixtures.

Command: uv run --offline pytest --noconftest -p no:cacheprovider
tests/test_core.py tests/test_consent.py tests/test_ui_env_editor.py
tests/test_ui_runs_parallel_trace.py tests/test_run_trace.py --tb=short
Result: exit0; 78 passed, 1 skipped, 6 warnings in 8.42s.
Covers final bounded cross-process key setup, malformed/lost signing history,
huge integer wall-clock refusal, exact fresh grants and redacted named-stop traces.
Skip is the existing POSIX-only permission check on Windows; warnings are existing
Starlette deprecation and explicitly synthetic no-secret StageContext fixtures.

Command: uv run --offline ruff check src tests scripts
Result: exit0; All checks passed!
Command: uv run --offline autotester doctor
Result: exit1; exactly 2 root-clutter violations: at113-fixture-wn6g4n_e and
pytest-of-unknown. Source caps, function caps, generated MAP/SNAPSHOT and T171
ledger findings no longer appear. Inaccessible directories have not been deleted,
renamed or had their ACL changed. No clean doctor claim.

Two pytest batches ran one after another: 181 passed total, 1 skipped. No full
suite, final checker, real account, new goal closure, commit or push. Remaining
CN11 isolated falsification is builder work; manifest stays BUILDING.

Receipt identity: Windows/PowerShell, offline uv, root D:/autoTesting,
HEAD bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf; no browser/deploy/data snapshot.
uv.lock SHA256 188681B3A300C36FB485C3979CCB735236E3073443D73015BBB3BACE34C86BA1
qa/adapter.json SHA256 5CAF01B14CF8214DD4357B01FB38825CFBB7FE3E44DB05C1FCE0D0E90AF56BCF
qa/contracts/consent.md SHA256 C07714A3283345243F44943DD533A1DA36B4DE46A59987023E53F6C831861FB1
tests/conftest.py SHA256 9BBB6A4BC2BE7EB9ADFB1B6ADFDFCC8DA4708287349ECB108A0C66C99FF4652A
(not loaded by these --noconftest runs).
ui/routes_runs.py SHA256 30578444178328ABDBBEB2FFB5F9D35DE08069D194B5A1B048D8529ADE9CD3A0
core/trace.py SHA256 DB2C7365F0989A22D3422F8125349AB2B83B534CCD344B9F8F05AD59FBCF34B4
schema/trace.py SHA256 862FE09CB635FAD621F654B25F4523C732B68C454D95CA0FDFEF6DE935A65769
Other product/test hashes are the worker handoff hashes above. Any subsequent
test edit invalidates that test file's receipt identity, not an unchanged source
file's evidence. Later isolated proof must identify its own copied test hash.
Current RAM measurement: FreePhysicalMemory473388KiB (~462MiB) at
2026-10-06T13:17:07+05:30. No unrelated process was stopped to obtain these checks.
Policy check: node C:/Users/Lenovo/.agents/skills/maker/tools/tick.mjs --policy-check
exit0; proportional-verification/2026-10-06.5 targets=2 drift=0.
git diff --check: exit0 (line-ending warnings only).

### CN11 isolated budget/receipt builder falsification

Attribution: /root/build_aggregate_run_budget; copies under
.work/cn11-budget-receipt-falsification-20261006/sticky-brake and escaped-prior.
One Python process at a time; copied-source PYTHONPATH, plugin autoload disabled,
PYTEST_CURRENT_TEST set and synthetic signing key; no live browser/provider.
No bound product mutation. Approved test-only strengthening added two assertions
to tests/test_parallel_run_approval.py::test_budget_spends_cannot_replenish_or_bypass
after the already asserted refusal. All earlier assertions preserved. Its current
bound/copied SHA256 is 402127129239C2455815953E987298B6726E24E7D28514DF45A9162C5DDD281E.
The 103-pass receipt predates this test-only edit; updated touched-file proof below.

Sticky brake: copied touched-file baseline22passed5.38s; mutate the sole
`if require_running and self._stop_reason is not None:` anchor to use False.
Command: D:/autoTesting/.venv/Scripts/python.exe -m pytest --noconftest
-p no:cacheprovider tests/test_parallel_run_approval.py
-k 'spends_cannot_replenish' --tb=short
Result: exit1; 10 failed, 12 deselected2.98s at the intended line178 assertion,
DID NOT RAISE RuntimeError. Byte-identical restore and same whole-file baseline
command without -k: exit0;22passed2.05s.
Product baseline/restored SHA256 F980FF2644F82C1DCB58BE32A67491A440A90152B9E7AFC93D62AF3E4AB51D45
Mutant SHA256 A3D3C8538896248E9B61E873A0CDC91F67577206E13A05EB1AE18A0E6AB953C6

Secret prior receipt: baseline selected11receiptmodes,13deselected15.81s;
the escaped case was included (-k matched the copied directory name too).
Single mutation replaces repr(self.secrets.redactor().scrub(value)) with repr(value).
Command: D:/autoTesting/.venv/Scripts/python.exe -m pytest --noconftest
-p no:cacheprovider
'tests/test_browser_actions.py::test_fill_receipt_observes_values_but_never_reads_secrets[escaped]'
--tb=short
Result: exit1;1failed3.30s at line196, synthetic credential fragments leaked in
the before receipt. Byte-identical restore and same named command:exit0;1passed4.00s.
Product baseline/restored SHA256 39A13D06A4C268AC8099E858C906D603CBC8A3460B9A37BC600E0812B15E54B8
Mutant SHA256 83F4777F3DD700E1DE9CA9445D1996C96A2ECAC5EF9C79D14A7D08720B0227FD
Test SHA256 E8A7174236D6092EFE83283F4A45B33B1EB580E2D548811C4963210DD16CF835
These are two intended assertion failures, not setup/import failures. No acceptance
checker/PASS, full suite, account run, task closure, commit or push follows.

### CN11 isolated signed-grant builder falsification

Attribution: /root/build_signed_account_grant. Existing copies
.work/signed-grant-falsification-20261006/lost-history and verify-new refreshed;
each checked175files (171source/assets plus4tests) hash-identical before mutation.
One serial Python process, copied-source PYTHONPATH, plugin autoload disabled,
PYTEST_CURRENT_TEST and synthetic signing key. No bound-tree product mutation.

Lost-history command: D:/autoTesting/.venv/Scripts/python.exe -m pytest
--noconftest -p no:cacheprovider -o addopts=-q
'tests/test_core.py::test_explicit_approval_key_preparation[lost]' --tb=short
Baseline:exit0;1passed6.88s. Sole mutation changes
`if any(row.signature for row in historical_approvals()):` to `if False:`.
Mutant:exit1;1failed8.18s, intended DID NOT RAISE(SigningKeyMissing, ValueError).
Byte-identical restore:exit0;1passed2.30s.
Restored ids.py SHA256 E667C641247DB1B1940B5F109D3591B705DEF3084370E9B35618CBD92BD35098

Fresh-own-grant command: D:/autoTesting/.venv/Scripts/python.exe -m pytest
--noconftest -p no:cacheprovider -o addopts=-q
'tests/test_consent.py::test_account_grant_is_new_exact_and_bounded[valid]' --tb=short
Baseline:exit0;1passed11.78s. Sole mutation removes new candidate's .sign().
Mutant:exit1;1failed3.66s, ApprovalRequired for missing fresh signature at the
actual require_approval([candidate]) seam in consent.py:87.
Byte-identical restore:exit0;1passed2.22s.
Restored consent.py SHA256 B46EC9BC85486FF936722E3A9038241E8F881AD551AA943FA55CFF34F0926BD5
No claim that removing the final verification call alone was falsified.

All builder test sessions completed; no owned process remains. Eight named maker
mutations now evidenced in total (4exact-host,2budget/receipt,2signed-grant), all in
isolated copies and restored. Broader feature-wide acceptance remains incomplete.
Landplane verification remains REFUSED: doctor has2root-clutter failures; L full
suite and real-product account/browser acceptance are unrun. No release side effect.

### Cleanup re-audit, 2026-10-06 13:59 IST

User requested closing apps/jobs unused for five hours. No confirmed stale
AutoTesting runtime identified; nothing terminated or stopped. Latest RAM sample
FreePhysicalMemory786560KiB (~768MiB); an earlier sample2117988KiB (~2GiB)
was transient, not cleanup credit. No claim of sustained4GiB acceptance headroom.
Old local8000 listener resolves to Docker backend PID32228, created2026-10-05
20:01, forwarding deepinterview-agent-api-1; not an AutoTesting viewer.
Ports8900/8901 have no listener in the current read-only probe. Docker holds
other projects' services and databases; deepinterview-agent-worker-1 restarted
47seconds before the ps sample. Service age does not prove five-hour inactivity.
Active/unknown-ownership Codex/ChatGPT/Chrome/VSCode, HEI Python jobs and other
project databases remain untouched. Exact active-app shutdown needs identified
unused targets, not a blanket image/name kill. Small serial mocked development
tests continue; native/full-suite/live acceptance remains unrun.
T196 coverage diagnostics now also make whole-repo doctor non-green during its
BUILDING migration:1547coverage/89declaration plus2root-clutter on its current
260-reviewed-occurrence identity. These are not T122 product PASS evidence.

### Explicit Chrome cleanup and later governance checkpoint,2026-10-06

The earlier no-process-stopped audit predates Umesh's specific whole-Chrome
choice. On that explicit approval, root requested graceful closure of the two
Chrome windows, then reverified mainPID19204, executable path/start identity
and zero visible window handle before stopping that exact background PID.
No profile/files deleted; other apps/services/databases untouched. Three Chrome
residual processes remained in the cleanup sample; no image-wide kill claimed.
Free RAM later varied from about1.46GiB to1.93GiB and then719224KiB; cleanup
does not establish sustained4GiB acceptance headroom. Small serial mocked tests
are not subject to a blanket4GiB product requirement.

T196 current455-review identity doctor:exit1,1352coverage245declaration,
2root-clutter(1599total). Older260-row counts above remain historical only.
These governance diagnostics, and the remaining native/full-suite/live gates,
are not T122 product verdicts. No real-account/browser/provider run or PASS.
