# Manifest — at575-orchestrator-caller

**Status:** in-progress (cycle 3 — see the Fix cycle 3 section at the end)
**Fix cycle:** 3 of 3
**Dual check:** no
**Issues addressed:** AT-575
**Branch:** `wave/at575-orchestrator-caller` (from master `76dfbde`)
**Commits:** `26d7d93` (cycle 1 feature) · `9bfcd8e` (cycle 1 manifest) · `a6efb6c` (checker FAIL,
cycle 1) · `e65b8f0` (cycle 2 fix) — HEAD is `e65b8f0`
**Contract:** `qa/contracts/orchestrator.md` (OR1-OR6, D-036)

## The gap this closes

T-163's resumable orchestrator (`src/autotester/stages/orchestrate.py::run_or_resume`, D-036) had
no caller outside `tests/test_orchestrate*.py` — `grep -rn run_or_resume src/autotester` (excluding
`stages/orchestrate*`) returned no hits on master `ef1b043` (AT-575's own evidence). `at562-564`
wired the UI Run route to build its own `StageContext` directly (trace + secrets) and run cases,
not through `run_or_resume`, so learn/explore resume-after-interruption stayed reachable only from
pytest. `docs/FEATURES.jsonl` F-053 carries a caveat naming exactly this gap.

## What changed (cycle 1 — historical)

Line numbers below are as of commit `26d7d93`; the file has since changed — see "Fix cycle 2" below
for the current state and line numbers.

- **`src/autotester/cli_orchestrate.py`** (new, 186 lines) — `orchestrate_cmd` (line 145), a new
  `autotester orchestrate <project>` command. It:
  - loads the project (`ProjectStore.load_project`, line 166-169) and its `SecretStore`
    (`SecretStore.load(proj, paths.env_file, strict=False)`, line 174), same as `explore_cmd`
    (`cli_crawl.py:86`);
  - decides the entry path via the SAME `choose_mode` the driver uses (line 172), then
    `_build_runners` (line 94-114) wires **exactly** `{INGEST|DISCOVER, MODEL}` through the
    existing stage adapters `stages/orchestrate_runners.py::make_ingest_runner` /
    `make_discover_runner` / `make_model_runner` — no new stage logic, no new approval mechanism
    (matches `orchestrate.py`'s own "a stage with no registered runner is a STOP point" contract,
    the driver halts at the review gate exactly as it does under test);
  - for the `explore` path, calls `_require_crawl_consent` (line 51-65) — the same D-018 gate-2
    check (`stages/explore_consent.py::require_consent`) `explore_cmd`'s own preflight
    (`cli_crawl.py::_preflight_consent`) runs, BEFORE any directory or browser opens (AT-111's
    invariant: a refused run leaves no trace);
  - constructs `StageContext(store=store_, run_id=run_id or mint_run_id("run"), runners=runners,
    secrets=secrets)` (line 181-182) — `secrets=` is the AT-561 fix: without it `StageContext`
    silently falls back to an unredacted `Redactor({})` and the RT6 trace gate goes dark;
  - `--run-id` (line 146-149) lets the same run be re-invoked to resume it — omitted, a fresh id is
    minted; the printed summary (`_echo_state`, line 117-141) always echoes the run id back so an
    operator can resume it.
- **`src/autotester/cli.py`** — `cli.py:10` adds `cli_orchestrate` to the import line (was at its
  line budget, 294/300, so the command lives in a sibling module exactly like `cli_crawl.py` /
  `cli_video.py`); `cli.py:291` mounts `app.command("orchestrate")(cli_orchestrate.orchestrate_cmd)`.
- **`tests/test_cli_orchestrate.py`** (new, 197 lines) — drives the real CLI via
  `typer.testing.CliRunner`, never `run_or_resume` directly. Temp `AUTOTESTER_ROOT`
  (`monkeypatch.setenv`, no real `.env`/`projects/` touched), `MockProvider` for the model call.
- **`docs/MAP.md`** regenerated (`uv run autotester map`) — the only way `doctor`'s
  `stale-generated` check passes after a new module.

### The wiring itself (`cli_orchestrate.py:94-114`)

```python
def _build_runners(...) -> dict[StageName, Callable]:
    if mode == "learn":
        source = _entry_source(sources)
        model = providers.get(provider_id)
        return {
            StageName.INGEST: make_ingest_runner(source, project, model, RepoDocs()),
            StageName.MODEL: make_model_runner(source_id=source.id),
        }
    _require_crawl_consent(proj, store_, bounds)
    crawl_fn = _make_crawl_fn(proj, store_, paths, secrets, bounds, login_case_id)
    return {
        StageName.DISCOVER: make_discover_runner(proj, crawl_fn),
        StageName.MODEL: make_model_runner(),
    }
```

```python
ctx = StageContext(store=store_, run_id=run_id or mint_run_id("run"), runners=runners,
                   secrets=secrets)
state = run_or_resume(proj, ctx)
```

## Tests (red-first; TDD, all through the CLI entry point)

`tests/test_cli_orchestrate.py`, 4 tests, all against a temp `AUTOTESTER_ROOT`:

1. `test_fresh_learn_run_checkpoints_ingest_and_model_through_the_cli` — (a) a fresh run: INGEST +
   MODEL land `done` in `state.json`, and the flowspec on disk actually gained the ingested screen
   (DRAFT, never auto-approved).
2. `test_resume_after_interruption_never_redoes_the_done_stage` — (b) MODEL is made to raise once
   (`merge_flowspec` monkeypatched flaky); first invocation: INGEST `done`, MODEL `failed`, exit 1.
   Second invocation with the SAME `--run-id`: `ingest_video` call count stays at 1 (proven via a
   counting wrapper), INGEST's `artifact_ref` is byte-identical, MODEL re-enters and this time
   succeeds, exit 0.
3. `test_secrets_reach_stagecontext_so_the_trace_gate_never_falls_back` — (c) a declared secret in a
   temp `.env`; asserts NO `RuntimeWarning` about `StageContext` falling back to an unredacted
   `Redactor({})` fires during a real invocation (the AT-561 defect, proven live rather than
   inferred).
4. `test_explore_mode_without_an_approval_refuses_before_the_crawl_starts` — (d) a credentials-only
   project (no approval granted) on the `explore`/DISCOVER path: exit 2, "approv" in the message,
   no run directory left on disk.

Run: `uv run pytest tests/test_cli_orchestrate.py -q` → `4 passed`.

## Capability-coverage table (cycle 1 — historical record)

**Flagged by the checker (cycle 1 verdict, "the maker's flags" §a) and by the coordinator: doing
this in-place in the committed worktree, even with a clean `git checkout --` revert, is the wrong
method — the third such case on this repo. Not repeated. Cycle 2's rows below are all done in a
throwaway copy outside the worktree instead**, per the coordinator's hard rule this cycle. This
section is left as-is (unedited) for the historical record of what cycle 1 actually did.

Each row: committed code is green; a single-hunk falsifying edit (via `git checkout -- <file>`
revert afterward, never left in the worktree) reproduces red **for the named reason**; reverted →
green again. All four done directly in the worktree via edit → run → `git checkout --` revert
(code was committed first specifically so this revert is exact and clean — no throwaway copy
needed for a same-repo git-tracked revert).

| # | Capability | Falsifying edit | Red — named reason | Revert | Result |
|---|---|---|---|---|---|
| 1 | The CLI actually exposes a command that drives `run_or_resume` (acceptance bar item 1) | Commented out `cli.py:291` (`app.command("orchestrate")(...)`) | `No such command 'orchestrate'` — typer refuses the invocation outright | `git checkout -- src/autotester/cli.py` | green (4 passed) |
| 2 | `--run-id` enables a real resume, not a relabelled fresh run | `cli_orchestrate.py:181` — dropped `run_id or` so a fresh id is minted every invocation | `test_resume_after_interruption_never_redoes_the_done_stage` fails: `state.json` never lands at the requested run dir (`assert None is not None`) | `git checkout -- src/autotester/cli_orchestrate.py` | green (4 passed) |
| 3 | Secrets reach `StageContext` (RT6 gate live, acceptance bar item 2) | `cli_orchestrate.py:181-182` — dropped `secrets=secrets` | `test_secrets_reach_stagecontext_so_the_trace_gate_never_falls_back` fails: the AT-561 `RuntimeWarning` fires | `git checkout -- src/autotester/cli_orchestrate.py` | green (4 passed) |
| 4 | DISCOVER honours the same D-018 consent gate `explore` does, before anything starts | `cli_orchestrate.py:109` — commented out `_require_crawl_consent(...)` | `test_explore_mode...` fails: exit code drops from 2 to 1 — the crawl now reaches `run_crawl`'s own deeper gate and dies as a **failed checkpoint with a run directory left on disk**, instead of the clean AT-111 "no trace" refusal; proves the CLI-level preflight is what delivers the correct, trace-free refusal, not merely defense in depth | `git checkout -- src/autotester/cli_orchestrate.py` | green (4 passed) |

Row 4 finding: even with the preflight removed, `stages/explore.py::run_crawl`'s own consent check
still refuses the crawl (defense in depth, D-018 gate 2 is checked at two seams by design) — but
without the CLI's own preflight the refusal shows up as a failed `RunState` checkpoint (a run
directory on disk, exit 1) rather than AT-111's "a refused run leaves no trace" (exit 2, nothing
written). The preflight is load-bearing for that invariant even though the deeper gate cannot
actually be bypassed.

