# Plan — AutoTester, remaining units

**Purpose:** the 26 remaining work units in dependency order — files touched, how each is tested, criticality, persona walk — and the four tasks held on a human gate.
**Open me when:** picking the next unit or wave, or asking what is deliberately not being built right now.

<!-- PLAN phase step 4, BACKFILL. Covers only what is NOT yet shipped; M0–M6 units are already
     checker-PASSed and live in docs/FEATURES.jsonl. Rows become qa/QUEUE.md TODO rows. -->

**Spec:** docs/spec.md (backfill, 2026-09-27) · **Status:** draft — awaiting approval

**Scope decisions (Umesh, 2026-09-27):** build order = everything, max parallel, bounded only by
measured RAM. Track C is built through C3 only; T-154 (adversarial pass) and T-155 (its report)
are **held for a separate approval** — no probe traffic in this push.

## Units (in dependency order; independent rows run in the same wave)

| # | unit slug | task | requirements | files it touches | how it is tested | criticality | persona walk | depends on |
|---|---|---|---|---|---|---|---|---|
| 1 | `at621-exit-call-aliases` | T-195 | design-rule guard | `src/autotester/core/doctor*` | pytest + doctor; alias/`os.path` binding cases | critical | skip (no UI surface) | — |
| 2 | `at408-416-scroll-reach` | T-185 | R13 honesty | visual-order/reach geometry | shape corpus + checker Mode D | critical | skip (geometry logic, no screen changed) | — |
| 3 | `t125-catalog` | T-125 | R8 | catalog module + schema | pytest; blocked entries name their one unblocking action | low | skip (backend) | — |
| 4 | `at335-modal-determinism` | AT-335 | R3 | crawl modal handling, `scripts/flake_probe.py` | flake probe over N runs, bounded | high | skip (crawl internals) | — |
| 5 | `at518-grandchild-pid-flake` | AT-518 | infra | probe process teardown | probe kill proven, not argued | medium | skip (infra) | — |
| 6 | `t186-details-content` | T-186 | R13 | visual-order detector | fixture rows A3/A4; max 2 cycles (gate) | medium | skip (detector logic) | — |
| 7 | `t189-stale-evidence-tag` | T-189 | governance | evidence spec + its checker | byte-intact assertion + tag a check can read | medium | skip (governance) | — |
| 8 | `t191-run-video` | T-191 | R29 | `browser/session.py`, run artifacts, run view | pytest + live browser: video only on FAIL/INCONCLUSIVE, 20 kept, secrets masked | high | required (dev) | — |
| 9 | `t192-erp-url-pattern-heal` | T-192 | data | `projects/erp` artifacts | one approved Analyze vision call; 3 corrupted `url_pattern` rows healed | medium | skip (data repair) | — |
| 10 | `t190-persona-ux-advisory` | T-190 | R28 | `schema/user_persona.py`, grade/report surfaces | pytest: a UX finding can never change a PASS/FAIL; severity scored | high | required (lead, tester) | mini-grill first |
| 11 | `t165-hybrid-traversal` | T-165 | R3, R6 | `stages/explore.py` + crawl schema | frontier exhaustion proven; every bound names what it left unreached; live crawl on the fixture site | critical | skip (crawl engine) | — |
| 12 | `t174-cli-mcp` | T-174 | R25 | CLI modules + new MCP entry point | documented exit codes asserted; `--dry-run` sends nothing; MCP tools answer | high | skip (CLI/MCP) | 3 |
| 13 | `t178-failure-bundle` | T-178 | R24 | `schema/` bundle model, report surfaces | bundle is atomic and replayable; pruning happens before LLM spend | high | required (dev) | 3 |
| 14 | `t179-deep-agents-lead` | T-179 | R26 | new `agents/` package wrapping existing stages as tools | guards proven to live in the tools, not the model; skills loaded via `skills=` | high | skip (agent layer) | — |
| 15 | `t150-track-c-governance` | T-150 | R30 | goal registration + criteria filed for the checker | the C tasks exist and the checker has criteria to write against | low | skip (governance) | — |
| 16 | `t171-permission-surface` | T-171 | R27 | crawl/exercise layer | a blocked control never counts as covered; writes only under TEST_ACCOUNT + approval | high | skip (engine) | 11 |
| 17 | `t176-script-replay` | T-176 | R23 | `Script` / `case.script_ref`, locator layer | a replayed script reproduces the run; semantic locators preferred over CSS | high | skip (engine) | 11 |
| 18 | `t166-eval-compiler-kg` | T-166 | R7 | `stages/expand.py`, new KG artifact | every generated eval traces to its source; component PASS cannot hide workflow failure | high | skip (engine) | 3, 11 |
| 19 | `t180-subagents` | T-180 | R26 | `agents/` | the grader subagent holds no action tools (C7); judge vendor named, warned when it matches | high | skip (agent layer) | 14 |
| 20 | `t151-track-c1-discovery` | T-151 | R30 | new Track C discovery module | every Signal cites a real `file:line`; no model chooses which checks run | high | skip (read-only discovery) | 15 |
| 21 | `t167-langgraph-regression` | T-167 | R21 | `stages/orchestrate.py` → LangGraph 1.x | a release trigger runs the approved suite; consent via `interrupt()`; resumes after a crash | critical | required (release-manager) | 18 |
| 22 | `t177-browser-use-fallback` | T-177 | R23 | actuator + revived `agent_loop.run_with_fallback` | an unknown screen is driven with typed outputs; AT-253 dead code is alive | high | skip (actuator) | 17 |
| 23 | `t181-agent-gain-measured` | T-181 | R26 | `agents/` + bench | measured gain vs the plain pipeline on a fixture; per-run token/cost budget enforced | high | skip (measurement) | 19 |
| 24 | `t152-track-c2-registry` | T-152 | R30 | check registry reusing T-125's Catalog | kind→checks is a literal table a checker can re-derive | low | skip | 3, 20 |
| 25 | `t153-track-c3-behavioural` | T-153 | R30 | behavioural checks over a captured run | the capturer never grades (C7); every capture scrubbed before a judge sees it | high | skip | 24 |
| 26 | `t168-damage-control-report` | T-168 | R22 | report layer | blocked/unvisited never renders as pass; one operator-readable report | high | required (lead) | 11, 21 |

