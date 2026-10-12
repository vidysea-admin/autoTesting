# Brief — t153-behavioural-checks (T-153, Track C3)

Written 2026-10-11 by a readiness pass (read-only; no build, no test, no browser). Everything below was measured against `master` 3a16616cf2c99a63c8d763150a1ca6410dfc0acc and the named branches. Re-read `git -C D:/autoTesting rev-parse master` before branching; if it moved, re-check the files in section 5.

**Verdict: READY.** The product code is already written and reviewed through checker cycle 1 on `codex/t153-completion`. The builder's job is to re-land it as one clean unit on a fresh branch from master and hand the checker a closed manifest. It is not a green-field build.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier L.** Trigger: security. The unit admits or refuses secrets before any byte is sent and calls the consent gate at the capture seam (`src/autotester/stages/ai_capture.py:91-97` on `codex/t153-completion@31631ecb`: the `assert_clean` loop at 91-94, `require_approval` at 95). The earlier Codex manifest cited `:88`; that line is the `wall_clock_s` check, not the gate. Use 91 and 95.
- **Dual check: required.** Trigger: `security src/autotester/stages/ai_capture.py:91` (secret admission before transport; C5) and `:95` (signed-consent gate before transport; D-018). Re-measure the lines after the cherry-pick and write the measured ones in the manifest.

## 2. Root and base

- Root `D:/autoTesting`. Base = current `master` (3a16616cf2c99a63c8d763150a1ca6410dfc0acc at writing).
- **Branch: a fresh `wave/t153-behavioural-checks` from master.** Do not build in `codex/t153-completion` or `t152-153`.
  - Why not `codex/t153-completion` (HEAD 31631ecb, 4 commits ahead of ff7f4ff2, 9 behind master, merges into master with 0 conflicts): D-080 item 1 makes Codex-branch work an input to re-land unit by unit, and `qa/QUEUE.md` (t153 row) says "INPUT only". Its worktree `D:/autoTesting/.worktrees/codex-t153-completion` is dirty (modified `qa/manifests/t153-completion.md`; untracked `qa/checkpoints/t153-completion*.md` and `qa/verdicts/t153-completion*.md`). That is checker evidence; do not touch, move or delete any of it.
  - Why not `t152-153` (worktree clean, 2 ahead / 32 behind, 3 conflicts with master in `docs/MAP.md`, `qa/manifests/t152-ai-check-registry.md`, `src/autotester/schema/ai_check.py`): its T-152 commit is superseded by the T-152 release already on master, and its T-153 commit (97103cf3, manifest cycle 0, no verdict) was rebuilt by the Codex branch.
- **Method:** on the fresh branch, apply the two product commits from the Codex branch without their evidence files: `git -C D:/autoTesting/.worktrees/<new> cherry-pick -n 544b95ce b0abd1d7`, then unstage `qa/manifests/t153-completion.md` and `docs/MAP.md` (regenerate MAP with `uv run autotester map`). Commit `544b95ce` = build; `b0abd1d7` = C12(b) repair (latency has no zero default). Write a new manifest `qa/manifests/t153-behavioural-checks.md`; `Fix cycle: 0` on the new branch (the prior cycles were on a different commit).

## 3. Acceptance criteria (verbatim, with ids)

Source: `qa/contracts/ai-target.md`. Only AI6 and AI7 bind T-153. (AI1-AI5, AI8 bind T-151/T-152.)

### AI6 — The capturer never grades
**[D-017 explicit + core-invariants C7]**
- `stages/ai_capture.py` contains no `Verdict`/`Result` construction and makes no PASS/FAIL
  decision; judgement happens only in `stages/grade.py` against a `Rubric`, mirroring
  `execute.py`'s existing observation/judgement split (C7: "the executor never grades itself").
- **Landing note:** `stages/ai_capture.py` does not exist yet (T-153 depends on T-152). Binds
  T-153's own unit check.
