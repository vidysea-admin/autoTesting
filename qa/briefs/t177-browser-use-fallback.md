# Build brief - t177-browser-use-fallback (T-177, readiness pass 2026-10-11, NOT-DISPATCHABLE until three preconditions clear)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Verdict: **NOT-DISPATCHABLE.** The contract exists and the candidate build exists, but (1) the repair plan for the remaining source defects is `PROPOSED - awaiting fresh independent plan review` (`.work/t177-takeover/plan.md` line 3), (2) the repo cites no authorization for the new modules this unit adds (section 8), and (3) the unit needs a `pyproject.toml`/`uv.lock` writer slot (section 10). All three are quick to clear. Dispatch trigger: plan review APPROVED, a module authorizer cited, lock slot free. The plan review itself is dispatchable now and runs in parallel with the T-178 build.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- Tier: **L**. Triggers: a dependency addition (`browser-use==0.5.9`, an addition is always L, D-075), and security controls (AF3: destination, write-policy, deny-list, budget; a DevTools `cdp_url` endpoint; telemetry and `.env` exposure).
- `Dual check: required`. Triggers: `security src/autotester/stages/browser_use_backend.py:191` (`BrowserUseBackend._drive`, where the agent acts on a page that holds credentials) and `security src/autotester/stages/agent_actuator.py` (`ActionGuard`, the AF3 refusal logic; exact line `unknown`, the builder cites it in the manifest). D-075 `Result` also demands it: "T-177 merges only after both dual-check coordinators PASS and the pin and telemetry change has had its repair check."

## 2. Root and base

- Root: `D:/autoTesting`
- Base: master `3a16616cf2c99a63c8d763150a1ca6410dfc0acc` (re-read at dispatch). Candidate branches are NOT the base:
  - `wave/t177-followup` @ `205302b4c030e5d3e15bfe02036201ba0559a2c1` (worktree `D:/autoTesting/.worktrees/t177f`, clean except two verdict renames): cycle-1 build, manifest `Status: ready-for-check`, `Fix cycle: 1`, never checked. 7 commits ahead of master, merge-base `7782df41`.
  - `wave/t177-agent-fallback` @ `1f950714` (worktree `.worktrees/t177`): the cycle-0 build checked by verdicts A (FAIL) and B (PASS), commit `4e06f18c`.
  - A trial merge of `wave/t177-followup` into master conflicts only in `docs/MAP.md` (generated). `uv.lock` has no textual conflict today but is 4143 lines of generated output.
- Branch to build in: fresh `wave/t177-agent-fallback-reland` from master. Reason: D-080 item 1 (master is the single trunk; worktrees and branches are INPUT, re-landed unit by unit, never merged wholesale). Port the section-5 files from `wave/t177-followup` with `git show wave/t177-followup:<path>`, regenerate `uv.lock` with `uv lock` on the new base (never copy its 4143 lines), leave the candidate's verdict and QA history behind.
- Drift guard: the takeover plan pins SHA256 for every source file (`.work/t177-takeover/plan.md` lines 85-111). At dispatch, recompute them in `.worktrees/t177f`; observed in this pass: `stages/browser_use_backend.py` = `E33624ED05B86F3E...` (matches the plan pin), `stages/agent_loop.py` = `89C873093C271FE0...`, `stages/run_case_pipeline.py` = `31CCD17F47F9005B...` (first 16 hex digits only; the plan holds the full values). A mismatch means a peer edited the candidate: stop and reconcile, never reset.

## 3. Acceptance criteria (verbatim from `qa/contracts/agent-fallback.md`, status DRAFT, goes ACTIVE on T-177's first checker PASS)

### AF1 - The fallback runs only when the deterministic path has no answer

The browser-use actuator is engaged for a screen with no matching persona/script answer, **never** for
a screen Playwright already handles. AL1 ("never consulted on a clean run") holds and this contract
adds no exception to it.

**Verify:** a fixture with one known and one unknown screen and a counting stub for the actuator —
known screen: **0** invocations; unknown screen: **exactly 1**. Sabotage: engage the actuator
unconditionally — the known-screen count goes red.

### AF2 - Its output is typed and refused when malformed

The actuator returns a Pydantic model (`extra="forbid"`): the action taken, the observed result and
the evidence reference. A free-text-only or malformed return is **rejected**, not passed through.

