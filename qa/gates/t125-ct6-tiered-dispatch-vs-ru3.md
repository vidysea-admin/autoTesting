# HUMAN_GATE — CT6 tiered dispatch vs ui-run.md RU3

**Opened:** 2026-09-27 by the maker, on checker finding **ISS-t125-1** (high) in
`qa/verdicts/t125-catalog.md` (cycle 1, FAIL, 5/8).
**Decider:** Umesh. **Status:** OPEN — asked once, then written here.
**Blocks:** CT6 reaching PASS on t125-catalog. Does **not** block the rest of the unit; cycle 2
fixes ISS-t125-2 and leaves this one named.

## The conflict, in one paragraph

Two ACTIVE contracts want opposite things from the run trigger.

- **`qa/contracts/catalog.md` CT6** requires that `ui/routes_runs.py::trigger_run()` dispatch cases
  **tier by tier**, cheap before expensive, and **stop** before paying for a tier with zero runnable
  entries — so a cheap structural failure is visible before an expensive tier is billed.
- **`qa/contracts/ui-run.md` RU3** requires the run trigger to run **every case on file**. That is
  also what makes F-058's pinned-regression guarantee true: a known bug's case runs *every time* and
  cannot be skipped.

Honouring CT6 means filtering which cases execute, which breaks RU3 and weakens F-058. Honouring
RU3 means CT6 can never be met by the running system.

## What actually exists today (verified, not assumed)

`stages/catalog.py::tiers_to_run()` is implemented, correct and unit-tested — and **unused**:
`grep -rn 'stages.catalog|tiers_to_run|Tier' src/autotester/ui/routes_runs.py` returns nothing.
`trigger_run()` runs `store.list_cases()` unconditionally. The three CT6 tests all call
`tiers_to_run(cat)` directly; none drives the run endpoint.

The gap was disclosed in `stages/catalog.py`'s own docstring and in commit `cfc13b0b`'s message
("Not yet wired… conflicts with the ACTIVE `qa/contracts/ui-run.md` RU3"). The cycle-1 manifest's
claim that CT6 "held … no gaps found" was wrong, and the checker was right to fail it: CT6 as
written is a claim about dispatch behaviour that does not exist.

## Why the maker is not choosing

This is a contract-level conflict between two ACTIVE contracts, and either resolution changes a
shipped user-facing guarantee. D-039's `Changes-authorized` does not cover `ui-run.md`, and
`qa/contracts/` is checker-owned in any case. Picking a side here would be the maker amending
ground truth to make its own unit pass.

## The options, with the cost of each

| | Option | What it costs |
|---|---|---|
| **A** | **Amend CT6** to require tier *ordering and reporting* only — run everything, cheapest tier first, and surface the cheap failure prominently — never skipping. | RU3 and F-058 stay intact. The cost-avoidance half of CT6 is given up: an expensive tier still gets paid for. Smallest change; `tiers_to_run()` becomes an ordering helper and gets wired as one. |
| **B** | **Amend RU3** to allow tier stopping, with pinned cases (F-058) explicitly exempt so a known bug's case always runs. | Delivers CT6's cost saving. Weakens "every case runs every time" to "every pinned case, plus every case in a reached tier". A regression can hide behind a skipped tier — exactly the failure AutoTester exists to prevent. |
| **C** | **Make stopping opt-in** per run (`--stop-on-empty-tier`, default off). | Both contracts stay true by default; the saving is available when asked for. Adds a run-shaped flag and a second dispatch path to keep honest. |
| **D** | **Retire CT6** and delete `tiers_to_run()`. | Honest about what the system does. Loses the cheap-before-expensive idea entirely, and `docs/FEATURES.jsonl` would need a correction if anything claimed it. |

The maker's reading, for what it is worth and not as a decision: **A** is the only option that costs
no shipped guarantee, and CT6's ordering half is most of its value — but A does give up the money
saving that motivated CT6, so if that saving is the point, **C** is the honest way to have it.

## Until this is answered

- CT6 stays FAIL on t125-catalog. The unit can still reach PASS on the other seven criteria only if
  the checker judges CT6 gated rather than failed — **that is the checker's call, not the maker's.**
- `tiers_to_run()` stays in place and unused, with its docstring disclosure intact. It is not
  deleted (that would pre-empt option A/C) and not wired (that would pre-empt B).
- ISS-t125-1 stays `open` in `qa/issues.jsonl`.

---

**Brought onto master 2026-09-27 by the maker, and why that is a correction, not housekeeping.** This
file was written into the `wave/t125-catalog` worktree and committed only there, so for two ticks a
decision reported to Umesh as "gated on you" existed on a branch he had no reason to look at — and
that branch has since stalled at its cycle cap and may be reverted, which would have deleted the
gate along with the code. **A gate the human cannot see is not a gate.** Gate files are human-facing
decision records, not unit artifacts: they belong on master the moment they are opened, whatever
happens to the branch that prompted them. The CT6 question below is unchanged and still open.

Answered: 2026-09-29 — A — "A: order only, never skip (Recommended)"; CT6 narrowed to ordering + reporting, RU3/F-058 intact, tiers_to_run() wired as ordering helper only; Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057

Answered: 2026-10-07T06:34:21Z — A — chat (Umesh): run every case, cheapest tier first, cheap failures surfaced at the top; never skip. RU3/F-058 intact.
