# Gate — AT-383: `loop-status --strict` has no caller, and every place to put one is gated

**Opened:** 2026-09-16T12:52+05:30
**Blocks:** AT-383 (medium) and, behind it, AT-368 (high) — which the checker deliberately left
open until "an outage announces itself without being asked"
**Raised by:** maker, before building

## The question in one line

Where should `autotester loop-status --strict` actually be called from, given that the consumer
the checker named lives outside this repo and the only in-repo candidate is an enforcement path?

## Why I cannot just wire it

I checked all four candidates:

| Candidate | Verdict |
|---|---|
| **Mode B sweep check 1** — what AT-383's `expected` names | Lives in `C:/Users/Lenovo/.claude/skills/checker/SKILL.md`, **outside the bound root**. The maker's project-binding rule forbids writing there, and it is shared by every maker-checker project. |
| **`autotester doctor`** | Already ruled out and the checker agreed: doctor is in the adapter's verify chain, so a stale loop would fail every future unit's verification. |
| **`docs/SNAPSHOT.md`** (injected at every session start) | Looks ideal, and is a **trap**. `doctor.py:119-129` regenerates the snapshot and compares it to the file on disk. A liveness line is time-varying, so the on-disk copy would differ from the regeneration immediately and `stale-generated` would fire on every run — poisoning the verify chain by the back door. |
| **`qa/hooks/mc-sessionstart.ps1`** — the real in-repo candidate | An **enforcement path** under this repo's Lab Protocol (project CLAUDE.md names `qa/hooks/*` explicitly), so it needs a `docs/DECISIONS.md` entry carrying `Approved-by: Umesh`. I grepped every `Changes-authorized:` line in DECISIONS: **none covers `qa/hooks/mc-sessionstart.ps1`.** |

## The decision — Umesh picks one

- **A — Authorize the session-start hook.** `qa/hooks/mc-sessionstart.ps1` runs
  `autotester loop-status --strict` and prints any unexplained outage alongside the existing
  "Last tick: N min ago" line. Honest caveat, stated up front: this still cannot fire *during* an
  outage — nothing here runs while the app is closed — but it announces at **the first moment
  anyone could act**, without being typed. That is a real improvement over today and strictly less
  than AT-368's full ask.
- **B — Route it to the checker's sweep instead.** Amend Mode B check 1 to shell out to
  `loop-status --strict` rather than reading `.last-tick`'s age by hand. Correct home, benefits
  every project — but it edits a shared skill outside this root and needs its own authorization.
- **C — Both** (A now, B when the skill is next touched).
- **D — Accept it stays manual.** Close AT-383 `wontfix`, and AT-368 with it, on the grounds that
  a human typing one command is enough. I'd note this is the reading that lets the next 5-day
  outage pass unremarked.

**Answer format:** reply `A`, `B`, `C` or `D` with one line of reasoning, or append an
`Answered:` line to this file directly.

## State

Nothing written. No hook touched, no DECISIONS entry drafted — under the Lab Protocol the
authorizing entry comes **before** the change, not after.

Answered: 2026-09-26T22:34:22+05:30 — C (both) — Umesh via AskUserQuestion in the checker session. A now: call `autotester loop-status --strict` from qa/hooks/mc-sessionstart.ps1 (report at session start; enforcement path, authorized with Approved-by Umesh in D-048). B later: the shared sweep routine outside this repo, when that file is next touched.
