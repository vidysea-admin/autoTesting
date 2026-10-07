# Verdict — t202-litellm (cycle 0)

Date: 2026-10-07. Bound to `D:/autoTesting`, worktree `.worktrees/t202-litellm`, commit d5c200b7 (base 7782df41 = origin/master, unmoved).
Policy-Version: proportional-verification/2026-10-06.6 (the manifest's pin; judged under it).
Cycle checked: 0
Checkpoint: qa/checkpoints/t202-litellm.md
Checker: single, tier L (no dual: the dependency and credential guard make it L, but this is not an auth/tenancy or production-write unit).

## Check plan (step 0)

| Signal | Check |
|---|---|
| Logic changed (provider, factory, two routes) | affected tests plus the falsification floor, one throwaway copy per row |
| Dependency bump | `uv lock --check`, exact pin, lock diff additions only |
| Credential guard boundary | own probes: a real litellm 1.104.0 against a loopback HTTP mock, plus fake-SDK error probes |
| UI surface | `routes_runs.py` / `routes_learn.py` change error pages only; no template or rendering change, so no Mode D browser walk (LL15 UI is not in this slice). Probed through TestClient. |
| Protected test change | diff review of the 12 retargeted tests |

Mocks only: no external or paid call. The only sockets opened were loopback to a local mock server I ran.

## Re-run evidence

- `uv lock --check` clean; `pyproject.toml` diff is exactly one line, `litellm==1.104.0`; the `uv.lock` diff has no removed lines and 36 added packages (transitive closure: aiohttp, boto3, botocore, huggingface-hub, tokenizers, openai, tiktoken, jinja2, jsonschema and others).
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean.
- Falsification, 20 rows, each in its own throwaway copy (tests+src+scripts+docs), named node green in the copy before, red after, bound tree untouched. All 20 red on the intended assertion (LL1 x2, LL2 x2, LL3 x2, LL4, LL5 x2 incl. the stage-guard twin, LL6, LL7, LL8 x3, LL9, LL10 x2, LL11 x2, LL12). One first-draft mutant for LL8 (environ write) survived because it rewrote an already-set value (equivalent mutant); the replacement mutant (exports the key to OPENAI_API_KEY) is red. LL13 (pin loosened to `>=`: `uv lock --check` says the lockfile needs updating) and LL14 (a 337-line module: doctor `file-too-long`) are red.
- Independent real-SDK probe (real litellm 1.104.0 against a loopback mock): one physical HTTP request on a 500 (no hidden SDK retry, LL6 holds in practice); bearer key from the explicit kwarg; `os.environ` delta is exactly `LITELLM_MODE` and `LITELLM_LOCAL_MODEL_COST_MAP`; success and failure callback lists empty; no `litellm.telemetry` attribute; connections opened were loopback only.
- Full suite: started 18:50 (`uv run pytest`, no -q/-x), still running at the 45-min budget with about 38% done, because RAM and CPU were shared with several other checkers' suites (`suite.lock` was held by t190-ux, so I could not take it; I was denied permission to stop my own run). It has produced no result. A full suite is not a FAIL prerequisite; the repair checker should run it once on the repaired tree. One `F` showed at about 20%; its node is not yet known (log: `D:/autoTesting/.work/t202-suite.log`, summary at the end). `full-suite trigger: dependency manifest and lock change`, also for the step 6c pre-push check.

## Per-criterion

| Criterion | Result | Basis |
|---|---|---|
| LL1 spec grammar | MET | parse tests; 2 falsifications red |
| LL2 one factory | MET | AST test, three-way TestClient tests, 2 falsifications red; the literal grep matches a comment at `ui/app.py:66` (AT-785, wording) |
| LL3 validated or typed error | MET | 2 falsifications red |
| LL4 roles | MET | falsification red |
| LL5 guard before every call | MET | 4 provider tests red when the guard is removed, stage twin red when the stage call is removed |
| LL6 no hidden retries | MET | falsification red; real-SDK probe showed 1 request on a 500 |
| LL7 usage and trace | MET | falsification red |
| LL8 endpoint and key handling | NOT MET | the error path withholds only `LITELLM_API_KEY`/`LITELLM_API_BASE`; a vendor-native key (exported `GEMINI_API_KEY` or any `.env` value) echoed by a vendor error reaches the ProviderError verbatim (AT-782) |
| LL9 Gemini dialect | MET | falsification red |
| LL10 lazy, quiet | MET | 2 falsifications red; the telemetry wording is AT-785 |
| LL11 availability and no-credentials error | MET for what exists | run and learn route refusals proven; the HO16 queue does not exist in this tree and the CLI line is generic (AT-784, ledger) |
| LL12 mock stays, no network | MET | falsification red; `test_providers`, `test_langchain_fallback`, `test_ensemble_honesty` are not in the diff |
| LL13 dependency | MET | lock check, exact pin, additions only, falsification red |
| LL14 design rules | MET | ruff, doctor, falsification red; module is 261 lines |
| LL15, LL16 | not built; out of this slice | see the rulings |

## Rulings on the maker's open items

1. LL15 not built: a separate slice (plan unit 3), not a failure of LL1-LL14. T-202 stays open.
2. LL16: human-gated by the contract; T-202's done_check stays open.
3. LL11 partial: the queue does not exist yet and the CLI exits non-zero with a one-line message. Ledger row AT-784.
4. Learn route 500 on a malformed spec: reproduced (500, plain text). LL1 requires only a typed error; not a criterion failure. Ledger row AT-783.
5. Vertex `@` names: contract as written rejects them, so no failure. Ledger row AT-786, a product decision.
6. `litellm.telemetry` absent: confirmed against the installed source and a real-SDK run (no telemetry mechanism, no non-loopback connection). Wording only, AT-785.
7. Guard scan: floorless on every non-config `.env` value. A short value (`HEADLESS=1`) does false-refuse any prompt containing it, reproduced; it fails closed and cannot leak. The stage guard already behaves this way for the judge (AT-002), so the new surface is `act()` only. Ledger row AT-787. Leak direction: skipping `LITELLM_API_BASE` as config could let a userinfo-bearing URL through, but the explicit endpoint is also withheld in errors. No leak found on the prompt path.
8. Transitive lock packages: 36 added, none removed or bumped; consistent with D-071. Not a failure. The dependency review belongs to Umesh.
9. The 12 retargeted tests: all 16 changed lines swap the patch target `LangChainFallbackProvider` to `for_role` (a lambda returning the same fake provider) or fix a docstring. No assertion deleted, weakened or reordered; no threshold or skip. Protected-change justification: accepted.

## Findings

FAILURES:
- [LL8] sev: high - a vendor error text that contains a vendor-native key or any `.env` value is returned in `ProviderError`. Reproduced: a fake SDK raising `RuntimeError("...?key=AIza-EXPORTED-CANARY-999")` with `GEMINI_API_KEY` exported, and `RuntimeError("auth failed for key sk-ant-DOTENV-CANARY-777")` with that value in `.env`, give messages containing both canaries (litellm_provider.py `_failure`, the `hidden` list built from `_endpoint()` only, read this check). The learn route prints the exception on its refusal page. Fix: reuse the `_guard` value set in `_failure` and add canary tests. issue: AT-782.

PROPOSED/FILED ledger rows (low): AT-783 learn route 500, AT-784 LL11 partial, AT-785 contract wording, AT-786 Vertex `@`, AT-787 short `.env` value false refusal, AT-788 30-character prompt-echo check.

Scratch note (not a product finding): a first launch of my runner reused the shared scratchpad names `fals.py`, `fals.out` and `row0..row3`, so the maker's scratch copies of those may have been overwritten or removed. They were scratch only; my evidence lives in `scratchpad/ck-t202/`.

VERDICT: FAIL
SCOREBOARD: 13/14 criteria met for the slice (LL8 not met; LL15, LL16 out of slice), 0/0 invariants
TIER: L (dependency pin `pyproject.toml:35`, credential guard `litellm_provider.py:_guard`; single checker)
CAPABILITY-COVERAGE: 20/20 rows reproduced red, plus LL13 and LL14 red
LIVE-BROWSER: not-applicable (the changed UI routes alter error handling only, no template or rendering change)
ISSUES-WRITTEN: AT-782, AT-783, AT-784, AT-785, AT-786, AT-787, AT-788
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Everything LL1-LL14 holds under my own falsifications and a real-SDK loopback run except LL8's "no key in any ProviderError": the error path withholds only the LITELLM_* values, so a vendor-native key echoed by a vendor error reaches the message and the learn page. The fix is small and local. The full suite did not finish inside the budget and is left for the repair cycle.
Metrics: start=2026-10-07T18:49+05:30 end=2026-10-07T19:20+05:30 wall_min=31 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=22 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