**Verify:** feed the adapter a malformed actuator result — it raises a typed error and the case
outcome is not `PASS`. A well-formed result round-trips through the model.

### AF3 - It obeys the same guards as every other actuation, and never grades

An agent-chosen action is subject to: the deny-list (D-016), the same-domain destination check (X7),
`write_policy`, and the run's `RunApproval` budget — it consumes a probe like any other. It never
produces a verdict (C7); `grade.py` still owns that.

**Verify:** under `write_policy=READ_ONLY`, an agent-chosen write/destructive action is **refused**
and recorded; an agent-chosen off-domain navigation is refused; the run budget is decremented by
agent actions. Sabotage: bypass the destination check inside the adapter — the off-domain test goes
red on the refusal assertion.

### AF4 - It is bounded, and exhaustion is never a pass

A fallback invocation has a maximum number of steps and a wall-clock bound. Exhausting either ends in
an explicit unresolved/inconclusive outcome that names the bound — never `PASS`, never silence (O4).
`run_with_fallback`'s own bound (AL4, `MAX_ITERATIONS`) is unchanged.

**Verify:** a fixture actuator that never resolves — the invocation stops at the bound, the outcome
names it, and it is not `PASS`.

### AF5 - `run_with_fallback` becomes a production path, driven by a real test

At least one production call site of `run_with_fallback` exists, and a test drives **that path** end
to end against a fixture page (a corrected step folds back idempotently, AL3). A repair changes a
stored script only through the explicit, recorded act `script-replay.md` SR5 requires.

**Verify:** `grep -rn "run_with_fallback" src/` finds a call site **outside** its own definition
**and** a test that reaches it through that site, not by importing the function directly (the
present state — a test that calls it directly — is exactly what this criterion is written against).

### AF6 - Model calls go through the Provider seam, and the dependency is this unit's only

`browser-use` is added to `pyproject.toml` only within this unit (C11), its licence checked (D-041
says MIT) and `check_dependencies_declared` clean. Whatever LLM the actuator uses is reached through
`providers.base.Provider` — no direct vendor client outside `providers/`.

**Verify:** the dependency line arrives in this unit's commit; a grep of `src/` for a vendor-client
import outside `providers/` returns nothing; the actuator adapter accepts a fake `Provider` and the
test uses it.

### Also binding (verbatim)

- Contract no-fire list: "The loop's own correctness — `agent-loop.md` AL1-AL5." / "The lead agent and its subagents (`agent-layer.md`, T-179)." / "Multi-step fixes, and any change to what `run_case` does." / "Persisting a repaired script (`script-replay.md` SR5)."
- Contract landing note: "AF5 is deliberately phrased around the **call site**, because a criterion satisfied by the existing test file would pass on today's tree."
- D-075: "The UI wiring (`agent=`/`actuator=` into `run_and_grade_case` in ui/routes_runs.py) waits until T-203 and T-204 land, to avoid a three-way conflict with the peer session's branches." So AF5's production call site is `stages/run_case_pipeline.py::fallback_executor` (called by `run_and_grade_case`); wiring a UI caller is out of scope here.

## 4. What exists and what is missing

