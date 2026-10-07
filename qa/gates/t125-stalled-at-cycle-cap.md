# HUMAN_GATE — T-125 has burned all three fix cycles; how should it proceed?

**Opened:** 2026-09-27 by the maker, on the cycle-3 checker verdict (`a27f9794`): **FAIL, 5/8,
unit STALLED at its 3-cycle cap.**
**Decider:** Umesh. **Status:** **ANSWERED 2026-09-27 — option A** (specify relevance first, then
exactly one scoped cycle). Recorded as **D-051**. The checker amends `qa/contracts/catalog.md` to
define which flows a row is about; only then does the maker build cycle 4 against the written rule.
The cap is broken by one cycle, deliberately and on the record, because its premise (a maker failing
at a *specified* task) was never met. Constraint carried into the amendment: `secret_key` is never
inferred (`stages/explore_merge.py:50-51`), so no keyword or structural classifier — the two
candidate shapes are a flow dimension on `CatalogEntry` or a declared relevance field on `SecretRef`,
and the checker chooses. `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` is untouched by this answer.
**Blocks:** T-125 only. Nothing else in the backlog waits on this, and **nothing broken has
shipped** (see "Blast radius").
**Related gate, still open:** `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` — CT6 is a *second,
independent* reason this unit cannot reach 8/8. Answering this gate does not answer that one.

## Blast radius — read this first, because it is the reassuring part

**`src/autotester/stages/catalog.py` does not exist on `master` at all.** The entire T-125 catalog
stage, and both regressions described below, live only on the unmerged branch `wave/t125-catalog`.
No shipped behaviour is affected, no operator has ever seen a wrong catalog row, and reverting
costs nothing that is in production. This is a decision about how to finish a feature, not an
incident.

## What happened, without softening it

Three cycles, three different answers to one question, each fixing the last and breaking something
new — all inside `stages/catalog.py::catalog()`:

| Cycle | What it did | What the checker found | Failure mode |
|---|---|---|---|
| 1 (`cfc13b0b`) | one global missing-key list; every blocked row named the **union** of every unset secret | `auth_wrong_creds` told the operator to set a sign-up-only token — one of its two named actions is always a no-op (**ISS-t125-2**) | misleading, but **visible** |
| 2 (`72f71aa1`) | scoped the key list per flow — and used the narrowed list for the blocked/runnable **decision** as well as the wording | one flow that both clicks "Sign up with Google" *and* fills the product's own password was read as OAuth-only, so its unset key vanished from the auth rows and they rendered a green `runnable` pill (**ISS-t125-3**, high) | **invisible** — ships a case that fails for real at run time |
| 3 (`513a08c7`) | separated them: the gate never narrows (every declared key), only the wording is scoped. **This genuinely fixed ISS-t125-3** — the checker verified it live | a login flow whose own password is set is now **wrongly blocked** because an unrelated flow (an OAuth sign-up, or even an admin-import flow) has an unset secret of its own (**ISS-t125-5**, high) | **false positives**, on any spec with more than one credential-consuming flow |

Both cycle-2 and cycle-3 defects are mine. Cycle 2's was the dangerous one and I reported it as a
fix; the checker caught it because I asked it to attack the rule, and caught cycle 3's the same way.

## The diagnosis, which is the actual decision you are being asked about

**No criterion in `qa/contracts/catalog.md` ever defines which secret key "belongs to" which
catalog row.** CT5 and CT8 judge the blocked state and its `unblock_action`, so a checker can prove
an answer *wrong* without the contract ever saying what is *right*. Each cycle was therefore a guess
at unwritten ground truth, and a fourth guess is not obviously better than the third.

**An independent read-only review has now confirmed this, and it corrected me on one point.** Full
report: `qa/debug/t125-catalog-cycle3.md`. Its findings that change this gate:

1. **The contract is genuinely silent** — and not only per my reading. *Both* fresh checkers, on
   different cycles, hit the same wall and each recorded it as outside its own blast radius rather
   than filing it (`qa/verdicts/t125-catalog.md:132-146` and `:340-343`). Three independent parties
   reached the same diagnosis from different angles. The ambiguity traces to `docs/plan.md:521-523`
   — the only worked example D-039 authorizes — which says "an unset secret … naming the key",
   singular and spec-wide. **It predates any maker touching the file.**
2. **No coherent rule exists at the current schema level.** The review added a fifth fixture I had
   not considered: a flow clicking a Google button for an unrelated purpose (“sign in with Google to
   import a Drive file”) is misclassified by the very heuristic cycles 2 and 3 relied on. Inferring
   which field is a credential would also violate this repo's own stated discipline
   (`stages/explore_merge.py:50-51`: *“`secret_key` is deliberately never inferred”*). So a cycle 4
   built on any keyword or structural classifier fails in the same shape again.
