# Contract — crawl-traversal (hybrid BFS+bounded-DFS, form replay, incremental crawl, change tracking)

**Status:** **ACTIVE** (2026-09-27) — flipped from DRAFT on T-165's first PASS, which is a D-040
dual PASS: `qa/verdicts/t165-crawl-traversal.md` carries both "CHECK B — cycle 2" and
"CHECK A — cycle 2", each PASS, each derived in a fresh context without reading the other. Check A
made the flip after confirming check B's section was already on disk; neither check flipped it
alone. The merge to `master` is the orchestrator's, not a checker's.
**Criticality:** CRITICAL — T-165 stays a **dual check** per D-040 (two independent checkers,
`qa/verdicts/<slug>.md` and `qa/verdicts/<slug>.b.md`, same protocol as `explore.md`'s own X-series
work). This contract governs code that widens what the explorer visits and re-visits automatically,
in a real browser against a real product — the same criticality class `explore.md` itself carries.
**Feature:** widens T-165 in place (D-040), on top of the existing bounded-BFS crawl
(`qa/contracts/explore.md`, unamended by this contract — see "Relationship to explore.md" below):
a `strategy: bfs | hybrid` traversal mode, form-input replay in `_replay_discovery`, an incremental
crawl seeded from `portal_persona.json`, and change tracking (new/changed/missing/broken) extending
`portal_persona.py::_merge` beyond add-only PP2.
**Covers:** goal task T-165. **Deps:** T-163 (orchestrator, done), T-144 (crawl report, done).
**Grounding:** D-040 (authorization, exact scope); `docs/research/crawl-reuse-2026-09.md` (verified
licences + ported mechanisms: Crawljax Apache-2.0 idea-port for traversal, Stagehand MIT idea-port
for the incremental cache-key); `.goal/goal.json` T-165's note (frontier-completeness wording,
carried forward verbatim into CR5); Umesh, `qa/feedback-inbox.md` 2026-09-23T07:30 (source demand).

## Relationship to `explore.md` (read first — this contract does not replace it)

`explore.md`'s X1-X18 govern the crawl's identity, safety matrix, dialog handling, artifact
durability and merge discipline; **none of them are amended, softened, or duplicated here.** This
contract governs only the four widenings D-040 named. In particular:
- X1 (only `explore.py` invents a click), X2 (actuator chokepoint), X5/X6 (the safety matrix,
  deny-list, never-click), X10/X10-b (nothing typed except synthetic values under the four gated
  conditions) are **byte-unchanged and still in force** — every criterion below that touches
  clicking or typing is a *replay of an action already permitted once*, never a new kind of action.
- X3 (structural identity), X13/X14 (propose-never-approve, conflicts kept not resolved) are the
  identity and merge primitives this contract's incremental/change-tracking criteria are built on
  top of, not around.
- Permission-surface coverage (every reachable control exercised or blocked-with-reason) and
  first-party API/network assertions were both split OUT of T-165 by D-040, into T-171 and T-170
  respectively — **not this contract's job** (see no-fire list).

## Criteria (CR1-CRn) — each judged on re-runnable evidence

### CR1 — Traversal strategy is explicit, bounded, and does not revive D-023's rejection
A `strategy: bfs | hybrid` field governs traversal. `bfs` is byte-identical to today's FIFO
`_bfs`/`.pop(0)` behaviour (`stages/explore_node.py`). `hybrid` means: BFS still maps the whole
portal first — every discovered screen is still enqueued breadth-first — and, per discovered
workflow, a **bounded** depth-first descent (Crawljax's depth-first candidate ordering, ported as
fresh Python per `crawl-reuse-2026-09.md` §1 — idea only, no code copied, Apache-2.0 read
permission) goes deeper than plain BFS would before backtracking. `hybrid` invents no new bound: it
is governed by the same `max_screens`/`max_actions`/`wall_clock_s`/`max_depth` from X4, unchanged.
This is explicitly **not** D-023's rejected single happy-path DFS — D-023 rejected DFS as the
*only* traversal (a single depth-first line through the portal, never mapping the whole thing);
`hybrid` here always maps breadth-first first and only then goes deep, per workflow, bounded.