## Held / blocked (not in this plan's waves)

| task | why |
|---|---|
| T-154, T-155 | Umesh 2026-09-27: build C1–C3, hold the adversarial pass for a separate approval |
| T-122, T-145 | needs TEST-account **ERP** credentials. Corrected 2026-09-27: a gitignored **repo-root** `.env` does exist and holds `PATHLYNKS_USER_*` / `PATHLYNKS_COUNSELLOR_*` key names, so Pathlynks-targeted live work is credential-capable — but `ERP_EMAIL`/`ERP_PASSWORD` are absent from every store and no `projects/*/.env` exists, which is what T-122's gate (D-048) names as its unblock condition. T-145 additionally needs a fresh D-018 RunApproval per run |
| T-136 | `ERP_Issues_Trainers.xlsx` truth sheet is not on disk |
| T-169 | depends on all three above |

## Persona walk rule

Required when a unit adds or changes a screen, a navigation path or a user-facing flow, or touches
onboarding/sign-in/payment. High criticality alone does not trigger one — the unit must also touch
a UI surface. Audience is `internal-tool`, so a required walk covers 1–2 user types, not all five.

## Release slices

- **S1** — units 1–9: the in-flight branches plus the gate-answered leaves. Ledger clean, no new
  capability claimed.
- **S2** — units 10–15: UX advisory, the traversal engine, the CLI/MCP surface, the failure bundle,
  the agent-layer skeleton, Track C governance.
- **S3** — units 16–20: permission surface, script replay, the eval compiler + KG, subagents,
  Track C discovery.
- **S4** — units 21–26: LangGraph regression, browser-use fallback, the measured agent gain,
  Track C2/C3, and the unified damage-control report.

## Risks

1. **RAM is the binding parallelism ceiling** (3.9 GB free of 23.7 measured 2026-09-27) — waves get
   trimmed to what fits, so "max parallel" is bounded by the machine, not by the plan. Noticed in
   each tick's `concurrent peak=` line.
2. **T-165 is the spine** — units 16, 17, 18 and (through 18) 21 and 26 all sit behind it. A stall
   there stalls S3 and S4. Noticed as a STALLED stamp with a `qa/debug/` report.
3. **The agent layer may not earn its place** — T-181 measures it against the plain pipeline, and a
   negative result means it is removed, not patched. Noticed in T-181's own bench numbers.

## T-190 concrete PLAN proposal — 2026-10-06

Status: proposed, not implementation-approved or shipped. This supplements unit10/R28;
it does not replace the canonical goal dependencies or turn an advisory finding into a
functional verdict. Product direction is already answered A in
`qa/gates/meeting-user-persona-ux-judging.md`; do not ask that question again.
The implementation/count preview and review receipts live in the existing
`qa/manifests/t190-plan-preparation.md`.

The contract's five required plan choices are:

1. Use the project's configured functional judge through the existing Provider registry,
   with a separate UX prompt/output schema. Preserve vendor/model/fallback order; the UI's
   currently hardcoded provider is not evidence of correct configuration resolution.
2. Proposed opt-in default:20 physical call attempts per run, serial across eligible cases,
   failed attempts and retries spent. This is not a money/token ceiling. Enforce the shared
   budget below retry/redirect/fallback dispatch; unsupported transport/output-limit
   capabilities refuse before a call with a typed reason. Record exhausted remaining cases
   as advisory skipped_budget; functional results remain unchanged. The numeric limit,
   payload/output limits and complete installed-adapter wiring still need plan approval.
3. Persist one typed `projects/<slug>/runs/<run_id>/ux_report.json`, separately from result
   and verdict files. Include per-case findings, exact evidence path/step, severity, effective
   conditions and safe error/skip status. Absent, malformed and incomplete are distinct;
   exports must never turn a failed UX load into a completed empty report.
4. Store typed personas in `projects/<slug>/user_personas.jsonl`; attach optional refs on
   both Project and Case, case override first. Validate project-local ids, guard complete
   snapshot values before persistence, and preserve refs during fixed-step construction.
5. `ux_enabled=False` by default. Explicit opt-in snapshots run inputs, then performs one
   read-only UX pass after functional results/verdicts persist, in stable case order. No
   rerun of product actions; advisory failure must not abort functional reporting.

Condition claims are evidence-local:measure each successful screenshot's capture interval,
not merely equal start/end samples for the case. Unknown/unsupported locale or device
conditions cannot support persona findings. Keep Verdict/Judgment and functional rubric
construction untouched; require byte-identical functional verdicts with and without UX.

Exact creation approval was requested once for the six proposed schema/stage/store/prompt/test
paths listed in the manifest. It remains pending; no file is created by this proposal.
The remaining implementation gate is a complete independently approved candidate patch/count
proof plus installed-provider budget fidelity. These engineering obligations, full-suite,
falsification, export/browser checks and final independent acceptance remain mandatory.
No paid run, live write, contract change, architecture change or product PASS is authorized here.