3. **Option B is not the safe fallback I wrote it as — see the corrected row below.**

**CT2 is confirmed as the real constraint, structurally.** `schema/catalog.py:120-131`'s
`CatalogEntry` carries `case_class` and nothing identifying a flow, and `Catalog` has no per-flow
index — while `schema/case.py:22` keys the pipeline's *actual* generated artifact by `flow_id` and
`stages/expand.py:55-56` already computes "does this flow need auth" **per flow**. `catalog()` is the
one place forced to throw that dimension away. So: once a project has more than one
credential-consuming flow — which is AT-588's own modal case, a login form plus an OAuth carry-over
— "which secret does *the* `auth_wrong_creds` row need" has **no single correct answer**, only
safe-but-broad (cycles 1/3) or unsafe-narrow (cycle 2). There is no third option in the current shape.

**Least-harmful ranking, on the review's side-by-side diff read:** cycle 3 ≈ cycle 1 (tied, both
over-block) ≪ cycle 2 (the only version that renders a false green). And per CT7 the `Catalog` is
consumed by T-152/T-166, so a false green could propagate into an automated dispatcher rather than
only misleading a human reading a page — which is why over-blocking is the safer of the two errors.

## The options, with the cost of each

| | Option | What it costs |
|---|---|---|
| **A** | **Specify relevance first, then one scoped exception cycle.** The checker amends `catalog.md` to define which flows a row is about (it owns the contracts); the maker then builds once against a written rule instead of guessing. | Breaks the 3-cycle cap, which is a real discipline and exists precisely to stop this pattern. The justification would be that the cap assumes the maker is failing at a *specified* task, which the diagnosis says is not the case — fixing the specification changes the conditions rather than buying another guess. **Maker's recommendation — the condition is now met: the review confirmed the contract is silent.** The rule must be *written* before the cycle, not guessed inside it; the review's two candidate shapes are a flow dimension on `CatalogEntry` or a human-declared relevance field on `SecretRef` (matching the "never infer, only declare" pattern this repo already uses). |
| **B** | **Revert cycles 2 and 3** (`513a08c7`, `72f71aa1`) back to `cfc13b0b` and re-open T-125 with a corrected design from the start. | **CORRECTED 2026-09-27 — I had this wrong, and the row said the opposite before the review read the actual diffs.** `cfc13b0b:catalog.py:128` threads a **global unscoped union into the gate**, exactly as cycle 3 does — so **cycle 1 has the identical ISS-t125-5 defect**, not a milder one. It also loses cycle 3's scoped wording, and **`cfc13b0b` was never a passing commit** (no manifest, and the cycle-1 check failed it on CT5/CT6). The standing regression rule assumes a last *good* state to return to; in this function's history there is none — every version ever checked has failed. Reverting therefore buys nothing on correctness and costs the genuinely-correct ISS-t125-3 hybrid fix and its test. **Still listed because it is your rule and your call, but I no longer present it as the low-risk option.** |
| **C** | **Ship the catalog without a credential gate at all** — the rows report applicability and blocked-for-write-policy, and say nothing about whether secrets are set. | Honest: the system stops making a claim it has no specified rule for. An operator then discovers a missing credential when the case runs and fails, with a clear error, instead of beforehand. Costs a real feature that AT-588 asked for, and CT5/CT8 would need amending to match — so it is also a contract change, not just a deletion. |
| **D** | **Amend CT2 to allow more than one row per `CaseClass`** (per-flow or per-screen), so "which secret" becomes answerable by construction, then build. | Addresses the root shape rather than its symptom. Costs the catalog's best property — a fixed-length table an operator can scan — and is much the largest change of the four. |

**The maker is not choosing.** A and D both amend checker-owned ground truth; B and C give up
shipped scope. Each is a decision about what the product promises, not an implementation detail.

## Until this is answered

- `wave/t125-catalog` stays **unmerged**. Nothing is reverted yet either — reverting pre-empts A and
  D, and merging would ship ISS-t125-5.
- `ISS-t125-5` (high) and `ISS-t125-1` stay `open`; `ISS-t125-3` is `verified` (genuinely fixed).
- **No cycle 4 will be started without an answer here.** The cap is respected rather than quietly
  exceeded, which is the whole point of having one.
- T-125 stays `pending` in `.goal/goal.json`. The rest of the backlog continues; this gate blocks
  only this unit.

Answered: 2026-10-07 — option A (generalized): drop the native-egress sandbox precondition; local visible browser + full suite on any machine, against any product URL with its supplied credentials; test-suite guards kept (no real creds/.env, no paid calls, no external network in unit tests) — chat 2026-10-07, D-070
