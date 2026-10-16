# Intent — Multi-role, multi-platform testing (group 11, T-207..T-218)

**Purpose:** the feature-level intent and design for Group 11: why AutoTester must test N role accounts across M linked platforms, its outcomes O16-O21, the user types, Umesh's 2026-10-16 answers, the leak-evidence safety policy, the CEO-benchmark scoring rule, and the schema/stage file per piece.
**Open me when:** you are building or checking any of T-207..T-218, a criterion cites `serves: intent#O16`..`O21`, or you need to know which file owns a Platform, RoleAccount, cross-role scenario or oracle.

**Originator:** Umesh (chat 2026-10-16, answers below) · **Date:** 2026-10-16 · **Status:** draft, awaiting Umesh's approval of the decision draft (`qa/manifests/g11-decision-draft.md`) and a G11 plan gate. Nothing here is built.

## Problem
The north star is now the CEO's own end-to-end manual test of PathLynks, done live on 14-16 Oct. It
used 8 product roles (school admin, coordinator, two counsellors, a Grade 8 and a Grade 10 student, a
parent, and a retail self-signup student) and read every role's own inbox. It produced **69 findings:
21 P0, 38 P1, 10 P2.** By detection technique (a finding can use several): copy/branding/i18n lint 16,
multi-role comparison 16, inbox check 11, state consistency after an action 11, cross-role consistency
10, negative input 8, handoff chain 8, notification absence 7, cross-tenant authorization probe 4, API
error capture 3, answer-key scoring 3, responsive layout 2, payment flow 2, request count 1.

AutoTester today drives **one account on one platform through one flow at a time.** Most of those
techniques need two or more accounts at once (A does, B sees), a mailbox, or a second platform reached
by a redirect. A single-account run cannot find them, and an incomplete report that reads clean is the
failure this project refuses (O4).

## Umesh's answers (2026-10-16, recorded in substance)
1. **The CEO findings are the benchmark and the depth reference.** They span 2-3 linked platforms
   (the PathLynks app, the vidysea.com marketplace and the session subdomain), not one app. Their depth
   is the reference for how validation must be done.
2. **Test any platform whose URL and user credentials are provided.** Plan for N platforms with
   credentials and for how they link: redirects, SSO and shared accounts, cross-platform handoffs.
3. **Data leaks are detected and HIGHLIGHTED prominently, the way the CEO did:** P0, release-blocking,
   at the top of the report.
4. **The person using AutoTester provides the role accounts when they start a NEW PROJECT.** Onboarding
   accepts N role accounts across M platforms.

## Proposed outcome
Numbered to continue `docs/intent.md` (O1-O15 there). Adding them to the root file is a follow-up the
decision draft authorizes; until then this file is their only home.

- **O16** Given N platforms (URL, allowed domains) and the links between them, AutoTester follows each
  declared redirect, SSO hop, shared account and handoff, and reports each one as followed, failed or
  not reached. A hop that lands outside every declared platform is a finding, never a silent follow.
- **O17** A new project accepts N role accounts across M platforms at onboarding. Each has a role, a
  platform, credential keys (never values), a tenant label and an optional mailbox key. A credential
  whose domain scope is wider than its own platform is refused with the reason.
- **O18** A cross-role scenario tags each step with the role that performs it and asserts what another
  role sees or receives within a time bound T: on screen, in its mailbox, or in an API response. The
  absence of an expected message by T is evidence, as it was for the CEO.
- **O19** Data leaks and privilege escalation are found by bounded probes and HIGHLIGHTED: always P0,
  release-blocking, in a banner at the top of the report, with reproducible steps. Evidence is counts,
  hashed ids and masked screenshots, never third-party personal data.
- **O20** Each depth oracle (mailbox, hidden API error, request budget, cross-role consistency,
  answer key, copy/branding/timezone lint, responsive sweep, credential policy, payment-flow presence)
  produces findings with evidence and an honest label (O3). An oracle that did not run says so by name.
