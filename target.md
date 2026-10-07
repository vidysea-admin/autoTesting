# AutoTester — Target & Roadmap

**What this file is.** The human-readable roadmap: what is *shipped* vs what is *target*, as a
step-by-step checklist, so any session (human or agent) can open it and know exactly where we are
and what is next. The machine backlog with done-checks is `.goal/goal.json` (55 tasks); this is the
milestone view over it. Open me at session start alongside `docs/SNAPSHOT.md`.

**Legend.** `[x]` ✅ shipped & checker-verified · `[~]` 🟡 shipped, proven on fixtures only (not yet
on a real product) · `[!]` 🔒 blocked on a human input · `[ ]` 🎯 target, not built yet.

**Read the honesty rule first:** a box is ticked only when the code exists AND a checker/test proved
it. Coverage never counts an unexplored branch as tested. Goal statements say "AutoTester **will**";
status statements say "currently does".

---

## The two-layer goal

### North Star (the one line)
> **Give AutoTester a product, not a test script.** It will independently discover how the product
> works, systematically explore its meaningful states and branches, decide what is working or
> suspicious, preserve evidence of every failure, and re-verify the product after every release.

### Two sentences to remember
- **Vision:** explore the product like a *graph*, not a *journey*.
- **Proof:** find the same real defects as a strong human tester — with fewer false positives,
  transparent coverage, and reproducible evidence.

### Product goal (full, "AutoTester will…")
AutoTester will be an autonomous end-to-end software-testing platform that can learn, explore and
validate a web application with minimal prior knowledge. Given a URL, scoped test credentials and
optional evidence (business flows, requirements, videos, screenshots, docs, existing test cases), it
will progressively build a persistent model of the application's screens, states, actions and
workflows. Rather than following one likely journey, it will maintain the application's **unexplored
testing frontier**: every meaningful action from a state is either exercised or explicitly accounted
for as pending / blocked / unsafe / unsupported / intentionally skipped — never silently dropped.
The engine will combine bounded graph-exploration strategies (breadth-first discovery, deeper
workflow traversal, structural state deduplication, loop detection, reliable backtracking & state
restoration, risk-based prioritisation). For each workflow it will test the expected path plus
negative, boundary, edge, permission, recovery and adversarial scenarios. Where verified business
knowledge exists it is the explicit **oracle**; where it is absent, AutoTester runs in discovery
mode and clearly separates confirmed regressions from AI-inferred suspicion. Every action yields
traceable evidence (what was attempted, prior state, what changed, why it was classified as it was).
Coverage measures exercised-vs-discovered; untested branches stay visible. After releases it reuses
its product understanding to re-exercise workflows, find regressions, reproduce the exact failing
path, and report failures + remaining gaps. Later versions extend below the UI (API / backend /
infra signals) for authorization, security, reliability, integration and performance defects. First
acceptance targets: Vidysea ERP and Pathlynks. First proof of quality: a measured comparison against
human testers on defects found, false-positive rate, coverage and effort.

---

## The differentiator (BFS/DFS is a mechanism, not the moat)

State-graph crawling is not new (Crawljax ~2010s; QA.tech commercially today). AutoTester's edge is
the **product**, not any one algorithm:

> Exploration quality × Oracle quality × State restoration × Coverage honesty = AutoTester quality

If exploration is great but every oddity is called a bug → useless. If the oracle is brilliant but
only 8% is seen → insufficient. Both must hold together.

---

## Issue classification (the credibility layer) — 🎯 target taxonomy
Every finding must carry exactly one label, so AI inference is never dressed as fact:
`CONFIRMED REGRESSION` · `LIKELY DEFECT` · `SUSPICIOUS BEHAVIOUR` · `UX / CONSISTENCY ISSUE` ·
`PERFORMANCE ANOMALY` · `SECURITY CONCERN` · `UNABLE TO VERIFY` · `EXPECTED / PASSED`.
*(Today: execute/grade produce PASS/FAIL/INCONCLUSIVE verdicts; the richer taxonomy is target.)*

---

## Target pipeline (DISCOVER + MODEL become first-class)
**Today (shipped):** `INGEST → EXPAND → EXECUTE → GRADE → REPORT/COVERAGE → BENCH`, with crawl/
explore a standalone **Track B** capability that hydrates the FlowSpec — *not* a canonical stage.
**Target:**
```
INPUT → { INGEST(evidence) | DISCOVER(app) } → MODEL(state/action graph) → EXPAND
      → EXPLORATION FRONTIER → EXPLORE+EXECUTE → OBSERVE → GRADE → EVIDENCE
      → COVERAGE → REPORT → LEARN → RE-RUN
```
DISCOVER and MODEL are primary stages, not side features. 🎯 (promotion tracked as T-163.)

