# Verdict - g11-multirole-design

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** b8862b3581f2d49a0b53a7c434abdda19ee2320e (base 7409a48678d3568a75a360aa6d2c1a65bff78479; single commit above base, worktree clean)

## Scope
Design-only unit: `docs/features/multi-role-platform/intent.md` (N), `qa/manifests/g11-decision-draft.md` (N),
`qa/manifests/g11-multirole-design.md` (N), `.goal/goal.json` (T-207..T-218), `qa/feedback-inbox.md`
(MP1-MP31), `CLAUDE.md` (one router row), `docs/SNAPSHOT.md` (regenerated). Judged against the
orchestrator brief (Umesh's 2026-10-16 answers), the manifest acceptance list, core-invariants C2/C3/C5/C9/C10/C12,
`qa/gates/write-policy-tier.md` (D-018, D-053) and the private ground truth in `.work/ceo-groundtruth/`.

## Blocking finding (why FAIL)
**F1 - Two CEO detection techniques map to no unit, oracle or criterion.** In `findings.jsonl`,
`state-consistency-after-action` (11 tags) and `data-validation/negative-input` (8 tags) appear only in the
intent's technique counts (intent.md lines 12-15). No row of the oracle table, no O16-O21 outcome, no T-207..T-218
row and no MP criterion owns them, and no reuse of an existing stage (for example `expand` input classes or
`grade` postconditions) is named for them. 13 of the 69 findings (2 P0, 10 P1, 1 P2) carry only these two
techniques, and 18 touch them. Umesh's answer 1 makes the CEO depth the reference, so the design has to map
every technique. Narrow fix: map both, either to a new oracle or to named existing stages run per role
account, with an MP criterion each and a per-technique line in the T-218 scoring.

All other techniques are mapped: multi-role comparison (MP13, MP23), copy/branding/i18n (MP25), inbox (MP16-17),
cross-role consistency (MP23), handoff chain (PlatformLink `handoff`, MP12/MP13), notification absence (MP14),
cross-tenant probe (MP18), API error (MP21), answer key (MP24), responsive (MP26), payment (MP28), request count (MP22).

## Checks that passed
1. **Public-repo safety: PASS.** I grepped the added lines for `@`, 4+ digit and comma numbers, school, board,
   coupon and assessment names, OTP/UPI/GST, stack traces and the known counts. The only `@` is MP2's rule text.
   The only digits are dates and SHAs. No names, emails, phones, student IDs, passwords, school names or
   school-tied counts appear. The committed text carries only aggregate counts (69; 21/38/10; per-technique),
   the role structure and the public platform names.
2. **Fidelity: PASS.** All four answers are recorded. Multi-platform support and PlatformLink
   (redirect/sso/shared_account/handoff) are O16/MP1/MP12. Onboarding of N role accounts on a new project is
   O17/MP4. The P0 banner is O19/MP7/MP8. The leak policy is counts, field names, at most 5 HMAC ids, masked
   screenshots and URL templates, with no third-party PII on disk, in logs or in prompts (MP9 canary sweep),
   and it stays reproducible (MP10). ALLOW_WRITES is cited per D-018/D-053, "not re-litigated", with no
   narrowing below what the account may do.
3. **Goal rows: PASS (with advisory A2).** The JSON parses. Rows go from 92 to 104. The new ids T-207..T-218
   are sequential: the base maximum and the master maximum are both T-206. No base row was changed or
   removed. Every dep resolves and the graph is acyclic. The row shape matches existing rows, and the
   criticality and user_value values are in the existing vocabulary. The done_check slugs follow the
   `check_deliverable.py --exists qa/verdicts/t-NNN-*.md` pattern. The listed file sets in W2 (T-208/T-209)
   and W5 (T-212..T-217) are pairwise disjoint. One model per schema file holds, with enums in
   `schema/multi_role_enums.py` because `schema/enums.py` is at 300 lines (verified). None of the new
   module paths exist yet. All reused modules exist (verified).
4. **Criteria: PASS (with advisory A4).** MP1-MP31 each state an observable pass/fail. Every `serves:` cites
   O16-O21 (defined in the feature intent) or the root O3/O4/O6/O7 (defined in docs/intent.md). None conflicts
   with C5 (keys only, scrub, no leaked content to a model), C12 (MP15 "not built", MP30 "unavailable"), or
   D-018/D-053. The escalation probes fall under the bounded adversarial pass, which D-081 un-held (T-154 is done).
5. **No forbidden edits: PASS.** The diff touches exactly the 7 manifest paths (C10). Nothing changed in
   qa/contracts/, docs/DECISIONS.md, ARCHITECTURE, src, tests or the enforcement paths. The decision draft
   uses the placeholder `D-NEXT` with `Approved-by: PENDING`, and the append script was not run.
6. **Doctor: PASS.** I ran `.venv/Scripts/python -c "...app()" doctor` from the worktree root with
   PYTHONPATH=<worktree>/src. It imported `<worktree>/src/autotester/__init__.py`, exited 0 and printed
   "doctor: clean" in 216 s. Its warnings are the pre-existing D-087 advisories.

## Advisories (non-blocking; fold into the fix cycle)
- **A1:** Two MP verify fixtures echo specific CEO findings: MP25 "UTC time shown to an IST user" and MP27
  "accepts a short password and mails it". This conflicts with the intent's own contamination wording ("no
  ... fixture ... written from a specific finding") and with the manifest's "no observed value" claim. Neither
  contains PII. Use neutral fixtures, or state that local unit-test fixtures are outside the rule.
- **A2:** `schema/multi_role_enums.py` is a hidden shared file. Only T-207 lists it, but T-209 (priority/class),
  T-211 (channel, present/absent) and the W5 oracles will need enums. Either have T-207 create all G11 enums
  up front, or let each unit own its enum file.
- **A3:** `stages/unified_report.py` is 297 lines. T-209's banner edit has to go in the render file or a new file.
- **A4:** MP29-MP31 have no `Verify:` line, although the section header says every Verify names a fixture.
- **A5:** T-213's probes should reuse the existing T-154 bounded adversarial pass (consent, probe cap) and
  must not become a second probe concept (C3).
- **A6:** O16-O21 are not yet in docs/intent.md, so the `serves:` citations resolve only after the decision
  is appended. Master has moved past the base (a CLAUDE.md URL line changed), so a merge is needed.

## Evidence (independent; nothing reused from the maker)
Scratch: `C:/Users/product/AppData/Local/Temp/claude/C--Users-product-Desktop-autoTesting/5aec902b-1207-4886-9e7e-7e118352b899/scratchpad/`
contains doctor.out/doctor.exit (0), goalchk.py/goalchk.out (exit 0), metrics-final.json/assess.out (exit 2).

## Accounting
Mode BOOTSTRAP_REVIEW (maker usage unknown): 180 s / 6,000 tokens, plus the brief's standing escalation of
<=300 s, for a 480 s limit. The checker took about 1,145 s active before finalization, including 216 s of
doctor on the loaded machine. **Breach recorded, not waived:** the helper assess returned NEEDS_EXTRA_REVIEW
(exit 2, exceeded active_s and tokens). Tokens: actual null (the host does not expose them). Cost: null.
Ratio: unverified. The per-phase assess gate was run only at finalization; this is a recorded process miss.
Finalization went past the cap so this FAIL could be persisted. It needs ORCH approval of the finite extra.

## Remaining gates
Fix cycle 1 (F1, plus A1-A4 recommended). Umesh's approval of the decision draft. A checker fold of MP*
into `qa/contracts/multi-role-platform.md` after approval.