- **O21** AutoTester is scored against the CEO benchmark on recall, false positives and time against an
  atomic finding list, with ordering and independence handled as the T-136 gate requires (O6).

## Affected users and systems

### User types (AutoTester users; drafted from Umesh's answers, not each field confirmed)
| id | who | goal | blocks on | patience | mental model | confirmed |
|---|---|---|---|---|---|---|
| `onboarder` | whoever starts a new project (tester, lead or dev) | hand over N platforms and their role accounts once and have every role tested | a form that takes one login only; a key refused with no reason | 3 | a test-account sheet: role, URL, user, password, inbox | answer 4, 2026-10-16; fields drafted |
| `lead` | Umesh / product lead | see at the top whether the build leaks data or lets a role escalate; decide ship / no-ship | a leak buried on page 4, or a clean report from a run that never probed | 1 | the CEO's own findings sheet: P0 first | answer 3, 2026-10-16 |
| `dev` | the developer who must fix a P0 | reproduce the leak from the steps without seeing anyone's data | steps that say "a leak" with no role, URL, or count | 2 | CI output, request logs | `dev` confirmed 2026-09-27 |
| `benchmark-owner` | Umesh as the author of the CEO list | see recall, FP and time against his own list | a recall number with no provenance for list ordering | 2 | his findings list, P0/P1/P2 | answer 1, 2026-10-16 |

**Product roles are not AutoTester users.** "school admin", "counsellor", "parent" and the rest are
`RoleAccount.role` values the onboarder types. Nothing in the code names a PathLynks role.

### Systems
Playwright contexts (one per role account), `browser/session.py`, `stages/parallel_run.py` isolated
contexts, `stages/network_capture.py`, the permission surface (`schema/crawl.py::PermittedControl`,
T-171), `expand` with its `CaseClass` taxonomy, `grade`, `stages/acceptance_comparison.py` and
`stages/bench.py`, `sources/email.py` (parse only today), the unified report (T-168), the repo-root
`.env`, and a role's mailbox reached over IMAP (new, read-only).

## Safety (non-negotiable for every G11 unit)
- **Leak evidence never stores third-party personal data.** A leak is recorded as: a count of foreign
  rows, the field names seen (column headers, not values), up to 5 ids hashed with HMAC-SHA256 under a
  per-project key from the repo-root `.env`, a screenshot masked before it is written (every data cell
  blurred, headers and the count kept), and the URL template with ids replaced by placeholders. Names,
  emails, phone numbers, marks and timestamps of another tenant's children are never written to disk,
  to a log, or to a prompt.
- **Leaked content never goes to a model.** Leak and privilege oracles are deterministic. A page an
  oracle flagged is excluded from the judge's evidence and from UX passes; the judge sees the finding
  record only.
- **The leak is still HIGHLIGHTED as P0 with reproducible steps:** the role, platform, URL template,
  the action sequence and the count. Masking the data never softens the finding.
- **Probes are bounded.** Per run: at most 3 id-swap reads per endpoint, 1 list page per list view, one
  escalation attempt per role-assign control, a request-rate cap per platform, and a wall-clock budget
  inside the `RunApproval` bounds. A bound that stops a probe names what it left unprobed (O4).
