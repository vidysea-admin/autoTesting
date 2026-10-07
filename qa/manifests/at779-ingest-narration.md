# Manifest — at779-ingest-narration

**Status:** checked-PASS
**Fix cycle:** 0
**Policy-Version:** proportional-verification/2026-10-07.7
**Tier:** S
**Unit:** AT-779 (low) — ingest saved model-authored narration unverified and unscrubbed.
**Contract:** `qa/contracts/reconcile.md` RC3 (amended by the criteria below; maker does not edit the contract)
**Branch:** `wave/at779-ingest-narration` (from origin/master 7782df41)
**Dual check:** no

## Criteria (verbatim, amending RC3)

- **(a)** Every narration that ingest saves is verified against the transcript, using the existing `verify_narration` in `stages/reconcile.py` (reuse it, do not duplicate it). It is also scrubbed at the save path with the existing redaction in `core/redact.py`.
- **(b)** Planted test cases behave correctly: a planted narration the model invented is dropped, or flagged unverified; a planted secret-like string is redacted.
- **(c)** Sabotage check: removing the call turns the test red.
- **(d)** Older FlowSpec files still load.

## What changed

- `src/autotester/stages/ingest.py::ingest_video` (and new private `_project_redactor`): after `flowspec_from_observation`, every flow goes through `reconcile.verify_narration` against `{source.id: transcript}` with a `Redactor`. New optional kwarg `redactor`; default = the project's own `SecretStore.redactor()` (same path as `report_export._load_redactor`), empty `Redactor` when the project has no config. `flowspec_from_observation` stays pure and unchanged (reconcile's frozen fixture uses it).
- A narration not found in the transcript (or any narration when no transcript was given) is set to `None`; the step is kept. Dropped narrations are not returned as a report (ingest returns a FlowSpec only; reconcile still reports them in its own run).
- Condensed two docstrings (`build_ingest_prompt`, `load_sidecar`, `persist_ingest`) so the file stays at 299 lines (design rule <=300); wording only, no behaviour.
- `tests/test_ingest_narration.py`: 5 new tests.

## Falsification records (one per criterion; mutation applied in the working copy, test run, file restored from backup; `git status` after shows only the intended diff)

| ID | Criterion | Mutation | Result |
|---|---|---|---|
| F-a | (a)/(b) invented narration dropped | `verify_narration(f, heard, redactor)[0] for f in spec.flows` -> `f for f in spec.flows` | 3 failed (invented-dropped, secret-redacted, no-transcript) |
| F-b | (a)/(b) secret redacted at save path | `verify_narration(f, heard, Redactor({}))` (verification kept, scrub emptied) | 1 failed (`test_a_secret_in_a_real_quote_is_redacted_at_the_save_path`) |
| F-c | (c) sabotage: remove the call | final `return spec.model_copy(update={"flows": flows})` -> `return spec` | 3 failed |
| F-d | (d) legacy FlowSpec still loads | legacy fixture JSON given an unknown key `narration_x` (what a schema break would look like) | 1 failed (`test_a_flowspec_saved_before_this_change_still_loads`) |

Restored baseline after all four: 5 passed.

## Commands and outputs

- `uv run pytest tests/test_ingest_narration.py` before the fix: `5 failed` (TypeError: unexpected keyword `redactor`).
- `uv run pytest tests/test_ingest_narration.py tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py tests/test_reconcile.py tests/test_orchestrate_runners.py` -> `70 passed, 3 warnings` (the warnings are the pre-existing AT-561 StageContext notice).
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`
- Full suite NOT run (scope instruction).

## Residuals for the checker

- `core/redact.py` untouched (other builder owns it); only `Redactor.scrub` is called.
- `orchestrate_runners.make_ingest_runner` calls `ingest_video` with no transcript, so under it every narration is dropped. That is consistent with the prompt it sends ("no speech detected - do not invent dialogue"), but it is a behaviour change worth a look.
- Default redactor reads the repo `.env` through `SecretStore.load(strict=False)`; no test here depends on a real `.env`.

**Metrics:** files changed 3 (1 src, 1 test, 1 manifest) · tests added 5 · affected tests 70 passed · falsifications 4/4 red · ruff clean · doctor clean · ingest.py 299 lines