## Verify (cycle 2, current)

```
uv run pytest tests/test_cli_orchestrate.py tests/test_cli_orchestrate_resume.py \
  tests/test_orchestrate.py tests/test_orchestrate_runners.py \
  tests/test_cli_surface.py tests/test_expand_cli.py tests/test_ingest_real_cli.py \
  tests/test_crawl_real_cli.py tests/test_approve_cli.py
  -> 103 passed (no CLI -q -- pyproject's own addopts already sets -q; stacking a
     second -q makes it -qq, which drops the summary line entirely, AT-503)
uv run ruff check src tests scripts   -> All checks passed!
uv run autotester map                 -> docs/MAP.md unchanged (no diff — the split module's
                                          exported concepts are the same)
uv run autotester doctor              -> doctor: clean
```

**Full non-browser suite:** RAM-gated again this cycle — free RAM measured as low as 1.78 GB
(down from 2.94-2.95 GB during cycle 1) with the trend consistently downward across polls; no
background monitor was launched this time (per the coordinator's explicit note that the checker
runs the full suite itself, and the hard requirement to leave no monitor running at handback). This
is a **gap**: the targeted modules above stand in as the closest available substitute.

**Pre-existing state:** `docs/DECISIONS.md` / Lab Protocol are not active in this repo (no
`docs/DECISIONS.md` at the root — `qa/` maker-checker discipline applies instead, per
`d:/autoTesting/CLAUDE.md`).

