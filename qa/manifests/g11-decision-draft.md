# Decision-entry draft — Group 11 (multi-role, multi-platform testing)

**For:** Umesh to approve. **Not appended.** The maker did not run `scripts/append_decision.ps1`.
**Unit:** g11-multirole-design (`qa/manifests/g11-multirole-design.md`).

How to append once approved:
1. Copy the fenced block below into a scratch file under `.work/` (for example `.work/g11-decision.md`).
2. Replace `D-NEXT` in its first line with the next sequential id (max existing + 1; the script refuses
   anything else). The placeholder is not a number so this draft cites no decision that does not exist.
3. Replace the `Approved-by` placeholder with Umesh's own words and date.
4. Run `powershell -ExecutionPolicy Bypass -File scripts/append_decision.ps1 -EntryFile .work/g11-decision.md`.

No enforcement path is named in `Changes-authorized`, so the script's F1 rule does not apply; the
`Approved-by` line is still required by project practice for a new group.

```markdown
## D-NEXT | 2026-10-16 | type: decision | status: ACTIVE

**What:** Open Group 11, multi-role and multi-platform testing (T-207..T-220), designed in `docs/features/multi-role-platform/intent.md` (outcomes O16-O21). (1) A project may declare N platforms (url, allowed_domains) and the PlatformLinks between them (redirect, SSO, shared account, handoff); an old single-URL project loads as one implicit platform. (2) The person starting a NEW project supplies N role accounts across M platforms at onboarding: role, platform, SecretRef keys, tenant label, optional mailbox key; values stay in the one repo-root `.env`. (3) A multi-role session runner drives one isolated browser context per role account; a CrossRoleScenario tags each step with its role and asserts what another role sees or receives within T, on screen, by mail or by API, including absence. (4) Depth oracles: read-only IMAP mailbox, cross-tenant authorization probe, vertical privilege and role-assign escalation, API error hidden by the UI, request-rate and polling budget, cross-role consistency, answer-key scoring, copy/branding/timezone lint, responsive sweep, credential policy, payment-flow presence, negative input per role (reusing expand's input classes) and state consistency after an action (reusing ExpectedState), so every CEO detection technique has an owning unit. (5) Data-leak and privilege findings are always P0, release-blocking, in a banner at the top of the report. (6) The CEO's 14-16 Oct PathLynks test is the benchmark and depth reference, scored for recall, FP and time against an atomic finding list under the T-136 ordering rule.

**Why:** Umesh, 2026-10-16: the CEO findings (69: 21 P0, 38 P1, 10 P2, across 8 roles and 2-3 linked platforms, every role's inbox read) are the benchmark and the depth reference; test any platform whose URL and credentials are provided, planning for N platforms and how they link; detect data leaks and HIGHLIGHT them prominently as the CEO did, P0 and release-blocking at the top; the user provides the role accounts when starting a new project. AutoTester today is single-account and single-flow, so most of those techniques (multi-role comparison, inbox checks, handoff chains, cross-tenant probes) are out of its reach and its report would read clean where the CEO's reads 21 P0 (intent O4).

**Leak-evidence policy:** a leak is recorded as a count of foreign rows, the field names seen, at most 5 ids hashed with HMAC-SHA256 under a per-project key from the repo-root `.env`, a screenshot masked before it is written, and a URL template with ids replaced. No name, email, phone, mark or timestamp of a third party (in particular another school's children) is written to disk, a log or a prompt, and leaked pages never go to a model: leak and privilege oracles are deterministic. The finding is still highlighted as P0 with reproducible steps (role, platform, URL template, actions, count). Probes are bounded (3 id-swap reads per endpoint, 1 list page per view, one escalation attempt per role-assign control, a per-platform request cap, inside RunApproval bounds); a successful escalation is reverted in the same run. Writes follow ALLOW_WRITES per D-018 and D-053 as far as the account permits; not re-litigated. No real-money charge is completed. The mailbox is read-only (EXAMINE, BODY.PEEK).

**Result:** fourteen pending goal rows T-207..T-220 (foundation schema; onboarding; severity and banner; session runner; cross-role runner; eight oracle units in parallel; CEO-benchmark acceptance). Probes reuse the T-154 bounded-pass mechanism (RunApproval probe count, code-side ceiling, refusals.jsonl); there is no second probe concept. Contract criteria MP1-MP33 proposed verbatim in `qa/feedback-inbox.md` for /checker to fold into a new `qa/contracts/multi-role-platform.md`. No code is changed by this entry.

**Changes-authorized:** docs/ARCHITECTURE.md prose sections "Concept → file (one concept, one place)" (Platform, RoleAccount, cross-role runner, oracle registry rows), "Data model (the core five)" (Platform and RoleAccount beside Project), "Execution model" (one context per role account, cross-role assertions within T) and "Security (non-negotiable)" (leak-evidence policy, read-only mailbox, per-platform SecretRef scope); docs/intent.md (add O16-O21 and the `onboarder` and `benchmark-owner` user types); docs/spec.md (G11 requirements citing O16-O21); docs/plan.md (G11 units); new qa/contracts/multi-role-platform.md and a read-only IMAP amendment to qa/contracts/source-adapters.md (both checker-owned); new modules named per unit in the intent's design section, plus edits to schema/project.py, ui/routers.py, stages/unified_report_render.py (stages/unified_report.py is not edited). No enforcement path, write-policy, verification policy or credential value changes.

**Approved-by:** PENDING — Umesh's words and date go here.

**Links:** T-207; T-208; T-209; T-210; T-211; T-212; T-213; T-214; T-215; T-216; T-217; T-218; T-219; T-220; T-154; T-136; T-171; T-170; T-168; D-018; D-053; docs/features/multi-role-platform/intent.md; qa/manifests/g11-multirole-design.md; qa/gates/t136-independent-human-list.md
```