---

## Milestones — what's built vs what's next

### M0 · Foundations & governance — ✅ done
- [x] T-000 P0 design lock: schema, core, provider seam, doctor, ARCHITECTURE
- [x] T-004 schema research scout → `docs/research/schema-2026-09.md`
- [x] T-005 living map + feature ledger + CLAUDE.md router + doctor freshness
- [x] T-020 filestore: every artifact JSON/JSONL under `projects/<slug>/`
- [x] T-121 governance: register plan.md, goal tasks, Track A/B backlog
- [x] T-160 revised-goal governance (D-023: the T-16x roadmap registered)

### M1 · Credential boundary & browser substrate — ✅ done
- [x] T-011 `.env` → `{{SECRET:KEY}}` fill-time injection, domain-scoped (security-critical)
- [x] T-010 headed Playwright + persistent profile + screenshot masking
- [x] T-045 read-only Mongo assertion helper (production Mongo never written)

### M2 · Core pipeline stages — ✅ built / 🟡 fixture-proven
- [x] T-060 ingest: video/docs → FlowSpec with SourceRefs
- [x] T-065 FlowSpec review gate (nothing drives off an unreviewed spec)
- [x] T-070 expand: FlowSpec → best/worst/edge cases per CaseClass
- [x] T-040 execute: script-first runner → RawResult + Evidence (observe only)
- [x] T-041 grade: independent stateless judge (rejects fake-pass, no evidence)
- [x] T-080 agent fallback loop → durable re-runnable script
- [x] T-055 multi-vendor provider fallback (Anthropic→Gemini→Ollama→ChatGPT)
- [x] T-090 coverage: route/screen diff → CoverageGap → VideoRequest
- [~] T-120 bench: human-vs-AI scorecard — *engine shipped; only real numbers come from T-136*

### M3 · First real proof on a product — ✅ done
- [x] T-030 onboard Pathlynks (project.json + knowledge file)
- [x] T-050 first real run: 3 hand-written Pathlynks cases verdicted in a headed browser
- [x] T-110 regression proof: break a staging feature, confirm exactly that case FAILs

### M4 · Exploration engine (Track B) — ✅ shipped, with named gaps
- [x] T-140 observation primitives + actuator choke-point
- [x] T-141 screen identity (url templating + structural signature) + crawl schema/store
- [x] T-142 explorer safety layer (deny-list, write-policy matrix, dialog breaker)
- [x] T-143 bounded **BFS** crawl stage + `qa/contracts/explore.md` (checker-PASS)
- [x] T-144 crawl → FlowSpec merge + exercised/discovered coverage + crawl report
- [x] T-124 consent gates as an artifact (RunApproval) — real done-check for T-145
  - Shipped ✅: screen-level FIFO frontier · state dedup · loop detection · 5-step restoration
    ladder · enumerate-all-controls-per-screen · honest coverage (45/677 = 6%).
  - 🎯 **edge-level `(state,action)` frontier** — today a bound (`per_node_action_cap=25`) turns
    remaining actions into coverage *holes*, not persisted future work. (folded into T-165)
  - 🎯 **DFS / adaptive / risk-first traversal** — today BFS only. (target)

### M5 · Video-learning (Track A) — ✅ done (real ERP recordings)
- [x] T-130 video-learning schema + storage · [x] T-131 hardened Gemini vision provider
- [x] T-132 host media prep (probe/chunks/transcript/frames)
- [x] T-133 two-model ensemble + deterministic adjudication + Issue derivation + Excel + scorer
- [x] T-134 product map / journeys / issues / sources pages · [x] T-135 coverage/merge/expand reconnected

### M6 · Unified intake & no-CLI UI — ✅ done
- [x] T-100 FastAPI onboarding, masked `.env` editor, live run view, report
- [x] T-161 unified project intake (URL, credential refs, evals, conditions, use cases, sources)

### M6b · Evidence, advisory UX & hardening (issue-driven units, D-048/D-050) — mostly ✅
*These eleven units (T-185..T-195) existed in `.goal/goal.json` and were missing from this roadmap
until 2026-09-27 — nine of them already done. Recorded here so the milestone view stops
under-reporting the build.*
- [x] T-191 run video on FAIL/INCONCLUSIVE only, last 20 retained, secrets masked as in screenshots
      (contract `run-video.md` V1–V8, D-050). **Open follow-up: `ISS-t191-run-video-2` — a kept video is
      reachable by no human through any shipped path; `run_view` filters on SCREENSHOT only. In build.**
