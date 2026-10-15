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

Verify: select the D-100 unit risk tier in `qa/adapter.json` (`verify.unit_policy`), then
judge every applicable criterion against an immutable head. Unit PASS is independent evidence
about that unit; it is not integration/release PASS. The exact full commands in
`verify.commands` remain mandatory at the combined integration/release gate. A `rubric_ref`
`done_check` (T-050, T-110, T-120) additionally requires a satisfied `/outcome-grader`
verdict once its own rubric exists.

D-100 proportional independent review (effective for this repo):
- **Minimal fresh-context packet:** base/head SHAs, complete changed-file list and diff, contract
  criteria and claim-to-evidence mapping, selected risk tier with rationale, affected callers and
  deferred integration obligations, exact commands, exit codes and immutable output paths/hashes,
  environment/dependency fingerprint, fixture/config identity, and maker active seconds/tokens/cost.
  Missing measurements are `unknown`, never zero. The checker starts fresh with this packet,
  governing criteria and changed surfaces; broader historical reading needs a specific unresolved risk.
- **Evidence preflight:** validate packet completeness, hash/content and commit bindings, command
  applicability and environment/dependency/fixture/config compatibility before reuse. A cited SHA
  is insufficient when the working tree was dirty. Record reuse/rejection and reasons per claim.
  Use `checker/scripts/review_budget.py preflight --root <checkout> --import-name autotester
  --import-root <checkout>/src --temp-parent <existing temp parent>` for actual import/environment
  preflight; its `reuse --input <fingerprints.json>` compares existing/requested evidence bindings.
  Packet completeness and hashes still require direct inspection. A missing/unusable helper is
  recorded explicitly and equivalent checks performed directly, never silently assumed passed.
- **Docs/config tier:** no runtime effect; inspect every changed statement and validate syntax,
  schema/structure, references and applicable policy consistency. Executable config changes leave
  this tier. An independent discriminating consistency/structure probe is required; a fabricated
  runtime mutation for prose is not. This tier cannot certify runtime behavior.
- **Bounded-code tier:** select affected tests and callers, scoped lint and applicable doctor
  checks. Independently inspect the diff and run at least one discriminating focused probe or
  representative sabotage of the changed property. Validate maker per-guard mutation evidence;
  missing, inconclusive or stale proof stays unproven and requires focused new evidence.
- **High-risk tier:** auth, permissions, credentials/secrets, PII/image privacy, production/write
  approvals, destructive controls, shared schema/provider boundaries and enforcement changes
  require independent focused checks of each affected safety boundary, including rejection paths,
  plus the mandatory combined integration gate. Size alone never downgrades risk. Sensitive
  checks cannot be waived to meet a budget or replaced entirely by maker evidence.
- **Reuse:** compatible, bound maker/CI evidence may satisfy repeated deterministic commands.
  The checker still re-derives the claim, judges applicability and supplies the independent probe
  above; copying a maker PASS is not verification. Semantic mutations retain all C7 baseline,
  applied-patch and named-failure proof. Added/rewritten tests and introduced guards retain maker
  proof for every claimed guard; checker representative reruns may expand for concrete risk.
- **Integration/release gate:** after units combine, run `uv run pytest` (no CLI `-q`),
  `uv run ruff check src tests scripts`, and `uv run autotester doctor` on the exact combined
  candidate, with existing machine resource/browser serialization rules. The independent checker
  may reuse compatible attested results for that same candidate instead of starting duplicates.
  A changed candidate invalidates affected evidence; explain any narrower reuse. Missing full-gate
  evidence blocks integration/release certification even when all individual units have PASS.
- **Efficiency:** target checker active duration, tokens and cost each <=10% of comparable maker
  measurements when both exist. Exclude queue/wait time from active duration and record it
  separately; do not invent denominators, equate wall time to active time or infer missing spend.
  With unknown/zero denominators do one fixed bootstrap scope: packet preflight, changed-surface
  review and the tier's focused independent probe/checks, capped at 180 active seconds and 6000
  checker tokens by the global helper; unavailable telemetry stays unknown. Report ratio
  `unverified`; hitting the cap with unresolved criteria requires NEEDS_EXTRA_REVIEW.
- **Overrun:** never autoPASS or weaken correctness. Stop redundant broad reruns and name
  `NEEDS_EXTRA_REVIEW` with unresolved criteria, concrete extra scope, reason and estimated effort
  when the bounded review cannot establish them. Continue extra review only under a recorded
  allocation; use `HUMAN_GATE` only for a decision/residual risk requiring Umesh. A known defect
  is FAIL, not a budget exception. No unfinished review is reported as PASS.

Steps (OCAVR):
1. **Observe** — bind to `d:/autoTesting`; read `qa/.last-tick`, `qa/.last-sweep`,
   `qa/QUEUE.md`, open rows in `qa/issues.jsonl`, and `.goal/goal.json`'s pending tasks.
2. **Choose** — one work unit: the top clear QUEUE.md TODO row, else the highest-severity open
   issue, else a contract gap, else a feedback-inbox item. A `GRILL:` row or a task genuinely
   requiring live Pathlynks/video input is never "chosen" — it is named as `HUMAN_GATE` and the
   next unblocked unit is picked instead.
3. **Act** — write or fix the code/doc against its contract; run the selected tier commands for real and record integration obligations.
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
