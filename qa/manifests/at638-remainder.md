# Manifest — at638-remainder

**Contract:** none owned by this unit — `qa/contracts/permission-surface.md`,
`qa/contracts/eval-compiler.md`, `qa/contracts/release-regression.md` and
`qa/contracts/damage-control-report.md` do not exist yet; they are proposed, checker-owned
deliverables this unit files criteria for.
**Issue:** AT-638 (`high`, filed 2026-09-27, checker-sweep) — "Five north-star capabilities in
`.goal/goal.json` have ZERO checkable contract criteria." `t150-track-c-governance` already
answered the Track C portion (T-150..T-155). **This unit answers the remaining four: T-171, T-166,
T-167, T-168.**
**Date:** 2026-09-27
**Fix cycle:** 1 of max 3
**Dual check:** no
**Persona walk:** skip — governance only. No screen, route, component, schema, or stage changed;
nothing a rendered page reads is different.
**Executor:** a `/maker` **build subagent, in its own git worktree**
(`D:\autoTesting\.claude\worktrees\agent-a94b2eb74f09f9a73`, branch `wave/at638-remainder`),
dispatched by the maker orchestrator. This is the accurate statement of who did the work — stated
explicitly because the sibling unit `t150-track-c-governance`'s own manifest first mis-described
its Executor as "the maker orchestrator, inline" and the orchestrator had to correct it before
check; in a pair whose whole point is that the record says who did what, getting a manifest's own
authorship wrong is a defect in the evidence, not a typo, and this manifest does not repeat it.

## What changed

- `qa/feedback-inbox.md` — one dated entry appended (2026-09-27, "maker (at638-remainder,
  T-166/T-167/T-168/T-171 governance)"), filing four groups of **proposed** contract criteria for
  the checker:
  - **`qa/contracts/permission-surface.md` — PS1–PS4**, covering T-171 (permission-surface
    coverage, D-040).
  - **`qa/contracts/eval-compiler.md` — EC1–EC4**, covering T-166 (traceable eval compiler +
    knowledge graph, D-041 + the AT-586 scenario-variant extend).
  - **`qa/contracts/release-regression.md` — RR1–RR5**, covering T-167 (commit/release-triggered
    regression on LangGraph 1.x, D-041).
  - **`qa/contracts/damage-control-report.md` — DC1–DC4**, covering T-168 (unified damage-control
    report — no authorizing decision found for this one at all; see "Authorization finding" below).
  Each criterion is tagged with its authority source (`[D-040]` / `[D-041]` / a specific existing
  contract cross-reference) or `[maker]` for my own judgement, matching the convention
  `ai-target.md`/`adversarial.md` set on the sibling unit. No other file was touched.
- `qa/manifests/at638-remainder.md` — this file (new).

## Authorization finding — stated plainly, not resolved by this unit

Every checker-authored contract file in this repo's history has an explicit `docs/DECISIONS.md`
`Changes-authorized` line naming it before the checker wrote it (`catalog.md` → D-039;
`crawl-traversal.md` + `network-assertions.md` → D-040; `run-trace.md`/`parallel-run.md`/
`cli-mcp.md`/`skills.md`/`script-replay.md`/`agent-fallback.md`/`failure-bundle.md` → D-041;
`agent-layer.md` → D-042; `ai-target.md` + `adversarial.md` → D-017/D-018). I read D-040 and D-041
in full, not paraphrased:

- **D-040's `Changes-authorized`** names only `qa/contracts/crawl-traversal.md` and
  `qa/contracts/network-assertions.md`. T-171 is registered in `.goal/goal.json` by the same
  decision, but **no contract file is named for it.** `crawl-traversal.md` line 164 forward-refers
  to "`qa/contracts/permission-surface.md` (future, T-171)" — a naming hint left by the checker who
  wrote that file, not an authorization from Umesh.
