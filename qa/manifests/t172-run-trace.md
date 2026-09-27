# Manifest — t172-run-trace
**Contract:** qa/contracts/run-trace.md (DRAFT, RT1-RT7) + qa/contracts/core-invariants.md
**Goal task:** T-172
**Date:** 2026-09-25
**Fix cycle:** 2 of max 3
**Dual check:** no (goal task criticality is `high`, not `critical`)
**Issues addressed:** AT-561 (checker cycle-1 FAIL, RT6/C5 real-wiring gap)
**Executor:** claude-sonnet-subagent
**Executor rationale:** schema/redaction/security-adjacent unit (RT6 touches the secret guard) — stays on a Claude subagent per the "never delegate ... security units" rule; no delegation attempted.

## Fix cycle 2 (checker cycle-1 FAIL, ledger AT-561 + supervising note)

**Failure quoted verbatim (checker, `qa/verdicts/t172-run-trace.md`):**
> RT6 / core-invariants C5 (credential boundary): the real/default wiring never redacts anything.
> `core/trace.py:26`: `self._redactor = redactor or Redactor({})`. `stages/orchestrate.py:76` (the
> *only* production call site that builds a `TraceWriter` — `StageContext.__post_init__`) never
> passes `redactor=`, so every trace this unit's own orchestrator wiring produces is written with
> an **empty** `Redactor({})`... The unit's own two RT6 tests do not catch this because both
> manually construct `TraceWriter(..., redactor=Redactor({...}))`... They prove the *mechanism*
> works when given real secret values; they never prove the *wiring* ever gives it any.

**Supervising checker's cycle-2 asks:** (1) thread `SecretStore.redactor()` into the writer
`StageContext` builds (pattern at `stages/execute.py:101` / `stages/explore.py:230`), and don't let
a real-span `TraceWriter` fall back to `Redactor({})` silently; (2) add RT6's falsification through
the REAL wiring (`StageContext` with no `trace=` kwarg, a fake `SecretRef`, a span that would carry
it → zero raw matches), with a capability row that removes the threading and goes red; (3) every
non-browser test file green.

**Fix:**
- `src/autotester/stages/orchestrate.py` — `StageContext` gains `secrets: SecretStore | None = None`.
  `__post_init__`'s default-trace branch now builds `self.secrets.redactor()` when `secrets` is
  given; when it is **not** given, the writer still falls back to `Redactor({})` (unchanged for the
  existing fixture-only callers in `test_orchestrate.py`/`test_orchestrate_runners.py`, which declare
  no secrets on purpose) but this is **no longer silent** — a `RuntimeWarning` names the `run_id` and
  the exact risk (AT-561), so a future caller that forgot `secrets=` sees it immediately instead of a
  quiet no-op gate.
- **TDD, written first, shown red:** `tests/test_run_trace.py::test_the_real_stagecontext_wiring_never_leaks_a_declared_secret`
  drives the exact wiring the checker's adversarial probe used — a `StageContext` with **no `trace=`
  kwarg**, a `SecretStore` built from a fake, in-memory `SecretRef`/value (never the real `.env`),
  and `provider.trace = ctx.trace` exactly as `orchestrate_runners.make_ingest_runner` does it — and
  asserts a declared secret fed into a span never reaches `trace.jsonl` raw.
  - Before the fix: `TypeError: StageContext.__init__() got an unexpected keyword argument 'secrets'`.
  - After the fix: passes; the merge-hazard mutation (below) confirms it actually discriminates.

**Merge hazard (T-175, discovered mid-cycle, coordinator-flagged):** T-175 merged to master
(`9b3fd5e`) renaming `grade.py`/`expand.py`/`ingest.py`'s `PROMPT_NAME` → `SKILL_NAME` (Agent-Skills
`SKILL.md` migration). This unit's own `prompt_file=PROMPT_NAME` call sites (added cycle 1, RT4)
went stale after merging master and would `NameError` on every grade/expand/ingest model call.
Fixed: all three switched to `prompt_file=SKILL_NAME` — `prompt_file` now records the skill id (there
is no loose prompt file left to name). `providers/base.py`'s merge conflict was with T-175's own
`load_skill_prompt` addition at the bottom of the file; resolved by keeping this unit's `record()`/
`self.trace` body exactly as cycle 1 shipped it and appending `load_skill_prompt` unmodified after
it — both coexist, neither refactored.

