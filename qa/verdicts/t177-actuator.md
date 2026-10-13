# Verdict - t177-actuator

Verdict: PASS
Cycle checked: 1
Checker: independent (Claude Opus 5.5), head 96051785, worktree t177, master not merged in.

## Per criterion (qa/contracts/agent-fallback.md)
- AF1 PASS: tests/test_agent_fallback.py green (known screen 0 invocations, unknown exactly 1).
- AF2 PASS: typed FallbackResult (extra=forbid), malformed return raises and is not PASS (green).
- AF3 PASS: per-action Controller guard in stages/browser_use_backend.py (vet before, landing check after, unmapped action refused, sticky stop); test_browser_use_guard 14 green.
- AF4 PASS: IsolatedProvider kill verified (below); BoundExhausted names max_steps / wall_clock.
- AF5 PASS: production call site run_case_pipeline.py:156 (run_with_fallback), driven by tests.
- AF6 PASS: no vendor-client import outside providers/ (grep clean); browser-use pinned; pin/telemetry tests 12 green.

## D-089 item 2 / isolation
- test_a_hung_provider_returns_inside_the_deadline_and_the_child_is_dead: fake sleeps 120 s, ProviderDeadline (a ProviderError) raised at the 8 s bound, child not alive.
- Mutation: _reap made a no-op -> that test goes RED (child alive); restored, green.
- Child errors return as typed ProviderError; usage merged; bind_deadline caps a call at the invocation wall clock.

## Security reads
- ProviderChatModel applies the secret guard (redactor scrub, same seam as assert_no_raw_secrets) to the full prompt before Provider.act; the only text added after is a JSON-schema note. Provider is the only model path.
- Smuggling: raw JSON from an isolated provider is parsed by output_format.model_validate_json (browser-use AgentOutput); every resulting action still passes GuardedController vet before dispatch. Not bypassable.
- Video mask: _mask_context installs the init script on the context (once per context), flipped test shows a second tab masked.
- Browser-use path does no secret substitution itself; typed values are the model's literal text, scrubbed outbound, and the existing allowed_domains check applies (session domains passed as browser-use allowed_domains plus landing check).

## Not built (deferrable)
- expose_cdp=True wiring in ui/routes_runs.py: held by D-075 until T-203/T-204; headed-Chrome bind check. Contract AF1-AF6 do not require either (AF5 is the pipeline call site; AF3/AF6 use fakes). Deferral allowed for T-177 close, but IsolatedProvider is not yet constructed by any production path: record as follow-up for the wiring unit.

## Runs
- 137/139 passed in the first run; the 2 failures were load flakes: child spawn imports take ~25 s on this host while the Chrome worker runs (FAST=60 s budget; a PermissionError DuplicateHandle in one case while my concurrent kill probe ran). Reruns green (guard test; isolated tests 7/7 after rerun of the flaky one, mutation run included). Non-blocking advisory: tests/test_isolated_provider.py FAST=60 is tight under load.
- ruff clean, autotester doctor clean.
- docs/DECISIONS.md: git diff master -- docs/DECISIONS.md is empty (byte-identical); not edited.
- Branch is not merged with master (separate reconciliation after AT-651); the diff vs master is large for that reason only.