- [ ] T-190 advisory UX track: `UserPersona` (role, tech comfort, locale, device) + severity-scored UX
      findings that **never** change PASS/FAIL (AT-583/AT-584, contract `persona-ux-advisory.md`
      PU1–PU9, D-048/D-050). **Needs the maker PLAN gate + a grill with Umesh before any code.**
- [x] T-186 closed `<details>` judged by `::details-content` display as well as `content-visibility` (D-049)
- [x] T-189 stale evidence spec stays byte-intact and carries a distinguishable "stale on purpose" tag
- [x] T-192 one approved Analyze re-run healing the 3 corrupted `url_pattern` rows on the erp project
- [x] T-187 session-start hook calls `autotester loop-status --strict` and prints its report
- [x] T-188 `--expires <date>` means end of that day for newly minted approvals
- [x] T-193 base64-of-UTF-16 (PowerShell `-EncodedCommand`) no longer bypasses either redaction door
- [x] T-194 `redact_encodings.py` docstring corrected (credited a removed `lru_cache`)
- [x] T-195 `_is_exit_call` now catches `os._exit(1)` and aliased `sys` (`import sys as s; s.exit()`)
- [ ] T-185 re-check `wave/at408-416-scroll-reach` (merge master, fresh cycle, real-Chromium Mode D)

---

## THE PROOF (must clear before AutoTester counts as "working on a real product")

### M7 · Real-product trust number — 🔒 human-gated, then 🎯
*Umesh 2026-09-24: prove it on **Pathlynks first**; a second product's test account (ERP or any other)
comes only after that — "not only erp". T-122/T-145/T-136 get re-scoped to "second product".*
- [!] T-122 login case + first logged-in run on the second product — credentials after Pathlynks is proven
- [!] T-145 live bounded READ_ONLY crawl of the second product — needs T-122 + consent (CRITICAL, dual-check)
- [!] T-136 score recordings vs a trainer truth sheet → real recall/FP/time — **needs the truth sheet**
- [ ] **T-136a (D-052, 2026-09-27): a fixture-derived trust number now** — build and review the
      recall / false-positive / time harness against a fixture product so it is proven before real
      inputs exist. Labelled **fixture-derived in `schema/bench.py`'s own fields**, never only in prose,
      and never rendered where a reader could take it for the real number. It does **not** tick M7 and
      does not close T-136. Its own proof is falsifiability: it must produce a *wrong* score on a
      known-bad fixture, or it has not been proven.
      **Ordering requirement (AT-653, D-053):** Umesh authors the human findings *after* reading
      AutoTester's report, and a list written after seeing the machine's output is anchored to it — the
      bugs AutoTester **missed** are the ones such a list is least likely to contain. So **FP rate
      survives that ordering and recall does not.** The comparison artifact therefore carries an
      `ordering` field and, when he reads first, an independent-vs-prompted mark per human item, with
      **recall computed from the independent subset only.** The fields exist before the number does.
- [x] T-123 medium credential-safety batch — AT-085 `/healthz` + AT-065 rubric stamp ✅ (18ff2a9); AT-086/087 ✅ merged 6e5c806 (checker FINAL PASS + Mode D; gate answered: both a)
- [ ] T-125 test catalog (runnable/blocked + cheap→expensive) — D-039 ✅, contract `catalog.md` DRAFT
- [x] T-126 governance debt sweep — maker side ✅ (allowlist + FEATURES backfill, checker PASS, merged); AT-560 follow-up ✅ merged f94c5c2; closed by checker sweep 2026-09-25
- [x] AT-110 tamper-proof consent approvals (HMAC keyed from `.env`) — ✅ checker PASS cycle 2 + live Mode D, merged 48aba2f
- [x] AT-483 orphaned-crawl liveness — re-landed onto master (2d58215) after its 09-18 PASS never merged

*Status truth: the plumbing is real, but everything downstream of a **learned** FlowSpec is
fixture-proven only. The ERP trust number is the first time AutoTester is measured against a human.*

---

## THE PRODUCT VISION (reusable platform) — 🎯 target, mostly unbuilt

