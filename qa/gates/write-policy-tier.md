# GATE ANSWERED — write_policy tier for live runs

**Asked by:** checker session (Mode B), 2026-09-27
**Answered by:** Umesh, 2026-09-27. Asked once; this file is the record so it is never asked again.
**Authority:** D-018 (`docs/DECISIONS.md:225`) — *"write_policy is enforced ... as an INNER guard inside
Umesh's outer boundary (the test account's own permissions) ... **ALLOW_WRITES is Umesh's switch.**"*
This file records the switch being thrown. It does not create a new policy.

## The question

Which of the three declared tiers applies to live runs, and on which targets?
`READ_ONLY` (deny-list on, no submits, no typing) · `TEST_ACCOUNT` (deny-list on, submits + typing)
· `ALLOW_WRITES` (deny-list **off**, submits + typing).

## The answer

**`ALLOW_WRITES`, on every target, production included.**

Umesh's standing position, consistent across four records and unchanged:

- `qa/gates/at052-bfs-video-corpus-grill.md:43` — *"this will all dependent on the account of which
  credentials provided. jo jo uss account mai access hoga vo krr lengee"*
- `docs/DECISIONS.md:860` — *"jo account mai dunga usme jitni permission hogi utni tho testing ho hi
  jaani chaiyee"*
- `qa/gates/at110-approval-forgery.md:38` — the real boundary is the test account's own permissions
  plus the per-run approval
- 2026-09-27, this gate — *"jis acccount k credentials diyee hongee usko jo jo right honge vo sabb
  action test aand validate krr skta hai"* and *"production prr bhi agar jo user creditials diya hai
  agar uss user ko koi write krna allos hai tho write krr skta hai"*

**The boundary is the account's own permissions.** Whatever the supplied test account is entitled to
do, AutoTester may do and validate.

## Asked with the consequences stated, and reaffirmed

The checker put the specific consequences to Umesh in the question itself before he chose, naming
that at `ALLOW_WRITES` the 19-term deny-list goes off, so on production the crawler may click
`Delete` on a real record, `Send` (a real email to a real person), and `Pay` (real money) — and that
an account having the *right* to do something is not the same as the action being reversible. He
chose `ALLOW_WRITES` everywhere with that in front of him. **It is his decision, recorded, not
re-litigated.** A future session must not reopen this gate; it may only report what a run actually did.

## What this does NOT waive — unchanged, and NOT part of the answer

1. **Per-run approval still applies.** D-018 gate 2 governs every outward-facing run. The maker's
   D-052 states it directly: *consent gate 2 existing is not permission to use it.* This gate sets
   the ceiling; each run still needs its own `RunApproval` naming target and scope.
2. **Logout/sign-out is never clicked at any tier** — `DEFAULT_NEVER_CLICK_PATTERNS`,
   `schema/crawl.py:41`. Not a policy setting.
3. **Real user accounts are never used** — test accounts only (D-018; test accounts carry no 2FA,
   Umesh 2026-09-07).
4. **`T-154`/`T-155` stay held** — see below. `ALLOW_WRITES` plus adversarial is not authorized.
5. **The tier is still a per-project config value.** The checker does not flip
   `projects/*/project.json` — segregation of duties, not caution. **But the flip for `pathlynks` is
   now DUE, not pending further approval:** it is the project whose credentials Umesh supplied, and
   leaving it at `read_only` is the paper-yes/config-no outcome this file's withdrawn residual caused.
   The maker owns the edit and its DECISIONS entry.

## WITHDRAWN — the "residual" that became a brake

An earlier version of this file carried a residual: that `send` and `pay` are outward-facing to third
parties and undone by nothing, with "a run may be approved with a narrower scope than the tier
permits" as the mitigation. **That sentence is withdrawn, 2026-09-27.** It was cited in D-053 as a
reason to leave all nine projects at `read_only`, so the net effect on disk was an authorization on
paper and a refusal in config. The checker wrote the brake; the checker removes it.

