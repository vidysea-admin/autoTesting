# PLAN gate — remaining work: acceptance trio (T-136, T-169, T-206) + Group 11 multi-role (T-207..T-220) + open-issue lane

**Asked:** 2026-10-17 · **Owner:** Umesh · **Status:** OPEN, no Answered line yet.
**Artifacts:** `docs/features/multi-role-platform/intent.md` (O16-O21, design per unit), `qa/manifests/g11-decision-draft.md`
(D-NEXT, `Approved-by: PENDING`), contract proposals MP1-MP33 in `qa/feedback-inbox.md`, D-089/D-090/D-094 (T-136 without a human list).
**Method:** spec-driven pipeline from the brain (spec → review → technical design plan → review → tasks → build → validate against the
spec's acceptance criteria; `concepts/claude-code-campusx/spec-driven-development.md`, `concepts/ai/ai-native-sdlc-intent-md.md`).
Humans gate at intent, spec, plan and release, never mid-build. Units in between are judged by `/checker`.

**Repo state this plan starts from:** master = origin/master `fcedc9f4` (2026-10-16). 106 goal tasks: 89 done, 17 pending.
417 open issues: 12 high, 103 medium, 301 low, 2 security-tagged.

---

## Part A — Acceptance trio (no new decision needed; buildable now)

These units produce evidence, not product code. Every dependency is done: T-133, T-145, T-168, T-197..T-201, T-203, T-204, T-205.
They share the **browser lane (max 1)**, so they run in this order while the code lanes build Group 11.

| # | Unit | What runs | Done when (goal `done_check`) | Known risk |
|---|---|---|---|---|
| A1 | **T-136** Pathlynks comparison | AutoTester column from the T-145 live report, plus a comparison artifact. Recall against Karunn's 8 Oct Release Review, labelled "AI-assisted video review, not independent" (D-094). FP rate and time measured (bench K10). Recall against an independent human is `unavailable until the human list arrives` (D-090). | `uv run python scripts/check_acceptance_comparison.py pathlynks` exits 0 | AT-653 (high): an ordering problem can make recall unmeasurable. The artifact must record list provenance and commit time before scoring. |
| A2 | **T-169** two-mode generic acceptance | Mode (a): rich teaching inputs. Mode (b): URL plus credentials only, no CLI. Both run on the real target; compare bugs, FP, branch coverage and time. | `uv run pytest tests/test_generic_acceptance.py` passes, plus the live-run evidence in its verdict | AT-281 (high): no human-approved acceptance threshold. D-089 lets it pass as a "mechanically complete artifact, judged by Umesh". |
| A3 | **T-206** G10 end-to-end | Redacted videos, then review pointers, then the bug loop, then a schedule tick, then a Test press, then reports on the website and by email, then persona walks (dev, admin) in a live browser. Runs on the **local Windows host** (D-090). | `qa/verdicts/t-206-g10-acceptance.md` exists with a checker PASS | The Ubuntu-hosted check stays deferred: `qa/gates/t203-host-and-dns.md` is still OPEN. T-206 closes with that part named "not run". |

## Part B — Group 11 technical design plan

### B1. Objective
AutoTester tests **N role accounts across M linked platforms in one run**, and catches the CEO's detection techniques that a
single-account run cannot: multi-role comparison, inbox checks, handoff chains, cross-tenant and privilege probes, and the rest.
It reports data leaks as P0, release-blocking, at the top of the report (intent O16-O21).

### B2. Architecture choice (agentic standard check)
- **No new agent and no new framework.** Per `patterns/agentic-architecture-standard.md` rule 1 (simplest layer that fits) and rule 3
  (deterministic guards before LLM calls), G11 is **workflow code**:
  - stages are pure `run(input, ctx) -> output`;
  - every oracle is deterministic;
  - leak and privilege findings never reach a model.
- The only model in the loop is the existing independent judge, and it sees finding records only.
- The existing LangGraph lead tester (T-179/T-180, D-041/D-042) can call G11 stages as tools later. G11 does not depend on it.
- **The four layers:**
  - Graph: the existing `stages/orchestrate.py`, plus the new `cross_role_runner` (order, polling, bounds).
  - Agents: none new.
  - Skills: none.
  - Tools: Playwright contexts, read-only IMAP, `network_capture`.
- Typed Pydantic schemas carry data between every step (`extra="forbid"`).

### B3. Data model (all new files in `schema/`, one model per file)
- `multi_role_enums.py`: every G11 enum up front (LinkKind, AccountOrigin, Priority, FindingClass, AssertChannel, Expectation,
  OracleName). T-207 is its only editor. `enums.py` is at its 300-line cap.
- `platform.py`, `platform_link.py`: N platforms and the redirect, SSO, shared-account and handoff links between them.
  An old single-URL `project.json` loads as one implicit platform.
- `role_account.py`, `mailbox_ref.py`: role (free text), platform, SecretRef **keys only**, tenant label, mailbox key, origin.
- `cross_role_scenario.py`, `role_step.py`, `cross_role_assertion.py`: steps tagged by role; observer role; channel
  `ui | mailbox | api`; `present | absent` within T.
- `multi_role_finding.py`, `leak_evidence.py`: P0/P1/P2, repro steps. Leak evidence holds a count, field names, at most 5
  HMAC-hashed ids, a masked screenshot and a URL template.
- Oracle schemas, one per oracle that needs one: `mail_observation`, `state_probe`, `request_budget`, `entity_reading`, `answer_key`, `lint_rule`.
- `project.py` (edited): optional `platforms` and `platform_links` fields.

### B4. Functional flow
```
onboard (N role accounts × M platforms, keys only, scope-checked)
  → multi_role_session: one isolated browser context + profile per role account; follow declared platform links
  → cross_role_runner: role-tagged steps in order → poll each assertion (ui / mailbox / api) until within_s
  → oracle_registry: runs every registered oracle by name; unbuilt ⇒ "not built", skipped ⇒ "not run" (never 0)
  → finding_priority: leak/privilege ⇒ P0, no model, no override → leak_evidence: hash + mask BEFORE any write
  → unified report: report_banner first when any P0 leak/privilege exists → bench/acceptance_comparison scoring
```

### B5. Safety (applies to every unit; it comes from the intent and is not re-decided here)
- No third-party personal data reaches disk, a log or a prompt.
- Probes are bounded and covered by a signed `RunApproval`, reusing the T-154 ceiling and `refusals.jsonl`.
- The IMAP mailbox is read-only (`EXAMINE` + `BODY.PEEK`).
- A successful escalation is reverted in the same run.
- No real-money payment is completed.
- Writes follow ALLOW_WRITES (D-018, D-053).
- A sibling-platform credential uses `include_subdomains=False`, because `_host_matches` is a suffix match.

### B6. Units and waves (code lanes max 4, browser lane max 1, per `qa/adapter.json`)
| Wave | Units (parallel inside a wave) | Owns (no two parallel units share a file) | Needs first |
|---|---|---|---|
| W0 | Gate work: append D-NEXT; `/checker` folds MP1-MP33 into `qa/contracts/multi-role-platform.md` plus the IMAP amendment to `source-adapters.md`; O16-O21 into `docs/intent.md`; G11 requirements into `docs/spec.md`; G11 units into `docs/plan.md` | docs and contracts only | **this gate + Approved-by** |
| W1 | **T-207** schema foundation | `schema/multi_role_enums.py`, platform, link, role account and mailbox ref, `project.py` | W0 |
| W2 | **T-208** onboarding form · **T-209** priority, leak evidence and report banner · **T-210** multi-role session runner | T-208: `ui/routes_role_accounts.py`, `ui/role_accounts_view.py`, `stages/role_onboarding.py`, `ui/routers.py`. T-209: `stages/finding_priority.py`, `leak_evidence.py`, `report_banner.py`, `unified_report_render.py`. T-210: `stages/multi_role_session.py`, `platform_links.py` | T-207 |
| W3 | **T-211** cross-role runner + oracle registry | `stages/cross_role_runner.py`, `oracle_registry.py`, `schema/oracle_context.py` and the scenario schemas | T-210 |
| W4a | **T-213** tenant + privilege · **T-214** API error + request budget · **T-215** consistency + answer key · **T-219** negative input per role | one `stages/oracle_*.py` (+ schema) each | T-211 (T-213 also reuses T-154) |
| W4b | **T-212** mailbox (IMAP) · **T-216** copy lint + responsive · **T-217** credential policy + payment · **T-220** state after action | one `stages/oracle_*.py` (+ schema) each; T-212 adds `sources/imap_mailbox.py` | T-211; **T-212 needs the IMAP answer below**; T-217 needs T-212 |
| W5 | **T-218** CEO benchmark acceptance (browser lane, live) | `stages/ceo_benchmark.py` | all of W1-W4, 8 role accounts in `.env`, the atomic CEO list with its hash pinned **before** the run |

**Test discipline:**
- TDD per unit: write the failing test first.
- Fixtures are synthetic and blind. No fixture or scenario may be written from a specific CEO finding (contamination rule).
- Every unit runs `uv run pytest`, `uv run ruff check src tests scripts` and `uv run autotester doctor`.
- `/checker` judges each unit against MP1-MP33. Dual check applies to security-class units (T-209, T-212, T-213).

### B7. Validation (spec acceptance → T-218 scorecard)
- Recall is reported overall, per priority (P0 first) and **per CEO technique**, each line naming its owning unit.
- FP rate is computed over adjudicated findings only. Unmatched findings count as "unadjudicated", neither true nor false positives.
- AutoTester wall time is reported. The CEO's time stays `unknown` until Umesh gives his active hours.
- Matching uses the existing `acceptance_comparison`/`bench` scorer. There is no second scorer.

## Part C — Open-issue lane ("fix it all")
Issues are fixed in severity order on whichever code lane is free between G11 waves. Each fix runs through `/maker` and `/checker`.

1. **First, 12 high + 2 security:**
   - process and ledger integrity: AT-656, AT-668, AT-710, AT-711, AT-712, AT-718, AT-740;
   - measurement, which also unblocks Part A: AT-653, AT-281, AT-654, AT-663;
   - machine: AT-672;
   - security: ISS-d063-grant-budget-1 and -3.
2. **Then 103 medium**, grouped by type: correctness, silent-failure, security-hardening, robustness and test-gap first.
3. **Then 301 low**, batched per feature file so one unit closes several issues.

All 417 cannot be closed in one wave. Progress is measured as issues verified per checker PASS, not as commits.

---

## What Umesh must provide or answer

**Answers (write one `Answered:` line each):**
1. **Approve this plan and the G11 decision draft.** Give your own words for `Approved-by` in `qa/manifests/g11-decision-draft.md`.
2. **IMAP:** the mailbox host, plus per-role mailbox keys in the repo-root `.env`. Also say how to handle accounts created inside a run.
   T-212 and T-217 wait on this; the rest of G11 does not.
3. **CEO list:** the 69 findings as a private file under `.work/`. Confirm the atomic split, then its sha256 is pinned before the G11 run.

**Inputs (not decisions):**
- 8 Pathlynks role test accounts as `PATHLYNKS_*` keys in the repo-root `.env`: school admin, coordinator, 2 counsellors, Grade 8,
  Grade 10, parent, retail self-signup. These are test accounts, never a live user's.
- The CEO's active hours, for the time comparison. Optional; time stays `unknown` without them.
- Later, not blocking: the Ubuntu host and DNS (T-203 gate), and the independent human list (T-136 recall).

## Assumptions I made (reply only to change them)
- Part A and the Part C high-severity issues start immediately. They are covered by D-081/D-089/D-090/D-094 and need no new gate.
- G11 W1 starts only after answer 1. Waves W1-W4 do not wait on answers 2 and 3, except T-212 and T-217.
- The maker loop runs on this machine. The remote session has been silent since 2026-10-16 16:06 UTC.

Answered: 2026-10-17T09:24Z — Part A (T-136, T-169, T-206) and Part C (high + security issues first, then medium, then low) APPROVED: Umesh in chat "hn ho go for it" + "tu khud krr and use maximum possible subagents" (session e46c0e51). Part B (G11, T-207..T-220) NOT approved: still needs Umesh's own Approved-by words on qa/manifests/g11-decision-draft.md.