Widening the verify set (per the checker/coordinator's ask) to `test_analyze_video.py`/
`test_analyze_cache.py`/`test_ensemble_honesty.py`/`test_expand_cli.py` surfaced a **real cycle-1
gap this unit had never actually run**: three test-only `Provider` subclasses
(`tests/video_fakes.py::SpyProvider`, `tests/test_ensemble_honesty.py::_NamedFakeProvider`,
`tests/test_expand_cli.py::_Exploding`) override `see_video`/`act` with a signature that predates
`prompt_file`/`fed_id` and `TypeError`'d the moment the real call sites started passing them. All
three production providers (anthropic/gemini/langchain_fallback/mock) were already correct in cycle
1 — only these fixtures were missed because they weren't in cycle 1's targeted list. Fixed by adding
the same `*, prompt_file=None, fed_id=None` the production providers already carry; `tests/test_source_adapters_audio.py::_FailingProvider`
was checked and left alone — it is never called with those kwargs (`sources/audio.py` was not
touched by this unit), so it was never broken.

**Commits (code before manifest, per instruction):**
- `46e7c2966d134f2c814c824fb7cb9963a8f1aa8f` — thread `SecretStore.redactor()` into `StageContext`.
- `a96b0ef` — `Merge branch 'master' into wave/t172-run-trace` (T-175's SKILL.md migration + other
  master work; one real conflict in `providers/base.py`, resolved as above).
- `2ef6ddf51886583d58af612e22ff82038babf4fb` — SKILL_NAME call-site fix + the 3 test-fixture Provider
  signature fixes.

## What changed

New files:
- `src/autotester/schema/trace.py` — `StageSpan`/`LLMSpan` pydantic models (`extra="forbid"`), the on-disk shape of a trace line.
- `src/autotester/core/trace.py` — `TraceWriter` (the only place a span is built + appended, RT5) and `read_spans` (the UI's read path, RT7).
- `src/autotester/core/pricing.py` — `estimate_cost(label, in_tokens, out_tokens)`, a small honestly-partial per-model $/1k-token table; unknown label → 0.0, never a raise.
- `tests/test_run_trace.py` — RT1-RT7 driver, 9 tests, fully offline (mock stage runners + `MockProvider`, temp project dirs).

Edited in place:
- `src/autotester/core/paths.py:110` — added `ProjectPaths.run_trace(run_id)` next to `run_dir`, per the architecture table's "every path on disk lives in core/paths.py".
- `src/autotester/core/redact.py:218-224` — added `Redactor.assert_clean(text)`: the RT6 hard gate, reusing the Redactor's own loaded values so a caller never has to hold raw secrets separately.
- `src/autotester/providers/base.py:16,40-46,59-131` — **confined to record()/span emission as instructed**: `self.trace: TraceWriter | None` attribute; `see_video`/`act`/`judge` gain optional `prompt_file`/`fed_id` kwargs (pure plumbing, raise-stub bodies unchanged); `record()` extended with `prompt_file`/`fed_id`/`latency_s`/`retries`/`fallback_hops` and now calls `self.trace.record_llm(...)` when a writer is attached — the single choke point (RT5). No other part of the file touched (no refactor of `label`, `available`, etc).
- `src/autotester/providers/anthropic.py`, `gemini.py`, `langchain_fallback.py`, `mock.py` — thread the new `prompt_file`/`fed_id` kwargs through, measure real `latency_s` via `time.perf_counter()` around the actual model call, and (langchain_fallback only) pass a real `fallback_hops` = the index of the tier that answered (0 = no fallback).
- `src/autotester/stages/orchestrate.py:16,55-71,110-119` — `StageContext` gains `trace: TraceWriter | None = None`, auto-built in `__post_init__` from `store.paths.run_trace(run_id)` when not given (every run is traced by default, RT1); `_record()` — the one place every checkpoint transition already passes through — writes the stage's `StageSpan` when the checkpoint reaches a terminal status (`done`/`failed`/`skipped`), so a pending/running checkpoint never gets one (RT3's "a stage that never ran produces no span"). **Cycle 2:** also gains `secrets: SecretStore | None = None`; when given, its redactor threads into the auto-built `TraceWriter` (AT-561 fix); when not given, a `RuntimeWarning` names the risk instead of silently gating on nothing.
- `src/autotester/stages/orchestrate_runners.py:70-74` — `make_ingest_runner`'s closure now does `provider.trace = ctx.trace` before calling `ingest_video`, so INGEST's real LLM call joins the run's own trace file (the one stage `run_or_resume` actually drives today).
- `src/autotester/stages/ingest.py`, `grade.py`, `expand.py`, `analyze_video.py` — pass `prompt_file=<the stage's own skill/prompt id>` and `fed_id=<source.id / result.case_id / flow.id>` into their `see_video`/`judge`/`act` calls. **Cycle 2:** `ingest.py`/`grade.py`/`expand.py`'s `prompt_file` argument follows T-175's rename, `PROMPT_NAME` → `SKILL_NAME` — `prompt_file` now records the Agent-Skills skill id (`"grade"`, `"expand-case"`, `"ingest-video"`), not a loose prompt filename (T-175 removed the loose files). `analyze_video.py` was unaffected (it already used a local `prompt_name` variable + `SKILL_NAMES` dict, not a module `PROMPT_NAME` constant).
- `docs/MAP.md` — regenerated via `uv run autotester map` (generated section only, per doctor's `stale-generated` check; not hand-edited).
- **Cycle 2, test-fixture-only:** `tests/video_fakes.py::SpyProvider.see_video`, `tests/test_ensemble_honesty.py::_NamedFakeProvider.see_video`, `tests/test_expand_cli.py::_Exploding.act` each gain `*, prompt_file=None, fed_id=None` — pre-existing test doubles that predate these kwargs and would `TypeError` once the real call sites above pass them (see Fix cycle 2 above for how this was found).

**New module reason (C3):** two new modules (`core/trace.py`, `core/pricing.py`) rather than folding into an existing file — `core/redact.py` is the redaction concept (extended, not duplicated) and `core/paths.py` is the path concept (extended, not duplicated); the trace-span shape and the cost table are each a new concept with no existing home, and both stay well under the 300-line cap.

## How to verify (commands + expected)
- `uv run pytest tests/test_run_trace.py` → expected: exit 0, 10 passed (this is T-172's `done_check`; 9 cycle-1 + the cycle-2 real-wiring test)
- `uv run pytest tests/test_run_trace.py tests/test_orchestrate.py tests/test_orchestrate_runners.py tests/test_providers.py tests/test_ui_report.py tests/test_ui_report_no_runs.py tests/test_prompt_skills.py tests/test_grade.py tests/test_expand.py tests/test_ingest_persist.py tests/test_analyze_video.py tests/test_analyze_cache.py tests/test_ensemble_honesty.py tests/test_expand_cli.py` → expected: exit 0, 134 passed
- `uv run ruff check src tests scripts` → expected: exit 0, "All checks passed!"
- `uv run autotester doctor` → expected: exit 0, "doctor: clean"
- **Cycle 2, RAM allowed it:** the full non-browser suite (`uv run pytest` with the 17 browser-launching test files `--ignore`d) → expected: exit 0 or only pre-existing/unrelated failures (see below).

## Actual outputs (from maker's own run)

```
$ PYTHONUTF8=1 uv run pytest tests/test_run_trace.py tests/test_orchestrate.py tests/test_orchestrate_runners.py tests/test_providers.py tests/test_ui_report.py tests/test_ui_report_no_runs.py tests/test_prompt_skills.py tests/test_grade.py tests/test_expand.py tests/test_ingest_persist.py tests/test_analyze_video.py tests/test_analyze_cache.py tests/test_ensemble_honesty.py tests/test_expand_cli.py
134 passed, 15 warnings in 3.87s

$ uv run ruff check src tests scripts
All checks passed!

$ PYTHONUTF8=1 uv run autotester doctor
doctor: clean
```

**Full `uv run pytest` (whole suite, 17 browser-launching files excluded — this project has no
registered pytest marker, so "the project's equivalent" of `-m "not live"` is `--ignore`ing every
test file that imports `BrowserSession`/`playwright` directly, found via
`grep -rl "BrowserSession(\|sync_playwright\|playwright.sync_api" tests/test_*.py`): RUN this
cycle** once conditions were actually met (3.5 GB free, `Get-CimInstance Win32_Process` showed no
other `D:/autoTesting` pytest process) — cycle 1's attempt never got a clean window; this one did:

```
$ PYTHONUTF8=1 uv run pytest --ignore=<17 browser-launching files>
1 failed, 1546 passed, 5 skipped, 15 warnings in 189.37s (0:03:09)

FAILED tests/test_goal_done_checks.py::test_revised_goal_contract_is_registered
  assert all(value in dashboard for value in facts)
  AssertionError: .goal/dashboard.html does not contain the progress/percent/north_star facts
  computed fresh from .goal/goal.json
```

**This failure is pre-existing on the merged-in master state, not caused by T-172.** Verified:
`git diff 295d543 HEAD -- .goal/dashboard.html .goal/goal.json` is **empty** — neither file has
been touched by this branch since the merge-base, and `git log --oneline -1 -- .goal/dashboard.html
.goal/goal.json` both point to `9a266f4` (a T-173 close-out commit, well before T-175 or this unit's
merge). The dashboard/goal.json pair was already mutually stale at the exact commit this branch
merged in; regenerating it is a `.goal` write this unit is explicitly barred from making (per the
cycle-2 instruction "Do NOT ... edit ... the ledger or .goal"). Disclosed here rather than fixed —
the checker or a human should regenerate the dashboard (likely `monitor.py`) on master directly, not
inside this unit's diff.

## Capability coverage (each new claim -> its isolating falsification)

The 8 cycle-1 falsifications below were reproduced in a throwaway copy at
`%TEMP%\claude\d--autoTesting\<session>\scratchpad\rt-verify\` (outside the worktree; `src`,
`tests`, `scripts`, `pyproject.toml`, `uv.lock` copied from the working tree, `.venv` built fresh
in the copy) — never against the bound worktree. Baseline asserted green (`9 passed`) before every
edit; each edit reverted from the pristine worktree file immediately after its red run, with the
suite re-confirmed green before moving to the next row. The cycle-2 row (RT6-real-wiring) was
reproduced the same way in a fresh throwaway copy (`.../scratchpad/rt-verify2/`) after the merge —
`orchestrate.py`'s content at the falsified lines is byte-identical pre- and post-merge (the merge's
only conflict was in `providers/base.py`, resolved without touching `record()`'s body), so the
8 cycle-1 rows still hold verbatim against the current tree; they were not re-run a second time.

| capability (RT#) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| RT1 — one trace.jsonl per run, incrementally written, never overwriting a sibling run's file | `test_two_runs_of_a_project_get_two_distinct_nonempty_trace_files` | `core/trace.py::TraceWriter._append` — deleted the `mkdir` + `with open("a")...write(...)` block, leaving only the `mkdir` | BEFORE: `9 passed in 2.82s`. AFTER: `assert trace_a.exists() and trace_b.exists()` → `AssertionError: assert (False)` — `.../runs/run_a/trace.jsonl` does not exist. REVERTED → `9 passed in 21.26s`. |
| RT2 — every span's `trace_id` equals `RunState.run_id`, never re-minted | `test_every_span_trace_id_equals_the_runs_own_run_id` | `core/trace.py::TraceWriter.record_stage` — `trace_id=self.trace_id` → `trace_id="minted-" + self.trace_id` | BEFORE: `9 passed`. AFTER: `assert all(line["trace_id"] == "run_tid" for line in lines)` → `assert False`. REVERTED → `9 passed in 1.15s`. |
| RT3 — exactly one span per stage that actually ran, in stage order, no others | `test_a_run_produces_exactly_one_stage_span_per_stage_that_ran` | `stages/orchestrate.py::_record` — `if checkpoint.status in ("done","failed","skipped") and ctx.trace is not None:` → `if ctx.trace is not None:` (also fires on the `running` transition) | BEFORE: `9 passed`. AFTER: `assert [s.stage for s in spans] == custom_stages` → `AssertionError: ... At index 1 diff: MODEL != EXECUTE — Left contains 3 more items`. REVERTED → `9 passed in 1.62s`. |
| RT4 — every LLM-call span carries the case/verdict id it fed, non-null when the call produced one | `test_a_fixture_stage_of_2_judge_calls_and_1_act_call_makes_3_llm_spans` | `providers/base.py::record` — inside the `self.trace.record_llm(...)` call, `fed_id=fed_id` → `fed_id=None` | BEFORE: `9 passed`. AFTER: `assert span.fed_id is not None` → `AssertionError: assert None is not None`. REVERTED → `9 passed in 1.00s`. |
| RT5 — `Provider.record()` is the only site that appends an LLM-call span (no second recorder) | `test_provider_base_record_is_the_only_site_that_appends_an_llm_span` (static scan of `src/autotester/**/*.py` for `.record_llm(` outside `providers/base.py`) | `stages/grade.py::grade` — added one extra line after the real `judge.judge(...)` call: `judge.trace.record_llm(...) if judge.trace else None` (a second, independent call site) | BEFORE: `9 passed`. AFTER: `assert offenders == []` → `AssertionError: ... Left contains one more item: '...\\stages\\grade.py'`. REVERTED → `9 passed in 0.98s`. |
| RT6a — every span passes through `Redactor.scrub` (+ the `assert_clean` hard gate) before touching disk | `test_every_span_is_redacted_before_it_is_persisted` | `core/trace.py::TraceWriter._append` — `clean = self._redactor.scrub(line); self._redactor.assert_clean(clean)` → `clean = line` (both steps skipped in one hunk) | BEFORE: `9 passed`. AFTER: `assert secret_value not in raw` → `AssertionError: ... 'sk-fake-9f2c7a1b' is contained here: id":"case-sk-fake-9f2c7a1b",...`. REVERTED → `9 passed in 2.27s`. |
| RT6b — `Redactor.assert_clean` is a real hard gate, not a no-op | `test_redactor_assert_clean_raises_on_a_surviving_secret` | `core/redact.py::Redactor.assert_clean` — body `assert_no_raw_secrets(text, self._values)` → `pass` | BEFORE: `9 passed`. AFTER: `raise AssertionError("assert_clean did not raise on a raw secret")` fired (the `try/except ValueError` found no exception). REVERTED → `9 passed in 1.06s`. |
| RT7 — the run-view panel is a live VIEW over `trace.jsonl`, not a cached/second copy | `test_the_run_view_panel_reflects_a_mutated_trace_file` | `ui/routes_report.py::_trace_card` — `f"<td>{s.duration_s:.2f}s</td></tr>"` → `f"<td>1.00s</td></tr>"` (ignores the parsed value) | BEFORE: `9 passed`. AFTER: `assert "999.00s" in after` → `AssertionError: assert '999.00s' in "...<td>1.00s</td>..."`. REVERTED → `9 passed in 1.01s`. |
| RT6-real-wiring (cycle 2) — a `StageContext` built with a project's `SecretStore` (no `trace=` kwarg) auto-threads a real redactor; it never silently falls back to `Redactor({})` for a run that declares secrets | `test_the_real_stagecontext_wiring_never_leaks_a_declared_secret` | `stages/orchestrate.py::StageContext.__post_init__` — `if self.secrets is not None:` → `if False:  # RT6-real-wiring falsification: secrets threading removed` (single line, syntactically valid; the `else` branch's `redactor = None` + `warnings.warn(...)` then always runs) | BEFORE: `10 passed`. AFTER: `assert secret_value not in raw` → `AssertionError: 'sk-real-DEADBEEF12345' not in '{"kind":"ll....076826Z"}\n' ... is contained here: id":"case-sk-real-DEADBEEF12345",...` (plus the expected `RuntimeWarning` fired, confirming the warn-path is what ran). REVERTED → `10 passed in 0.46s`. |

No `UNVERIFIED`/debt rows — every claim in "What changed" above has a covering row. `retries`/
`cost` fields exist on `LLMSpan` and are exercised by RT4's test (non-negative, present) but carry
no dedicated falsification row of their own: `retries` is honestly always `0` today (no provider
in this repo has a retry-on-failure loop yet — falsifying "retries" would mean falsifying a
constant, not a mechanism), and `cost` is a thin pure function (`core/pricing.estimate_cost`)
already exercised indirectly by RT4/RT6's runs; a dedicated mutation of its lookup table would
falsify the pricing constants, not this unit's tracing mechanism.

## Live browser evidence
Not UI-touching in the browser-automation sense, but the run-view panel IS a UI surface
(`src/autotester/ui/routes_report.py`, matches the `**/routes/**` UI-surface glob) — however:

**SKIP — RAM ceiling, no browser launched by the maker in either cycle.** Free RAM stayed under
the safe threshold (or a sibling worktree/pytest was live) whenever this unit checked. The RT7
capability itself IS verified at function level —
`test_the_run_view_panel_reflects_a_mutated_trace_file` calls `ui/routes_report.py::_trace_card`
directly against a real `ProjectStore`/temp dir and proves it re-reads the file on every call.
**Cycle 1's checker already closed the DOM-level gap independently** (`qa/verdicts/t172-run-trace.md`
Mode D): started a real `uvicorn` server, drove a real Chromium instance via the playwright MCP to
`/projects/demo/runs/run_ui_demo` with a `trace.jsonl` written through this unit's own `TraceWriter`
using a populated `Redactor`, confirmed the Trace card rendered a stage row and an LLM row, 0
console errors, and `document.body.innerHTML.includes(<secret>) === false`. That check also ruled
RT7 was never a reason for the FAIL. Nothing new to add here for cycle 2 — the AT-561 fix touched
`orchestrate.py`/providers, not the UI panel.

## Status: checked-PASS (qa/verdicts/t172-run-trace.md, Cycle checked: 2)
