# Verdict — t202-litellm (cycle 1, repair checker)

Date: 2026-10-07. Bound to `D:/autoTesting`, worktree `.worktrees/t202-litellm`, commit 7b87b222 (fix c27133d8, base a77ed746). Cycle-0 verdict kept at `qa/verdicts/t202-litellm.r0-1.md`.
Policy-Version: proportional-verification/2026-10-06.6 (the dispatch's pin).
Cycle checked: 1
Checkpoint: qa/checkpoints/t202-litellm.md
Resume: none (first dispatch of cycle 1). Checker: single, tier L.

## Check plan (step 0)

| Signal | Check |
|---|---|
| Failed criterion LL8 (AT-790) | own canaries through every ProviderError surface, own falsifications in throwaway copies |
| Fix diff = `litellm_provider.py` only (`_secret_values`, `_guard`, `_failure`) | affected tests; LL5 re-falsified because `_guard` was refactored |
| Dependency manifest and lock | `uv lock --check`, hashes vs the cycle-0 identity, one full suite owed |
| UI | error text only, no template or rendering change: no Mode D |
| Other criteria | reused by evidence identity (below) |

Mocks only; no network (every probe ran under the `no_network` socket guard, except the TestClient learn route, which needs a loopback socketpair and uses the fake SDK).

## LL8 re-run (own canaries, own mutants, in a copy outside the bound tree; the bound tree was never mutated)

Probe file `qa/evidence/t202-ll8-probe-cycle1.py.txt` (rename to .py to run), runner `t202-ll8-fals-cycle1.py.txt`. 8 secret sources x 3 echo shapes (`?key=` URL, "Incorrect API key provided: X", bare value): exported GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, LITELLM_API_KEY; `.env` ANTHROPIC_API_KEY; an arbitrary `.env` key (MY_DB_PASSWORD); the `secrets=` option.

Surfaces, each asserted canary-free:
- provider direct, `judge()` and `act()`: 48 combinations.
- learn route, the 400 refusal page (TestClient, real `LiteLLMProvider` over the fake SDK): 8.
- CLI `autotester expand demo --provider litellm` (CliRunner, output plus exception): 7 run (the `secrets=` option is programmatic, so 1 skipped).
- run route's grader-failure path, `run_and_grade_case_resilient`: verdict and result JSON, and every file written under the project root: 8.
- Controls: `LITELLM_API_BASE` userinfo is still withheld; a benign "429 rate limit exceeded" still reaches the message (the fix does not blanket-withhold).

Result: 50 passed, 1 skipped.

Single source: `test_secret_set_is_single_source` counts `_secret_values()` calls for one failing `judge()`: exactly 2 (one in `_guard`, one in `_failure`). Source read at `litellm_provider.py:183-203`: both call `self._secret_values()`; no second list exists.

Falsification, one copy each, green before and red after (probe + guard + learn tests):

| Row | Edit | Red |
|---|---|---|
| F1 | `_failure` withholds only the endpoint (the cycle-0 bug) | 46 failed, including the maker's 4 AT-790 tests and my route families |
| F2 | `_secret_values` drops exported vendor keys | 27 failed |
| F3 | drops `.env` values | 14 failed |
| F4 | drops the `secrets=` option | 7 failed |
| F5 | `_guard` gets its own copy of the list (breaks single source) | 2 failed (my single-source probe, the guard's exported-key test) |
| F6 | LL5: guard call replaced by a no-op | 4 failed (guard tests) |

LL8: MET.

## Criteria reused by evidence identity (cycle-0 checkpoint)

Unchanged since cycle 0: `uv.lock` hash ad191bacfcd0dae4, `pyproject.toml` hash 5a4c8969ae612f0a. The only product file under `providers/` that changed since d5c200b7 is `litellm_provider.py` (10 added, 5 removed, the three methods above). Cycle-0 evidence for LL1-LL4, LL6, LL7, LL9-LL14 is kept (their inputs are unchanged); the affected tests were re-run anyway: `test_litellm_provider`, `test_litellm_guard`, `test_provider_factory`, `test_ui_learn`, `test_ingest_narration`, `test_providers`: 87 passed.
`uv lock --check`: Resolved 118 packages, no change. `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean. The provider module is 266 lines.

## Not completed: the one full suite

Mandatory remaining: `uv run pytest` (no -q, no -x; deselect `tests/test_crawl_inventory_live.py` by name, pre-existing hang), trigger: dependency manifest and lock change.
I did not take `D:/autoTesting/.work/suite.lock`. It was held by `t203-hosting cycle 1 suite` from 19:29; I waited about 13 min (19:53-20:06, counted as blocked_min). The lock then became free, but the coordinator's queue (T-125 checker A, at758-759 dual, T-204 dual, 8f integration head, AT-773, then T-202 last) tells me to leave it and return CONTINUE-NEEDED. This is not a code finding. No suite run was started.

Not done because the verdict is not PASS: manifest flip to checked-PASS, merge, push.
Merge note for the maker: origin/master is at f1e8be56 and its `qa/issues.jsonl` already uses AT-787..802, so T-202's AT-790..796 collide. Renumber them after the highest master id at merge time (803 or later) in `qa/issues.jsonl`, the manifest, the r0-1 verdict and the checkpoint, and confirm no id appears twice before pushing.
LL15 and LL16 are not built; T-202 stays NOT done in goal.json whatever this verdict says.

PROPOSED non-blocking (low): no repo test fails when `_guard` and `_failure` diverge in their secret list (only my probe F5 does); adding the call-count assertion from `test_secret_set_is_single_source` would pin it.

REMAINING: full suite (queued 7th), then manifest flip, merge, push if the suite is green.

VERDICT: CONTINUE-NEEDED
SCOREBOARD: all slice criteria evidenced except the owed full suite (LL8 now met); LL15, LL16 out of slice
TIER: L (dependency pin `pyproject.toml:35`, credential guard `litellm_provider.py:_guard`; single checker)
CAPABILITY-COVERAGE: 6/6 repair rows reproduced red (F1-F6), green before in each copy
LIVE-BROWSER: not-applicable (error text only, no template or rendering change)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: LL8 holds on every surface that prints a ProviderError (provider, learn page, CLI, run grader verdict and saved files) against 8 secret sources and 3 echo shapes, and the secret set is one method shared by `_guard` and `_failure`. Only the one full suite is missing, held back by the agreed lock queue, not by a defect.
Metrics: start=2026-10-07T19:37+05:30 end=2026-10-07T20:09+05:30 wall_min=19 agent_min=unavailable blocked_min=13 suite_runs=0 repeat_runs=0 mutations=6 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
