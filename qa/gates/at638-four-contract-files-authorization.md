# HUMAN_GATE — may the checker author four new contract files, or does a decision entry come first?

**Opened:** 2026-09-27 by the maker, on the `at638-remainder` cycle-1 verdict (**FAIL**, worktree
commit `a9146761`). **Decider:** Umesh. **Status:** **ANSWERED 2026-09-27 — option A, all four** (not the three-file
subset). Recorded as **D-054** with `Approved-by: Umesh`, appended via `scripts/append_decision.ps1`.
The checker may now author `permission-surface.md` (PS1–PS4), `eval-compiler.md` (EC1–EC4),
`release-regression.md` (RR1–RR5) and `damage-control-report.md` (DC1–DC4), each DRAFT → ACTIVE on its
own unit's first PASS. Carried into D-054 for whoever authors them: RR2's CN5/CN6 authority claim is
overstated against its own stated Verify; PS2 is `[D-040 verbatim]`, not arguable; and this unit's
check never completed `uv run pytest` (disclosed, sound for a contracts-only diff, recorded as an
evidence gap). **The T-167 dependency contradiction listed below is separately resolved by D-055:**
T-167 depends on T-166 and T-110 only, `release-regression.md` encodes no T-179 dependency.
**Blocks:** T-171, T-166, T-167, T-168 (their contract criteria) and the closure of **AT-638**.
Nothing else waits on it, and **nothing is broken** — this gate is about authorization, not a defect.
**Ledger:** `ISS-at638-remainder-1` (high, `approval-required`). **Verdict:** `qa/verdicts/at638-remainder.md`.

## This is a FAIL on governance, not on the work

The build subagent filed 17 proposed criteria and **the checker judged all 17 sound and buildable
as worded** — it reproduced every pasted grep, confirmed the diff touched exactly the two claimed
files, and verified `schema/portal_persona.py` really can carry the knowledge graph EC1 requires.
The unit failed for one reason only: **the checker ruled it may not author the four contract files
yet**, because no `docs/DECISIONS.md` entry authorizes them.

Both the build subagent and the checker found this independently, and **neither wrote a decision
entry to manufacture the authorization** — which is the correct refusal, since an authorizing entry
needs your `Approved-by:` line and cannot be self-granted.

## The finding, verified twice

Every checker-authored contract in this repo — **5 for 5** — was named in a `Changes-authorized`
line of an `Approved-by: Umesh` decision *before* the checker wrote it:

| Decision | Contract files it named |
|---|---|
| D-017 / D-018 | `ai-target.md`, `adversarial.md` |
| D-039 | `catalog.md` |
| D-040 | `crawl-traversal.md`, `network-assertions.md` |
| D-041 | the seven T-172–178 contracts |
| D-042 | `agent-layer.md` |

The four now proposed have **no such line**. The checker read the text directly rather than trusting
the manifest: D-040's `Changes-authorized` (`docs/DECISIONS.md:871-874`) names only
`crawl-traversal.md` and `network-assertions.md` — T-171 gets a `.goal/goal.json` registration and
nothing more. D-041's (`:923-928`) names only the seven T-172–178 files — T-166 and T-167 get
goal.json notes and nothing more. **T-168 is named by no decision at all**, despite existing in
`.goal/goal.json` since 2026-09-10.

`CLAUDE.md`'s Lab Protocol states the rule generally: *"no edit to `ARCHITECTURE.md` or
`contracts/` without an authorizing DECISIONS entry written FIRST."* Authoring these now would be
the first exception in this repo's history — exactly the kind of precedent that should be set
deliberately by you, not quietly by an agent that finds it convenient.

## The decision

