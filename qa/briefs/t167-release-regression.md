# Build brief — t167-release-regression (T-167, criticality critical)

Prepared 2026-10-10 by a read-only readiness pass. Nothing was built, run or committed. Facts marked `unknown` are not in the repo; do not guess them. Re-read `git -C D:/autoTesting rev-parse master` at dispatch and rebase this brief's "base" if master moved.

**Dispatchable: YES.** Contract `qa/contracts/release-regression.md` (RR1-RR6, DRAFT, goes ACTIVE on first PASS) exists, dependencies T-166 and T-110 are `done`, and no human gate is open for this unit.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier: L.** Triggers: dependency bump (new `langgraph` dependency in `pyproject.toml` and `uv.lock`, RR5); concurrency/resume (a checkpointer substrate replaces the filestore `RunState` resume path, RR1); config/CI (a release trigger that starts runs on a developer change). The goal criticality is `critical`.
- **Dual check: required.** Trigger: `security: src/autotester/core/consent.py:182` (`require_approval`). RR2 requires a release run to be refused before the graph is invoked unless a valid signed `RunApproval` exists, and the run then drives a live visible browser with a project whose `write_policy` may be `allow_writes` (`qa/gates/write-policy-tier.md`). That approval gate is the security boundary of this unit.
- No enforcement-path file (`.claude/hooks/*`, `scripts/append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`) is touched by this brief.

## 2. Root and base

- Root `D:/autoTesting`. Base = `master` @ `4f8f5da100931ebda1b26836304bfbd38460764b` (at preparation time).
- **Branch: a fresh `wave/t167-release-regression` from master.** Reason: the existing branch `wave/t167` points at `c42dd8f9` (the T-166 PASS commit, 14 commits behind master, 0 commits ahead). Its worktree `D:/autoTesting/.worktrees/t167` holds about 2,000 uncommitted changed lines in 22 files plus 2 untracked files (last edited 2026-10-09 04:29, no manifest, no `tests/test_regression_trigger.py`, no verdict). `qa/QUEUE.md` says "worktree t167 is INPUT only" and D-080 item 1 says uncommitted work is not canonical.
- **Use that worktree as read-only INPUT.** Read its diff (`git -C D:/autoTesting/.worktrees/t167 diff`) and its two untracked files, re-derive each piece against current master, and re-prove it. Do not copy it in wholesale and do not edit it: it is 14 commits stale, so a file-level copy would silently undo master changes. Never stash, checkout or reset in it.

## 3. Acceptance criteria (verbatim from `qa/contracts/release-regression.md`)

Contract-level facts: criterion ids RR1-RR6. The goal `done_check` is `uv run pytest tests/test_regression_trigger.py` (exit 0). That file does not exist yet; creating it is part of this unit.

### RR1 — LangGraph converts `orchestrate.py` IN PLACE, and must not weaken OR2/OR4 [D-041 verbatim]

It is a conversion, **not a second orchestrator**. `orchestrator.md`'s own no-fire list declined
LangGraph "in this unit" (T-163) pending a superseding entry; **D-041 is that entry**, scoped to
T-167. Edit in place — this repo's standing anti-drift rule, and here it is also a contract term.

OR2's resume-without-redo and OR4's crash-honesty must be **preserved, not merely re-implemented**.

**Verify:** OR2/OR4's own falsification shapes, reproduced against the LangGraph checkpointer
substrate instead of the filestore `RunState` — mark a stage done, re-run, assert it is not redone;
force a raise, assert `failed` status and the correct resume point.

### RR2 — `interrupt()` LAYERS ON TOP OF `RunApproval`; it never replaces it [D-041 explicit]

A release run needs its own valid `RunApproval` **before it starts**, exactly as every other
outward-facing entry point does. `interrupt()` is a human-in-the-loop pause inside the graph; it is
not an approval mechanism.

