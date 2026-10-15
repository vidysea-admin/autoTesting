# Contract — agent-fallback (a browser-use actuator for screens the model does not know)

**Status:** **DRAFT** (authored by /checker 2026-09-29 under **D-041**, `Approved-by: Umesh` —
Result names this file). Goes **ACTIVE** on T-177's first checker PASS.
**Feature:** T-177 — a browser-use fallback actuator for **unknown** screens with typed outputs, and
the revival of `stages/agent_loop.py::run_with_fallback` (AT-253) as a production path.
**Serves:** intent O5 (insufficient model → ask, don't guess) and O2 · spec R23.
**Code:** `run_with_fallback` exists (`stages/agent_loop.py:67`) and is called **only from
`tests/test_agent_loop.py`** — no production caller (AT-253). `browser-use` is not a declared
dependency. T-177 `pending`, depends on T-176.
**Tests:** `tests/test_agent_loop.py` covers the loop in isolation; none for the actuator.
**Grounding:** D-041 §1 (Playwright stays the deterministic actuator; browser-use (MIT) is the
fallback for unknown screens) and §6 row T-177 · D-042 (T-177 becomes a runner-subagent tool) ·
`agent-loop.md` AL1-AL5 (the existing loop's contract — cited, **not** restated) · `agent-layer.md`
(T-177 named as a later runner tool) · `explore.md` X7 (host re-checked after every action) and the D-016 deny-list · `consent.md`
CN1/CN9 · core-invariants C3, C7, C11, C12 · CLAUDE.md "all model calls go through
`providers.base.Provider`".

## Why it exists

The deterministic path is right for screens we know. When the model meets a screen it does not
know, the alternatives are a guess or a VideoRequest (O5); an agent that drives the page is a third
option, and the most dangerous one, because it can click. The failure this contract refuses is an
agent that is allowed to do what the deterministic actuator is not: leave the domain, press a
destructive control under a read-only policy, or grade its own run.

## Criteria

### AF1 — The fallback runs only when the deterministic path has no answer

The browser-use actuator is engaged for a screen with no matching persona/script answer, **never** for
a screen Playwright already handles. AL1 ("never consulted on a clean run") holds and this contract
adds no exception to it.

**Verify:** a fixture with one known and one unknown screen and a counting stub for the actuator —
known screen: **0** invocations; unknown screen: **exactly 1**. Sabotage: engage the actuator
unconditionally — the known-screen count goes red.

### AF2 — Its output is typed and refused when malformed

The actuator returns a Pydantic model (`extra="forbid"`): the action taken, the observed result and
the evidence reference. A free-text-only or malformed return is **rejected**, not passed through.

**Verify:** feed the adapter a malformed actuator result — it raises a typed error and the case
outcome is not `PASS`. A well-formed result round-trips through the model.

### AF3 — It obeys the same guards as every other actuation, and never grades

An agent-chosen action is subject to: the deny-list (D-016), the same-domain destination check (X7),
`write_policy`, and the run's `RunApproval` budget — it consumes a probe like any other. It never
produces a verdict (C7); `grade.py` still owns that.

**Verify:** under `write_policy=READ_ONLY`, an agent-chosen write/destructive action is **refused**
and recorded; an agent-chosen off-domain navigation is refused; the run budget is decremented by
agent actions. Sabotage: bypass the destination check inside the adapter — the off-domain test goes
red on the refusal assertion.

### AF4 — It is bounded, and exhaustion is never a pass

A fallback invocation has a maximum number of steps and a wall-clock bound. Exhausting either ends in
an explicit unresolved/inconclusive outcome that names the bound — never `PASS`, never silence (O4).
`run_with_fallback`'s own bound (AL4, `MAX_ITERATIONS`) is unchanged.

**Verify:** a fixture actuator that never resolves — the invocation stops at the bound, the outcome
names it, and it is not `PASS`.

### AF5 — `run_with_fallback` becomes a production path, driven by a real test

At least one production call site of `run_with_fallback` exists, and a test drives **that path** end
to end against a fixture page (a corrected step folds back idempotently, AL3). A repair changes a
stored script only through the explicit, recorded act `script-replay.md` SR5 requires.

**Verify:** `grep -rn "run_with_fallback" src/` finds a call site **outside** its own definition
**and** a test that reaches it through that site, not by importing the function directly (the
present state — a test that calls it directly — is exactly what this criterion is written against).

### AF6 — Model calls go through the Provider seam, and the dependency is this unit's only

`browser-use` is added to `pyproject.toml` only within this unit (C11), its licence checked (D-041
says MIT) and `check_dependencies_declared` clean. Whatever LLM the actuator uses is reached through
`providers.base.Provider` — no direct vendor client outside `providers/`.

**Verify:** the dependency line arrives in this unit's commit; a grep of `src/` for a vendor-client
import outside `providers/` returns nothing; the actuator adapter accepts a fake `Provider` and the
test uses it.

## Landing note

`run_with_fallback` has tests, so "the loop works" is already true and already proves nothing about
T-177. AF5 is deliberately phrased around the **call site**, because a criterion satisfied by the
existing test file would pass on today's tree.

## No-fire list

- Building T-177 itself.
- The loop's own correctness — `agent-loop.md` AL1-AL5.
- The lead agent and its subagents (`agent-layer.md`, T-179).
- Multi-step fixes, and any change to what `run_case` does.
- Persisting a repaired script (`script-replay.md` SR5).

## Amendment log (append-only; git history is the version)

- 2026-09-29 · init · authored by /checker under D-041 (Result names `agent-fallback.md`). Cause:
  T-177 had a plan row (unit 22) and a goal task but zero checkable criteria; the authorization has
  stood since 2026-09-24 and the file was never written. DRAFT until T-177's first PASS.
  **Changes-authorized:** this file (named by D-041). No enforcement-path file touched.
  **Links:** D-041; D-042; T-177; T-176; AT-253; R23.

## 2026-10-15 completion amendment (D-099)

Owner authorization: Umesh approved the complete Ollama-first plan in chat
2026-10-15 and requested implementation through checker PASS. The clauses
below take precedence only on the named behavior; other criteria remain.

### AF7 — Explicit opt-in production integration
The production-wiring hold is released solely for an explicit opt-in fallback
after deterministic replay fails. Default clean replay invokes no actuator; a
disabled fallback invokes no actuator even after failure. AF1-AF6 remain binding,
including provider routing, bounded work and recorded repair persistence. Functional
results survive fallback errors. D-095 keeps the separate lead-agent layer off by
default; this amendment does not enable it. D-098 account-destroying controls stay
blocked at every write policy, in addition to domain and run-approval guards.
Verify the real run caller, disabled/clean/failed paths, exhaustion, guarded actions
and explicit persistence of an accepted repair; direct loop tests alone do not pass.