- **Writes follow `ALLOW_WRITES` (D-018, D-053), as far as the account permits.** Creating counsellors,
  scheduling tests, sending messages and assigning roles are in scope where the supplied account may do
  them. This is not re-litigated here. Two fixed lines: a real-money charge is never completed (the
  payment oracle stops at the gateway's own page unless the provider is in its test mode); and an
  escalation probe that succeeds is reverted in the same run, with the revert recorded.
- **Credentials:** keys only, in the one repo-root `.env`, namespaced per project. Because
  `browser/secrets.py::_host_matches` is a suffix match, a role account on one subdomain declares
  `include_subdomains=False` when its sibling platforms share the parent domain, so a counsellor's
  password for one platform is never typed into another.
- **Mailbox access is read-only:** IMAP `EXAMINE` plus `BODY.PEEK`, so no message is marked read,
  moved or deleted. Bodies pass `Redactor.scrub`; a password found in a mail body is recorded as "a
  credential-shaped token was present", never its value.

## Scoring (how the CEO benchmark is scored, T-218)
- **Atomic list.** The 69 findings are split into atomic findings (one defect, one observable each)
  before AutoTester's G11 run. The list stays private under `.work/`; committed artifacts carry only
  counts and the list's sha256. Umesh confirms the split (human gate).
- **Matching.** A finding matches when the defect and the observable agree and the roles overlap;
  matching is one-to-one, done by the existing `acceptance_comparison`/`bench` scorer, never a second
  scorer. Unmatched AutoTester findings are "unadjudicated" until Umesh rules on them; they are not
  counted as false positives, and not as true ones.
- **Ordering and independence (T-136 gate, `qa/gates/t136-independent-human-list.md`).** The CEO list
  was written 14-16 Oct, before any G11 report exists, so recall is computable, provided the list's
  hash and commit time are recorded before the run. **Contamination rule:** oracles may be designed from
  the technique categories above, but no scenario, fixture or prompt may be written from a specific
  finding. Any scenario derived from one is labelled and its matches are excluded from recall.
- **Reported numbers:** recall overall and per priority (P0 first), recall excluding findings that
  need seeded data AutoTester was not given, FP rate over adjudicated findings, and AutoTester wall
  time. The CEO's active hours were not recorded; time stays `unknown` until Umesh gives them.
- **Out of scope for recall:** what the CEO left untested (phone/SMS/WhatsApp, past the payment
  gateway, a meeting join).

## Design: the pieces, their files, and reuse
One model per schema file. Every enum G11 adds goes in `schema/multi_role_enums.py` (`schema/enums.py`
is at its 300-line cap). R = reused, E = edited, N = new.

### Platform and PlatformLink (T-207)
- `schema/platform.py` N: `Platform` (id, name, base_url, allowed_domains, include_subdomains,
  login_case_id). `schema/platform_link.py` N: `PlatformLink` (from_platform, to_platform, kind
  `redirect | sso | shared_account | handoff`, trigger url_template or control name, expected landing
  host, carries_session).
- `schema/project.py` E: optional `platforms: list[Platform]` and `platform_links`; an old project.json
  (one base_url) loads as one implicit platform. Stage: `stages/platform_links.py` N (T-210).

### RoleAccount (T-207, onboarding T-208)
- `schema/role_account.py` N: `RoleAccount` (id, role free text, platform_id, username and password
  SecretRef keys, tenant_label, mailbox_ref, user_persona_ref, provided_by `onboarder | created_in_run`).
- `schema/mailbox_ref.py` N: `MailboxRef` (host, user and password keys; folder; never a value).
- Onboarding: `stages/role_onboarding.py` N (validation), `ui/routes_role_accounts.py` N and
  `ui/role_accounts_view.py` N (the form), `ui/routers.py` E (registration). R: `ui/env_editor.py`,
  `ui/credential_guard.py`, `schema/project.py::SecretRef`.

### Multi-role session runner (T-210) and CrossRoleScenario (T-211)
- `stages/multi_role_session.py` N: one isolated browser context and profile per role account. R:
  `browser/session.py`, `stages/parallel_run.py` isolation, `stages/manual_login.py`.
- `schema/cross_role_scenario.py` N, `schema/role_step.py` N (role account, platform, flow or case
  ref, named handles it produces), `schema/cross_role_assertion.py` N (observer role, channel
  `ui | mailbox | api`, expect `present | absent`, matcher, within_s).
- `stages/cross_role_runner.py` N: runs steps in order, then polls each assertion until within_s.
  `schema/oracle_context.py` N and `stages/oracle_registry.py` N: the registry names every G11 oracle
  module up front and imports it by name, so an unbuilt oracle reports `not built` and the oracle units
  never edit a shared file.

### Oracles (T-212..T-217, parallel)
| oracle | stage file (N) | schema (N) | reuses |
|---|---|---|---|
| mailbox read + absence within T | `sources/imap_mailbox.py`, `stages/oracle_mailbox.py` | `schema/mail_observation.py` | `sources/email.py` parsing, `Redactor` |
| cross-tenant authz probe | `stages/oracle_tenant.py` | `schema/probe_budget.py` | `network_capture`, permission surface |
| vertical privilege, role-assign escalation | `stages/oracle_privilege.py` | (probe_budget) | permission surface, captured higher-role requests |
| API error hidden by the UI | `stages/oracle_api_error.py` | — | `network_capture`, `grade` evidence |
| request rate and polling budget | `stages/oracle_request_budget.py` | `schema/request_budget.py` | `network_capture` |
| cross-role consistency | `stages/oracle_consistency.py` | `schema/entity_reading.py` | cross_role_runner handles |
| answer key and scoring fixtures | `stages/oracle_answer_key.py` | `schema/answer_key.py` | `expand` CaseClass HAPPY/INPUT_BOUNDARY |
| copy, branding, timezone lint | `stages/oracle_copy_lint.py` | `schema/lint_rule.py` | `ux_advisory` evidence reading |
| responsive sweep | `stages/oracle_responsive.py` | — | `CaseClass.VIEWPORT_MOBILE` |
| credential policy | `stages/oracle_credential_policy.py` | — | mailbox oracle, `synthetic_values` |
| payment-flow presence | `stages/oracle_payment.py` | — | permission surface `destructive` flag |

### Severity and the report banner (T-209)
- `schema/multi_role_finding.py` N: `MultiRoleFinding` (oracle, priority P0/P1/P2, class, roles,
  platform, repro steps, evidence refs, leak evidence). `schema/leak_evidence.py` N: `LeakEvidence`
  (count, field_names, hashed_ids, masked_screenshot, url_template).
- `stages/finding_priority.py` N: data-leak and privilege classes are always P0, with no model input
  and no override. `stages/leak_evidence.py` N: HMAC hashing and pre-write masking.
- `stages/unified_report.py` E and `stages/unified_report_render.py` E: a release-blocking banner as the
  first block of the report header when any P0 leak or privilege finding exists, with the count and a
  link to each repro. P0/P1/P2 map onto the existing `Severity` S1-S3 for the bug loop; the banner reads
  the priority, not S1.

### CEO benchmark acceptance (T-218)
- `stages/ceo_benchmark.py` N: maps the private atomic list to a `BenchCorpus` the way
  `stages/known_bugs.py` does. R: `stages/bench.py`, `stages/acceptance_comparison.py`.

## Non-goals
- Phone, SMS and WhatsApp channels; joining a live video meeting.
- Completing a real payment, or any action the supplied account may not take outside an escalation probe.
- Storing, displaying or sending to a model any third-party personal data found by a leak probe.
- Product-specific code: no PathLynks role, URL or label is hard-coded.
- Re-deciding write policy (D-018, D-053) or the T-136 ordering rule.

## Open questions (human gates for Umesh)
- [ ] Approve the decision draft (`qa/manifests/g11-decision-draft.md`) and the G11 plan.
- [ ] IMAP host and per-role mailbox keys; `qa/contracts/source-adapters.md` says no IMAP today and
      needs a checker-folded amendment.
- [ ] Confirm the atomic split of the CEO list and pin its hash before the G11 run.
- [ ] Adjudicate AutoTester-only findings (FP rate); give the CEO's active hours for the time number.
- [ ] Mailboxes for accounts created inside a run (the admin creates counsellors and students).