### M8 · Systematic exploration upgrades
- [x] T-163 resumable learn-or-explore orchestrator + durable per-stage checkpoints (F-045, dual PASS) — ✅ live caller `autotester orchestrate` (AT-575, merged ec98b33)
- [x] T-170 first-party API/network assertions (D-040 split from T-165) — F-047, checker PASS, merged 1fc7276
- [ ] T-165 hybrid BFS→bounded-DFS traversal + frontier completeness + form-input replay + persona-seeded
      incremental crawl + change tracking — 🎯 **NOT DONE (corrected 2026-10-07; AT-744..756 sweep).**
      The 2026-09-27 D-040 dual PASS at cycle 2 (F-062/F-063, merged 162c3dc7) was **reopened 2026-09-30**:
      an independent checker reproduced AT-113 (crawl reports completed with an empty frontier while
      the product still has unreached states). `at113-crawl-completion` cycle 3 **FAILed / STALLED**,
      and **cycle 4 is pending** — its runtime blocker was lifted by D-070 (2026-10-07: the local visible
      browser runs directly, sandbox-egress precondition dropped), but it has not run. goal.json has T-165
      `pending`. Contract `crawl-traversal.md` stays ACTIVE; the claim "frontier exhausted" is what is unproven.
      **Disclosed residual (separate from AT-113):** two states at one URL where one is genuinely deleted is
      reported nowhere (`ISS-t165-crawl-traversal-a8`) — a sound closure needs per-signature reachability.
- [ ] T-171 permission-surface coverage — every reachable control exercised or blocked-with-reason (D-040).
      **Unblocked by T-165 as of 2026-09-27; also waits on `at638-four-contract-files-authorization`.**
- [x] T-173 parallel case execution — ✅ merged 626fa03 + live UI wiring ef1b043 (at562-564: per-case evidence, crash isolation; checker PASS c3 + Mode D). Open: AT-574 serial-path resilience, AT-570 RunApproval (T-122)

### M9 · Durable product model
- [x] T-164 durable **Portal Persona** JSON + knowledge page + change history (F-046, 3ceb7b9)
- [x] T-162 multi-source adapters (Drive, video, audio, doc, email, text → one evidence model) (F-044)
- 🎯 Knowledge graph = the persona graph extended (screen/control/flow/scenario/case/verdict/API/release;
  JSON, no graph DB) — built inside T-166 (D-041)

### M10 · Compile, re-run, report
- [ ] T-166 traceable eval compiler (rules + scenarios + taught flows + persona + discoveries → best/worst/edge) + KG
- [ ] T-167 commit/release-triggered visible-browser regression — **built on LangGraph 1.x** (D-041)
- [ ] T-168 unified damage-control report (regression diff, API failures, workflows, screenshots, Excel)
- [ ] T-176 persist + replay generated script, semantic locators (competitor A+C, D-041)
- [ ] T-178 atomic failure bundle + case priority p0–p3 + human pruning of proposed cases (competitor D+H+G)