**Scope correction carried from D-054, and it narrows this criterion deliberately:** the filed
version of RR2 claimed authority from `consent.md` CN5/CN6, and that claim is **overstated against
RR2's own stated Verify**. What RR2 actually tests is CN1's shape (nothing outward-facing starts
without approval) and CN9's unconditionality. CN5/CN6 are not cited here. A unit must not import
CN5/CN6 obligations from this file.

**Verify:** a release run with no `RunApproval` is refused **before** the LangGraph graph is invoked
— CN1-shaped: no run directory, no navigation. A run *with* approval reaches the `interrupt()` point,
and a resume without human input never proceeds past it.

### RR3 — "The last trusted baseline" is ONE named, testable rule — never "whatever ran last"

D-041 and `.goal/goal.json` name the *property*; they do not specify its mechanics. This criterion
does not assert a particular rule. It requires the build to **pick one, name it, and test it.**

**Verify:** a fixture with three release runs — good, bad, good. Whichever "trusted" rule the build
adopts must be named and exercised. For example, if a flagged-bad run is excluded, the third run's
diff must compare against the **first good** run and skip the bad one — not silently against the
immediately-prior run.

### RR4 — The release trigger never grades [C7; third instance of one family]

The mechanism that starts a release run does not also judge its outcome. This is the same shape as
`ai-target.md` AI5 and `adversarial.md` AD5, and it is **cited, not re-derived**.

**Verify:** the AI5/AD5 test shape, applied to the release-trigger module.

### RR5 — `langgraph` is declared in `pyproject.toml` only within this unit [D-041, C11]

**Verify:** `grep -n "langgraph" pyproject.toml` returns a real line, and `uv run autotester doctor`'s
`check_dependencies_declared` reports clean.

### RR6 — Per-flow validation plans are stitched into ONE release run that ends in ONE issues log

