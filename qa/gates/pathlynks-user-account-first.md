# HUMAN_GATE — which credentials AutoTester runs against first


> **CITATION CORRECTED 2026-09-28 (AT-718).** This file cited `D-056` as the entry
> authorizing Pathlynks `allow_writes`. No such entry existed. `D-056` has since been
> appended for an unrelated subject (the at673 round-cap waiver), so the old citation
> now RESOLVES TO THE WRONG ENTRY. The write-policy entry is to be written under the next free D-number (NOT D-057, which was spent on another subject — AT-740, D-058)
> by the maker, per `qa/gates/write-policy-tier.md`. Until it exists this citation is a
> forward reference, and is marked as one rather than left looking satisfied.

**Opened + ANSWERED:** 2026-09-27. **Decider:** Umesh. **Status:** ANSWERED — recorded here, not
re-asked.

## The answer, verbatim

> "sabse phle pathlynks user account use krro, vo working credentials hai"

**First target is the Pathlynks USER account, not the counsellor account.** The keys already on
disk in the repo-root `.env` (names only, never values):

| Key | Role |
|---|---|
| `PATHLYNKS_USER_LOGIN_URL` | entry point — already in `core/env.py::PUBLIC_ENV_KEYS` (AT-086), so it may appear in logs/prompts as a value |
| `PATHLYNKS_USER_EMAIL` | `SecretRef` key, value never leaves `page.fill()` |
| `PATHLYNKS_USER_PASSWORD` | `SecretRef` key, value never leaves `page.fill()` |

`PATHLYNKS_COUNSELLOR_*` stays on disk and unused until a later unit names it. They are a second
user type, not a fallback for this one.

## What this settles

- **T-122** (login bootstrap case) is built against `PATHLYNKS_USER_*`. The `erp-credentials` gate
  and D-048's `ERP_EMAIL`/`ERP_PASSWORD` are superseded as the *first* target — ERP is not the
  first product under test any more (D-052: Pathlynks first).
- **T-145** (first live crawl) runs against `https://pathlynks.vidysea.com/signin`,
  `allowed_domains: ['vidysea.com']`.
- The account's own permissions ARE the test scope. Umesh provisions access when he provisions the
  account — *"मैंने यूजर क्रेडेंशियल दे दिए हैं… अब उस यूजर को कितने मैंने अकाउंट में एक्सेस दिए वो
  तो मेरे हाथ में है ना"*. AutoTester does not invent a narrower scope (WP-DECISION (NOT YET WRITTEN; number assigned when written — D-057 was spent on another subject, AT-740, D-058)).

## Still outstanding after this answer

1. **`projects/pathlynks/project.json` is `write_policy: read_only`.** WP-DECISION (NOT YET WRITTEN; number assigned when written — D-057 was spent on another subject, AT-740, D-058) authorizes
   `allow_writes`; the one-field edit is refused in the maker's session by the harness safety
   classifier ("Security Weaken") and is with Umesh. Until it lands, a run can log in and read but
   cannot press a mutating button — which is exactly the incomplete report WP-DECISION (NOT YET WRITTEN; number assigned when written — D-057 was spent on another subject, AT-740, D-058) refuses.
2. **A per-run `RunApproval` for the first live run** (D-018) is a separate act and is not granted
   by this answer.
3. **`AT-651`** — `browser/secrets.py:88-90` `_host_matches` suffix-matches, so
   `dev-new.vidysea.com` is fill-eligible for production `pathlynks` secrets declared against
   `['vidysea.com']`. Not caused by this answer, but it is on the path this answer opens: fix
   before any run whose crawl can leave the production host.
4. **`AT-570` is now an ordering defect on THIS path, and it was not one before.** A crawl/explore
   run checks a signed approval (`stages/explore_consent.py::require_consent`, HMAC keyed from
   `AUTOTESTER_APPROVAL_KEY`). **A UI case run does not** — `grep -n 'approval\|Approval'
   src/autotester/ui/routes_runs.py` returns **nothing** (verified 2026-09-27, maker). T-122 is a
   *case* run, so the first logged-in Pathlynks run goes through the one path with no approval
   check — and `allow_writes` (item 1) is what turns that from a read into a mutation on
   production. Filed medium on 2026-09-25 when the tier was `read_only` and the target was ERP;
   **both premises have changed.** Requested of `/checker`: re-triage `AT-570` to **high** and make
   it a T-122 precondition, so `trigger_run` refuses without a covering `RunApproval` before the
   first live case run, not after it. Found by the peer session's audit of its own `AT-652` fix —
   it had committed the very claim it was correcting (*"each run needs its own RunApproval"*) and
   caught it in the audit step; `CLAUDE.md:67-72` now names the enforcing path instead.

## T-136's `done_check` names a script that does not exist — deliberately, and the name stands

`uv run python scripts/check_acceptance_comparison.py pathlynks` (f9adfdec). The file is absent, which
is correct for a pending task: its check must fail until the artifact is built. The peer disclosed that
it picked the filename out of the air and asked whether the maker had already chosen another.
**It had not** — `ls scripts/ | grep -iE 'accept|compar|approval'` returns only
`check_crawl_approval.py`. So this name is hereby the chosen one: it matches the sibling convention,
and whoever builds T-136 creates **this** path. Do not add a second script to match a different guess.

**Links:** D-052 · D-053 · WP-DECISION (NOT YET WRITTEN; number assigned when written — D-057 was spent on another subject, AT-740, D-058) · D-018 · D-048 (superseded as first target) · T-122 · T-145 ·
`qa/gates/erp-credentials.md` · `qa/gates/live-crawl-target.md` · `core/env.py:46-67` · `AT-086` ·
`AT-651` · `projects/pathlynks/project.json`

Answered: 2026-09-27 — first target is the Pathlynks USER account (`PATHLYNKS_USER_*` keys), not the counsellor account — Umesh, chat (verbatim in "The answer, verbatim" above); Pathlynks-first routing recorded as D-052 (`docs/DECISIONS.md:1281`, `Approved-by: Umesh`)