- **On master:** `stages/agent_loop.py::run_with_fallback` (85 lines on master) called only from `tests/test_agent_loop.py`; no actuator, no `browser-use` dependency, no `cdp_url`. AF1-AF6 all unmet in `src/`.
- **Cycle-0 build** (`wave/t177-agent-fallback` @ `4e06f18c`, manifest `qa/manifests/t177-agent-fallback.md`): two blind verdicts at `Cycle checked: 0`. `qa/verdicts/t177-agent-fallback.a.md`: **FAIL**. Verdict text: "AF1, AF2, AF4, AF5 and the unit-test side of AF6 are met. **AF3 is not met.** X7 is the named destination check, and it requires a post-action landing-URL re-check. That re-check is not implemented, and the write guard has a bypass. In addition, the browser-use backend cannot construct its `Agent` at all." Findings F1-F10: F1 no landing-URL check (high), F2 `ProviderChatModel` rejected by `browser_use.Agent` (high), F3 `PRESS_KEY` guard blocks only "enter"/"return", F4 no production caller, F5 secret guard defaults to identity, F6 scheme unchecked, F7 telemetry/cloud sync default ON, F8 import-time `load_dotenv()`, F9 AGPL `pymupdf` in the closure, F10 `ProviderError` handling untested. `qa/verdicts/t177-agent-fallback.b.md`: **PASS** (22 mutants, wiring and correctness). Neither is a verdict on cycle 1.
- **Cycle-1 build** (`wave/t177-followup` @ `205302b4`, manifest `qa/manifests/t177-followup.md`, `ready-for-check`, no verdict): exact pin `browser-use==0.5.9` (F1 of the follow-up list), telemetry/cloud-sync/dotenv forced off, read-only `BrowserSession.cdp_url` behind opt-in `expose_cdp` (D-075), I1 landing-URL re-check, I2 `PRESS_KEY` allow-list, I3 http/https only, I4 real `browser_use.Agent` constructs, I5 dotenv off, I6 guard never identity, I7 `ProviderError` falls back. 16 falsifications killed in its own table. Its own caveat: "`routes_runs` (not touched, waits for T-203/T-204) must construct the session with `expose_cdp=True`".
- **Still missing after cycle 1 (the takeover plan, `.work/t177-takeover/plan.md`, PROPOSED 2026-10-09, not approved):**
  1. `run_with_fallback` at its `ProviderError` catch (`stages/agent_loop.py`, line 114 in the candidate): add one masked `Evidence(kind=DOM)` carrying the scrubbed diagnostic, keep ERRORED, never fixed/PASS.
  2. `BrowserUseBackend._drive` (`stages/browser_use_backend.py:191`): per-action guard around the SDK's `Controller.act` via a per-invocation `Controller` subclass passed as `Agent(controller=...)`, checking destination/write/budget before dispatch and the authoritative landing URL right after (including a failed action), so an off-domain landing prevents action 2 of the same SDK step; sticky typed refusal raised after the run even if the SDK swallows the step error; SDK `max_steps` exhaustion raises a named `BoundExhausted` instead of an ordinary unresolved outcome. The step callback stops pre-vetting the whole batch (no double budget spend). The guard must read already-initialised page state only and never call `get_current_page` or any recovery path.
  3. AF1 test strengthening (a screenshot-less non-ERRORED deterministic result must spend 0 Provider and 0 actuator calls).
- Open item the plan itself names: `T177-HARD-PROVIDER-DEADLINE`. `asyncio.wait_for` cannot kill a synchronous `Provider.act` running in `asyncio.to_thread`, and `Provider` has no timeout parameter. The plan proves named outcomes for cancellable async timeouts only. If the owner wants AF4 to guarantee a physical return within `wall_clock_s` under a hung provider, that is an owner decision (section 10); this brief does NOT claim that stronger guarantee.
- Architecture docs lag: `docs/ARCHITECTURE.md` lines 54 and 93-94 still say the agent fallback is unwired. The maker does not edit it (Lab Protocol); record it in the manifest.

## 5. Files the builder will touch

Phase A ports the candidate (`wave/t177-followup` line counts); Phase B applies the takeover repair to the starred files. Cap: file <= 300, function <= 50.

