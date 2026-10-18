# Verdict - at1304-trace-redact (coordinator B, blind)

**Verdict: PASS**
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-18.15
Checked: HEAD f25948ca (code at 1d9d2cd3), base 8f2b6df3 = `git merge-base HEAD int/1017`. Tier L (redaction boundary), dual-check coordinator B.
Metrics: start=2026-10-18T21:13:00Z end=2026-10-18T21:26:00Z wall_min=13 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=780 mutants=0 defects_unit=0 defects_6c=0

## Check plan
Diff scope, C1 numbers/timestamps, C2 no raw secret on disk (adversarial), C3 bad line named by file:line without content, residuals judged, floor falsification x3, lint.

## Scope (git diff --stat 8f2b6df3..HEAD)
Only: core/trace.py, schema/failure_bundle.py, stages/run_artifacts.py, tests/test_trace_numeric_secret.py, tests/test_run_failure_artifacts.py, qa/manifests/at1304-trace-redact.md. `core/redact.py` is not in the diff. No foreign-worktree files (stash incident not visible in the range). Untracked `qa/evidence/at1304-trace-redact.a/` belongs to coordinator A and was not opened.

## Criteria
- C1 PASS. `uv run pytest` on the 8 affected files: 71 passed. trace.py:45-48 scrubs only `str` values, numbers/datetimes pass through, then `_LINE.dump_json` (trace.py:59) encodes. Differential probe (evidence .b/probe2.py): with no secrets, old and new lines are byte-identical apart from `recorded_at`, NaN latency serialises to null in both.
- C2 PASS. Adversarial probe (.b/probe.py): 8 secrets (quote+backslash, unicode, newline, tab, base64-like, HTML chars, emoji, `587`) x 11 variants (raw, embedded, upper, JSON-escaped, base64, reversed, percent x1/x2, html-escaped, hex) x 8 string fields (error, fed_id, trace_id, tool name, refusal, provider, role, prompt_file) x old/new. Every line that reached disk: 0 raw / folded / JSON-escaped secret in any decoded string value (0 leaks). 56 old-vs-new differences, all in the safe direction: quote/backslash secrets, old RAISED (fail closed), new masks and writes; upper-cased newline/tab secrets, old wrote, new now RAISES from `assert_clean` (fail closed, nothing written). No case where old masked/raised and new writes a secret.
- C3 PASS. trace.py:124 raises `TraceParseError(f"{path.name}:{number}: not valid JSON")`, file name and 1-based line only; run_artifacts.py:92-97 stores it in `BundleAssembly.reason` (max 200, extra=forbid kept) and logs only that string (no exc_info); any other exception stays value-free. Test asserts the secret is absent from index.json and the log.

## Falsification floor (copy outside the repo: scratchpad .../b/fz; green 11 passed before, restored 11 passed after; restored files diff-identical to the worktree)
- C1: scrub the encoded line again (trace.py:59) -> 5 failed, incl. `test_smtp_port_587_secret_while_a_step_latency_is_0_587_stays_valid_json` (JSONDecodeError on `"input_tokens":[REDA...`) and `test_a_timestamp_containing_the_secret_digits_still_parses`.
- C2: string branch returns value unscrubbed (trace.py:46-48) -> 3 failed, incl. `test_string_fields_are_still_scrubbed_with_the_same_numeric_secret` and the assert_clean gate test.
- C3: drop `reason=reason` (run_artifacts.py:97) -> 1 failed, `test_unparseable_trace_line_is_recorded_with_file_and_line_not_swallowed` (reason=None).

## Residuals judged (none is a raw-secret leak; none blocks)
1. Dict KEYS are not scrubbed by `_scrub_value` (trace.py:49-50). Unreachable today: every span is a `extra="forbid"` model with fixed field names and no dict field (schema/trace.py). LOW row (future-proofing: a dict-valued span field would pass keys unscrubbed).
2. `StageName` enum member (the `stage` field) is passed through unscrubbed (trace.py:43-44). Probe: a declared secret equal to a stage name (`execute`) appears in `stage`. The value is a public fixed vocabulary, so it discloses nothing; `status` is a plain str and IS scrubbed. LOW row, as the manifest discloses.
3. Free-text strings and `trace_id` still lose a digit run equal to a short numeric secret; line stays valid JSON (probe shows no parse failure). Conservative, unchanged rule.
4. Behaviour change: an upper-cased/reversed secret containing a newline or tab now makes `assert_clean` raise from `record_*` where the old encoded-line check missed it. Fail closed, matches RT6 intent; LOW (the raise propagates to the stage writer, same class as any other RT6 refusal).
5. `ui/routes_report.py:117` `read_spans` has no handler for a corrupt trace; it was unhandled with `JSONDecodeError` before too, so no regression.

## Lint
`uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> 4 violations, all stale-generated/stale-committed for docs/MAP.md and docs/SNAPSHOT.md (the merge owner regenerates), none in changed files. trace.py is 131 lines.

PROPOSED-ISSUE: low | core/trace.py:49 | `_scrub_value` does not scrub dict keys; add `self._scrub_value(k)` for str keys if a dict-valued span field is ever added.
PROPOSED-ISSUE: low | core/trace.py:43 | Enum pass-through skips scrub/assert_clean for `StageName`; disclosed, fixed public vocabulary, no leak.
PROPOSED-ISSUE: low | core/trace.py:47 | `assert_clean` can now raise on upper-cased/reversed newline- or tab-bearing secrets in span strings (fail closed); confirm the stage writer tolerates the ValueError.

Evidence: qa/evidence/at1304-trace-redact.b/ (probe.py, probe2.py, mut.py).
