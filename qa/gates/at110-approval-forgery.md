# GATE — AT-110: a consent approval can be forged, not just detected as edited

**Opened:** 2026-09-08T08:20:00+05:30 · **Status: ANSWERED -> built and merged** (option 1, HMAC keyed from .env; at110-approval-signing cycle-2 checker PASS, merged 48aba2f, AT-110 fixed) · **Approver:** Umesh

## The question, in one line
Should a `RunApproval` be **signed with a secret** so a widened row cannot be forged — and if so,
where does the key live — or is "detects an accident, not an adversary" the accepted posture?

## Why it needs you
It is a security-posture decision, not an implementation detail, and the checker explicitly said
**"do not let the maker pick this one."** Whatever is chosen becomes the guarantee the whole
consent gate makes when the explorer is pointed at the live production ERP.

## The evidence — a checker did this, on disk, with the real CLI
`core.ids.content_id` is an **unkeyed sha256**, so the id is recomputable by anyone who can write
`approvals.jsonl` — including the agent the gate exists to bound.

- A *naive* edit is caught: changing `max_actions` 12 → 9999 while keeping the stored id is
  refused with `edited after it was granted`. That part works.
- A *forged* row is not: rewrite the row with `max_actions=9999`, `wall_clock_s=99999`,
  `production=True` and the `id` key **removed**, and `model_post_init` mints a matching id
  (`is_intact: True`). `autotester explore --max-actions 500` then **ran** on a human grant of 12.

So the current property is **tamper evidence, not tamper proofing**. My own prose said an approval
"cannot be edited on disk to widen itself" — that overclaimed, and is corrected in this same fix
cycle regardless of which option you choose.

## Options
1. **HMAC keyed from the repo-root `.env`** (recommended). The `.env` is already the credential
   boundary: gitignored, `0600`, never in chat, never sent to a model. An approval gains a
   signature over its bound payload; forging one then requires the key, not just write access.
   Cost: a new key to not lose; approvals granted before the key existed become unverifiable and
   must be re-granted.
2. **A separate append-only signed audit line** (e.g. a hash chain in a second file). Detects
   *history* tampering as well as row tampering, but an agent that can write both files can still
   rewrite both. Strictly better than today, strictly weaker than option 1.
3. **Accept "accident detection only"** and say so plainly in the contract and the `--help` text.
   Defensible: the real boundary is the test account's own permissions plus your per-run approval,
   and an agent that can write the repo can also edit the code that checks the signature. Costs
   nothing and claims nothing false.

**My read, for what it is worth:** option 3 is more honest than it first sounds — an attacker who
can write `approvals.jsonl` can equally edit `core/consent.py`. Option 1 raises the bar against a
*confused* agent rather than a hostile one, which is the realistic threat here. But this is your
call, not mine.

## How to answer
Reply with `1`, `2`, or `3`. On any answer I append
`**Answered:** <ISO date> — <choice> — <where>` to this file **before** acting on it.

## What this blocks
Nothing, immediately. The consent gate works against accidents today, and AT-111 (the real
cycle-2 failure) is being fixed independently. This gate decides only what the gate is *allowed to
claim* — and it should be answered before T-145 runs against the live ERP.

Answered: 2026-09-24T16:32:17+05:30 — Umesh: "if needed tho krr dee" — option a: sign RunApproval with a secret key held in .env (keyed HMAC), so a widened row cannot be re-minted — chat 2026-09-24