Umesh, 2026-09-27, when shown that outcome:

> *"तुझे एक्सेस देने के लिए मैंने यूजर क्रेडेंशियल दे दिए हैं ... अब उस यूजर को कितने मैंने अकाउंट में एक्सेस दिए वो तो मेरे
> हाथ में है ना, एक्सेस कंट्रोल. तुझे तेरा काम है एज़ अ टेस्टर उस यूजर से लॉग इन करना और सारा सब कुछ एक्टिविटी करना. तो अगर
> बटन प्रेस ही नहीं करेगा तो पता कैसे चलेगा बटन प्रेस करके क्या होता है? डेटा एंटर करेगा नहीं तो कैसे पता चलेगा डेटा एंटर होता
> है नहीं होता है? ... मैं अकाउंट वैसा ही बना के दे रहा हूँ जिसमें मेरे को जो टेस्ट करवाना है. तो ओवर स्मार्टनेस क्यों चाहिए इतनी."*

**The division of labour, as the owner states it:** access control is his and is exercised when he
provisions the account. The account he supplies IS the scope. A tester that will not press the button
cannot report what the button does; one that will not enter data cannot report whether data saves.
Narrowing the tier below the account's own permissions does not make the run safer — it makes the
report incomplete, which is the one failure this project exists to refuse (O4).

**So: no run is scoped narrower than the supplied account's permissions on the checker's initiative.**
A narrower `RunApproval` scope remains available when *Umesh* asks for one for a specific run. It is
not a default, not a recommendation, and never again a reason to withhold the tier.

**What survives, because it is reporting rather than gating:** a run report states what the run
actually did — every mutating action taken, with its evidence. That is the tester's output, not a
permission question.

## T-154 / T-155 (adversarial pass + its report)

**HELD.** Umesh 2026-09-27: *"Pehle proof run ho, phir kholenge"* — the T-169 proof run happens
first, he reviews the comparison, and only then is the adversarial pass opened. This gives the
open-ended morning hold a condition. Track C builds through C3 only.

## Links

`AT-651` (prepod has no environment of its own; the `_host_matches` suffix match makes production
secrets fill-eligible on `dev-new.vidysea.com`) · `AT-281` (T-169 acceptance) · `AT-653` (ground-truth
ordering) · `T-145` · `T-171` (permission surface — the tier is what makes it reachable) · D-018 · D-052

Re-confirmed 2026-09-28 by Umesh, unprompted and with visible impatience at the repetition.
projects/pathlynks/project.json write_policy = allow_writes, on production. See
qa/gates/at654-d029-dev-only-vs-production-pathlynks.md for the verbatim instruction.
NOTE (updated 2026-09-28, AT-718): the "D-056" cited elsewhere as authorizing this DID NOT EXIST
on disk -- highest decision id was D-055. That missing entry is why this question kept coming back.
Filed as a finding (AT-710). **The state has since changed and the citation is now WORSE, not fixed:**
D-056 was appended 2026-09-28 for an unrelated subject (the at673 round-cap waiver), so every
citation pointing here now resolves to the wrong entry instead of dangling visibly. The authorizing
entry for Pathlynks `allow_writes` is to be written under the next free D-number (NOT D-057, which was spent on another subject — AT-740, D-058) by the maker, who owns both that
edit and the `projects/pathlynks/project.json` flip per the section above. The seven citations in
`at654-d029-dev-only-vs-production-pathlynks.md` and `pathlynks-user-account-first.md` were corrected
to `WP-DECISION (NOT YET WRITTEN; number assigned when written — D-057 was spent on another subject, AT-740, D-058)` the same day; `qa/QUEUE.md` is the maker's surface and still carries the
old one.

Answered: 2026-09-27 — `ALLOW_WRITES`, on every target including production — Umesh, chat; recorded as D-053 (`docs/DECISIONS.md:1360`); re-confirmed 2026-09-28 (see the note at the end of this file)