- **Verify (at T-153's check):** `grep -n "Result\.\|Verdict(" src/autotester/stages/ai_capture.py`
  returns nothing; a test proves a capture's output is handed unmodified to `grade()` and the
  PASS/FAIL comes back from the grade call, not from capture.

### AI7 — Every capture is scrubbed before a judge sees it
**[T-153's own goal-task note, C5 lineage]**
- `ai_capture.py`'s output passes `core.redact.Redactor.scrub` and
  `core.redact.assert_no_raw_secrets` before it is ever placed in a prompt built for `grade()` — the
  same boundary C5 already requires everywhere else in the pipeline.
- **Landing note:** binds T-153's own unit check, same file as AI6.
- **Verify (at T-153's check):** plant a synthetic secret-shaped string in a mocked target response;
  assert it never reaches the built judge prompt (mirrors C5's own verify pattern, applied to this
  new caller).

Also judged against this unit (the earlier checkers did; the goal note says so): `core-invariants.md` C5 (secrets, `:48`), C7 (verification independence, `:81`), C12 (fail closed: `schema/ai_check.py` must have no zero-best-case default for an unmeasured latency; `core-invariants.md:258`), `consent.md` CN1/CN5/CN6 for the approval call, `grade.md` G1-G6, and `core-invariants.md` C1-C4 (design rules, enforced by doctor). Goal-task note (T-153): "C7: the capturer never grades. Latency/schema computed in code, not judged. Every capture passes Redactor.scrub + assert_no_raw_secrets before reaching a judge."

## 4. What exists and what is missing

On master today (T-152 done, `qa/verdicts/t152-release-integration.md` PASS cycle 0):
- `src/autotester/schema/ai_check.py:1-27`: `AiCheckKind` (5 members), `AiCheckMethod`. No capture models.
- `src/autotester/stages/ai_catalog.py:1-103`: `CHECKS_BY_KIND`, `CHECK_METHOD`, `CHECK_TIER` literal tables, `match()`.
- `src/autotester/stages/grade.py:1-212`: `grade(...)` with `secrets` guard only; no `redactor` parameter (`_withheld` at ~:98).
- `src/autotester/core/consent.py:182` `require_approval`; `src/autotester/schema/approval.py` `RunApproval` (signed, content-addressed).
- `src/autotester/core/redact.py:43` `Redactor` (`scrub:69`, `scrub_obj:77`, `assert_clean:103`).
- Not on master: `stages/ai_capture.py`, `stages/ai_judge.py`, `AiReply/AiExchange/AiCapture`, `tests/test_ai_capture.py`.

Provided by the two cherry-picked commits (measured on `codex/t153-completion@31631ecb`):
- AI6: `ai_capture.py` (112 lines) records facts only (`_exchange:53`, `_send_one:65`, `capture_run:77`); it never imports `grade` and builds no `Verdict`/`Result`. `ai_judge.py` (201 lines) maps a capture to a `RawResult` plus `Rubric` (`_rubric`, `_raw_result`, `_evidence`) and delegates to the real `grade()` (`judge_capture`, last function); COMPUTED checks use a private `_ComputedJudge` provider so `grade()` still alone creates the `Verdict`.
- AI7: `capture_run` runs `Redactor.assert_clean` over project, endpoint, every prompt and every approval JSON before `require_approval` (nothing sent on failure); the finished capture is re-checked (`CaptureWithheld`). `ai_judge._scrubbed` and `_assert_clean` re-scrub and refuse again at the judge side; `grade.py` gains an optional `redactor` applied to the final prompt.
- C12(b): `AiExchange.latency_s` has `Field(ge=0, allow_inf_nan=False)` and no default (repair `b0abd1d7`).

Gaps and open obligations (be honest in the manifest):
- No real HTTP sender exists or is in scope. Transport is an injected `send(endpoint, prompt) -> AiReply`. How an AI endpoint authenticates is decided by no contract. Do not add a client.
- Nothing is persisted (`AiCapture` is returned, not stored). Persistence and the `.gitignore` entry for `projects/*/ai/` belong to T-154 (first writer) and T-155 (reader). Do not add either here.
- Approval kind for a behavioural capture is `ApprovalKind.LIVE_CASE` (`ai_capture.py:95`), recorded by the maker as an `[ASSUMPTION]`; ADVERSARIAL is T-154. Keep, and list it for the checker.
- Last cycle's open items were checker-side, not code: the AI7 final-grade falsification floor (host died before collection; `qa/verdicts/t153-completion.md`, VERDICT BLOCKED-PROCESS) and one security/full-suite integration run (`...b.md`, BLOCKED-CAPABILITY). Cycle-0 blind checker B had FAILed C12(b) (`...b.r1-1.md`); `b0abd1d7` repairs it and B2 confirmed 1/1.
- Policy: the full suite is a deferred LAST release obligation (owner correction 2026-10-09, quoted in the old manifest). The builder runs no full suite.

## 5. Files the builder will touch

Line counts are master today / after the cherry-pick (branch values).

| File | New or existing | Lines |
|---|---|---|
| `src/autotester/schema/ai_check.py` | existing | 27 -> 72 |
| `src/autotester/stages/ai_capture.py` | new | 112 |
| `src/autotester/stages/ai_judge.py` | new | 201 |
| `src/autotester/stages/grade.py` | existing | 212 -> 221 |
| `tests/test_ai_capture.py` | new | 300 (at the cap) |
| `tests/test_approval_signing.py` | existing | 253 -> 300 (at the cap) |
| `tests/test_grade_evidence.py` | existing | 175 -> ~300 (+125 on the branch; verify) |
| `docs/MAP.md` | existing, generated | regenerate with `uv run autotester map` (doctor flags a stale one: `src/autotester/doctor.py:203`) |
| `qa/manifests/t153-behavioural-checks.md` | new | the maker's evidence |

8 product/test/generated files plus the manifest. Do not edit `docs/ARCHITECTURE.md` (150 lines = `ledger/render.py:22` `ARCHITECTURE_MAX_LINES`, so any addition fails doctor) or any contract. Any further edit to a file at 300 lines must split it first.

## 6. Test scope (exact files; no directory runs, no full suite)

- `tests/test_ai_capture.py` (whole file; 20 test functions listed in section 7)
- `tests/test_grade_evidence.py` (whole file; new AI cases: `test_ai_capture_incomplete_observation_reaches_grade_without_judge`, `test_ai_joined_short_secret_is_withheld_by_actual_grade`, `test_ai_computed_grade_enforces_the_final_prompt_redactor`, `test_ai_invalid_latency_budget_refuses_before_grade`, `test_ai_valid_latency_boundary_remains_computed`, `test_grade_secret_store_guard_survives_optional_redactor`)
- `tests/test_approval_signing.py` (whole file; new `test_capture_refuses_invalid_bound_before_any_send`, `test_capture_honors_zero_time_without_blocking_positive_bound`)
- Affected closure, run once: `tests/test_ai_catalog.py`, `tests/test_grade.py`, `tests/test_schema.py`
- Then `uv run ruff check src tests scripts` and `uv run autotester doctor`. Run pytest per file or with explicit node ids, no `-q` flag (pyproject already sets it; `-qq` prints no summary, AT-503). Do not pipe a gate command (C12 pipe row).

## 7. Reachable test cases (per criterion, happy path first)

AI6: (1) a clean capture returns facts only (`test_capture_records_facts_latency_and_scrubs_every_field`, `test_capture_carries_no_judgement_field`); (2) the source never builds a Verdict/Result (`test_capturer_source_never_constructs_a_verdict_or_result`, mirrors the contract's grep); (3) the capture reaches `grade()` unmodified and the PASS/FAIL comes from grade (`test_the_capture_is_handed_to_grade_unmodified`, `test_the_judged_verdict_comes_from_the_judge_not_the_capture`); (4) no second grading path (`test_module_exposes_no_second_grading_path`); (5) incomplete or empty capture is INCONCLUSIVE, never PASS (`test_an_empty_capture_is_inconclusive_never_a_pass`, `test_an_errored_capture_never_reaches_the_judge`); (6) computed checks: shape and latency decided in code (`test_response_shape_is_computed_from_recorded_facts`, `test_latency_is_computed_against_the_budget_in_code`, `test_a_failed_exchange_fails_the_latency_check`).

AI7: (1) a synthetic secret in the target response never reaches the judge prompt (`test_a_secret_in_the_target_response_never_reaches_the_judge_prompt`); (2) a secret in a prompt is never sent (`test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint`); (3) an encoded secret surviving the scrub withholds the capture (`test_an_encoded_secret_surviving_the_scrub_withholds_the_capture`); (4) a hand-built capture is re-scrubbed at the judge (`test_a_hand_built_capture_is_scrubbed_again_at_the_judge`, `...with_an_encoded_secret_never_reaches_the_judge`); (5) final-prompt redactor in grade (the `test_ai_*_final_prompt_*` cases above).

Consent/failure edges: no approval means nothing is sent (`test_no_matching_approval_means_nothing_is_sent`); a transport failure is recorded, not raised, and names no value (`test_a_send_failure_is_recorded_not_raised_and_names_no_value`); the wall clock stops a capture and counts unsent prompts (`test_wall_clock_stops_the_capture_and_says_how_many_prompts_went_unsent`); C12(b): an unmeasured latency can never PASS a zero budget (the repaired schema; the old checker-B test `test_checker_b_unmeasured_latency_never_passes_a_zero_budget` was a checker artifact, not on the branch).

Falsification, in a throwaway copy only (never the live tree): for each of AI6, AI7 and C12(b), apply one single-hunk sabotage with an asserted unique anchor and a changed-bytes assertion, show the named test red, restore byte-exact, show green. The checker owns the persisted floor; the builder's own run is a pre-check. The AI7 final-grade floor is the one the last checker could not complete.

## 8. Gate answers (verbatim)

None open for T-153. Applicable answers on disk:
- `qa/gates/t151-dependency-authorization.md:20`: "Answered: 2026-10-07T01:34:13Z — A — chat (Umesh): approve all three (pyyaml==6.0.3, the target-discovery prompt file, the mock.py act hunk). DECISIONS entry to follow." (T-151; no new dependency is added by T-153.)
- `qa/gates/d081-run-approvals.md`: "Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081". This does not make T-153 fire anything: T-153 sends no real request, and D-052 Part 3 keeps probe traffic to named, per-run approvals.
- No new module gate: D-017 names `stages/ai_capture.py`. `stages/ai_judge.py` is not named in D-017 or any gate; the maker's earlier manifest justified it (AI6 forbids a Verdict in `ai_capture.py`, and `grade.py` cannot map captures). Neither `qa/gates/new-module-authorization.md` (AT-710 only) nor a standing rule covers it. The checker should be told this is a new, un-gated module with a stated reason; if the owner wants a gate, that is a decision, not a builder choice.

## 9. UI surface and persona walk

`Persona walk: skip (backend-only: no human screen; the capture, judge and consent gate are called from code and tests, no route, template, CLI command or browser step is added)`. Browser: not applicable.

## 10. Dependencies and conflicts

- Must land first: nothing. T-152 is on master (`qa/verdicts/t152-release-integration.md`).
- Blocks: t154 needs `AiReply/AiExchange/AiCapture` and `capture_run`; t155 needs `AiCapture`, `judge_capture` and the `Verdict`s.
- Shared files (owner in bold):
  - `src/autotester/schema/ai_check.py` — **t153** (also touched by t154/t155 if they append; see their briefs: t154 uses a new `schema/ai_probe.py` instead).
  - `src/autotester/stages/ai_capture.py` — **t153**; t154 may add one additive hunk (two keyword parameters) in its own commit after the cherry-pick base.
  - `src/autotester/stages/ai_judge.py` — **t153**; t155 only imports it.
  - `src/autotester/stages/grade.py` — **t153**. No other pending unit's queue row names it.
  - `docs/MAP.md` — generated; every unit regenerates, the merge integrator regenerates last (do not hand-resolve it).
- Other pending units that touch things T-153 reads: `land-integrate-combined` edits `src/autotester/core/redact.py` (T-153 only calls `Redactor`; re-run `tests/test_ai_capture.py` if it lands first). No pending queue row edits `stages/ai_catalog.py` or `core/consent.py`.
- Branch merges: `wave/t153-behavioural-checks` is merged only by the exact commit a checker PASS reviewed (D-080 item 1, C10, D-048).

## 11. Budget and process rules

- Check budget: **L = 45 minutes** active wall. Builder budget: no stated figure; stop and hand off at the first honest `ready-for-check`.
- The builder runs no full suite and no browser. The sharded full suite is the checker's single LAST release step.
- Falsification only in a throwaway copy (for example under `.work/`), with the script copied too (AT-693).
- Kill only PIDs the builder started; record them. Do not touch other worktrees, the Codex worktree's evidence files, `qa/.paused`, `qa/issues.jsonl` or any contract.
- Send no request to any real endpoint. There is none in scope.
