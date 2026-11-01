# Pathlynks (pathlynks)

**Purpose:** what this system has learned about the Pathlynks product from real,
credentialed exploration — screens reached, auth boundaries, gotchas.
**Open me when:** onboarding a new flow, deciding what a video request should show,
or checking whether a screen was already seen.

## Quick Re-Run
```bash
uv run python scripts/onboard_pathlynks.py --role user
```

**Last successful run:** 2026-10-28 | role=user | run=run-01M617NCNB8RBBME2RSH9ZQ87P (login case `case_cfa40e6b95c2` completed in 13.1 s; judge verdict INCONCLUSIVE only because a screenshot was masked, criteria 1/1 met) | earlier: 2026-09-03 onboard-01M1JQDHA8296D4EQ484CPKP1Z
**Output file(s):** projects/pathlynks/runs/run-01M617NCNB8RBBME2RSH9ZQ87P/ ; reference pass: .work/pathlynks-explore/ (pass2-summary.md, findings.md, comparison.md, screens/) ; shared copy: D:/ai_os/references/portals/pathlynks.knowledge.md

## Portal Profile
| Field | Value |
|-------|-------|
| URL | (see project.json base_url; redacted here where it overlaps a declared secret) |
| Type | saas |
| Intent explored | audit (onboarding) |
| AI involvement | Tier 2 -- agent + knowledge, deterministic once mapped |
| Browser tool used | Playwright via autotester.browser.session.BrowserSession |
| Auth | email + password, two roles exist (counsellor, user); only `user` (student, Premium, Grade 12) explored. Login reached `/dashboard` on 2026-10-28 after the password fix. |
| Write policy | read_only (no writes performed) |

## How it works
Sign-in form at the project's base_url takes an `identifier` (email) field and a
`password` field, submitted via a "Login" button. No 2FA/OTP was presented for
this dev-environment account on this run.

## Screens reached
Student (`user`) role, 2026-10-28, hand pass (Playwright, read-only, no clicks in pass 2): 16/16 sidebar routes load 200 with 0 API errors >= 400 (`.work/pathlynks-explore/pass2-summary.md`).

| Route | Notes |
|---|---|
| /signin | login form: `identifier`, `password`, Login |
| /dashboard | post-login landing; Build your profile, assessments (0 pending), Request a counsellor, journey map, consent details, Quest Guide |
| /career-quest/know-yourself | 4 assessment reports done (Aptitude, Personality, Motivators & Values, Interest) |
| /career-quest/career-selection | Top 3 picks, fit bands, search; load-timing sensitive (pass 1 saw 0 controls) |
| /career-quest/profile-building | Add activity, plan durations, Make my plan |
| /career-quest/university-selection | gated: "Career needed first" |
| /my-report, /my-matches, /favorite, /profile | report viewers; `/profile` has View Combined Report |
| /career-repository, /career-compare | search, 3 tabs, 20 category pickers |
| /help-faq, /messages (empty), /my-academics | FAQ search + Quest Guide chat; upload/enter marks |
| /settings, /resource-library | the only real forms (2 and 1) |
| /career-quest | hub (screenshot only) |

Not yet mapped: dialog/detail depth beyond the p3/p4 shots, and the whole counsellor role (needs a visible-browser login by Umesh).

## Findings (audit, 2026-10-28)
- P1 (Medium, UX): combined report page shows "PDF not available" because `GET /api/assessment-management/get-this-combined-report` returns 403; header says "Parent consent needed" but the page never gives consent as the reason.
- P2 (Low): university list is loaded at runtime from jsDelivr serving GitHub `Hipo/university-domains-list@master` (unpinned, third party).
- P3 (Info): 16/16 routes 200; settings and resource-library are the only real forms.
Source: `.work/pathlynks-explore/findings.md`.

## AutoTester crawl state (PARTIAL)
`crawl_01M618QPC6B4YKB2XG609TSQP1` (hybrid, production, test_account) was killed for low memory after 649 s: 21 screen records = 13 unique routes, 65 actions, 75 edges, 9 denied, 11 issues, max depth 2; marked `aborted` by hand. Missed `/my-matches`, `/profile`, `/my-academics`, `/career-quest`. Full table and named causes: `.work/pathlynks-explore/comparison.md`. Crawl record says `provider: mock`; that is the schema default, the crawl uses no model.

## Gotchas & edge cases
- Two account roles exist for this product (counsellor and user/student); this
  run exercised the `user` role only. The other role's login page differs
  (see `.env.example` for both `*_LOGIN_URL` shapes) -- a separate run should
  cover it before this knowledge file is considered complete.
- Login URLs stored in `.env` are NOT declared as project secrets, so they are
  masked by the redactor as undeclared values (AT-004 behaviour) -- this is a
  known false-positive redaction of non-sensitive URLs, not a security issue;
  use `project.json::base_url` for the canonical, unmasked entry point instead.

## Change detection
- Sidebar links `Know Yourself`, `Career Selection`, `Career Matches`, `My Profile` can report as covered by an in-page overlay on `/dashboard` and `/messages` (crawl `overlay` issues); `Collapse sidebar` creates a new screen signature for the same URL, inflating screen counts (8 of 21 records were duplicates).
- Re-run and diff the screenshot set; a materially different login form or a
  redirect to an unexpected host means this file needs a fresh pass.

## History
| Date | Intent | Findings | Duration | Tool | Notes |
|---|---|---|---|---|---|
| 2026-09-03 | audit | login form mapped, 3 screenshots | -- | BrowserSession | T-030 first pass |
| 2026-10-28 | audit | run-01M617NCNB8RBBME2RSH9ZQ87P: login (`case_cfa40e6b95c2`) reached /dashboard after the password fix, 13.1 s | 13 s | BrowserSession | verdict INCONCLUSIVE (masked screenshot), criteria 1/1 |
| 2026-10-28 | audit | reference pass 1-4, student role: 16/16 routes 200, 3 findings (P1 P2 P3) | -- | Playwright MCP | .work/pathlynks-explore/ |
| 2026-10-28 | audit | crawl_01M618QPC6B4YKB2XG609TSQP1: 21 screens/13 routes, killed low memory, aborted by hand | 10m49s | autotester explore (hybrid) | PARTIAL; see comparison.md |
