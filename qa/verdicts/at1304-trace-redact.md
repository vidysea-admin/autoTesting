# Verdict - at1304-trace-redact (coordinator A, blind)

Cycle checked: 0
Date: 2026-10-18 · Base 8f2b6df3 (merge-base with int/1017 verified) · Head f25948ca (code 1d9d2cd3) · Policy proportional-verification/2026-10-18.15

## Plan (step 0)
Tier L (redaction boundary). Checks: C1 numbers/timestamps untouched + valid JSON; C2 no raw secret on disk in any string field; C3 bad trace line named by file:line, content never. Diff-scope read (4c), adversarial redaction probe, one falsification per criterion in a copy outside the repo. Lane: normal (cycle 0, tier L, quick lane off).

## Block
VERDICT: PASS
SCOREBOARD: 3/3 criteria met, core-invariants C5 (redaction) holds, RT6 holds
TIER: L (core/trace.py:46-47 changes the Redactor.scrub/assert_clean call site on the persistence path)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no UI, no capability rows)
LIVE-BROWSER: not-applicable (changed paths: core/trace.py, stages/run_artifacts.py, schema/failure_bundle.py)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Strings are now scrubbed and gated before JSON encoding, so a numeric secret cannot edit a float or timestamp and a quote/backslash/unicode/newline secret no longer slips past the escaped line. I re-ran the affected set (71 passed), probed six adversarial secrets across every string field (0 leaks, all lines valid JSON, read_spans parses), and falsified each criterion in a copy (green then red then restored). Residuals are low rows, none is a raw-secret leak.

## Evidence (all run by me in this check)
- Diff scope: `git diff --stat 8f2b6df3..HEAD` lists only trace.py, failure_bundle.py, run_artifacts.py, 2 test files, the manifest (6 files). `core/redact.py` untouched. Nothing removed except the old encoded-line scrub at trace.py:55-62. No stash residue, no sibling-worktree file.
- Read trace.py 1-131, run_artifacts.py and failure_bundle.py diffs, schema/trace.py (all span fields are str/int/float/bool/datetime/Literal/Enum; no dict-valued field), redact.py Redactor (scrub raw-substring replace, assert_clean raw substring).
- Re-run: `uv run pytest tests/test_trace_numeric_secret.py tests/test_run_trace.py tests/test_provider_attempts.py tests/test_ui_runs_parallel_trace.py tests/test_run_failure_artifacts.py tests/test_failure_bundle.py tests/test_failure_bundle_escape.py tests/test_failing_step_bundle.py` -> 71 passed (7.6 s). `uv run ruff check` on the 5 changed files -> clean. trace.py is 131 lines.
- C1: 0.587 latency, 587/5870 tokens and `.587` timestamps survive with secret 587 (test + probe, valid JSON, read_spans parses).
- C2 adversarial probe `qa/evidence/at1304-trace-redact.a/adversarial-probe.txt`: secrets with quote+backslash, unicode, newline, tab, 587, 13-digit numeric, each placed in error, trace_id, provider, role, prompt_file, fed_id, tool name, refusal; raw, JSON-escaped, ensure_ascii and unicode_escape forms all absent from disk; every line valid JSON; BAD 0.
- C3: `trace.jsonl:2: not valid JSON` carried into `BundleAssembly.reason` (max 200, default None, extra=forbid kept); log line value-free.

## Falsification (copy outside the repo, fresh git archive per mutant, PYTHONPATH to the copy, green before 21 passed)
- [C1] trace.py:55-62 back to scrub of the encoded line -> 5 failed (test_smtp_port_587..., test_a_timestamp...); restored 21 passed.
- [C2] trace.py:46-48 `return value` (no scrub, no gate) -> 5 failed incl. test_no_raw_long_secret..., test_the_assert_clean_gate..., test_run_trace::test_every_span_is_redacted_before_it_is_persisted; restored green.
- [C3] run_artifacts.py:97 drop `reason=reason` -> red on `entry.reason` assertion; a second mutant putting the line content in the TraceParseError message -> red (reason mismatch, content in log line shown); restored 21 passed.

## Residuals judged
- Enum members (stage/status) pass through unscrubbed (trace.py:43-44): a secret equal to a stage word like `execute` is not masked. Fixed public vocabulary, masking it would break `read_spans` validation, nothing sensitive is disclosed. Low.
- `_scrub_value` does not scrub dict KEYS (trace.py:49-50); no span has a dict field, so unreachable today. Low.
- `read_tool_spans` (trace.py:106) still uses bare `json.loads`, so a corrupt tool line raises `JSONDecodeError` whose `.doc` holds the line; unchanged by this unit, not on the bundle path. Low.
- Short numeric secret still masks digits inside string fields such as `trace_id` (conservative, line stays valid JSON), as the manifest states. Not a leak.
- Process note (git stash incident) is not a product defect.

PROPOSED-ISSUE: {"severity":"low","title":"read_tool_spans parses trace.jsonl with bare json.loads; a corrupt tool line raises JSONDecodeError (carries the line in .doc) instead of TraceParseError with file:line","detail":"core/trace.py:106; same C3 rule as read_spans, outside AT-1304 scope","found_by":"checker"}
PROPOSED-ISSUE: {"severity":"low","title":"TraceWriter._scrub_value passes Enum members and dict keys through unscrubbed","detail":"core/trace.py:43-44,49-50; unreachable with today's span shapes (fixed vocabulary, no dict fields); revisit if a span gains a free-text Enum or dict field","found_by":"checker"}

Metrics: start=2026-10-18T21:08:00Z end=2026-10-18T21:26:00Z wall_min=18 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=1080 mutants=0 defects_unit=0 defects_6c=0
