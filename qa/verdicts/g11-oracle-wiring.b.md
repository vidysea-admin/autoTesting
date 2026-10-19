# Verdict B - g11-oracle-wiring, coordinator B (blind), Cycle checked: 1

Date: 2026-10-19 · Policy-Version: proportional-verification/2026-10-18.15 · Tier L (dual trigger: tenancy plus a prod-write role-assign press) · Head 9cca3e6d (code b2eb6c7b), base 8b93e475, branch wave/g11-oracle-wiring. Judged against the contract text of qa/contracts/multi-role-platform.md (MP8, MP14, MP16-MP20, MP27, MP28, MPI4, MPI5), not the manifest wording.

## Check plan
Git identity and diff scope; security read of every changed line of role_port_authz.py, role_port_mail.py, unified_report_findings.py, schema/oracle_declarations.py plus the call sites they touch; affected tests (grep-based importer set, because the shard tool said integration-required: conftest changed and imports are dynamic); base-commit comparison for every red; ruff and doctor; one falsification per criterion in an isolated copy on D: outside the bound tree.

## Results
- Git: HEAD 9cca3e6d; code commit b2eb6c7b; `git diff --name-only 8b93e475..b2eb6c7b` = 34 files, none in qa/contracts/, none in docs/DECISIONS.md.
- Tests: run A (the 9 new/changed unit files) 97 passed. Run B (22 files: unit set plus every importer of the changed modules) 385 passed, 26 failed. The same 26 nodes fail identically on a clean archive of base 8b93e475 (`runB.fails` vs `base.fails` differ only by the summary line), so they are pre-existing and not caused by this unit. Evidence: qa/evidence/g11-oracle-wiring-b/{runA.log,runB.log,runB.fails,base.fails}.
- Note: suite_lock.py run is exclusive with no --slots, so I ran two pytest processes directly with TMP on D:.
- Manifest Tests[]: 51 named tests, all 51 exist (0 missing).
- Lint: `uv run ruff check src tests scripts` clean. `.venv/Scripts/autotester.exe doctor`: only the stale generated docs/SNAPSHOT.md, which the maker's close-out regenerates (not a unit defect).
- Security read (every changed line, dual trigger):
  - Approval gate: authz_probe.py:149-167 `gate` still runs scope, then `require_project_approval` (ADVERSARIAL, platform base URL, planned probes), then PROBE_CEILING=60; refusals log one non-secret line and raise before any send. `open_session` (authz_probe.py:249-255) keeps the gate and now caps the budget at min(plan.request_cap, PROBE_CEILING, approval.max_probes). No path calls the transport without a session. Held.
  - Probe ceiling and budget: `privilege_cost` = reads + 3 per control (look, attempt, revert); `_role_assigns` reserves 3 before `_reaches`, so a look is never sent that its press and undo cannot follow. A reachable control costs exactly 3; the full run never exceeds the cap or the signed max_probes (test_w3 plan-inside-signed-approval, test_mp20 max_probes). Held.
  - Off-platform: role_probe.http_get uses max_redirects=0, applies the platform-host test to every hop before requesting it (returns off_platform without a request), with MAX_HOPS=5, 1 MB and 10 s bounds; role_port_authz.read resolves inside the platform and raises PlatformScopeError on an off-platform redirect; host_of is fail-closed on backslash and userinfo. I also ran my own fake-session probe of the redirect handling. Held.
  - Mailbox read-only: role_port_mail.py only builds a MailQuery for declared keys and calls read_mailbox; the unchanged sources/imap_mailbox.py enforces ALLOWED_COMMANDS and readonly=True (EXAMINE/BODY.PEEK). ValueError maps to ChannelUnavailable with `from None` so no server text is carried. Held.
  - No foreign row or secret on disk or in the report: rows_from takes JSON only, 200 rows max, ProbeReply serialises status only; OracleContext.declarations is exclude=True with hide_input_in_errors; test_w3_no_foreign_row_or_secret_reaches_disk scans the whole tree for the planted foreign name, the mailbox password and the role password. Held.
  - Escalation always reverted: the `_assign` exception path runs `_revert`, `budget.extra()` and `_record_revert`; `assign` raises AssignUnproven if the outcome is not shown rather than guessing; an unreadable look is listed unprobed (transport_error), not clean. Held for Exception (see the low issue on BaseException).
