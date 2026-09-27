# Contract — run-trace (redacted per-run observability, D-041 phase 1)

**Status:** ACTIVE (DRAFT->ACTIVE by /checker on T-172's checker PASS, 2026-09-25; qa/verdicts/t172-run-trace.md Cycle checked: 2, merged 7975c81). Live orchestrator-wiring gap AT-564.
**Feature:** a redacted `trace.jsonl` per run under `projects/<slug>/runs/<run_id>/`, carrying one
span per pipeline stage and one span per LLM call, plus a UI panel on the run view surfacing
per-stage time/cost/model hops. This is D-041 phase 1 observability — local and file-based; phase 2
(Langfuse self-hosted export) is a separate, later unit and is explicitly out of scope here.
**Covers:** goal task T-172. **Deps:** T-163 (orchestrator; done). **Grounding:** D-041 §3
"Observability" (`docs/DECISIONS.md`); `schema/run_state.py::RunState` (the existing `run_id`-keyed
ledger this unit's `trace_id` reuses); `providers/base.py::Provider.record()` (the existing
usage-accumulation seam this unit's LLM-span recording extends); `core/redact.py::Redactor.scrub` /
`assert_no_raw_secrets` (the existing redaction gate every span must pass).

## What it is

Every run already has a durable identity: `RunState.run_id`, persisted at
`projects/<slug>/runs/<run_id>/state.json` (`schema/run_state.py:61-78`). This unit adds a sibling
file, `projects/<slug>/runs/<run_id>/trace.jsonl`, written incrementally as the run progresses: one
JSON line per pipeline-stage transition (`StageName` start/end, matching `RunState.stages`) and one
JSON line per LLM call (vision/agent/judge — the three `Provider` roles in `providers/base.py`).
The LLM-call recording extends the existing single choke point, `Provider.record()`
(`providers/base.py:85-101`), rather than adding a second, independent recorder — the same "one
concept, one place" discipline C3 already holds the repo to. A UI panel on the run view reads
`trace.jsonl` and renders per-stage time, cost, and model hops; it is a VIEW over the file (C6), not
a second store.

## Criteria (RT1-RTn) — each judged on re-runnable evidence

- **RT1 — One trace file per run, incrementally written.** `projects/<slug>/runs/<run_id>/trace.jsonl`
  exists after a run and contains at least one line; running two independent runs of the same project
  produces two distinct trace files, one per `run_id`, neither overwriting the other. (Falsifiable: run
  a fixture pipeline twice → two `trace.jsonl` files under two different `run_id` directories, both
  non-empty.)
- **RT2 — `trace_id` is reused, never re-minted.** Every span's `trace_id` field equals the run's own
  `RunState.run_id` (`schema/run_state.py:72`) — no second identifier is generated for the same run.
  (Falsifiable: read `state.json`'s `run_id` and every line of that run's `trace.jsonl`'s `trace_id` →
  identical for all lines.)
- **RT3 — One span per stage.** For every `StageCheckpoint` the run produces (`schema/run_state.py:43-58`),
  `trace.jsonl` carries a matching stage span recording at minimum: `stage` (the `StageName`), a status
  outcome, and a duration derived from `started`/`finished`. A stage that never ran (e.g. INGEST on an
  explore-mode run) produces no span. (Falsifiable: a fixture run with stages `[MODEL, EXECUTE, GRADE]`
  → exactly those three stage spans, in stage order, no others.)
- **RT4 — One span per LLM call, with the full required field set.** Every call through
  `Provider.see_video` / `Provider.act` / `Provider.judge` produces one LLM-call span carrying:
  provider/model (`Provider.label`, `providers/base.py:43-52`), the prompt-file id it used, tokens in,
  tokens out, latency, cost, retry count, fallback-hop count, and the id of the case or verdict the call
  fed. (Falsifiable: a fixture stage making 2 judge calls and 1 act call → 3 LLM-call spans, each with
  every named field present and non-null where the call actually produced that value.)
- **RT5 — Single choke point, no second recorder (core-invariants C3).** The only site in `src/` that
  appends an LLM-call span to `trace.jsonl` is `providers/base.py::Provider.record()` (or code it calls
  directly) — no stage writes a trace span for an LLM call by itself. (Falsifiable: `grep -rn` for
  trace-span-append logic outside `providers/base.py` returns nothing; a stage-level attempt to emit its
  own LLM span is the CONTRACT_MISMATCH shape this criterion forbids.)
- **RT6 — Every span is redacted before it is persisted (core-invariants C5).** Every span, stage or
  LLM-call, passes through `core.redact.Redactor.scrub` and `core.redact.assert_no_raw_secrets` before
  being written to `trace.jsonl`. (Falsifiable: seed a fixture project with a fake secret value bound to
  a `SecretRef`, drive a run whose prompt or evidence would otherwise carry it, and grep the resulting
  `trace.jsonl` for the raw value → zero matches.)
- **RT7 — UI panel, a view over the file (core-invariants C6).** The run view renders a panel showing
  per-stage time, cost, and model hops sourced by reading `trace.jsonl` — it is not a second source of
  truth and does not require a database. (Falsifiable: mutate a fixture run's `trace.jsonl` stage
  durations/model labels directly, reload the run view, and assert the panel reflects the mutated
  values.)

## Explicit no-fire list (do not raise these as findings)

- **Phase 2 (Langfuse self-hosted export) is NOT in this unit.** D-041 §3 names it explicitly as a
  later phase, conditioned on AutoTester running on a server. Raising "should also export to Langfuse"
  or "no `TELEMETRY_ENABLED` wiring" against this contract is out of scope.
- A trace schema requiring a graph database, a time-series store, or any store other than the filestore
  JSONL — D-041 keeps observability file-based, matching D-002's filestore precedent.
- Historical/cross-run trace aggregation (e.g. a dashboard across many `run_id`s) — this contract covers
  one run's trace file and its own run-view panel only.
- The UI panel's visual styling/layout choices, beyond showing time/cost/model hops per stage.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_run_trace.py` (bare, no CLI `-q`, AT-503; this is T-172's `done_check` in
`.goal/goal.json`) + `uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0;
each RT criterion carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2) apply; if
`providers/base.py` has no headroom under its 300-line cap, the new span-recording logic lands in a
new, justified module per C3 rather than pushing the file over budget.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from D-041 (Approved-by Umesh —
  AskUserQuestion answers + plan approval, chat 2026-09-24). No prior draft existed; nothing amended.
- 2026-09-25 · DRAFT->ACTIVE · /checker Mode B sweep, on T-172 checker PASS (qa/verdicts/t172-run-trace.md Cycle checked: 2, merged 7975c81), as this contract's own status line pre-authorized; precedent network-assertions.md at the T-170 PASS. No criterion text changed.
