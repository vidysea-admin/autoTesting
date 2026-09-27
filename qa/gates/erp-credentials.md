# GATE — ERP test-account credentials for the first logged-in run

**Opened:** 2026-09-08T15:05:00+05:30 · **Status: OPEN** · **Approver:** Umesh

## The question, in one line
Enter `ERP_EMAIL` and `ERP_PASSWORD` for the ERP **test account** at
`/projects/erp/env` in the running AutoTester UI.

## How to answer it — and how NOT to

**Do:** open the AutoTester web UI → project `erp` → **Credentials** → enter both values → save.

**Do not paste them into this chat, a commit message, a manifest, or any file in the repo.**
That is not caution theatre: `cases.jsonl` and `project.json` are **git-tracked in a public repo**
(github.com/umeshsugara-ai/autoTesting). A value that reaches a tracked file is published.

The values land only in `projects/erp/.env`, which is gitignored and mode-0600. `SecretRef` holds
the **key** and its domain scope — never a value. Prompts carry `{{SECRET:ERP_PASSWORD}}` and
substitution happens at `page.fill()` time only, scoped to the project's `allowed_domains`.

**It must be a test account.** `CLAUDE.md` forbids a live user's credentials outright, and the
test accounts carry no 2FA while real user accounts (Karun's, Shubi's) do — those are never used.

## What it blocks

| Task | Criticality | What it is |
|---|---|---|
| **T-122** | high | The first logged-in ERP run: the login case, executed, with the password masked in every screenshot |
| **T-145** | **critical** | The live bounded READ_ONLY crawl of the production ERP — Track B's entire payoff |

**Nothing else is blocked.** Track A, Track C, and the whole issue backlog proceed without this;
the maker has been picking unblocked units for the whole session and will keep doing so. This gate
does not idle the loop — it caps what the loop can ultimately demonstrate.

## Why it matters more than a normal blocker

The explorer is **code-complete and has never touched a real product**: `find projects -name crawl`
and `-name flowspec.json` both return nothing. Every crawl guarantee — the deny-list, the
never-click rules, the dialog breaker, the host re-check, "nothing is typed" — is proven against a
local fixture site and by `scripts/explore_proof.py` (11/11), and against no real application at all.

T-145 is the first run where those guarantees meet a product that can actually be damaged. It is
also gated on its own consent approval (D-018) **in addition** to these credentials, and the
`done_check` that guards it is now a command that can genuinely fail — verified by the sweep,
which ran it and got exit 1.

## Related, and deliberately separate
`qa/gates/at110-approval-forgery.md` — whether a consent approval should be **signed** rather than
merely content-addressed. That gate hardens the guarantee T-145 relies on, but it does not block
this one, and answering either does not answer the other.

## Why this file did not exist until now (recorded, not hidden)
Filed as **AT-142** by the 2026-09-08T14:40Z sweep. The maker's own rule is *"the moment you name a
gate, write `qa/gates/<slug>.md`"* — and this gate was named in the closing line of **every** tick
stamp for the entire session while no file was ever written. A gate that lives only in prose is the
2026-09-03 D-006 loop: the sweep keeps flagging it, the maker keeps re-asking, and nothing on disk
ever says whether it was answered. The rule existed; the maker did not follow it.

## Answer log
<!-- On answering, append exactly: **Answered:** <ISO datetime> — <choice> — <where> -->

**Answered:** 2026-09-26T22:34:22+05:30 — provide — Umesh via AskUserQuestion in the checker session. Umesh will enter a TEST account's ERP_EMAIL and ERP_PASSWORD himself in the UI (project erp -> Credentials -> gitignored projects/erp/.env), never in chat or a commit, never Karun's or Shubi's real 2FA login. T-122 unblocks once both KEYS are present (checked by key name only, never by value); every run still needs its own approval.