| # | Path | New/Existing | Master lines | Candidate lines | Note |
|---|---|---|---|---|---|
| 1 | `pyproject.toml` | existing | 74 | 75 | one line, `browser-use==0.5.9`; **lock writer, serialize** |
| 2 | `uv.lock` | existing | `unknown` (generated) | +4143 | regenerate with `uv lock`, never copy; **lock writer** |
| 3 | `src/autotester/browser/launch.py` | existing | 68 | 92 | `cdp_endpoint`, `loopback_port`, `launch_options(cdp_port=)` bound to 127.0.0.1 |
| 4 | `src/autotester/browser/secrets.py` | existing | 273 | 286 | `bad_scheme` |
| 5 | `src/autotester/browser/session.py` | existing | 299 | 300 | `cdp_url` read-only property, scheme check; at the cap |
| 6 | `src/autotester/browser/video.py` | existing | 150 | 157 | `_sweep_orphan_videos` moved here to free session.py lines |
| 7 | `src/autotester/prompts/agent_fallback_v1.md` | **new** | - | 27 | prompt is a file |
| 8 | `src/autotester/schema/agent_fallback.py` | **new** | - | 75 | `ActuatorResult`, `extra="forbid"` |
| 9 | `src/autotester/stages/agent_actuator.py` | **new** | - | 238 | `ActionGuard`, `parse_result`, `only_safe_keys`, `FallbackActuator` |
| 10 | `src/autotester/stages/browser_use_backend.py` * | **new** | - | 222 | `_drive`, `NO_NETWORK_ENV`, `ProviderChatModel` (Phase B edits here; 300-line headroom 78) |
| 11 | `src/autotester/stages/agent_loop.py` * | existing | 85 | 122 | `run_with_fallback` (Phase B adds the DOM evidence) |
| 12 | `src/autotester/stages/run_case_pipeline.py` | existing | 229 | 269 | `fallback_executor`, `_record_repair`; the AF5 production call site |
| 13 | `tests/agent_fallback_fake.py` * | **new** | - | 51 | fixture home; extend here, never a new file |
| 14 | `tests/test_agent_fallback.py` * | **new** | - | 273 | AF1, AF2, AF4, AF5 nodes |
| 15 | `tests/test_agent_fallback_hardening.py` * | **new** | - | 145 | F10 nodes, AF3 hardening |
| 16 | `tests/test_browser_session_cdp.py` | **new** | - | 115 | `cdp_url` tests |
| 17 | `tests/test_browser_use_pin_telemetry.py` * | **new** | - | 269 | pin, telemetry, dotenv, landing check |

- `docs/MAP.md` is regenerated last with `uv run autotester map`.
- `src/autotester/stages/agent_actuator.py` is the read-only guard owner in Phase B (the plan pins it and edits nothing there); an unplanned edit to it needs a plan amendment first.
- Module authorization: rows 7-10, 13-17 are new files. See section 8; do not start Phase A until the authorizer is cited.

## 6. Test scope (exact files and nodes; no directory, no full suite)