## Browser / Mode D

**Not UI-touching.** Cycle 1 + cycle 2 changed files, all told: `src/autotester/cli_orchestrate.py`,
`src/autotester/cli.py` (2-line mount + import), `tests/test_cli_orchestrate.py`,
`tests/test_cli_orchestrate_resume.py` (new this cycle), `docs/MAP.md` (regenerated, cycle 1; no
diff on cycle 2's regen). No file under `src/autotester/ui/` was read or modified, and no route was
added or changed. Mode D: **SKIP**.

## Fix cycle 2 (checker FAIL, verdict `qa/verdicts/at575-orchestrator-caller.md`, commit `a6efb6c`)

### The failure, quoted

> **[C3 / design rule "a class or function defined in two modules is a bug"]** sev: medium ·
> `cli_orchestrate.py::_require_crawl_consent` is a statement-for-statement copy of
> `cli_crawl.py::_preflight_consent` (checker AST comparison: statement bodies identical, same
> parameters; only the name and docstring differ). It's the D-018 consent gate, a security check,
> now in two copies that will drift the first time one is tightened. The module docstring also
> claims the existing primitives are "reused as-is", which isn't true of this one. doctor misses it
> because its duplicate rule matches public names only and these are private and differently named.
> · fix: delete `_require_crawl_consent` and call `cli_crawl._preflight_consent` (import it, or move
> it to a shared spot both commands import); keep test 4 as is, it will still pin exit 2 with no
> trace. · issue: AT-575 (stays open)

### Coordinator decisions (both: "fix it")

> **1. Resume in explore mode re-runs the consent preflight** even when DISCOVER is already done and
> only MODEL remains. `require_consent` doesn't use up the approval, so it costs nothing while the
> approval is valid, but an expired approval would block a resume that will never open a browser.

> **2. Mode is recomputed on resume.** `choose_mode(sources)` builds the runner dict from the current
> sources, while `run_or_resume` resumes from the stored state's mode. If a teaching source is added
> or removed between two invocations with the same `--run-id`, the runners can mismatch the stored
> stages. Worth a guard: build runners from the stored state's mode when resuming.

Plus three binding amendments the coordinator relayed mid-cycle: (1) **no `git stash`** — the stash
stack is shared across every worktree/session on this repo; (2) the consent skip must key on
DISCOVER's stored status being **exactly** `"done"` — failed/pending/missing still hits the
preflight, with a test proving no new trace span on that refusal; (3) an **unknown `--run-id`** must
behave like a fresh run with a clear message, not crash — with a test.

### What changed this cycle

- **`src/autotester/cli_orchestrate.py`**: deleted `_require_crawl_consent` (the copy) entirely.
  `_explore_runners` (was `_build_runners`'s explore branch) now calls `cli_crawl._preflight_consent`
  directly — `from autotester import cli_crawl` at module level (`cli_orchestrate.py:35`), call site
  `cli_orchestrate.py:146`. Module docstring corrected (no longer claims a false "reused as-is" for a
  function that was, in fact, copied).
- New `_resolve_run(store_, sources, run_id)` (`cli_orchestrate.py:154-167`) is the one place that:
  loads prior `RunState` for an explicitly-passed `--run-id` (`_load_state`, line 69-72; `None` for a
  fresh/unknown one — never an error); reads `mode` from `prior.mode` when a prior state exists,
  falling back to `choose_mode(sources)` only for a truly fresh run (fixes decision 2); prints a
  one-line `"no existing run '<id>' for <project> — starting fresh"` note when an explicit `--run-id`
  has no state on disk (amendment 3).
- New `_entry_done(prior, mode)` (`cli_orchestrate.py:75-86`) returns `True` only when the stored
  checkpoint for this run's entry stage (INGEST for learn, DISCOVER for explore) has status **exactly**
  `"done"` — `None`/`"failed"`/`"pending"` all return `False` (amendment 2). `_learn_runners` /
  `_explore_runners` (split out of the old `_build_runners`, line 115-151) each skip wiring their
  entry stage (and, for explore, skip the consent preflight) only when `entry_done` is `True` — fixes
  decision 1 (a resume past a `done` DISCOVER never re-checks consent) while still hitting the gate
  for a failed/pending one.
- `_entry_source` now returns `Source | None` instead of raising `StopIteration` when no teaching
  Source exists; a new `NoEntrySource` (line 55-58) is raised with a clear message only when a
  **not-yet-done** INGEST genuinely has nothing to watch, caught in `orchestrate_cmd` (line 250-252)
  as a clean exit 1 — never a raw traceback.
- `orchestrate_cmd` (line 212-258) shrank back under the 50-line function cap by delegating to
  `_resolve_run`.
- **Tests:** `tests/test_cli_orchestrate.py` trimmed back to its 4 cycle-1 tests (helper functions
  simplified, `cli_from_app()` indirection dropped for a plain `from autotester.cli import app`, same
  convention as sibling CLI test files). Four new tests split into
  **`tests/test_cli_orchestrate_resume.py`** (300-line cap, C2):
  1. `test_resume_past_a_done_discover_skips_consent_even_if_the_approval_lapsed` — decision 1.
  2. `test_resume_past_a_failed_discover_still_hits_consent` — amendment 2, plus asserts
     `trace.jsonl` byte-identical before/after the refused second invocation (amendment 2's "no new
     trace" requirement).
  3. `test_resume_keeps_the_stored_mode_even_if_current_sources_would_flip_it` — decision 2.
  4. `test_unknown_run_id_starts_fresh_with_a_clear_message_not_a_crash` — amendment 3.

### Capability-coverage table (cycle 2) — throwaway copy ONLY, never in the worktree

Per the coordinator's hard rule this cycle: no `git checkout --`/in-place revert dance, no
`git stash` (shared stash stack risk). All four rows were reproduced in a full throwaway copy at
`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/
scratchpad/at575-falsify/` (`src/`, `tests/`, `scripts/`, `pyproject.toml`, `uv.lock` copied out;
`.venv` reused via an NTFS junction to skip a slow reinstall). The real worktree was never edited for
this — confirmed after: `git status --short` empty and `diff` against the throwaway copy's
`cli_orchestrate.py` empty, both re-checked once all four rows were done.

| # | Capability | Falsifying edit (in the copy) | Red — named reason | Revert | Result |
|---|---|---|---|---|---|
| 1 | The explore path truly depends on the SHARED `cli_crawl._preflight_consent` (C3 fix is load-bearing, not a dead import) | Commented out the `cli_crawl._preflight_consent(...)` call in `_explore_runners` | `test_explore_mode_without_an_approval_refuses_before_the_crawl_starts` fails: exit code drops 2→1, `run_crawl`'s own deeper gate catches it instead as a failed checkpoint, no clean "no trace" refusal | restored the call | green (copy: 8/8) |
| 2 | Consent-skip precision — only an exact `"done"` DISCOVER skips the preflight | `_entry_done`: `== "done"` → `!= "pending"` (treats `failed` as done too) | `test_resume_past_a_failed_discover_still_hits_consent` fails: exit 2→1 — a failed DISCOVER is wrongly treated as "won't run again", so the run silently breaks at the failed checkpoint instead of re-hitting consent | restored `== "done"` | green |
| 3 | Mode is read from stored `RunState`, never recomputed via `choose_mode` on resume | `_resolve_run`: `mode = prior.mode if prior is not None else choose_mode(sources)[0]` → unconditional `choose_mode(sources)[0]` | `test_resume_keeps_the_stored_mode_even_if_current_sources_would_flip_it` fails: exit 0→2, `"refusing to start a crawl … no approval exists"` — reproduces the checker's exact described bug | restored the `prior.mode` branch | green |
| 4 | An unknown `--run-id` starts fresh, never crashes | `_resolve_run`: `mode = prior.mode if prior is not None else …` → unconditional `mode = prior.mode` | `test_unknown_run_id_starts_fresh_with_a_clear_message_not_a_crash` fails: exit 0→1, `AttributeError("'NoneType' object has no attribute 'mode'")` — a real crash, not a refusal | restored the guarded line | green |

## Gaps / follow-ups for the checker

1. Full non-browser suite RAM-gated again this cycle (see Verify section) — free RAM measured as low
   as 1.78 GB during this cycle's work (down from 2.94-2.95 GB in cycle 1), so no attempt was made to
   poll for it this time; the coordinator separately confirmed the checker runs the full suite
   itself.
2. This unit deliberately stops at MODEL (the review gate) per `orchestrate.py`'s own contract — it
   does **not** wire EXPAND/EXECUTE/GRADE/REPORT into the orchestrator; those stay reached through
   their existing standalone commands (`expand`, etc.) exactly as today. If F-053's caveat should
   only drop once the ENTIRE pipeline is orchestrator-driven rather than "resume through the review
   gate is live", that is a scope question for the checker/ledger, not something this unit silently
   assumed either way.
3. `--run-id` is a new, minimal convention (no prior "latest run" helper existed anywhere in the
   codebase to build on) — an operator must copy the printed run id to resume. A future unit could
   add a `--resume-latest` convenience; out of scope here (no issue currently open for it).
4. `_learn_runners`' `NoEntrySource` path (a not-yet-done INGEST whose teaching Source was removed)
   is implemented and raises cleanly but has no dedicated test this cycle — not part of the checker's
   three required items, flagged rather than silently added scope.


## Fix cycle 3 (checker cycle-2 FAIL, qa/verdicts/at575-orchestrator-caller.md @ 08e0eb6)

**Failure quoted:** "tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed -- `new: [('cli_orchestrate.py', 'ingest register')]`. Your NoEntrySource message '`autotester ingest register` one first' is a new advice site; the AT-210 guard requires registering it in EXPECTED_SITES."

**Fix (6b66de5, maker orchestrator inline — a two-line test-registry change):**
- tests/test_cli_advice_resolves.py — `("cli_orchestrate.py", "ingest register")` added to EXPECTED_SITES; EXPECTED_SITE_COUNT 17 -> 18. No source file changed this cycle. The advice itself resolves (the parametrized resolve test re-checks every collected site).

**Verify (cycle 3):**
- `uv run pytest tests/test_cli_advice_resolves.py` -> `27 passed in 9.95s`
- Full non-browser suite (per the checker's cycle-2 ask), ignoring only the Chromium-launching files (test_browser.py, test_browser_scroll_invariance.py, test_crawl_inventory_live.py, test_explore_live.py, test_explore_login_spa_live.py, test_explore_modal.py, test_explore_typing.py, test_ui_crawl_login.py, test_ui_runs_serial_entry_mix_live.py, test_mutation_check.py, test_mutation_check_judgement.py), run at 0.62 GB free RAM:
  `1 failed, 1600 passed, 5 skipped, 15 warnings in 158.21s` — the one failure is
  `tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild` (AT-518, real-process timing).
  Proven flaky, not this unit: this branch does not touch any flake_probe file (`git diff --name-only 76dfbde HEAD | grep -i flake` -> empty); on master it passed (`2 passed`); on THIS branch, same code, consecutive re-runs gave `1 failed, 1 passed` then `2 passed` at 0.36 GB free.
- test_cli_advice_resolves.py is now included in the suite above and passes.

**Capability row (cycle 3):** the AT-210 guard itself is the check. Falsifying edit = remove the new EXPECTED_SITES entry -> the cycle-2 run on a81dee1 IS that state: `new: [('cli_orchestrate.py', 'ingest register')]`, `1 failed, 26 passed` (checker-reproduced). With the entry: `27 passed`.

**Live browser:** Not UI-touching this cycle (tests/test_cli_advice_resolves.py only).

## Status: checked-PASS (qa/verdicts/at575-orchestrator-caller.md, Cycle checked: 3, 0ac4105)
