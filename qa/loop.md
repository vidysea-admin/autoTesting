# AutoTester maker-checker loop

Use when: advancing the AutoTester backlog (`.goal/goal.json`) — building one unit against its
contract, dispatching an independent checker, closing on PASS, and picking the next unit —
without a human hand-cranking each step.

Prompt: `/maker continue "d:/autoTesting"` — bind to the root, reconcile disk state, sweep if due
(every 5th tick or >2h since `qa/.last-sweep`), pull one unit (QUEUE.md top TODO row → open
issues by severity → contract gaps → feedback inbox), build it against its contract with real
command output, write `qa/manifests/<slug>.md`, dispatch a fresh `/checker` subagent in the same
turn, close out on its verdict file, then name a terminal state and either `ScheduleWakeup` the
next tick or `stop: true`. Never self-certify PASS; never touch `qa/contracts/`.

Verify: the adapter's slot-1 commands (`qa/adapter.json`, `"coding"` adapter) — `uv run pytest`
(no CLI `-q`; `pyproject.toml`'s `addopts` already sets it, AT-503) exit 0, `uv run ruff check src
tests scripts` clean, `uv run autotester doctor` clean — re-run
independently by the checker, never trusted from the maker's paste. A `rubric_ref` `done_check`
(T-050, T-110, T-120) additionally requires a satisfied `/outcome-grader` verdict once its own
rubric exists.

Steps (OCAVR):
1. **Observe** — bind to `d:/autoTesting`; read `qa/.last-tick`, `qa/.last-sweep`,
   `qa/QUEUE.md`, open rows in `qa/issues.jsonl`, and `.goal/goal.json`'s pending tasks.
2. **Choose** — one work unit: the top clear QUEUE.md TODO row, else the highest-severity open
   issue, else a contract gap, else a feedback-inbox item. A `GRILL:` row or a task genuinely
   requiring live Pathlynks/video input is never "chosen" — it is named as `HUMAN_GATE` and the
   next unblocked unit is picked instead.
3. **Act** — write or fix the code/doc against its contract; run every verify command for real.
4. **Verify** — write the evidence manifest, dispatch `/checker` in the same turn, read
   `qa/verdicts/<slug>.md` (the file, `Cycle checked: N` must match) — never trust the
   subagent's return text alone.
5. **Record** — on PASS: flip the manifest, close the goal task (checker does this; maker
   fallback-closes via `goal_cli.py done` only if the file shows it didn't land), append a
   `docs/FEATURES.jsonl` row for a `user_value: high` task, regenerate `docs/SNAPSHOT.md`,
   commit and push (checker pushes its own PASS commit per D-007; maker pushes its own
   deliverable commit split from the checker's, same standing authorization). On FAIL: fix
   exactly what the verdict names, re-dispatch (max 3 cycles, then `STALLED` + `/agent-debugger`).
6. **Repeat/stop** — stamp `qa/.last-tick` with the terminal state and either `ScheduleWakeup`
   (60s if the backlog is non-empty; a background heartbeat sleep is also armed on any tick that
   dispatched no subagent, since `ScheduleWakeup` measurably drops ~1 in 9 wakeups) or
   `stop: true`.

Stop (named terminal states — see maker/SKILL.md "THE CONTINUATION RULE"):
- `ADVANCED` — one unit moved on evidence → continue (60s).
- `BACKLOG_EMPTY` — no pending handshake, no open issues, no queue rows, sweep fresh → `stop: true`.
- `HUMAN_GATE` — the next unit needs a decision only Umesh can make and nothing else is
  unblocked → heartbeat every 1800s, max 8, then `stop: true`. (Currently: T-050 needs an
  unambiguous live-Pathlynks go-ahead; T-060 needs a Pathlynks demo video — both genuinely
  human-gated as of 2026-09-03.)
- `STALLED` — 3 fix cycles exhausted on the only available unit → dispatch `/agent-debugger`
  once, report, `stop: true`.
- `EXHAUSTED` — a tick/token bound hit → diagnose, `stop: true`, report the bound honestly.
- `BLOCKED` — environment prevents execution (plan mode, permission denial) → `ScheduleWakeup` 300s,
  **max 6 consecutive BLOCKED ticks** (~30 min), then `stop: true` and report the block to Umesh — a
  standing block must not wake the loop every 5 minutes forever (AT-566, sweep 2026-09-25).
  `BLOCKED (classifier)` follows the same cap.
- `PAUSED` — `qa/.paused` exists → `stop: true`; only `/maker resume` lifts it.

Human gate: exactly which actions stop and ask Umesh first, per the project's own standing rules
(`CLAUDE.md`, `qa/adapter.json`, and the maker skill's hard rules) —
- **Any live action against the real Pathlynks product** (a headed browser run, a login attempt,
  a deliberate wrong-credentials test, a read-only Mongo query against `PATHLYNKS_MONGO_URI`) —
  never auto-run without explicit per-use approval, even with dev-environment credentials already
  in hand. This is the rule that currently gates T-050 and any live-DB verification of T-045.
- **Writing to `docs/DECISIONS.md`** — append-only, and any entry touching an enforcement path
  (`.claude/hooks/*`, `scripts/append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`) needs
  `Approved-by: Umesh` on the entry before the path itself changes (this gates AT-015's fix).
- **Adding or changing a real credential** — `.env` values, new `SecretRef`s, any `.env.example`
  edit that could accidentally carry a real value (the AT-025 incident class).
- **Anything irreversible or outward-facing** — a force-push, a destructive git op, deleting a
  branch, publishing outside this repo, a payment or account-affecting action. (Routine PASS
  pushes to `origin master` are the one standing exception, D-007 — narrowly scoped, independently
  checker-verified before they happen, not a general push authorization.)
- **A `GRILL:` finding** — the engine can demand a re-grill when the goal has genuinely drifted;
  it never runs one itself.