**Falsifiable (D-040's acceptance test (a)):** on a fixture site with a workflow at least N screens
deep behind a branch BFS would ordinarily defer, a `hybrid` crawl under a fixed action budget
reaches a depth-N screen that a `bfs` crawl under the *same* budget does not.

### CR2 — Form-input replay: `_replay_discovery` re-issues fill values, not only the click
`stages/explore_return.py::_replay_discovery` re-performs the `ScreenEdge` that discovered a node.
Today it replays only `rt.session.click(edge.target)` (line 94); this criterion requires that when
the discovering edge was itself a typed action (an X10-b `FILL`/`SELECT` edge, synthetic values,
already permitted and already recorded once), the replay re-issues those same recorded values
before re-performing the submitting click — so a screen reachable only behind a filled, submitted
form can be re-entered by `return_to`, not just a screen reachable by a bare click chain. This
criterion **widens nothing under X10/X10-b**: it replays an action the crawl already performed
once, under conditions the safety matrix already approved; it originates no new value, no new
target, and no action `explore_typing.py::type_form`'s four gate conditions did not already clear
for the discovering edge itself.

**Falsifiable:** a fixture with a screen reachable only after filling and submitting a form (built
under X10-b's gated conditions) → after the browser navigates away, `return_to` on that screen
succeeds by replaying both the fill and the click; reverting the fill-replay addition (click-only)
in an isolated copy reproduces the original failure to re-enter (a `_replay_discovery` failure
naming "landed on a different screen" or an unresolved form-gated node).

### CR3 — Incremental crawl: persona-seeded skip
Before the crawl visits a candidate node, it looks up `(url_template, structural_signature)`
against `portal_persona.json`'s stored `PersonaScreen` (`PersonaScreen.key()` for the URL half,
`PersonaScreen.signature` for the structural half — both fields already exist,
`schema/portal_persona.py:64-67`) — the Stagehand cache-key idea-port named in
`crawl-reuse-2026-09.md` §3. A match **skips** re-visiting that node (no click, no re-fingerprint,
no re-enumeration of its already-known candidates) rather than re-exploring it from scratch; a node
with no persona match, or whose live signature differs from the stored one, is explored as normal.
A skipped node is recorded with its own status (never silently absent from the crawl's counts — see
CR5) and never counted as a "visited" action toward `CrawlFrontier.actions_used`.

**Falsifiable (D-040's acceptance test (b)):** a second crawl of a fixture project **unchanged**
since the first crawl (persona already seeded from crawl 1) issues **≤10%** of the first crawl's
`actions_used`; the same second crawl against a fixture with every screen's structure genuinely
changed issues close to the first crawl's action count (the skip triggers on stored-and-matching,
not merely on "seen before"). **Ruling on Q3 (routine amendment, 2026-09-27):** "close to" for the
changed-site arm means `second.actions_used >= first.actions_used` — a lower bound, not a two-sided
band. This is deliberately asymmetric: nothing in CR3 promises the changed arm costs *no more* than
the first crawl (every screen having gained a control legitimately costs more), only that the skip
mechanism cannot silently make it cost *less*. A future criterion wanting an upper bound must name
one; none is adopted here.

**Disclosed capability limit: an incremental crawl cannot see a change BELOW a skipped screen**
(routine amendment, 2026-09-27, cycle-2 ruling on Q6, check A). Pruning being intended (see CR4's
ISS-3 ruling), a change is detected only on screens the crawl actually reaches. Reproduced: a persona
holding `/` and `/deep3.html`; `/deep3.html` is edited; crawl 2 matches and skips `/`, never clicks
through, and reports `/deep3.html` as `missing_unjudged` and nothing else. That is **honest** — the
crawl says it did not look — but it is **not a change detector**, and this criterion's own falsifiable
test exercises only the all-changed and none-changed arms, so nothing above promised the mixed case
either way. It is named here rather than left implicit. A future unit wanting "detect a deep change
cheaply" needs a mechanism this one does not have — most plausibly a navigation-only re-walk that does
not count as exploration — and it needs its own criterion and its own acceptance figure.

**Disclosed cost: the persona GROWS without bound against an unstable structural signature**
(routine amendment, 2026-09-27, cycle-2 ruling on Q7, check A — **accepted, not capped**). The ISS-2
closure makes `_merge` dedupe screens on `PersonaScreen.ident()` (key AND signature) instead of
`key()`, which is what stops a second real screen at one URL being dropped. The cost, measured
independently by check A: five crawls of one URL whose signature rotates every run leave stored
screens `1, 2, 3, 4, 5`, one `PersonaRevision` each, `changed=['/']` from crawl 2 on. PP2 forbids
pruning, so nothing reclaims it. It is **growth, not new noise** — the same input before the change
gave 1 stored screen and the identical `changed` every crawl, so the revision count is unchanged.
**Accepted** because `screen_identity.structural_signature` already excludes `in_row` elements
precisely so that list pages do not churn, so signatures are meant to be stable and an unstable one is
a fingerprinting or product defect rather than a normal case — and a screen you never learn about is
worse than a screen you learn about twice. Also verified: the **stable** multi-state case does not
grow or churn — three crawls of a `/` with two fixed signatures leave 2 stored screens and 1 revision,
and a state that *alternates* between crawls (stored `{A,B}`, seeing only `A`, then only `B`, then only
`A`) reports `changed=[]`, `missing=[]`, `missing_unjudged=[]` every time. A future unit wanting a
bound should take the option that keeps **one entry per key carrying a set of signatures** — it is
PP2-compatible, where capping stored states per key would need a PP2 amendment of its own.

### CR4 — Change tracking: new / changed / missing / broken, extending `_merge` past add-only PP2
`portal_persona.py::_merge` (its current behaviour is PP2, add-only: new screens/transitions/flows
are added, nothing existing is dropped or blanked) gains a real diff when a crawl runs against a
project with an existing persona. Every persona screen the crawl's frontier could have reached is
classified as exactly one of:
- **new** — discovered this crawl, absent from the stored persona;
- **changed** — matched by `key()` but the live `structural_signature` differs from the stored one;
- **missing** — present in the stored persona, in the reachable frontier, but not reached this
  crawl (a genuine absence, not a bound-truncated frontier — see CR5's interaction);
- **broken** — reached this crawl, but the visit produced an error/timeout/off-domain-refusal
  status that the prior stored screen did not carry;
- **missing_unjudged** (routine amendment, 2026-09-27, ruling on the T-165 build's Q2; **widened by
  the cycle-2 ruling on Q4, below**) — a fifth, disclosed category on `PersonaRevision`: stored keys
  not reached by a crawl **whose evidence cannot support a deletion claim**. Populated only in that
  case, with `missing` then empty for those keys. Silence about an unreached screen is the dishonesty
  CR5 exists to prevent — reporting nothing would lose the fact, and reporting `missing` would claim
  a certainty the crawl does not have. `describe()`'s prose and every consuming surface must treat
  this as a distinct, disclosed "not judged" state, never folded into `missing`'s count.
  **Two causes, not one (routine amendment, 2026-09-27, cycle-2 ruling on Q4):** a bound firing, and
  a CR3 skip. The original wording said only "a bound stopped it", and
  `PersonaRevision.missing_unjudged`'s field description said "BOUND-TRUNCATED"; both are superseded
  here. A CR3 skip is a decision NOT to look, so it is equally unable to testify that an unreached
  screen is gone — and, unlike a bound, a skip-truncated crawl still ends with
  `stop_reason: frontier empty`, which is why `describe()`'s prose MUST name both causes rather than
  blaming the frontier. The category is not split: its purpose is "a disclosed unknown, never a
  finding", and both causes produce exactly that.
- **`broken`'s "prior state" ruling** — ~~the most recent `PersonaRevision` that classified
  anything~~ **SUPERSEDED (routine amendment, 2026-09-27, cycle-2 ruling on Q8a).** `PersonaScreen`
  carries no status field (and PP2 forbids adding a mutable one that would need rewriting in place),
  so "the prior stored screen['s status]" is still read from the append-only revision history — that
  half stands, and it is PP2-safe. **What is superseded is *how* the history is read.** The cycle-1
  amendment said "the most recent `PersonaRevision` that classified anything, via its own
  `broken_screens` list", which is *precisely the implementation `ISS-t165-crawl-traversal-4` was
  filed against* — the checker wrote both, and the clause was the error. The ruling is now the
  issue's own `expected`: **replay the whole history in order — a revision's `broken_screens` adds a
  key, its `healthy_screens` removes it.** A revision that did not observe the screen changes
  nothing, which is the case ISS-4 was filed about. A plain union without the subtraction is NOT
  acceptable: it trades a stale re-alert for a silently missed relapse (broken → healed → genuinely
  broken again reports nothing, forever), which is the worse failure for a regression-catching tool.
  A future amendment introducing a status field on `PersonaScreen` would itself need its own PP2
  interaction reviewed, not be inferred from this clause.
- **`healthy_screens` is PROVENANCE, not a sixth category** (routine amendment, 2026-09-27, cycle-2
  ruling on Q8b). The subtraction above cannot be computed from the five categories: a screen a crawl
  reached and found healthy appears in **none** of them, so "never re-observed" and "observed
  healthy" are indistinguishable in the stored history. `PersonaRevision` therefore carries a sixth
  **field**, `healthy_screens`, and it is ratified as evidence-for-a-later-crawl rather than a
  finding. The five-category surface this criterion names is unchanged, and the separation is
  asserted, not assumed — verified at runtime by check A, cycle 2: `CATEGORIES` is exactly the five
  above, `counts()` returns exactly those five keys, `PROVENANCE == ("healthy_screens",)` is disjoint
  from `CATEGORIES`, and every list field on the model is accounted for by their union (no orphan).
  It records only keys a PRIOR revision called broken that this crawl **visited** and found healthy;
  a `SKIPPED_UNCHANGED` node is not an observation and never lands there. It is `default_factory=list`
  so a persona written before T-165 still loads with `[]` meaning "recorded no observation", never
  "observed everything healthy". **Disclosed cost:** `extra="forbid"` cuts forward as well as back —
  a persona written by a build carrying this field cannot be loaded by a build that predates it. That
  is a rollback hazard, not a load bug, and it is class-level (already true of `missing_unjudged` and
  the four category fields); it is recorded here so a rollback plan does not discover it late.

A `PersonaRevision` (PP3, already dated + non-blank-summary-enforced) records the counts of all
five categories by name — not merely a prose "what changed" sentence, a machine-checkable count per
category. PP2's existing add-only guarantee is **preserved, not replaced**, for any merge path this
criterion does not touch (a taught-flow merge from FlowSpec review, for instance): CR4 is additive
to `_merge`, scoped to crawl-sourced screen classification.

**~~Known gap~~ CLOSED, with a narrower residual (ISS-t165-crawl-traversal-2 → closed; residual
`ISS-t165-crawl-traversal-a8` open. Cycle-2 ruling, check A, 2026-09-27):** the original gap was that
two structurally distinct screens sharing a `url_template` (the X3/X14 SPA-toggle shape) collided onto
one `PersonaScreen.key()` and the losing screen was **invisible to this classification entirely**.
T-165 cycle 2 took the second of the two closures this note offered — the reachability lookup keeps
every same-key-different-signature screen (`PersonaScreen.ident()` for storage,
`persona_changes._reached` mapping a key to EVERY node reached at it,
`explore_incremental.PersonaIndex` holding every stored state at a key). `key()` is deliberately left
signature-free, because folding the signature in would destroy `changed`, which is *defined* as the
same key with a different signature. Verified by check A: a second state at a known URL now reads
`changed`, is stored beside the first (PP2 intact), and is recognised as unchanged on the next
incremental crawl.

**The residual, ratified as DISCLOSED and deferred (`ISS-t165-crawl-traversal-a8`, open).** `missing`
and `changed` still work at `key()` granularity, so if a product holds two (or n) states at one URL
and **one is genuinely deleted while another survives**, the deletion appears in no category at all —
and because `describe()` then returns `None`, `build_portal_persona`'s `if summary:` gate does not
fire, so **no `PersonaRevision` is written either**. Reproduced by check A on a full, exhausted,
non-incremental crawl: stored `{/: sig-base, /: sig-panel, /other.html: sig-other}`, crawl reaching
only `sig-base` and `/other.html` → every category empty, `describe() -> None`; the control (delete
`/other.html`, which has its own URL) correctly reports `missing_screens == ['/other.html']`.

Why this is disclosed rather than blocking, so a future unit does not relitigate it: (1) it is
**strictly narrower** than the gap it replaces — before the ISS-2 fix the second state was never
stored, so it was invisible in every direction, not only on deletion; (2) the implementation took the
closure **this note itself offered**, so the inadequacy was in the note, not the code. (3) **The
obvious fix is wrong, and this is the part that must not be lost.** The naive rule — "a key whose
reached signatures are a strict subset of its stored ones lost a state" — fires identically on a state
the crawl simply did not reach this run (typing off under X10-b, or the toggle never clicked), which
the stored evidence cannot distinguish from a removal. It would replace a silence with a **fabricated
deletion on every crawl of every two-state screen**, which is the exact trade CR5 exists to refuse.
A unit closing this must therefore record per-signature **reachability** evidence — not merely
per-signature presence — and carry its own falsifiable test for the "not reached this run" vs
"removed" distinction.

**Falsifiable (D-040's acceptance test (c)):** removing a fixture screen between two crawls of the
same project produces exactly one `missing` classification on the second crawl's `PersonaRevision`;
the same two crawls with nothing removed produce zero `missing` entries. A screen whose structure
was edited between crawls produces exactly one `changed` entry, naming the screen.

**~~Known gap~~ CLOSED at the CLAIM, not at the traversal (ISS-t165-crawl-traversal-3; cycle-2
ruling, check A, 2026-09-27).** The defect was real and it was D-040's own acceptance test (c)
failing on the mainline incremental path: `explore_incremental.skip_unchanged` short-circuits BEFORE
`explore_node.visit_node`, and `_enqueue` runs only inside `visit_node`'s click loop, so a skipped
screen's children are never discovered on that crawl. The queue then drained with
`frontier_exhausted=True` having represented almost nothing, and `persona_changes.classify()`
reported every unreached stored key as `missing` — 8 fabricated deletions on a byte-identical
9-screen site (reproduced live, headed Chromium, `tests/fixtures/deep_site`, cycle 1).

**Ruling on Q5: pruning is INTENDED; the dishonesty was the claim, and that is where the fix
belongs.** This note previously proposed two closures — seeding the frontier from `persona.keys`, or
treating a skipped node's prior stored transitions as discovery edges. **Both are withdrawn as
unimplementable from what is on disk**, verified by check A rather than taken on the build's word:
`PersonaScreen.url_template` is a *template* (`/user/{id}`), not a resolvable URL, so seeding means
the crawler navigating to a destination it never observed, which X1/X7 exist to forbid; and
`PersonaTransition` records `from_screen`/`to_screen` as screen **names**, not node ids or
signatures, so it cannot re-materialise a `ScreenNode` to enqueue. Both also cost real navigations —
`deep_site` spends 20 actions on 9 screens, so re-reaching 8 of them is ~40% — which puts CR3's own
≤10% acceptance figure out of reach. **D-040 asking for ≤10% is D-040 asking for the subtree to be
pruned.** The closure adopted is therefore `persona_changes._judged_exhausted(nodes,
frontier_exhausted)`: a crawl that skipped ANY screen may not testify that a screen is gone, so those
keys go to `missing_unjudged` and `missing` stays empty. The skip is read off the NODES, not off the
caller's flag, so forcing `frontier_exhausted=True` on a skipped crawl's graph cannot launder it.
Verified live by check A on the same pair: `missing = 0`, `missing_unjudged = 8`, where cycle 1 gave
`missing = 8`.

**`_judged_exhausted` is deliberately ALL-OR-NOTHING, and that is ratified (cycle-2 ruling, check
A).** Any single skip makes every unreached key unjudged, including keys the crawl explored past and
found genuinely gone. This is NOT the AT-100 shape of a category that can never fire, and the
distinction was measured rather than argued: (1) `missing` fires normally on a full, non-incremental
crawl — the mode in which a deletion claim is honest — and D-040(c)'s first half is asserted on that
path; (2) when the predicate suppresses `missing`, the fact is still **disclosed**, never dropped —
a crawl that skips one screen and fully explores a subtree containing a real deletion reports that
deletion in `missing_unjudged`, with the cause named in `stop_reason` and in `describe()`'s prose
(measured: stored `/keep` skipped, `/gone` deleted, `/seen` reached → `missing_screens []`,
`missing_unjudged ['/gone']`). The coarseness costs **precision**, never **honesty**, which is the
correct direction for this contract.

**A per-subtree refinement is a FUTURE criterion, not a defect against this one.** It needs a
parent→child map at signature granularity. The persona cannot supply one (names, not keys — above).
The only source that could is a prior crawl's own **edge set** in the store, which is a mechanism
this unit does not have and D-040 did not scope. A unit wanting per-subtree judging must name that
mechanism and carry its own falsifiable test; until then the coarse predicate stands.

### CR5 — Completeness stays honest under the new machinery (frontier-completeness, carried forward)
"Complete" still means the actionable frontier was exhausted, or a named safety/time/action/depth
bound stopped it — carried forward verbatim from T-165's own goal-task note and from `explore.md`
X4/X16/X18, which this contract does not amend. This criterion is what stops the new machinery
from quietly breaking that honesty:
- A `hybrid`-strategy crawl that stops on a bound still names that bound in `stop_reason`, exactly
  as X4 already requires for `bfs` — `hybrid` is not a second code path that forgets to set it.
- A CR3 skip decision is recorded as its own status (e.g. "skipped — unchanged since <revision>"),
  **never** folded into "frontier empty" / `COMPLETED` as if the skipped node had been explored —
  a persona-seeded incremental crawl that skips 90% of the portal must not read as having explored
  90% of the portal.
- Every denied, skipped, and unreached control remains visible on every surface X16 already lists
  (crawl page, crawls table, CLI line, workbook, `crawl.json`) — this contract adds skip-for-
  unchanged as a new named category alongside `DENIED_POLICY`/`SKIPPED_UNNAMED`/`OFF_DOMAIN_REFUSED`,
  it does not let a skip disappear from those surfaces.

**Falsifiable:** a bound-stopped `hybrid` crawl's `stop_reason` names the bound (same test shape as
`explore.md` X18's own verify); a fixture crawl with a mix of persona-skipped and freshly-explored
nodes shows every skipped node counted and labelled on the crawl report, and the report's headline
completeness language does not claim full exploration when skips occurred.

### CR6 — DOM-driven and deterministic, still (X12 carried forward, as amended by D-118)
Strategy selection (`bfs` vs `hybrid`), the depth-first candidate ordering within `hybrid`, and the
CR3 skip decision are all pure functions of frontier/persona state on disk — **no provider, no
model, anywhere in the traversal and incremental modules this unit adds** (core-invariants C8). A
`hybrid` crawl completes with `provider=mock`, the same discipline `explore.md` X12 holds `bfs` to.
**Amended 2026-10-29 (D-118):** the traversal strategy, the CR3 skip decision and the depth bound
remain provider-free. The one place a model enters is ordering the ORDINARY (non-destructive)
candidate controls of a single screen through `stages/explore_guidance.py` (`crawl-guidance.md` G1,
G2, G9), called by `explore_traversal.ordered_candidates` only when per-project guidance is ON. The
model never chooses a traversal step, never causes a skip (a guided order cannot make CR3 skip or
re-visit a screen it would not otherwise), never reorders the destructive tail (D-040) and never
adds a control. With guidance off, behaviour and the falsifier below are exactly as before.

**Falsifiable:** `grep -rn` for a `Provider`/vendor-SDK import in the traversal/incremental modules
this unit adds returns nothing, **with one named exception: `stages/explore_guidance.py` is the sole
module under `stages/explore_*` permitted to import `Provider`** (and `explore_traversal.py` may
import only that module's ordering function, never a provider type); a `hybrid` crawl run with
`provider=mock` completes and its strategy/skip decisions are identical to a run with a real
provider configured but never called, **and identical to a guided run whose fake provider answers
garbage** (same assertion shape as `explore.md` X12's verify).

### CR7 — Nothing here widens the safety matrix, deny-list, or typing rules (X5/X6/X10 untouched)
This is a traversal and bookkeeping contract. `write_policy` enforcement (X5), the never-click
session-ending guard (X6), and the X10/X10-b typing gate are byte-unchanged by anything in CR1-CR6.
CR2's replay is explicitly bound by this: it may only replay a fill the crawl already performed once
under X10-b's four conditions — it can never originate a new typed value, a new target, or fire
under a policy/approval combination the original action itself would have been refused under.

**Falsifiable:** a fixture where the discovering edge's typing would be refused under the CURRENT
run's policy (e.g. `READ_ONLY`, or `synthetic_typing=False`) never has its form replayed — CR2's
"read the recorded values" path still passes through the same X5/X10-b gate a fresh type would, not
a bypass that only checks "was this typed once before."

**~~Known gap~~ CLOSED (ISS-t165-crawl-traversal-1; cycle-2 ruling, check A, 2026-09-27).** X7 ("the
host is re-checked after EVERY action") is byte-unchanged and still in force per this contract's own
"Relationship to explore.md" section, and `explore_replay` now honours it: `perform()` and
`replay_fills()` both call `check_destination(rt.project, rt.session.current_url())` after **every**
issued action — literally every re-issued fill, not only the final click, because a fill whose
`onchange` auto-submits can leave the domain before any click is replayed — and a `NavigationRefused`
is recorded exactly as `explore_node.try_action` records one (a NAVIGATION issue plus an
`OFF_DOMAIN_REFUSED` edge, via `_refusal_of`), with the reason returned upward so `_replay_discovery`
reports it rather than success. Falsified by check A: gutting `_landed_on_domain` to `return None`
reddens `test_a_replay_that_lands_off_domain_is_refused_and_recorded` on both parametrized exits.

**A required companion clause, learned the hard way (routine amendment, 2026-09-27, cycle-2 ruling on
Q9.2, check A): every X7 re-check must be preceded by a `settle()`.** `BrowserSession.fill()` is a
bare Playwright `.fill()` that does not wait for a JS-triggered navigation, so an unsettled
`current_url()` can still return the old, on-domain URL and the check passes **for free** — in
precisely the auto-submitting-fill case it exists to catch. A guard that cannot fail is not a guard.
`replay_fills` shipped without the settle in the first cycle-2 commit and every test passed, because
the fake session returned a constant URL. The fake now models navigation asynchronously (an action
only *schedules* the new URL; `current_url()` changes only after `settle()`), and deleting the settle
reddens a test. The general rule this contract adopts: **a fake that cannot be wrong about timing
cannot test a timing-dependent guard**, so any future X7 call site added under this contract must have
both the settle and a fake that can distinguish the ordering.

## Explicit no-fire list (do not raise these as findings)

- **Back-navigation replay "not built"** — it already exists (`stages/explore_return.py::return_to`
  + `_replay_discovery`, AT-227, shipped under `explore.md`). Only the **fill-value gap** (CR2) is
  new; raising "build replay from scratch" is wrong and ignores the existing mechanism.
- **Permission-surface coverage** (every reachable control exercised or blocked-with-reason) — split
  to **T-171** by D-040, not this contract. A finding that this crawl doesn't yet report coverage of
  every permission the role has belongs against `qa/contracts/permission-surface.md` (future, T-171),
  not here.
- **First-party API/network assertions** — split to **T-170** by D-040
  (`qa/contracts/network-assertions.md`), not this contract.
- **Vendoring Crawljax, Stagehand, Scrapling, Crawlee, or Playwright Test Agents as a dependency** —
  every one of them is a verified idea-PORT (Apache-2.0/MIT/BSD, no code copied) or an explicit
  AVOID (`crawl-reuse-2026-09.md`'s own verdict table); importing any of them as a library, or a JVM
  dependency for Crawljax specifically, is a defect against this contract, not a feature.
- **Locator self-healing / element relocation across a redesign** (Scrapling's structural-profile
  idea) — explicitly parked in `crawl-reuse-2026-09.md` §2 for D-031's future healer, not T-165.
- **Resuming an interrupted crawl mid-run** — still not built; unchanged from `explore.md`'s own
  no-fire list, this contract does not claim it either.
- **Relaxing `READ_ONLY`'s form-submit denial, or widening the default bounds** — both explicitly
  declined in `explore.md`'s 2026-09-16 amendment log entry and untouched here; CR7 restates why.
- **Persona merges for non-crawl material** (a taught-flow review merge, for instance) — PP1-PP6's
  existing add-only behaviour for those paths is unchanged; CR4 only extends the crawl-sourced
  screen-classification path.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_explore_completeness.py tests/test_explore_traversal.py
tests/test_persona_changes.py` (bare, no CLI `-q`, AT-503) + `uv run ruff check src tests scripts` +
`uv run autotester doctor`, all exit 0; each CR criterion carries a capability-coverage row with a
single-hunk falsifying edit reproduced green→red-for-the-named-reason→revert→green. Being a CRITICAL
unit, T-165 additionally requires the dual-check protocol (two independent verdicts,
`qa/verdicts/t165-*.md` and `.b.md`) before it may close. File/function caps (core-invariants C2)
apply to every new or extended module; `explore_node.py`, `explore_return.py`, and
`portal_persona.py` are all near their existing caps per prior amendment history, so new logic
belongs in a stated-reason new module (C3) rather than pushed into a file already at budget.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from D-040 (Approved-by Umesh — "go
  on" to `qa/gates/t165-d039-traversal-scope.md`) and `docs/research/crawl-reuse-2026-09.md`.
  `qa/feedback-inbox.md` 2026-09-23T07:30 (the source demand) is folded here in full — its DFS,
  schema/flow persistence, and change-tracking asks map to CR1, CR3/CR4, and CR4 respectively; its
  "permission = testing surface" ask is explicitly routed to T-171 (not this contract) per D-040.
  No prior draft existed; nothing amended.
- 2026-09-27 · routine · check B of T-165's dual check (D-040) ruled on the three contract-shaped
  questions the build filed (`qa/feedback-inbox.md` 2026-09-27, Q1-Q3): CR4 formalises
  `missing_unjudged` as a fifth disclosed category and ratifies reading `broken`'s prior state from
  the append-only revision history (Q1/Q2); CR3's changed-site "close to" is ruled as the lower
  bound `second.actions_used >= first.actions_used`, not a two-sided band (Q3). Also recorded two
  **open, not-ratified** gaps the same check found and filed as blocking issues
  (`ISS-t165-crawl-traversal-1`, `-2`): CR7 does not yet carry X7's host-recheck into the replay
  path, and CR4's classification silently drops one of two screens sharing a `url_template` (a
  `PersonaScreen.key()` collision). Still DRAFT — this contract goes ACTIVE only on T-165's first
  PASS, which this check did not grant.
- 2026-09-27 · routine · check A of T-165's dual check (D-040), independently, ratified the same
  Q1/Q2/Q3 readings (converged before reading check B's edit to this file) and found a third,
  distinct blocking gap: CR4's own `missing`/D-040(c) acceptance test fails on the ordinary
  incremental path because `skip_unchanged` short-circuits before the frontier can enqueue a
  skipped node's children, so an incremental crawl can represent only a handful of nodes yet still
  read `frontier_exhausted=True`, reporting the rest of a byte-identical, untouched portal as
  `missing`. Filed and documented under CR4 as `ISS-t165-crawl-traversal-3`, open, not ratified.
  Still DRAFT — this check also did not grant PASS.
- 2026-09-27 · routine · **check A of T-165's dual check, cycle 2 — PASS from this check, and the six
  contract rulings it authorises.** Still **DRAFT**: the flip to ACTIVE is the unit's first PASS, and a
  D-040 dual check has not passed until check B concurs, so check A deliberately did not flip it.
  Rulings, each from evidence check A produced itself (`qa/verdicts/t165-crawl-traversal.md`,
  "CHECK A — cycle 2"): **Q4** — `missing_unjudged` names two causes, a bound AND a CR3 skip; the
  "BOUND-TRUNCATED" wording in the criterion and in the schema field description is superseded.
  **Q5** — pruning a skipped subtree is INTENDED (D-040's ≤10% figure requires it); both closures this
  contract previously offered for ISS-3 are withdrawn as unimplementable from stored data
  (`url_template` is a template, `PersonaTransition` holds screen names), and the fix at the CLAIM
  (`_judged_exhausted`) is adopted. Its all-or-nothing coarseness is ratified as costing precision but
  never honesty — `missing` still fires on a full crawl, and a suppressed deletion still surfaces in
  `missing_unjudged` with the cause named in `stop_reason`; a per-subtree predicate needs a prior
  crawl's edge set and is a future criterion. **Q6** — the change-below-a-skip limit is named in CR3 as
  a disclosed capability limit. **Q7** — the persona growth against an unstable signature is accepted
  and named in CR3 with its measurement, with "one entry per key carrying a set of signatures" recorded
  as the preferred PP2-compatible closure. **Q8a** — CR4's "`broken`'s prior state" clause is
  SUPERSEDED: the nearest-revision reading it prescribed was the implementation
  `ISS-t165-crawl-traversal-4` was filed against, so the ruling is now the issue's own `expected`, a
  full in-order history replay with `healthy_screens` subtracting. **Q8b** — `healthy_screens` is
  RATIFIED as provenance, not a sixth category, with the separation verified at runtime and the
  `extra="forbid"` forward-rollback hazard disclosed. **Q9.2** is folded into CR7 as a standing
  companion clause: every X7 re-check needs a `settle()` in front of it, and a fake that cannot be
  wrong about timing cannot test a timing-dependent guard. Gaps CLOSED this cycle:
  `ISS-t165-crawl-traversal-1` (CR7, X7 on the replay path), `-2`'s storage/reachability half, and
  `-3` (CR4/D-040(c) on the incremental path) — each re-falsified independently by check A, and `-3`
  re-verified by check A's own headed-Chromium walk (`missing 0`, `missing_unjudged 8`, where cycle 1
  gave `missing 8`). One gap OPENED: `ISS-t165-crawl-traversal-a8`, the narrowed ISS-2 residual — a
  genuinely deleted second state at a shared URL is reported in no category and writes no revision at
  all. Recorded under CR4 **with the analysis that rules out the naive closure**, because the obvious
  subset rule would replace that silence with a fabricated deletion on every crawl of every two-state
  screen.
- 2026-10-29 · CRITICAL amendment · **CR6 amended (rewritten in place) under D-118** (Approved-by
  Umesh, chat 2026-10-29). CR6 said no model anywhere in the unit; it now keeps that for strategy
  selection, the CR3 skip decision and depth ordering, and permits exactly one model-assisted seam:
  ordering one screen's ordinary candidate controls via `explore_guidance.py`, default OFF, fully
  specified by `qa/contracts/crawl-guidance.md`. The CR6 grep falsifier is scoped (one named module
  exception) rather than deleted, and gains a guided-with-garbage-answer equivalence assertion.
  CR1-CR5 and CR7 are byte-unchanged; X5/X6/X10/X10-b remain untouched (CR7).
