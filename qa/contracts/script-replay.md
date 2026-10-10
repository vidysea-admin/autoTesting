# Contract — script-replay (persist the generated script, replay it, locate by meaning)

**Status:** **ACTIVE** (authored by /checker 2026-09-29 under **D-041**, `Approved-by: Umesh` —
Result names this file). ACTIVE since 2026-10-11: T-176's first checker PASS is `qa/verdicts/t176-script-replay.md`
(cycle 0, `VERDICT: PASS`, commit 5383a559, SR1-SR5).
**Feature:** T-176 — persist a case's generated script, replay it with zero provider calls, locate
elements by role / label before CSS, and honour a declared test-id attribute priority.
**Serves:** intent O2 · spec R23.
**Code:** the seams exist and are **unwired**: `schema/case.py::Case.script_ref` (`:31`, copied at
`:84`, never read) and `schema/case.py::Script` (`:111`). No `get_by_role` / `get_by_label` and no
test-id priority anywhere in `src/` (verified 2026-09-29). T-176 `pending`, depends on T-165 (done).
**Tests:** none yet.
**Grounding:** D-041 §6 row T-176 and §4 (**refused:** "regenerate tests instead of maintaining
them") · `docs/research/testsprite-2026-09.md` §4 A and C · `schema/flowspec.py:78` ("semantic
locator: role/name/label, not a brittle CSS path" — a promise nothing keeps) · `agent-loop.md`
(its no-fire list *deferred* literal script generation; **this contract is the D-041 act that lifts
that deferral**) · `execute.md` E1-E5 · core-invariants C7, C12.

## Why it exists

`ARCHITECTURE.md` promises a script-first design and the code re-derives every step through a
provider each time. A replayed script is what makes a regression run cheap, repeatable and the same
thing on Tuesday as on Monday. The failure this contract refuses is a replay that quietly regenerates
when it breaks: that turns a regression suite into a generator, and a passing run into an opinion.

## Criteria

### SR1 — A stored script is replayed with zero provider calls

`Case.script_ref` resolves to a persisted, versioned `Script`. A second run of an unchanged case
replays it and makes **no provider call**. The run records that it was a replay.

**Verify:** run a fixture case twice against a local fixture page with a counting fake provider —
first run: N calls and a stored script; second run: **0** calls, same outcome, the trace/run record
says `replay`. Sabotage: make the loader ignore `script_ref` — the second run's call count goes
non-zero and the named test is red.

### SR2 — A stale script is invalidated, never trusted

A stored script carries a content hash over everything that determines it (the case's steps, the
FlowSpec version, the locator-priority setting). If any input changed, the script is **not replayed**;
the run says why. Same fail-closed instinct as `grade`'s stale-rubric invalidation.

**Verify:** change one step of the fixture case → replay refuses the old script and reports the
reason. Sabotage: remove the hash comparison — the changed-step test turns red on the "old script was
used" assertion, not on a parse error.

### SR3 — Locators are semantic first, and a brittle one is named

Replayed steps locate by **role + accessible name** or **label** before falling back to CSS, and a
step whose only locator is a CSS path or a generated id is **flagged** (named in the report), not
silent. This makes the `flowspec.py:78` promise true.

**Verify:** a fixture page where the CSS class is renamed but role and name are intact — replay
passes. A fixture where the accessible name changes — replay **fails honestly** (`ERRORED`, naming
the step); it does not pass. The second half matters: a locator that "heals" onto the wrong element is
worse than one that fails.

### SR4 — A declared test-id attribute priority is honoured, in order, and nothing else is used

The project declares an ordered list of test-id attributes (research names
`project update --test-id-attributes <list>`; the flag name is the build's to confirm). It lives in
`schema/project.py` (`extra="forbid"`, a default stated), and the locator picks the first declared
attribute present. An attribute not on the list is never used. An empty list means role/label only.

**Verify:** a fixture element carrying two candidate attributes — the chosen one follows the declared
order, and **reversing the list flips it**. A project written before this unit still loads (default).

### SR5 — A failed replay reports; it never regenerates or overwrites

When a replay step cannot find its target, the outcome is `ERRORED` with the failing step named. The
stored script is **byte-identical** afterwards. Repairing a script is an explicit, recorded act (the
T-177 fallback or a human), never a side effect of running. Replay never grades (C7).

**Verify:** replay a fixture script against a page missing the target; assert outcome `ERRORED`,
the stored script's bytes unchanged, and zero provider calls. Sabotage: let a failed replay call the
generator and overwrite — the unchanged-bytes assertion goes red.

## Landing note

`Case.script_ref` is assigned and copied but never **read**, so a check that only asserts the field
exists passes on today's tree (AT-218 shape). Every **Verify** above runs a real replay against a
fixture page and counts provider calls; none can pass on the current code.

## No-fire list

- Building T-176 itself.
- Whether a `Script` stores Python source or a step list — the build's choice, provided SR1-SR5 hold.
- The browser-use fallback (T-177, `agent-fallback.md`) and the unknown-screen path.
- A differential base-vs-head oracle (research item E; deferred to Umesh by D-041 §5).
- Auto-healing locators. Refused here in SR3 and SR5 by construction.

## Amendment log (append-only; git history is the version)

- 2026-09-29 · init · authored by /checker under D-041 (Result names `script-replay.md`). Cause:
  T-176 had a plan row (unit 17) and a goal task but zero checkable criteria; the maker's 2026-09-29
  tick listed it as serial with "no authorizing contract", reading a never-written file as a gate.
  D-041 authorized it on 2026-09-24. Also recorded: `agent-loop.md`'s no-fire deferral of literal
  script generation is lifted by D-041 and this contract, so the two no longer disagree.
  DRAFT until T-176's first PASS. **Changes-authorized:** this file (named by D-041). No
  enforcement-path file touched. **Links:** D-041; T-176; R23; T-177.
- 2026-10-11 - routine (status change only; no criterion changed) - **DRAFT -> ACTIVE.** The status line
  set the condition "goes ACTIVE on T-176's first checker PASS". That PASS is on disk and on master:
  `qa/verdicts/t176-script-replay.md` (cycle 0, commit 5383a559, SR1-SR5, 10/10 falsifications). Nothing was edited, added or weakened in any criterion; this records the
  transition the header already promised. **Links:** T-176; qa/verdicts/.
