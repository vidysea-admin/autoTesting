# HUMAN_GATE — should a bare `--expires <date>` mean the END of that day?

**Raised by:** /checker, 2026-09-08, while PASSing `at147-at148-grant-boundary` cycle 1.
**Contract:** `qa/contracts/consent.md` CN4. **Issues:** AT-147 (fixed), AT-150.
**Gate class:** CRITICAL amendment — it *widens* a safety boundary. Checker may not auto-apply it.

## The question, in one line

`RunApproval.is_expired` reads `expires_at: "2026-09-09"` through `fromisoformat`, which yields
**midnight — the START of the 9th**. Should it instead mean the **END** of the 9th (23:59:59)?

## What is true today (measured, not assumed)

Checker probes at `0bed142`, real CLI in an isolated `AUTOTESTER_ROOT`:

- `--expires <today>` → **refused** at grant (AT-147's fix), naming today as the problem.
- `--expires <tomorrow>` → granted, and `require_consent` honours it — **until tomorrow 00:00:00**.
  Probed directly: expiry `2026-09-09`, `is_expired` at `2026-09-08 23:59:59` = False, at
  `2026-09-09 00:00:00` = False, at `2026-09-09 00:00:01` = **True**.
- So the *narrowest grant the CLI will now issue* buys the operator **only the remainder of today**.

The two comparisons now agree — that was AT-147 and it is fixed. This gate is about which of the
two agreeing meanings is the right one.

## Why the checker will not decide it alone

1. Adopting end-of-day **lengthens every `RunApproval` already on disk by up to 24 hours**,
   retroactively, with no re-grant. That is the textbook shape of a CRITICAL amendment under
   `/checker`'s own criticality gate: *removing or weakening a safety invariant*. CN4 ("consent is
   never open-ended") is the invariant it touches.
2. The maker declined to make the change for exactly this reason and referred it here. **The
   checker has ruled that reasoning SOUND, not over-cautious** (verdict
   `qa/verdicts/at147-at148-grant-boundary.md`). A maker that silently widened a live consent
   window on its own judgement would be the more serious finding.

## The case FOR end-of-day (the checker's own view, stated plainly)

- "Expires on the 9th" means *through* the 9th to every human who has ever read a passport, a
  credit card or a coupon. Start-of-day is a surprise, and a consent gate that surprises the
  operator is the failure mode this whole contract exists to prevent.
- Start-of-day creates a **live sharp edge**: a grant issued at 23:50 with `--expires <tomorrow>`
  is accepted with a green line and is dead ten minutes later, with nothing said. That is AT-147's
  shape again — narrower, and outside what any current test would catch.
- It would make `--expires <today>` work, removing the refusal AT-150 is filed against.

## The case AGAINST

- Every approval on disk silently gets up to 24 more hours. Nobody re-consented.
- The current semantics are now **explicit, tested, and honest**: the CLI refuses what it cannot
  honour, and CN4 records the meaning. Nothing is broken; it is only unintuitive.
- Shorter windows are the safe direction for a gate standing in front of a live production ERP.

## The decision Umesh is asked for — pick one

- **(A) Keep start-of-day.** Nothing changes. This gate closes; AT-150 (print the literal date)
  stays open as the usability fix.
- **(B) Move to end-of-day.** Then, per the maker's own request, the conservative refusal is
  **REPLACED, not layered on**: `is_expired` treats the named day as inclusive, `_validate_grant`
  goes back to `<`, `--expires <today>` is granted and honoured, and the property test
  `test_the_grant_and_the_runtime_agree_on_every_expiry_they_accept` is extended to offset `0`.
  Requires a CRITICAL amendment to CN4 and a DECISIONS entry, since it widens live approvals.
- **(C) End-of-day for NEW grants only** — store `expires_at` as an explicit
  `<date>T23:59:59` timestamp at grant time and leave bare-date rows reading as midnight. Gets the
  intuitive meaning with **no retroactive widening at all**; costs one line in `approve_cmd` and
  makes `approvals.jsonl` slightly less pretty. *The checker's recommendation.*

**Answered:** 2026-09-26T22:34:22+05:30 — C — Umesh via AskUserQuestion in the checker session. A date given to --expires means through the END of that day, for approvals minted from now on only; approvals already on disk keep their stored instant (no retroactive widening).
