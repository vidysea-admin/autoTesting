# Spec — AutoTester

**Purpose:** the requirements (R1-R31) mapped to the outcomes they serve and the contract that judges each one, plus the navigation flow per user type.
**Open me when:** deriving a contract criterion, picking a unit, or deciding which user types a persona walk must cover.

<!-- PLAN phase step 3, BACKFILL. Requirements below are derived from docs/intent.md and from the
     criteria already living in qa/contracts/ (checker-owned). Where a contract already states a
     rule, this file points at it rather than restating it — one concept, one place. -->

**Intent:** docs/intent.md (backfill, 2026-09-27) · **Status:** draft — awaiting approval

## Requirements

| id | requirement | serves | priority | contract |
|---|---|---|---|---|
| R1 | Onboard a product from one form: URL, credential refs, evals, conditions, use cases, sources | O1 | must | `ui.md`, `pathlynks-onboarding.md` ✅ |
| R2 | Learn flows from teaching material (video, audio, doc, email, Drive, text) into one evidence model | O1 | must | `ingest.md`, `source-adapters.md`, `video-learning.md` ✅ |
| R3 | Discover flows without teaching material, by bounded crawl from URL + credentials | O1 | must | `explore.md` ✅, `crawl-traversal.md` 🎯 |
| R4 | Nothing drives off an unreviewed FlowSpec — a human review gate stands between learning and testing | O3 | must | `review-gate.md` ✅ |
| R5 | Keep a durable per-product model across runs, with change detection and dated history | O1 | must | `portal-persona.md` ✅ |
| R6 | Maintain the exploration frontier: every action from a state is exercised or explicitly accounted for as pending / blocked / unsafe / unsupported / skipped — never silently dropped | O4 | must | `crawl-traversal.md` 🎯 |
| R7 | Generate best / worst / edge cases per applicable CaseClass, with source traceability | O2 | must | `expand.md` ✅, eval compiler 🎯 |
| R8 | Say which case classes are runnable, which are blocked, and the one action that unblocks each | O4 | must | `catalog.md` 🎯 |
| R9 | Execute in a real visible browser; the executor only observes, it never grades | O2, O3 | must | `execute.md`, `run-case-pipeline.md` ✅ |
| R10 | Grade with an independent stateless judge that sees the screenshots and rejects a fake pass | O3 | must | `grade.md` ✅ |
| R11 | Capture first-party API/network traffic as evidence; a test may assert expected calls | O3 | must | `network-assertions.md` ✅ |
| R12 | Report every failure with its criterion, judge reason, fix_hint and repro steps, in HTML and Excel | O3 | must | `report-export.md`, `ui-report.md` ✅ |
| R13 | Coverage reports exercised-vs-discovered and keeps untested branches visible | O4 | must | `coverage.md` ✅ |
| R14 | Raise a VideoRequest when a screen is not understood, instead of guessing | O5 | must | `coverage.md` ✅ |
| R15 | A known bug becomes a pinned regression case that runs every time and cannot be deleted | O2 | must | `execute.md` ✅ |
| R16 | Credential boundary: SecretRef only, fill-time substitution inside allowed domains, masked in screenshots/logs/video/prompts | O7 | must | `browser-and-secrets.md` ✅ |
| R17 | Consent: writes and crawls of a real product need a RunApproval; no approval means zero requests, asserted at the transport | O7 | must | `consent.md` ✅ |
| R18 | Resumable pipeline: durable per-stage checkpoints, a crash resumes at the first non-done stage | O2 | must | `orchestrator.md` ✅ |
| R19 | Redacted per-run trace (stage + LLM spans: model, tokens, latency, cost) | O3 | must | `run-trace.md` ✅ |
| R20 | Parallel case execution in isolated browser contexts, bounded by measured RAM/CPU | O2 | should | `parallel-run.md` ✅ |
| R21 | Commit/release-triggered regression against the last trusted baseline, with consent and resumable retries | O2 | must | 🎯 T-167 |
| R22 | One unified damage-control report: regression diff, API failures, workflows, screenshots, Excel | O3 | must | 🎯 T-168 |
| R23 | Persist and replay a generated script with semantic locators and declared test-id priority | O2 | should | 🎯 T-176 |
| R24 | Atomic failure bundle + case priority p0–p3 + human pruning before LLM spend | O3 | should | 🎯 T-178 |
| R25 | CLI contract (`--output json`, documented exit codes, `--dry-run`) + MCP server | O2 | should | 🎯 T-174 |
| R26 | Agent layer: a lead tester plus subagents over deterministic stage tools; guards live in the tools, not the model; kept only on measured gain | O2 | should | `agent-layer.md` 🎯 |
| R27 | Permission-surface coverage: every reachable control exercised or listed blocked-with-reason | O4 | must | 🎯 T-171 |
| R28 | Advisory UX findings with a UserPersona, severity-scored, that NEVER change PASS/FAIL | O3 | should | `persona-ux-advisory.md` 🎯 |
| R29 | Run video on FAIL/INCONCLUSIVE only, last 20 kept, secrets masked exactly as in screenshots | O3 | should | `run-video.md` 🎯 |
| R30 | Below-the-UI AI-target checks: read-only discovery, deterministic signals, a check registry, behavioural checks graded by the existing judge | O3 | should | 🎯 T-150–T-153 |
| R31 | Two-mode acceptance measured against a human on bugs / false positives / coverage / time | O6 | must | `bench.md` ✅ engine, 🎯 numbers |