- Falsification, one per criterion, isolated copy per mutant under D:/autoTesting/.work/tmp/ow-b-mut (tool qa/evidence/g11-oracle-wiring-b/mutate_b_c1.py, outputs in mutants/); each is green before and red after on the named assertion, not an import error:
  - W1 (MP8/MP14): the payment oracle ignores the context declaration -> RED test_w1_the_payment_oracle_takes_its_paths_from_the_context_and_reads_no_file (PaymentNotDeclaredError).
  - W2 (MP16/MP17): mailbox read errors swallowed into a clean Observation -> RED test_w2_an_unreadable_mailbox_is_never_read_as_absence_or_as_a_clean_run (passed != failed).
  - W3 (MP18-MP20), four mutants: per-hop `allowed(url)` removed -> RED test_w3_a_url_off_the_platform_is_never_requested (DID NOT RAISE PlatformScopeError); `approval.max_probes` dropped from the cap -> RED test_mp20_the_run_stops_at_the_signed_max_probes (3 == 1); the 3-reserve guard removed -> RED test_w3_every_request_the_run_made_is_counted_including_the_role_assign_page_loads ((5+3) <= 7).
  - W4 (MP19/MPI4): the revert click replaced with `pass` -> RED test_w4_an_accepted_assign_is_a_p0_finding_and_is_reverted_in_the_same_run (finding says NOT reverted).
  - W5 (MP27/MP28): findings not passed to the report renderer -> RED test_w5_a_recorded_p0_leak_opens_the_report_with_the_banner_and_its_repro (no release-blocker banner).

## Criteria
W1 met · W2 met · W3 met (gate, ceiling, scope, signed bound all hold) · W4 met · W5 met · MPI4 held · MPI5 held.

PROPOSED-ISSUE: {"sev":"low","title":"tests/imap_fake.py verbs() collapses UID subcommands, so the port-level MP16 test cannot see UID STORE","detail":"verbs() returns only the first word of each command; a regression to UID STORE would pass at the port level (the unchanged imap_mailbox ALLOWED_COMMANDS test still covers the source)","fix":"record the full verb (UID FETCH vs UID STORE) in the fake and assert on it"}
PROPOSED-ISSUE: {"sev":"low","title":"Redirect hops in role_probe.http_get are wire requests not counted by Budget","detail":"each followed same-platform hop (max 5) is a request the cap does not see; bounded by MAX_HOPS and platform-only, so the ceiling is exceeded by at most 5 per read in theory","fix":"count hops via budget.extra() or document the bound in the cap docstring"}
PROPOSED-ISSUE: {"sev":"low","title":"Raise-path RevertRecord can say reverted:false when the exception came before any press","detail":"an operator reading reverts.jsonl may think a role was left escalated when nothing was pressed","fix":"add a pressed flag to the record"}
PROPOSED-ISSUE: {"sev":"low","title":"http_get redirect check has no scheme filter for same-host non-http schemes","detail":"a same-host ftp:// Location passes the host test; the client cannot fetch it, so no request leaves, but the guard is by host only","fix":"require http or https in the hop test"}
PROPOSED-ISSUE: {"sev":"low","title":"_assign undo is skipped on BaseException (KeyboardInterrupt, cancellation)","detail":"the revert runs for Exception only, so an interrupted run could leave an escalated role","fix":"use try/finally for the revert"}

```
VERDICT: PASS
SCOREBOARD: 5/5 criteria met (W1..W5), 2/2 invariants hold (MPI4, MPI5)
TIER: L (tenancy and role-assign press; dual-trigger lines role_port_authz.py assign/revert and authz_probe.py gate confirmed in changed code)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no new UI; 7 changed-criterion falsifications reproduced)
LIVE-BROWSER: not-applicable (fixture-app Chromium tests only; no live leg in this unit by owner decision 2026-10-18)
ISSUES-WRITTEN: none (dual check: 5 low PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every criterion has a test that goes red when its line is mutated; the approval gate, probe ceiling, signed max_probes bound, platform-only redirects, read-only mailbox and always-reverted escalation all hold on a line-by-line read; the 26 reds in the importer set are identical on the base commit.
Metrics: start=2026-10-19T01:28:17Z end=2026-10-19T01:41:00Z wall_min=13 agent_min=unavailable blocked_min=0 suite_runs=2 repeat_runs=0 mutations=7 cycle=1 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=7 defects_unit=0 defects_6c=0
```
