# Verdict — at779-ingest-narration

**Verdict: PASS**
**Cycle checked:** 0
**Policy-Version:** proportional-verification/2026-10-07.7 · Tier S · single checker · no full suite
**Branch/head:** `wave/at779-ingest-narration` @ `1ea43123`

## Check plan
1. Read the diff (`origin/master...HEAD`): `ingest.py` (+`ingest_video`, `_project_redactor`), `tests/test_ingest_narration.py`.
2. Run the 6 affected test files (no `-q`), ruff, `autotester doctor`.
3. One falsification per criterion (a)-(d) in a throwaway COPY (scratchpad `cp/`, PYTHONPATH to copy `src`), worktree untouched.
4. Trace transcript supply on the real ingest paths to rule on the `make_ingest_runner` behaviour change.

## Criteria
- (a) PASS. `ingest.py:270-273`: after `flowspec_from_observation`, every flow goes through `reconcile.verify_narration(f, heard, redactor)` (imported, `ingest.py:32`; not duplicated). `verify_narration` (`reconcile.py:128-143`) scrubs a kept quote and nulls the rest. Source ref is set by `_to_flow` (`ingest.py:146`), so the transcript lookup by `source_id` works. Default redactor = project `SecretStore.redactor()` (`ingest.py:276-282`).
- (b) PASS. Invented narration -> `None`, step kept (test 1); secret in a real quote -> `[REDACTED]` in memory and in the persisted `flowspec.json` (test 2).
- (c) PASS. Removing the call turns 3 tests red (F-a, F-c).
- (d) PASS. `narration` is `str | None` default `None` (`schema/flowspec.py:92`), schema untouched; legacy JSON without the key loads (test 5).

## Commands and output
- `uv run pytest tests/test_ingest_narration.py tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py tests/test_reconcile.py tests/test_orchestrate_runners.py` -> `70 passed, 3 warnings` (AT-561 StageContext notice, pre-existing).
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`
- Baseline in copy: `5 passed`.

| ID | Criterion | Mutation (copy only) | Result |
|---|---|---|---|
| F-a | (a)(b)(c) | verify call replaced by `list(spec.flows)` | 3 failed (invented, secret, no-transcript) |
| F-b | (b) scrub | `Redactor({})` passed to `verify_narration` | 1 failed (secret test) |
| F-c | (c) | `return spec` instead of verified copy | 3 failed |
| F-e | (a) | `heard = {}` (transcript ignored) | 2 failed |
| F-d | (d) | `schema/flowspec.py:92` `narration` made required | 1 failed (legacy-load test) |

Worktree `git status --short` empty after all runs.

## Ruling on the flagged behaviour change (`make_ingest_runner` passes no transcript)
Correct for the changed code, not a data-loss defect.
- Real CLI path: `cli_video.py:202-203` passes `transcript=load_sidecar(source)`. A real sidecar therefore verifies and keeps genuine quotes; the change is behaviour-preserving there.
- `orchestrate_runners.py:72` never loads a transcript, and its prompt therefore renders "no speech detected" (`build_ingest_prompt`); the model never saw speech to quote. Under RC3 a narration is valid only as a verbatim transcript quote, so with no transcript supplied none can be valid. Dropping them follows the contract; the pre-change code saved unverifiable text.
- The gap is upstream of this diff: the runner (and the CLI, see below) do not load an available transcript. That is the AT-125 class, pre-existing, and outside criteria (a)-(d). Filed as PROPOSED-ISSUE, not a FAIL.

## Findings
- PROPOSED-ISSUE (low, process): builder ran its falsifications inside the worktree, not a throwaway copy. Recorded as a ledger row, not a FAIL.
- PROPOSED-ISSUE (low): `stages/orchestrate_runners.py:72` `make_ingest_runner` calls `ingest_video` with no transcript, so a source that has a sidecar or a persisted transcript loses all narration and the prompt says "no speech detected". Load via `analyze_video.load_transcript(ctx.store, source)`.
- PROPOSED-ISSUE (low): `cli_video.py:202-203` `ingest run` uses only `load_sidecar`; a transcript persisted by media prep (`stages/media_prep.py:62`, no sidecar) is ignored, so narration is dropped. `analyze_video.load_transcript` already prefers the store.
- PROPOSED-ISSUE (low): dropped narrations are not reported by ingest (it returns a FlowSpec only); the user cannot see that narration was discarded until reconcile. Consider logging a count.
- PROPOSED-ISSUE (low): test (d) cannot fail on a schema that stays backward compatible by construction; it only guards a future required-field change (F-d shows it does).

**Metrics:** files reviewed 3 · affected tests 70 passed · falsifications 5/5 red in a throwaway copy · ruff clean · doctor clean · worktree untouched · wall ~6 min
