# Contract — eval-compiler (the knowledge graph, and the evals compiled from it)

**Status:** **ACTIVE** (authored by /checker 2026-09-28 under **D-054**, `Approved-by: Umesh`).
**ACTIVE since 2026-10-11:** T-166's first checker PASS is `qa/verdicts/t166-eval-compiler.md` (cycle 0,
`Verdict: PASS`, commit c42dd8f9, EC1-EC5).
**Feature:** T-166 — extend the portal-persona graph into the full knowledge graph
(screen · control · flow · scenario · case · verdict · API · release) and compile evals from it.
**Code:** does not exist yet (T-166 `pending`). The base it extends is
`src/autotester/schema/portal_persona.py` (`PersonaScreen` / `PersonaTransition`), shipped under T-164.
**Tests:** none yet.
**Grounding:** D-041 (names EC1 verbatim; rejects a graph DB) · D-002 (JSON on the filestore) ·
AT-586 (structured scenario variants) · AT-638 · `grade.md` · `expand.md` · `portal-persona.md`.

## Why it exists

This is the capability Umesh keeps asking for in plain words: *"pura platform explore karke poora
knowledge graph banata hai"*. The pieces are already built and verified — the crawler, screen
identity, the persona graph with dated revisions — and what is missing is the graph that ties
screens, flows, cases and verdicts together so evals can be **compiled** from it instead of written
by hand.

Two failure modes this contract exists to refuse. First, a **second** graph: a new schema alongside
`portal_persona.py` would give one concept two homes and make both untrustworthy. Second, an eval
that cannot say where it came from — a test whose provenance is prose is a test nobody can maintain.

## Criteria

### EC1 — The knowledge graph is the existing persona graph EXTENDED, never a second schema [D-041 verbatim]

`schema/portal_persona.py`'s `PersonaScreen` / `PersonaTransition` family gains typed nodes and edges
for screen, control, flow, scenario, case, verdict, API and release. It stays **JSON on the
filestore** (D-002). **No graph database. No GraphRAG.** Both are explicitly rejected by D-041.

Same C3 "one concept, one place" discipline as `ai-target.md` AI4's Catalog-reuse precedent.

**Verify:** `grep -rn "class.*Graph" src/autotester/schema/` resolves to the extended
`portal_persona.py` family only — no second graph-shaped model anywhere. And
`grep -rniE "neo4j|networkx|graph[_-]?db" pyproject.toml src/` returns nothing.

### EC2 — Every generated eval traces to its source through a real graph edge, not free text

A `Case` with no resolvable source edge **is not produced**. Provenance is structural, not a
sentence in a description field.

**Verify:** a fixture flow's generated cases each resolve a graph edge to a real screen/flow node on
disk. Removing the edge-population step fails a test asserting every case carries a non-null trace.

### EC3 — A component PASS can never hide a workflow failure

An aggregate or summary view must not report an overall PASS for a multi-step workflow whose
**end-to-end** assertion failed while each individual component step passed. The rollup is
**workflow-first**, never "AND of the components".

This one is genuinely new — it was checked against `grade.md` and `expand.md` and neither states it
today. It is also the highest-value criterion in this file, because "all the parts passed" is
exactly the shape of a green report over a broken product.

**Verify:** a fixture workflow where every component step's own assertion passes but the end-to-end
assertion fails → the compiled top-level verdict is FAIL or INCONCLUSIVE, **never PASS**. The
sabotage is to revert the rollup to "AND of components" and reproduce the false PASS.

### EC4 — Scenario variants are distinct, traceable graph nodes [D-041 EXTEND, AT-586]

A declared scenario variant is its own node with its own case set. It is not folded into the base
flow.

**Verify:** a fixture flow with 2 declared scenario variants produces 2 distinct scenario nodes,
each with its own traceable case set.

### EC5 — A scenario list is an input contract: a branch with no compiled case is reported UNCOVERED

*(Added 2026-09-29 from Umesh's verbatim 2026-09-24 meeting direction, `qa/feedback-inbox.md`
2026-09-24T16:10, 10:35-10:57 and 05:30-06:05: "Sabse pehle scenario likhne zaroori hai taki aap
koi scenario bhoolo nahi ... us scenario me saare options test kar lena. Yes, no. Yes, no.")*

When evals are compiled from a written scenario list, every branch a scenario enumerates (yes / no,
each option) must end up with a compiled case **or** be listed as **uncovered**. A branch that
silently produced no case is the failure this refuses (intent O4).

**Verify:** a fixture scenario list with 3 scenarios, each with a yes and a no branch, where the
compiler is made unable to produce a case for exactly one branch — the compiled output lists that
branch under an `uncovered` heading with its scenario id, and the coverage figure is **not** 100%.
Sabotage: drop the uncovered-listing step — the named test goes red on the missing branch, not on an
import error.

## No-fire list

- Building T-166 itself.
- Taxonomy classes beyond what `expand.md` X3 already enumerates.
- A graph database or GraphRAG integration — explicitly rejected by D-041.
- Visual rendering of the graph — named by no task read.

## Amendment log (append-only; git history is the version)

- 2026-09-28 · init · authored by /checker under D-054 from the criteria filed in
  `qa/feedback-inbox.md` (2026-09-27, `at638-remainder`), judged sound by a prior checker. Cause:
  AT-638 — T-166 had **zero** checkable criteria, which is the real reason the knowledge graph never
  got built. Recorded plainly because it was mis-reported once: T-166 was **not** blocked on a human
  decision. Gate `at638` was answered 2026-09-27 (D-054); what was missing after that answer was this
  file. DRAFT until T-166's first PASS. **Changes-authorized:** this file (named by D-054). No
  enforcement-path file touched. **Links:** AT-638; AT-586; D-041; D-054; T-166; T-164.

- 2026-09-29 · routine (add) · EC5 added: a scenario list is an input contract, and a branch with no
  compiled case is reported UNCOVERED. Cause: Umesh's verbatim 2026-09-24 meeting direction, tagged
  "unfolded pending T-166's contract" since 2026-09-24 (`qa/feedback-inbox.md`, folded this sweep);
  EC1-EC4 govern the graph and provenance and none states it. Adds a criterion, weakens none.
  **Deliberately NOT folded here:** the "worst-case default" and "stalled handoff" patterns from the
  same transcript — they are new case/defect CLASSES, which this contract's no-fire list excludes
  ("taxonomy classes beyond `expand.md` X3") and which need an implementation site and, for the
  stalled handoff, an N that only Umesh can set (AT-666 stays open for them).
  **Changes-authorized:** this file (D-054). No enforcement-path file touched. **Links:** AT-666;
  D-054; T-166; qa/feedback-inbox.md 2026-09-24T16:10.
- 2026-10-11 - routine (status change only; no criterion changed) - **DRAFT -> ACTIVE.** The status line
  set the condition "goes ACTIVE on T-166's first checker PASS". That PASS is on disk and on master:
  `qa/verdicts/t166-eval-compiler.md` (cycle 0, commit c42dd8f9, EC1-EC5, 5 falsifications). Nothing was edited, added or weakened in any criterion; this records the
  transition the header already promised. **Links:** T-166; qa/verdicts/.