✅ = shipped and checker-verified · 🎯 = target. R31's numbers are gated on Umesh (credentials
plus the trainer truth sheet).

## Navigation flow per user type

### `dev`
- **Entry:** the run view for the run their commit triggered.
- **Main goal in ≤ 3 steps:** run view → failing case → its criterion + judge reason + repro steps.
- **Must understand without being taught:** which cases failed; why the judge said so; how to
  reproduce it locally; what was NOT covered by this run.
- **Happy path:** all cases PASS, and the run view still names the coverage that stayed unexplored.
- **Negative paths:** a case is INCONCLUSIVE (evidence too weak to judge) · the browser crashed
  mid-case and only that case is affected · no baseline exists to diff against.

### `tester`
- **Entry:** the onboarding form.
- **Main goal in ≤ 6 steps:** onboard → add sources or start a crawl → review the FlowSpec →
  review the catalog (runnable vs blocked) → prune the proposed cases → run.
- **Must understand without being taught:** that nothing runs off an unreviewed spec; which cases
  are blocked and the one action that unblocks each; which credentials are needed, and that only
  a key name is ever stored.
- **Happy path:** a freshly onboarded product reaches its first real run without touching a CLI.
- **Negative paths:** a domain outside `allowed_domains` · a crawl refused for want of consent ·
  a screen the model does not know → VideoRequest · a credential pasted into a case step (refused).

### `lead`
- **Entry:** the home dashboard.
- **Main goal in ≤ 2 steps:** dashboard → the damage-control report for the latest run.
- **Must understand without being taught:** what broke since the last trusted baseline; what was
  never explored; the confidence label on each finding; the trust number against a human.
- **Negative paths:** a report whose coverage is low must not read as green.

### `trainer`
- **Entry:** the sources page for a product, or a VideoRequest link.
- **Main goal in ≤ 3 steps:** open the request → see which screen is missing → upload the recording.
- **Must understand without being taught:** exactly which screen or flow is missing, and why.
- **Negative paths:** an unreadable or silent recording is reported as unreadable, never as an
  empty-but-verified transcript.

### `release-manager`
- **Entry:** the release/regression trigger.
- **Main goal in ≤ 2 steps:** trigger the approved suite → approve the consent gate → verdict.
- **Must understand without being taught:** which product and account the run touches; that
  `write_policy` bounds what it may do; that the run resumes rather than restarting after a crash.
- **Negative paths:** approval absent or expired → zero requests sent · run interrupted → resumes
  at the first non-done stage.

## Flow → user types map

| flow | user types |
|---|---|
| onboarding + intake | tester |
| teaching / sources / VideoRequest | trainer, tester |
| crawl + consent | tester, release-manager |
| FlowSpec review gate | tester |
| catalog + case pruning | tester |
| run trigger + run view | dev, release-manager |
| report + coverage + damage control | lead, dev |
| settings / providers / .env editor | tester |

## Out of scope (now)

- T-154 bounded adversarial pass and T-155 its tiered report — held pending a separate approval
  (Umesh, 2026-09-27). No probe traffic is sent in this push.
Decision claim D-041: "**Refused:** \"regenerate tests instead of maintaining them\" (docs/research/testsprite-2026-09.md §6)." <!-- decision-claim: {"id":"D-041","what":"**Refused:** \"regenerate tests instead of maintaining them\" (docs/research/testsprite-2026-09.md §6)."} -->
Decision claim D-041: "**Deferred to Umesh:** the differential base-vs-head oracle (research item E). It needs two deployable builds of the app under test." <!-- decision-claim: {"id":"D-041","what":"**Deferred to Umesh:** the differential base-vs-head oracle (research item E). It needs two deployable builds of the app under test."} -->
- Any run against a live user's credentials, or any write to production Mongo.

## Seeds

- `qa/adapter.json` `personas` ← one entry per user type above (seeded by T-190).
- `qa/scenarios/<feature>.csv` ← one row per happy/negative path above.
