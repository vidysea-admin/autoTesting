# Verdict - run-teardown-stall (checker B: contracts + adversarial)

**Cycle checked:** 0
**Verdict:** PASS (with non-blocking findings F1-F3 and one decision for Umesh, D1)
**Checked:** branch fix/run-teardown-stall @ 0adfb21f (base e74664f8), worktree only. Probes in `.work/probe_hk_b.py`, `.work/probe_trace_b.py`, `.work/probe_ram_b.py` (gitignored). New + judge-time tests re-run: `pytest -o addopts= tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py tests/test_run_budget_judge_time.py` -> 29 passed. No live run, no browser launched, no .env read.

## 1. Does housekeeping let browser time that ACTS on the target escape wall_clock_s?

Call sites of `RunBudget.housekeeping()` (grep `housekeeping` in src): only `browser/teardown.py:99-106` (`close_session`: context.close, driver.stop, video sweep) and `ui/run_execution.py:64` (`session.start()` = launch_persistent_context, no navigation) and `:112` (`_wipe_entry_profile`). No step/navigation/fill/click path is wrapped; `parallel_run.default_session_factory` start is traced but NOT housekeeping (conservative). So housekeeping wraps only wipe/start/close, as claimed.

Bound is enforced (`run_budget.py:53-54` `excluded = min(spent, allowance)`; `:132-133`). Probes:
- P1 allowance 0.4 s, 1.0 s spent -> charged 0.60 s (excess is charged). PASS.
- P2 housekeeping nested 3 deep for 1.0 s -> spent 1.00 s (union, not 3x). Nesting cannot inflate the exclusion. PASS.
- P5 wall_clock 1.0, hk allowance 0.5: acting 0.9 s + 0.5 s hk still allowed; acting 1.2 s refused. Fail-closed preserved.
- Worst case: acting time beyond `wall_clock_s` is capped by the pool `60 s * cases` (`run_budget.py:274-284`, `for_cases` :104-108). The "60 s per case" is a pool sized per case, not per-case enforced: one case can spend the whole run pool (non-blocking, matches judge precedent).

Findings (non-blocking, bounded):
- F1 (overlap -> acting time escapes). Both `_ExcludedClock`s subtract independently (`run_budget.py:130-133`). (a) P4: worker A in housekeeping while worker B acts on the target for 1.0 s -> charged 0.00 s, i.e. B's acting time is held off the clock (same property `judging()` already had; applies to the parallel fan-out where `session.close()` runs per case). (b) P3: a second of real time inside BOTH `judging()` and `housekeeping()` is subtracted twice (charged -1.00 s after 1.0 s overlap; after 1.0 s more acting charged 0.00 s, true acting 1.0 s). So total escape is bounded by `judge_allowance + housekeeping_allowance` (45 + 60 = 105 s/case) rather than by the union of non-acting time. Fix, not required for PASS: one shared union clock for all non-acting time with a single combined allowance (`run_budget.py:96`, `_browser_elapsed_locked`).
- F2 the exclusion is invisible in the run record: `RunBounds` (`schema/run.py`) reports `wall_clock_s` only; `housekeeping_s_used` / `judge_s_used` (`run_budget.py:140-151`) are not persisted. CN10's spirit ("reported, not capped") argues for recording the allowances next to the bound.
- `wall_clock_request_s` (`run_budget.py:250-258`) does not include the housekeeping allowance, so the gate is asked for the same number as before; nothing in the grant changes. Good (no silent widening of what Umesh is asked to approve), but it also means the granted `wall_clock_s` no longer equals max run time.

Contract judgement: `schema/approval.py:73` says `wall_clock_s` is "how many seconds this run may take in total"; consent.md CN10 / parallel-run.md PR7 say the bounds apply to the aggregate and are never widened per worker. Neither contract mentions judge or housekeeping time; there is no DECISIONS entry for the existing judge allowance either (precedent: `qa/verdicts/budget-judge-time.md` PASSed an equal, bounded, fail-closed exclusion with no amendment). The housekeeping exclusion is the same kind of change: non-acting time, bounded, excess charged, gate request unchanged, no per-worker multiplication of a bound. 
**D1 (Umesh decision, does NOT block this unit):** a DECISIONS entry (via `scripts/append_decision.ps1`, Approver Umesh) recording that `wall_clock_s` is the TARGET-ACTING clock and that bounded judge (45 s/case) and housekeeping (60 s/case) allowances sit outside it, plus a one-line consent.md CN10 / parallel-run.md PR7 note and the `approval.py:73` wording ("in total" is now inaccurate). The checker (not the maker) amends contracts. Recommend D1 before the next production-bound run; F1 fix can ride the same change.

## 2. B9 (browser-and-secrets.md:66-69): cancel-not-kill
- Diff adds no `kill`/`taskkill`/`pkill`/`terminate` (grep of added lines: only comments saying "No process is killed"). Repo-wide `proc.kill/terminate` hits are `providers/isolated.py:154,157` and `sources/gws_runner.py:112`, own child processes, untouched by this diff.
- `teardown.py:33-45` cancels asyncio tasks on the `_loop` of the one Playwright object being closed (`ChannelOwner._loop = parent._loop` verified in the installed playwright), so it can reach only that session's driver connection; each session has its own `sync_playwright()`. Teardown still targets only this session's context and driver (`session.py:137-146`); `forget_cdp_port(self.paths.profile_dir)` unchanged. A Chromium that survives is released by `driver.stop()`, not killed. B9 satisfied; no contract amendment needed. Residual (maker already disclosed, not a B9 breach): a lingering Chromium after a cancelled close is unproven on a quiet host.

## 3. Secrets in new trace rows / run.json
- `judge_tier_failed` note is `f"{name}/{role}: {type(exc).__name__}"` only (`langchain_fallback.py:171-176`); span goes through `TraceWriter._append` scrub + `assert_clean` (`core/trace.py:48-70`). Probe `.work/probe_trace_b.py`: a tier raising `RuntimeError("401 bad key sk-live-SUPERSECRET... token=...")`, a context.close raising with the secret, and a `traced_phase` raising with the secret -> trace.jsonl rows carry only `RuntimeError` / `ValueError` / `note:null`; `SECRET in trace: False`. Teardown notes are `type(exc).__name__` or "abandoned after Ns" (`teardown.py:85-87`).
- `Run.phase_totals_s` is phase-name -> seconds and `unaccounted_s` a float (`schema/run.py`, `run_launcher.py:170-173`): no free text.
- Pre-existing, outside this unit (informational): `langchain_fallback.py:158-165` still builds `ProviderError("... {name}: {Type}: {exc}")` containing the raw exception text (probe showed the key text in that exception). Not written to the trace by this diff; worth its own issue.

## 4. RAM warning never refuses a run
`run_launcher.py:154-165`: measurement raise -> swallowed (probe: returns False); low -> one stderr line and returns True; adequate -> silent. `prepare_run` ignores the return (`:145`). F3 (hardening, non-blocking): the `free_mb >= LOW_RAM_WARN_MB` compare and the `print` sit outside the `try`, so a seam returning None/str raises TypeError (probe) and `sys.stderr = None` is only safe because print(file=None) falls back. The real `_free_ram_mb` (`parallel_run.py:64-106`) always returns a float, so no refusal path exists in production. Move the compare/print inside the try.

## Result
PASS on the contracts-and-adversarial axis. No blocking finding. Decision D1 is Umesh's and recommended, not a gate on this unit. The other checker owns the sharded full suite; `autotester doctor` D-110 dangling citation is the known pre-existing item.