**Option A — approve (the checker's implied recommendation, and mine).** Append the entry below via
`powershell -File scripts/append_decision.ps1 -EntryFile <entry.md>` with your `Approved-by:` line.
The criteria are already reviewed, so the next checker authors the four files and closes AT-638 with
no further re-review. The draft, exactly as the checker wrote it:

> **What:** Authorize `/checker` to author four new checker-owned DRAFT contract files from the
> criteria filed in `qa/feedback-inbox.md` (2026-09-27, at638-remainder unit):
> `qa/contracts/permission-surface.md` (PS1–PS4, T-171, D-040), `qa/contracts/eval-compiler.md`
> (EC1–EC4, T-166, D-041), `qa/contracts/release-regression.md` (RR1–RR5, T-167, D-041),
> `qa/contracts/damage-control-report.md` (DC1–DC4, T-168, previously unauthorized by any decision).
> Each goes DRAFT → ACTIVE on its own unit's first checker PASS, same as every prior batch.
> **Why:** AT-638 (checker-sweep, high) found these four capabilities have zero checkable contract
> criteria; D-040/D-041 registered the goal tasks but never named contract files for them (T-168 was
> never named by any decision at all). This closes that governance gap the same way
> D-039/D-040/D-041/D-042 closed it for every other checker-authored contract in this repo.
> **Changes-authorized:** the four files named above (new, checker-authored DRAFT).
> **Approved-by:** Umesh — `<pending>`.
> **Links:** AT-638; T-166; T-167; T-168; T-171; D-040; D-041; `qa/verdicts/at638-remainder.md`

**Option B — approve a subset.** T-168 is the weakest case: no decision has ever named it, so
authorizing its contract is a slightly larger step than the other three, which at least have
authorizing decisions that merely failed to name a file. Naming only three leaves T-168 ungoverned
and AT-638 partly open.

**Option C — decline, and leave the criteria as filed proposals.** They stay in
`qa/feedback-inbox.md`, reviewed and sound, until a future decision picks them up. AT-638 stays
`open` and T-166/T-167/T-168/T-171 remain unbuildable under the pair, since a unit with no contract
has nothing to be judged against.

## Three smaller things, recorded rather than buried

- **RR2's authority tag is slightly overstated** (checker, low, not filed as a ledger issue since
  the file does not exist yet): it claims to extend `consent.md` CN5/CN6, but its stated `Verify`
  only exercises CN1-shaped behaviour — unlike its own named precedent AD2, whose Verify tests
  CN5's exactness and CN6's bound-shortfall. Whoever authors `release-regression.md` should either
  strengthen the Verify or drop the CN5/CN6 claim.
- **One correction against my own dispatch:** I told the checker PS2 (destructive-actions-last) was
  a freely-arguable `[maker]` addition. It is not — it is tagged `[D-040 verbatim]` and matches
  D-040's text exactly. The genuinely arguable ones are PS4, DC3 and RR3, and the checker reviewed
  and accepted all three as low-risk.
- **A pre-existing contradiction in the ground truth itself, unresolved and not this unit's to fix:**
  D-042 says T-167 "runs the lead agent on LangGraph checkpoints", implying a T-179 dependency, but
  `.goal/goal.json`'s T-167 `deps` is `["T-166","T-110"]` and `docs/plan.md` row 21 omits T-179 —
  and the contradiction sits *inside T-167's own `note` field*, which echoes D-042's sentence next to
  the deps array that omits it. Both the subagent and the checker deliberately left it disclosed
  rather than picking a side. It will need answering before T-167 is built.

## One disclosed shortcut in the check itself

The checker ran `ruff check` and `autotester doctor` live (both clean) but **did not complete
`uv run pytest`** — the full suite outran its interactive window, as the sibling unit's check also
did. It accepted ruff + doctor + the diff-stat as sufficient on the grounds that the diff touches
zero `src/` or `tests/` files, so there is nothing new for the suite to exercise. That reasoning is
sound for a contracts-only unit and it disclosed it rather than claiming a green run, but it is a
gap in the evidence and is recorded as one.

## Until this is answered

- `wave/at638-remainder` stays **unmerged**; the manifest stays at cycle-1 FAIL, **not**
  `checked-PASS`. The verdict is copied onto `master` so the record is visible without merging.
- **No cycle 2 will be started.** A fix cycle is for a maker defect, and there is no maker defect
  here — the blocker is a decision only you can make. Spending a cycle would be theatre.
- **AT-638 stays `open`.** Track C is genuinely closed (the sibling unit's PASS authored
  `ai-target.md` and `adversarial.md`); the other four capabilities have reviewed *proposals*, which
  is not the same as checkable criteria.

Answered: 2026-09-27 — option A, all four contract files (permission-surface, eval-compiler, release-regression, damage-control-report), not the three-file subset — Umesh; recorded as D-054 (`docs/DECISIONS.md:1432`, `Approved-by: Umesh`)