- **D-041's `Changes-authorized`** names "New checker-authored DRAFT contracts under
  `qa/contracts/`, as listed in Result" — and Result's list is `run-trace.md, parallel-run.md,
  cli-mcp.md, skills.md, script-replay.md, agent-fallback.md, failure-bundle.md` (T-172–T-178
  only). T-166 and T-167 each get "a note" added to their `.goal/goal.json` rows — **no contract
  file is named for either.**
- **T-168 is not mentioned by D-040 or D-041 at all.** It has existed in `.goal/goal.json` since
  2026-09-10, before either decision. No decision entry authorizes anything about it.

Per this unit's brief, **I did not append a `docs/DECISIONS.md` entry to manufacture this
authorization** — that would be exactly the "no gate file opened" shortcut the brief warned
against, and it is not a build subagent's call to make on Umesh's behalf. This is a real,
previously-undetected gap in this repo's own governance practice, not a technicality: 5 of 5 prior
contract files had explicit authorization, and these four don't. I am filing the criteria anyway
(the brief asks for that regardless of this finding), but the checker should not treat this
filing as sufficient authority to go straight to authoring the four files — that step, on this
repo's own established practice, wants a decisions-log entry first.

## Why this shape

`qa/contracts/*.md` is checker-owned territory (`CLAUDE.md` maker-checker discipline block:
"Ground truth lives in `qa/contracts/` — maker never edits it"); my job is to file proposed
criteria into `qa/feedback-inbox.md`, matching the shape `t150-track-c-governance`'s own entry used
(pattern statement, individually-tagged criteria with a Landing note and a Verify, a no-fire list,
an "applies next" line). I read `qa/contracts/ai-target.md` and `qa/contracts/adversarial.md` in
full before writing anything, per this unit's brief, to match the conventions their checker just
set: the **Landing note** on every forward-declared criterion (closing the AT-218 vacuous-guard
trap a `grep` against a not-yet-existing file would otherwise reopen), **authority tagging** so an
authorized claim is never fused with my own extension in one criterion, and **no second ground
truth for one concept** — before proposing anything I grepped `qa/contracts/coverage.md`,
`report-export.md`, `orchestrator.md`, `consent.md`, `crawl-traversal.md`, `network-assertions.md`,
`catalog.md`, `expand.md` and `grade.md` for existing criteria that already cover a claim I was
about to make, and cross-referenced rather than duplicated wherever one did (see "Cross-references
made" below).

## Cross-references made instead of duplicate criteria

- **PS1/PS3** (T-171, permission-surface) defer to `consent.md` CN1/CN9 (the approval gate) and
  `coverage.md` V7(a)-(c) (the controls_discovered/controls_exercised/reason-tallied book-balance
  that already computes exactly the "every reachable control exercised or blocked-with-reason"
  claim D-040 asks for) rather than restating either mechanism.
- **EC1** (T-166, knowledge graph) defers to `schema/portal_persona.py`'s existing
  `PersonaScreen`/`PersonaTransition` models — D-041 itself says the KG **is** that graph,
  extended, not a new one — mirroring `ai-target.md` AI4's Catalog-reuse precedent (one concept,
  one place, C3).
- **RR1/RR2** (T-167, release regression) defer to `orchestrator.md` OR2/OR4 (resume-without-redo,
  crash-honesty) and `consent.md` CN1/CN5/CN6/CN9 (the approval gate `interrupt()` layers on top
  of, not replaces) rather than re-deriving either.
- **RR4** is explicitly named as the third instance of the "exerciser never grades" pattern
  (`ai-target.md` AI5, `adversarial.md` AD5, now `release-regression.md` RR4) — same shape, new
  caller, not a new derivation.
- **DC1/DC2/DC4** (T-168, unified report) defer to `coverage.md` V7(b)-(c) and
  `crawl-traversal.md` CR5 (blocked/unvisited honesty), `network-assertions.md` NA1 (API-failure
  evidence, **already ACTIVE** since T-170's checker PASS), `report-export.md` RE1/RE5 (reads-only,
  no-secrets) — T-168's own criteria (DC1-DC4) require these existing guarantees to survive being
  re-rendered on a new, unified surface; they do not re-derive the guarantees themselves.

## How I chose the id prefixes

Checked via `grep -ohE '^### [A-Z]+[0-9]+' qa/contracts/*.md`, which today returns `AD AI AL B C CN
CR D E F G I K L LC LS ML O P R RE RP U V VL X` (`AI`/`AD` now taken since
`t150-track-c-governance`'s checker PASS). I chose **PS** (permission-surface), **EC**
(eval-compiler), **RR** (release-regression), **DC** (damage-control-report) — all four free, and
each reads unambiguously as its own capability rather than colliding with an `AT-NNN` issue id or
an existing contract prefix. The checker may pick different prefixes when it actually authors the
files; this is a proposal, not a claim of naming authority.

## What this unit cannot do, stated plainly

- **This unit cannot create the four contract files itself.** That would be the maker writing its
  own ground truth — the exact failure mode `t150-track-c-governance`'s own manifest named for
  Track C, restated here for these four.
- **This unit cannot resolve the authorization gap it found.** Writing a `docs/DECISIONS.md` entry
  naming these four files as checker-owned deliverables is Umesh's or the checker's call, not
  mine to manufacture. See "Authorization finding" above.
- **No code, no tests, no scripts.** Zero lines of `src/`, `tests/`, or `scripts/` changed.
  `qa/contracts/` itself was not touched — only `qa/feedback-inbox.md` and this manifest.
- **No network traffic of any kind.** Every landing-note fact below was verified with a local
  `grep`/`ls`/`pytest`/`ruff`/`doctor` command against this worktree; nothing left the machine.
- **AT-638 is fully answered by this unit plus its sibling — but flipping it is the checker's
  call, not mine.** AT-638 names five ungoverned capabilities: Track C (T-150..T-155, answered by
  `t150-track-c-governance`) and T-166/T-167/T-168/T-171 (answered by this unit). Between the two
  units, criteria now exist for all five. I am stating this plainly, per this unit's brief, but I
  am not marking AT-638 `fixed` in `qa/issues.jsonl` myself — `qa/issues.jsonl` is checker
  territory and only the checker verifies a fix before closing it.

## How to verify (commands + expected)

- `uv run ruff check src tests scripts` → expect exit 0, `All checks passed!` (no source changed).
- `uv run autotester doctor` → expect exit 0, `doctor: clean` (this unit touched no `docs/` file,
  so the router-row/Purpose/Open-me-when check has nothing new to verify against).
- **No pytest run** — explicitly, not left unexplained: this unit adds and changes no code, so
  there is nothing for the test suite to exercise beyond what the two commands above already cover.
- `git status --short` → expect exactly two paths: `qa/feedback-inbox.md` (modified) and
  `qa/manifests/at638-remainder.md` (new, untracked until committed).

## Actual outputs (pasted, real — this worktree, 2026-09-27)

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(Both re-run once before this filing, matched above; `git status --short` output is pasted in the
commit step below since it reflects the final state including this manifest.)

## Landing-note facts verified today (2026-09-27), pasted, not asserted

```
$ grep -rln "permission_surface|PermissionSurface" src/
(no output — exit 1, no matches)

$ grep -rln "knowledge_graph|KnowledgeGraph|kg_node|KGNode" src/
(no output — exit 1, no matches)

$ grep -n "langgraph" pyproject.toml
(no output — exit 1, not a declared dependency)

$ grep -rln "langgraph|interrupt(" src/
(no output — exit 1, no matches)

$ grep -rln "damage_control|DamageControl|unified_report" src/
(no output — exit 1, no matches)

$ ls src/autotester/stages/orchestrate.py
src/autotester/stages/orchestrate.py

$ ls src/autotester/agents/
ls: cannot access 'src/autotester/agents/': No such file or directory (exit 2)
```

These confirm every criterion proposed needed a **Landing note** (none of the four capabilities has
any code today), and specifically confirm the RR-series disclosed gap: `src/autotester/agents/`
(T-179, Deep Agents) does not exist, consistent with `.goal/goal.json`/`docs/plan.md` not listing
T-179 as a T-167 dependency even though D-042's prose mentions "the lead agent" running on T-167's
checkpoints.

## Capability coverage

Not applicable in the falsification-per-claim sense — `core-invariants.md`'s mutation duty applies
to a unit that **adds or rewrites a test**; this unit adds none. The deliverable is a filed
proposal; its correctness is judged by the checker reading PS/EC/RR/DC against D-040/D-041 and the
ground-truth files named above, not by a red/green test pair. Stating this explicitly rather than
fabricating a falsification table for prose.

## Gaps stated, not hidden

- **These are proposals, not contracts.** The checker may accept, reword, split, drop, or add to
  any of PS1–PS4 / EC1–EC4 / RR1–RR5 / DC1–DC4. Nothing here binds anyone until the checker writes
  the actual contract files — and per the authorization finding above, that step itself may first
  need a decisions-log entry this unit does not supply.
- **PS4 and DC3 are my own additions, not derivations** — flagged individually in the inbox entry
  (a no-second-coverage-number guard for T-171, and the "genuinely unified, not four files"
  requirement for T-168). The checker or Umesh may judge either as reasonable or as scope beyond
  what D-040/the goal-task note actually asks for.
- **RR3's "trusted baseline" criterion names a requirement for a rule to exist, not the rule
  itself** — D-041/goal.json state the property ("compare against the last trusted baseline")
  without defining what makes a baseline trusted; I did not invent that definition on their behalf.
- **The RR/D-042 tension is disclosed, not resolved.** D-042 says T-167 "runs the lead agent on
  LangGraph checkpoints" (tying it to T-179, Deep Agents), while `.goal/goal.json`'s own T-167
  `deps` and `docs/plan.md`'s dependency column both omit T-179. I wrote no criterion assuming
  either reading is correct — flagged explicitly in the inbox entry for the checker or Umesh.
- **No ground-truth contradiction found beyond the two disclosed above** (the authorization gap
  and the RR/D-042 tension). `docs/plan.md`, `docs/spec.md` (R21/R22/R27/R30/R31), `target.md`,
  and `.goal/goal.json`'s T-166/T-167/T-168/T-171 rows were all read and are internally consistent
  with each other and with this unit's brief.

## Live browser evidence

Not UI-touching — no surface changed. `qa/feedback-inbox.md` and this manifest are the only paths
touched; neither renders anywhere in the product.

## Status: cycle-1 FAIL; branch merged to master 2026-09-28 (aa368f8d); gate qa/gates/at638-four-contract-files-authorization.md ANSWERED 2026-09-27 (D-054); the four contracts now exist (c6f31f50)

## Close-out (maker orchestrator, 2026-09-27)

Verdict: `qa/verdicts/at638-remainder.md`, cycle 1, **FAIL** — copied onto `master` so the record is
visible without merging a failed branch. Gate: `qa/gates/at638-four-contract-files-authorization.md`,
also on `master`. Ledger: `ISS-at638-remainder-1` (high, `approval-required`).

**This FAIL is not a defect in this unit's work.** The checker judged **all 17 criteria sound and
buildable as worded**, reproduced every pasted grep exactly (all exit 1/2 as claimed, including
`ls src/autotester/agents/` exiting 2), confirmed the diff touched exactly the two claimed files with
zero deletions, and verified `schema/portal_persona.py` really carries the `PersonaScreen` /
`PersonaTransition` / `PersonaRevision` classes EC1's knowledge-graph extension needs. It failed the
unit solely on this unit's **own** finding: no `docs/DECISIONS.md` entry authorizes the four contract
files — and the checker independently re-derived that from the decision text rather than trusting
this manifest's paste.

**No cycle 2.** A fix cycle exists for a maker defect; the blocker here is a decision only Umesh can
make, and `Approved-by:` cannot be self-granted. Spending a cycle would be theatre. The unit resumes
the moment the gate is answered — and if answered as option A, the criteria need no re-review.

**Corrections the close-out owes this unit:**

- **The orchestrator's dispatch was wrong about PS2.** I told the checker PS2
  (destructive-actions-last) was a freely-arguable `[maker]` addition. It is not — this unit tagged
  it `[D-040 verbatim]` and it matches D-040's text exactly. The genuinely arguable ones are PS4,
  DC3 and RR3, all three reviewed and accepted as low-risk. The filing was right; my summary of it
  was wrong.
- **The Executor line held up.** This unit stated its authorship accurately and explicitly cited the
  sibling's mis-description rather than repeating it. Recorded because the pair's value depends on
  the record naming who did what, and this one did.

**Left open, not silently absorbed:** RR2's `consent.md` CN5/CN6 tag is overstated relative to its
own `Verify` (checker, low — not a ledger row, since the file does not exist yet); the D-042 / T-179
dependency contradiction sits inside T-167's own `.goal/goal.json` `note` field and both this unit
and the checker deliberately left it disclosed; and the checker **did not complete `uv run pytest`**,
accepting ruff + doctor + the diff-stat on the grounds that the diff touches zero `src/` or `tests/`
files. That reasoning is sound for a contracts-only unit and it disclosed it rather than claiming a
green run, but it is a gap in the evidence and is recorded as one.

**AT-638 stays `open`.** Track C is genuinely closed by the sibling unit's PASS; these four
capabilities have reviewed *proposals*, which is not the same as checkable criteria.

## Landing note (maker orchestrator, 2026-09-28) — what "NOT merged" now means

The branch `wave/at638-remainder` **was merged into `master`** on 2026-09-28. That does not
reverse the FAIL above, and the status line stays as written, because what merged is the
**record**, not the work:

- `qa/manifests/at638-remainder.md` (this file) — previously **absent from `master`**. The verdict
  had been copied over on its own, so `master` carried a cycle-1 FAIL verdict with no manifest to
  explain it: the AT-648-shaped dangling handshake, in reverse.
- `qa/feedback-inbox.md` — the ~200-line criteria filing (PS1-PS4 for T-171, EC1-EC4 for T-166,
  RR1-RR5 for T-167, DC1-DC4 for T-168) existed **only on the branch**. Criteria filed where the
  checker cannot see them are not filed.
- `qa/verdicts/at638-remainder.md` — gained the branch's ADDENDUM (the completed full run, and the
  two undisclosed pre-existing `test_goal_done_checks.py` failures it surfaced).

**Nothing under `qa/contracts/` was created or changed by the merge** — verified after resolving,
not assumed. `permission-surface.md`, `eval-compiler.md`, `release-regression.md` and
`damage-control-report.md` still do not exist, which is exactly the state the FAIL describes. Both
merge conflicts were **additive** (two independent entries appended at the same point) and were
resolved by keeping **both** sides; nothing was dropped.

**Why it was merged now:** `T-171` was dispatched to a build subagent earlier this tick against
`coverage.md` V7/V9. PS1-PS4 are that unit's filed criteria and were invisible on `master`. A unit
building without the criteria already written for it is the failure this filing existed to prevent.

The gate `qa/gates/at638-four-contract-files-authorization.md` is still open and still Umesh's.