### M10b · Platform & AI-framework layer (D-041, 2026-09-24; Agents row superseded by D-042, 2026-09-24)
| Layer | Choice | Unit |
|---|---|---|
| Workflow graph | LangGraph 1.x, from T-167 (stages migrate only when touched) | T-167 |
| Agents | LangChain Deep Agents lead tester + subagents (explorer, designer, runner, independent grader, reporter), after Wave 1 — T-179..T-181 (D-042, supersedes D-041's no-multi-agent) | T-179 · T-180 · T-181 |
| Skills | prompts as `SKILL.md` | T-175 ✅ merged 9b3fd5e (checker PASS) |
| Tools / MCP | Playwright (deterministic) · browser-use fallback · AutoTester as MCP server + CLI contract | T-177 · T-174 |
| Observability | local redacted `trace.jsonl` → Langfuse self-hosted on a server | T-172 ✅ merged 7975c81 (local trace; live caller = AT-564) |
- Prompts ship as `SKILL.md` skills (T-175) while crawl / run_case / get_persona / get_catalog / capture_network / grade_case / report stay plain tools with deterministic guards (safety, credentials, write-policy) inside them, not left to the model (D-042).
- Refused: "regenerate tests instead of maintaining them". Deferred to Umesh: differential base-vs-head oracle.

### M11 · Adversarial / below-the-UI (Track C) — 🎯 unblocked for BUILD only (D-052, 2026-09-27)
*UPDATE 2026-09-27 (later, `qa/gates/write-policy-tier.md`): T-154/T-155 are **still held**, now with
a condition — "Pehle proof run ho, phir kholenge" (the proof run first, then we open them). This is
compatible with the build-not-fire split below, since C4/C5 were never in it.*
*Umesh 2026-09-27 released T-154/T-155 from their hold. **The machinery is unblocked; firing it is not.**
No adversarial probe traffic against any real target without a separate per-run approval naming the
target and the consent scope — consent gate 2 existing is not permission to use it. T-154 is proven
against a fixture target only, and `adversarial_proof.py` must first demonstrate that the pass refuses
to exceed its declared scope. `write_policy` stays `read_only`.*
- [ ] T-150 Track C governance (file ai-target.md + adversarial.md criteria for the checker)
- [ ] T-151 read-only AI-target discovery + deterministic signals + classification
- [ ] T-152 AI check registry + catalog matching · [ ] T-153 behavioural checks graded by the judge
- [ ] T-154 bounded adversarial pass behind consent gate 2 (HIGHEST-RISK unit) · [ ] T-155 unified tiered AI report

### M12 · The finish line
- [ ] T-169 generic two-mode acceptance (rich-teaching mode AND url+credentials-only mode), no CLI,
      measured vs a human on bugs / false positives / coverage / time — **this is "done".**

---

## Definition of done (product-level)
1. ERP trust number exists (T-136): real recall / false-positive / time vs the trainer truth sheet.
2. Both intake modes work on a real target and beat-or-match a human tester (T-169).
3. Every finding is evidence-backed and correctly classified; coverage shows untested branches.

## Progress (from `.goal/goal.json`, 2026-10-07): **59 / 90 done (66%)**

**Roadmap reconciliation, 2026-09-27:** this file previously read "47 / 70 done (67%)" and listed no
tasks above T-184. `T-185..T-195` were in the machine backlog and absent here — **nine of the eleven
already done.** They are now in M6b. The roadmap was under-reporting the build by eleven tasks, which
is the opposite of the failure mode this file exists to prevent, so the count is now derived from
`.goal/goal.json` rather than maintained by hand.

**Landed 2026-09-27:** ~~T-165 hybrid BFS→bounded-DFS traversal~~ (**reopened 2026-09-30, not done** —
see M8; AT-113 cycle 4 pending under D-070) · T-186, T-189, T-192, T-193, T-194, T-195, T-191 · `at438-answered-gate-remainder`
· `at638-done-check-repair` · `.gitattributes` union-merge for the ledger.

**Decisions taken 2026-09-27:** **D-051** T-125 proceeds by specifying flow relevance in
`qa/contracts/catalog.md` first, then exactly one scoped cycle 4 (the 3-cycle cap is broken by one,
deliberately, because its premise — a maker failing at a *specified* task — was never met).
**D-052** Pathlynks stays first; a **fixture-derived** trust number is built now so the scoring harness
is proven before real inputs exist; Track C (T-150..T-155) is unblocked **for build, not for firing** —
adversarial probe traffic against any real target still needs a separate per-run approval naming the
target and consent scope.

**Critical path:** T-125 gates four tasks (T-152, T-166, T-174, T-178) and is the single highest-value
unblock. T-176 is free behind T-165 (T-171 has since landed). **Note (D-070, 2026-10-07):** T-125 and T-165 are runtime-unblocked. T-169 remains the definition of done and remains
gated on inputs only Umesh supplies.

**Write policy (D-053, 2026-09-27):** `ALLOW_WRITES` is the authorized **ceiling** on every target
including production (Umesh, `qa/gates/write-policy-tier.md`) — and **no project is set to it.** All
nine `projects/*/project.json` remain `write_policy: read_only`. Raising one is a separate act under
its own entry plus a per-run `RunApproval`. The gate's own residual is why: `send` and `pay` are
outward-facing to **third parties** and no policy, approval or rollback undoes them, so runs are
approved with a **narrower** scope than the tier permits — and T-171 wires against that narrower
per-run scope, never against the tier.

**Blocked on a human:** T-122 / T-145 / T-136 (Pathlynks proof, then credentials, then a truth sheet) ·
T-190 (PLAN gate + grill) · `qa/gates/at638-four-contract-files-authorization.md` (blocks T-166/167/168/171) ·
`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` (a second, independent reason T-125 cannot reach 8/8).

_Machine backlog + done-checks: `.goal/goal.json`. Whole-project screen: `docs/SNAPSHOT.md`._
_Note: rewriting `.goal/goal.json`'s north star or adding DISCOVER/MODEL to `docs/ARCHITECTURE.md`
is a state change that needs an authorizing `docs/DECISIONS.md` entry first (Lab Protocol) — this
roadmap doc does not require one._