*(Added 2026-09-29 from Umesh's verbatim 2026-09-24 meeting direction, `qa/feedback-inbox.md`
2026-09-24T16:10, 09:28-09:47: "jab yeh ek flow poora complete ho jayega next time woh ek hamara plan
ban jayega ... woh stitch ho jate hain ek ke upar ek. Toh jab aap badi release karte ho toh yeh saare
flow automatic check karke aapko last me log de dega ki yahan yeh yeh issues hain.")*

Each completed flow leaves a persisted validation plan. A release run executes **all** of them and
terminates in a **single** issues log naming each issue's flow. A flow with no plan is reported as
**not run**, never omitted from the log.

**Verify:** a fixture with 3 flows, each with a persisted plan and one seeded failure in two of them —
one release run produces one log containing both failures with their flow ids, and the third flow
appears as passed. Remove one flow's plan — it appears in the log as `not run`. Sabotage: run only the
first plan — the two-failures assertion goes red.


Also binding (same contract): the disclosed-dependency section is RESOLVED by D-055 (T-167 depends on T-166 and T-110 only; no T-179 dependency). No-fire list: the Deep Agents lead-agent integration, and the concrete webhook/CI trigger mechanism (named by no decision read). Contract OR2/OR4 live in `qa/contracts/orchestrator.md` (ACTIVE) and are quoted by RR1.

## 4. What exists and what is missing

On master (`4f8f5da1`):
- `src/autotester/stages/orchestrate.py` (203 lines) is the filestore `RunState` orchestrator; `run_or_resume` at line 182. No LangGraph anywhere in `src/` (the only `langgraph` string is a framework-name set in `stages/discover.py:29`). `langgraph` is not in `pyproject.toml`. There is no release schema, no release trigger, no baseline rule, no `tests/test_regression_trigger.py`.
- Reusable, already done: `core/consent.py::require_approval` (:182), `ApprovalRequired` (:25), `validate_account_bounds` (:66); `schema/approval.py::RunApproval`; `stages/execute.py::run_case` (:159); `stages/grade.py::grade`; `stages/eval_compiler.py` (T-166, PASS); `scripts/regression_proof.py` and the `tests/fixtures/regression_site/` fixture (T-110).

In the INPUT worktree `.worktrees/t167` (uncommitted; from file headers and greps only, nothing re-run, treat as unverified):
- `stages/orchestrate.py` (298 lines there) imports `langgraph.graph.StateGraph` and `langgraph.types.interrupt/Command` (lines 16-17); `_release_preflight` (:185) raises `ApprovalRequired` for a release; `RELEASE_PIPELINE` (:49); mode `"release"` (:120). Partial RR1, RR2.
- `stages/orchestrate_checkpoint.py` (264 lines, new): `FileCheckpointer(InMemorySaver)` at :157, a `CheckpointSerializer`. Partial RR1 (durable checkpoint substrate).
- `schema/release.py` (205 lines, new): `FlowPlan`, `ReleaseScope`, `ReleaseDecision`, `FlowOutcome`, `ReleaseIssue`, `ReleaseRecord`; `BASELINE_RULE = "latest_finished_all_pass_unflagged_complete_flow_release"` (:23). Partial RR3, RR6.
- `pyproject.toml` adds `"langgraph==1.2.14"`; `uv.lock` +109 lines. RR5 shape. (PyPI lists langgraph 1.2.14, requires-python >=3.10; this project is >=3.11.)
- Edits to `stages/orchestrate_runners.py` (+154), `stages/run_budget.py` (+123), `store/run_store.py` (+192), `store/filestore.py` (+44), `schema/run.py` (+60), `schema/run_state.py` (+16), `cli_orchestrate.py` (164 lines changed), `ui/run_execution.py` (214 lines changed), and test edits in 11 test files.

Gap per criterion (what the builder must still deliver and prove):
- **RR1:** a test that reproduces OR2 (done stage not redone on re-run) and OR4 (forced raise gives `failed` and the correct resume point) against the LangGraph checkpointer, plus the existing `tests/test_orchestrate.py` OR1-OR6 oracles green. Conversion in place, no second orchestrator.
- **RR2:** a test that a release run with no `RunApproval` raises `ApprovalRequired` before the graph is invoked and before any run directory exists (CN1 shape); a run with approval reaches `interrupt()`; resume without human input does not proceed.
- **RR3:** choose and name ONE baseline rule (the input tree names one in `BASELINE_RULE`) and prove it on the three-run good/bad/good fixture so the third run diffs against the FIRST good run.
- **RR4:** the release-trigger module does not grade. The trigger entry point name is `unknown` (the input tree adds a release flag in `cli_orchestrate.py`); an AI5/AD5-shape test on it is missing.
- **RR5:** `grep -n "langgraph" pyproject.toml` returns a real line; `uv run autotester doctor` `check_dependencies_declared` clean.
- **RR6:** 3-flow fixture, 2 seeded failures, one planless flow reported `not run`; the sabotage (run only the first plan) goes red.

## 5. Files the builder will touch

Counts are master line counts. The 300-line file cap and 50-line function cap apply (`autotester doctor`).

Existing, edit in place:
- `pyproject.toml`, `uv.lock` (shared lock, see section 10)
- `src/autotester/stages/orchestrate.py` (203)
- `src/autotester/stages/orchestrate_runners.py` (126)
- `src/autotester/schema/run_state.py` (90)
- `src/autotester/schema/run.py` (121)
- `src/autotester/store/run_store.py` (50)
- `src/autotester/store/filestore.py` (110)
- `src/autotester/core/paths.py` (**300, at the cap**: a new path accessor needs a split, not an append)
- `src/autotester/stages/run_budget.py` (165)
- `src/autotester/cli_orchestrate.py` (258)
- `src/autotester/ui/run_execution.py` (195), only if the release/consent surface needs it; shared with unit `at733-bounded`

New (names from the input tree; the exact set is `unknown` until the builder decides; each needs a C3 justification for the cap):
- `src/autotester/schema/release.py` (input tree: 205)
- `src/autotester/stages/orchestrate_checkpoint.py` (input tree: 264)
- a release-trigger module: name `unknown`
- `tests/test_regression_trigger.py` (the goal `done_check` file; required)

Tests edited in the input tree (existing, edit in place): `tests/test_orchestrate.py` (168), `tests/test_orchestrate_runners.py` (132), `tests/test_cli_orchestrate.py`, `tests/test_cli_orchestrate_resume.py`, `tests/test_schema.py` (153), `tests/test_store.py` (224), `tests/test_parallel_run_approval.py`, `tests/test_ui_runs_serial_entry_order.py`, `tests/test_ui_runs_serial_entry_screenshot_namespace.py`, `tests/test_ui_runs_serial_resilience.py`.

Regenerated, not hand-edited: `docs/MAP.md`, `docs/SNAPSHOT.md` (`uv run autotester map`).

Forbidden for the builder: `docs/ARCHITECTURE.md` (150 of 150 lines; D-041 authorizes one Pipeline line only after the PASS, as maker close-out), `docs/DECISIONS.md`, `qa/contracts/*`, `.goal/goal.json`, `qa/issues.jsonl`, `qa/QUEUE.md`. No enforcement-path file.

## 6. Test scope

Run only these files (bare `uv run pytest <file>`, no `-q`, AT-503), never a directory:
- `tests/test_regression_trigger.py` (new, done_check)
- `tests/test_orchestrate.py`, `tests/test_orchestrate_runners.py`, `tests/test_cli_orchestrate.py`, `tests/test_cli_orchestrate_resume.py`
- `tests/test_schema.py`, `tests/test_store.py`, `tests/test_consent.py`, `tests/test_parallel_run_approval.py`
- `tests/test_ui_runs_serial_entry_order.py`, `tests/test_ui_runs_serial_entry_screenshot_namespace.py`, `tests/test_ui_runs_serial_resilience.py` (only if `ui/run_execution.py` is touched)
- end gates: `uv run ruff check src tests scripts` and `uv run autotester doctor`. The full suite is NOT the builder's job.

## 7. Reachable test cases

- RR1: (1) a fresh run completes all stages through the compiled graph; (2) stage N marked done in the checkpointer, re-invoke, N's callable is not called and its artifact is byte-identical; (3) a stage raises, status `failed` with a non-empty error, resume re-enters that stage; (4) the existing teaching/explore OR1-OR6 oracles still pass.
- RR2: (1) no `RunApproval`: release run raises `ApprovalRequired`, no run directory, no browser call, graph never invoked; (2) valid approval: run reaches `interrupt()`; (3) resume with no human payload stays paused; (4) an approval whose bounds do not cover the scope is refused (CN6 shape, cited not re-derived).
- RR3: (1) runs good/bad/good: the third run's baseline is run 1; (2) a run with an incomplete or flagged flow is never a baseline; (3) the first-ever run has no baseline and says so, it does not compare against itself.
- RR4: (1) the trigger module imports no grader and writes no verdict; (2) every `Result` in a `ReleaseRecord` equals what `stages/grade.py` returned.
- RR5: grep plus doctor.
- RR6: (1) 3 flows, 2 seeded failures: one log, both failures named by flow id, third flow passed; (2) delete a plan: that flow shows `not run`; (3) the sabotage (first plan only) goes red.

## 8. Gate answers

- `qa/gates/d063-cn5-vs-cn11.md:17`: `Answered: 2026-10-07T03:17:22Z — B, widened — chat (Umesh): "agar credentials hai tho run krroo, approved maano … baar baar approval nhi chahiye. credentials de denaa sabse bada approval hai". Provisioned credentials for a project are the standing run approval; no per-run human approval. Recorded as D-068.` Effect for RR2: a signed approval row is still required before the graph; for a project with provisioned credentials the row is minted automatically (account-derived). RR2 is not weakened; do not invent a human step and do not skip the row.
- `qa/gates/write-policy-tier.md` (header `GATE ANSWERED`, "Answered by: Umesh, 2026-09-27"): `ALLOW_WRITES` is authorized on every target; the supplied account is the scope. It has no `Answered:` line; do not re-litigate.
- `qa/gates/d081-run-approvals.md:12` (untracked in master's working tree): `Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081`. It names the T-145 crawl and the T-154 pass only. **It does not authorize any live T-167 release run.**
- **No live run is authorized by this brief.** Proof is fixture-only (`tests/fixtures/regression_site/`, `scripts/regression_proof.py`, a scripted fake provider). No Pathlynks/ERP traffic, no model call, no real credentials.
- Decisions that bind: D-041 (LangGraph 1.x from T-167), D-054 (contract authorized), D-055 (deps T-166 and T-110 only), D-036 (the filestore orchestrator being converted), D-023 (release regression is the product promise). All `Approved-by: Umesh`.

## 9. UI surface and persona walk

`Persona walk: required (release-manager)` per `docs/plan.md:72` and `qa/QUEUE.md` (surface: release trigger, consent interrupt). The contract RR1-RR6 has no UI criterion, so the walk applies only to the human-facing release surface the builder actually ships (a CLI confirm/resume, or a UI route if `ui/run_execution.py` is edited). If the build is CLI-only, the manifest must say so and name the CLI commands walked. Do not start a visible browser against a live product.

## 10. Dependencies and conflicts

- Must land first: none. T-166 and T-110 are done.
- **Unlocks T-168** (`t168-damage-control-report`, depends on T-167). T-168 will need from this unit: a durable typed `ReleaseRecord` per release under the project store (per-flow outcome, the issues log with flow ids and `not run`, the baseline rule id, the regression diff) at a stable path T-168's report layer can read; the regression diff exposed as a typed artifact (`qa/contracts/damage-control-report.md` line 36 cites "regression diff (RR3)"); and a rule that blocked/unvisited is never recorded as pass. Write no T-168 code.
- Later composition (not this unit): D-042 says the lead agent may run on these checkpoints once T-181 proves a gain.
- Shared files (one owner each):
  - `pyproject.toml`, `uv.lock`: owner this unit (T-167) now. `qa/QUEUE.md:86` says t167, t174, t179 and t202 each add a dependency and must serialize on the lock.
  - `src/autotester/stages/orchestrate.py`, `orchestrate_runners.py`: owner T-167. T-179 only calls `run_or_resume`; T-181 uses it as the plain-pipeline baseline.
  - `src/autotester/core/paths.py` (300/300), `schema/run.py`, `store/*`: owner T-167.
  - `src/autotester/ui/run_execution.py`: shared with unit `at733-bounded` (`qa/QUEUE.md`, edits `_run_entry_case`). Owner T-167 if it must edit; otherwise leave it. Do not run both builders on this file at once.
  - `docs/MAP.md`, `docs/SNAPSHOT.md`: generated; every branch regenerates and they always conflict. Owner: whoever merges last, by re-running `uv run autotester map`, never by hand-merge.
  - `docs/ARCHITECTURE.md`: maker close-out after PASS (one line, D-041), serialized with T-179's line (D-042); the file has no headroom.
- Unit that can run in parallel without overlap: T-196 (disjoint source files).

## 11. Budget and process rules

- Check budget (tier L): 45 min. The builder runs no full suite; only the files in section 6.
- Falsification only in a throwaway copy outside the bound tree, then a byte-identical restore; one green, red-for-the-named-reason, restored row per RR criterion.
- Kill only PIDs you started. Scratch, logs and evidence go to `.work/`. Edit in place; no `*_v2.py` or `*_new.py`. All model calls go through `providers.base.Provider`; prompts are files.
- Open an evidence manifest `qa/manifests/t167-release-regression.md` at `Status: ready-for-check` with `Fix cycle: N`; only `/checker` can PASS. Do not push; the checker pushes on PASS (D-007).