Run with `uv run pytest <path>[::node]`, no `-q`. The suite is slow (checker A's six-file selection took 297.86 s for 117 tests), so run per file, not combined, and run at most the files below.

- `tests/test_agent_fallback.py::test_af1_known_screen_never_engages_the_actuator` (candidate line 94, strengthened in Phase B) and `::test_af1_unknown_screen_engages_the_actuator_exactly_once` (line 102; exact node name `unknown`, take it from `--collect-only`), then the rest of the file by file path.
- `tests/test_agent_fallback_hardening.py::test_f10_run_with_fallback_survives_a_provider_error` (line 131) and `::test_f10_the_actuator_still_gets_its_one_attempt_after_a_provider_error` (line 139), then the file.
- `tests/test_browser_use_pin_telemetry.py::test_item1_the_backend_checks_the_landing_page_before_each_steps_actions` (line 233, adapted to the per-action seam), then the file.
- `tests/test_browser_session_cdp.py` (file, 115 lines).
- Regression guards for the touched shared stages, by file: `tests/test_agent_loop.py` (153 lines), `tests/test_run_case_pipeline.py` (272), `tests/test_script_replay.py` (280).
- Lint and design: `uv run ruff check <the product and test files above>`, then `uv run autotester doctor` once (it includes `check_dependencies_declared`, AF6).
- No browser, no live provider, no network: the SDK-seam cases drive the REAL installed `browser_use` 0.5.9 `Agent.multi_act` against fake browser/page/controller boundaries (the plan's case B); they must be pinned to the installed version, not to remembered API.

## 7. Reachable test cases per criterion (happy path first)

**AF1** (a) happy: clean / non-ERRORED result -> 0 Provider calls, 0 actuator calls, including the screenshot-less shape that hides the guard behind an early return; (b) unknown screen (fix loop exhausted, still ERRORED) -> exactly 1 actuator call and a result that is never promoted to PASS by actuator success; (c) replay path -> 0 Provider calls, no repair persisted, stored script unchanged (SR5); (d) sabotage: drop the `ERRORED` condition -> test (a) goes red.

**AF2** (a) happy: a well-formed result round-trips through `ActuatorResult`; (b) None, int, `{}`, a missing field, an extra field, a non-dict -> `MalformedActuatorResult`, outcome not PASS (existing 8 parametrized cases); (c) sabotage: `extra="allow"` or no `min_length` -> red.

**AF3** (a) happy: an in-domain, read-only-safe action is admitted and spends exactly one budget unit; (b) `READ_ONLY` + fill/select/upload -> refused and recorded; (c) `PRESS_KEY` allow-list: Enter, NumpadEnter, modifier combos, multi-character strings and text ending in a newline are refused; (d) a non-http(s) scheme is refused; (e) off-domain literal URL refused before dispatch (registry count 0); (f) action 1 lands off-domain via redirect, JS, or hrefless click -> action 2 of the same SDK step is never dispatched (registry count 1), sticky `REFUSED` with a scrubbed reason "landed outside allowed domains"; (g) the same two actions in-domain dispatch twice and spend exactly two units; (h) a native action that errors still gets the landing check; (i) absent or closed active page fails closed and no guard call reaches `start()` / `new_page` / recovery; (j) `done` spends no page-operation budget; (k) no verdict is produced anywhere (C7); (l) sabotage: bypass the landing check -> (f) red on the refusal assertion.

**AF4** (a) happy-ish: an actuator that never resolves stops at the SDK `max_steps` bound with an outcome naming that bound; (b) adapter per-action bound names itself; (c) a cancellable async timeout names `wall_clock_s`; (d) none of them is PASS, through the serial and resilient pipelines; (e) sabotage: ordinary-unresolved on exhaustion -> its own assertion red.

**AF5** (a) happy: `run_and_grade_case(agent=...)` reaches `fallback_executor` -> `run_with_fallback` end to end on a fixture page; a corrected step folds back idempotently on a second invocation (AL3); (b) `ProviderError` containing a synthetic declared secret -> exactly one masked DOM evidence item, no raw secret, result stays ERRORED, `fixed` False, surviving BOTH `run_and_grade_case` and `run_and_grade_case_resilient`, one diagnostic per result across two separate invocations; (c) `grep -rn "run_with_fallback" src/` finds `stages/run_case_pipeline.py` outside the definition; (d) sabotage: drop the evidence append -> (b) evidence assertion red; drop the scrub -> secret assertion red; COMPLETED-on-ProviderError mutant -> red.

**AF6** (a) happy: the actuator accepts a fake `Provider` and the tests use it; (b) `pyproject.toml` carries `browser-use==0.5.9` exactly (pin test), arriving in this unit's commit; (c) vendor-client import grep over `src/` outside `providers/` returns nothing; (d) importing the backend forces `ANONYMIZED_TELEMETRY=false` and `BROWSER_USE_CLOUD_SYNC=false` and prevents the import-time `load_dotenv()` from reading the repo `.env`; (e) `check_dependencies_declared` clean (via `autotester doctor`).

## 8. Gate answers

- `qa/gates/at253-agent-fallback-wiring.md:47` (verbatim): `**Answered:** 2026-09-22 — Option A (wire it in) — recorded off-disk in `docs/DECISIONS.md` D-031:`
- D-075 (`docs/DECISIONS.md:2237`): `**Approved-by:** Umesh — chat answer 2026-10-07.` Authorizes `browser-use==0.5.9`, telemetry off, read-only `cdp_url`; holds UI `agent=`/`actuator=` wiring until T-203 and T-204 land; merge only after both dual-check PASS verdicts.
- D-077 (`docs/DECISIONS.md:2274`): `**Approved-by:** Umesh — chat answer 2026-10-07.` Accepts AGPL `pymupdf` as is; re-open trigger: before AutoTester is sold, hosted for customers, or the repo is made private.
- D-081 (owner asked for all remaining work to run; queue row `t177-browser-use-fallback`, `approved: 2026-10-10`).
- **New-module authorization: `none` found in the repo.** D-072 item 2 lists T-176, T-202, T-203/T-204, the Group 10 modules, T-190 and `agents/`, not T-177; `qa/gates/new-module-authorization.md:77` reads `Answered: 2026-09-29 — A — "A: new ledger/citations.py (Recommended)", AT-710 only (standing-rule variant not chosen); Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057`. The takeover plan says only "Root confirms original exact necessary-module authority is available" (line 11) without citing a file. Cycle-0 checkers did not raise it. Precondition: root cites the exact authorizer for `stages/agent_actuator.py`, `stages/browser_use_backend.py`, `schema/agent_fallback.py`, `prompts/agent_fallback_v1.md` before Phase A, or the owner answers a one-line gate.
- No `Answered:` line exists for `T177-HARD-PROVIDER-DEADLINE`; it is open (section 10).

## 9. UI surface and persona walk

- `Persona walk: skip (no screen, route, template or visible control changes in this unit: the actuator is reached from stages/run_case_pipeline.py::fallback_executor, and D-075 holds the ui/routes_runs.py wiring until T-203 and T-204 land; docs/plan.md row 21 says skip)`.
- The checker still runs the dual security check. No AF criterion demands a live browser (verdict B, "Known gap"); the builder runs none.

## 10. Dependencies and conflicts

- Must clear before dispatch: (1) an independent plan review of `.work/t177-takeover/plan.md` returns APPROVED (a fresh reviewer, not the plan's author; it can start now); (2) the module authorizer is cited (section 8); (3) a `pyproject.toml`/`uv.lock` slot: queue line 86 says t202, t167, t174, t179 and this unit each add a dependency, one lock writer at a time. Proposed lock order: `t202` re-land (litellm) first because it is already built, then `t177` (browser-use), then `t174` (mcp). Both browser-use and mcp resolve `mcp 2.3.0` (D-071), so the second writer must re-run `uv lock` and expect no package movement beyond its own.
- Lands before: `wave/at787-bundle-wiring` (its manifest: "Merge T-177 first, then this"; it contains the T-177 commits and edits `stages/run_case_pipeline.py` and `stages/failure_bundle.py`). Land the `run_case_pipeline.py` hunk once, here.
- Shared files and proposed ONE owner each:

| File | Also edited by | Owner |
|---|---|---|
| `pyproject.toml`, `uv.lock` | t202, t167, t174, t179 | one writer at a time (above); T-177 takes its slot after t202 |
| `stages/run_case_pipeline.py` | AT-787 (after this), the codex T-178 input (not ported, see t178 brief) | T-177 first, AT-787 second |
| `stages/agent_loop.py` | T-179 (lead agent, later) | T-177 (queue: "this row") |
| `browser/session.py` (299, cap 300) | T-203 / T-204 / G1 hosting-session work | T-177 for the `cdp_url` hunk; later units must free their own lines |
| `ui/routes_runs.py` | t203, t202, t178, t205, t204 | **not touched by T-177** (D-075 hold). The `expose_cdp=True` + `agent=` / `actuator=` wiring is a follow-up row after T-203 and T-204 land; owner to be named by the queue, `unknown` today |
| `docs/MAP.md` | every branch | last commit of each unit |

- Parallel-safe with: T-178 build, T-174 plan review (disjoint files, except the lock).
- Owner decisions: (a) the module authorizer (section 8); (b) `T177-HARD-PROVIDER-DEADLINE`: accept "named outcomes for cancellable timeouts only", or authorize a provider-level deadline or process isolation (a new gate if it needs a module); (c) who owns the later `routes_runs.py` wiring row.

## 11. Budget and process rules

- Budget: **L, 45 minutes** of builder wall-clock; Phase A (port + `uv lock` + MAP) and Phase B (repair) are separate checkpoints. At 45 minutes stop and write state to the manifest.
- The builder runs only the files and nodes in section 6; no full suite (the maker runs one integration suite under the machine lock later). Unit tests use fakes: no browser-use network, no telemetry, no real provider, no credential.
- Red first: run the AF1/AF3/AF4/AF5 cases against the ported code and show them RED before the Phase B edit, then GREEN after; a red caused by an import or setup error does not count.
- Falsification only in a throwaway copy of the touched files, one named green / red / restored run per changed criterion; never leave a mutant in the tree. Kill only PIDs the builder started, verified by identity first.
- Never edit an SDK vendor file or copy one into the repo; the guard may read pinned `browser_use` 0.5.9 private state only behind the exact pin and an explicit compatibility check (plan, "Static primary SDK facts").
- Handshake is files: manifest `qa/manifests/t177-browser-use-fallback.md` with `Status: ready-for-check`, `Fix cycle: N`, `Policy-Version: proportional-verification/2026-10-10.9`, `Tier: L`, `Dual check: required`, the two `dual-trigger:` lines from section 1; verdicts from the checker at `qa/verdicts/t177-browser-use-fallback.a.md` and `.b.md`. Maker never edits `qa/contracts/`. Use `git -C D:/autoTesting ...`, never `cd X && ...`; no merge of the candidate branches.
