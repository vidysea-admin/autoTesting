# Verdict - t168-damage-control-report, cycle 1, coordinator B (blind dual check)

Cycle checked: 1
Bound to: D:/autoTesting. Commit checked: fb47735c (product 82ba1f1e). Repair base 56d24768 verified as an ancestor.
Policy-Version: proportional-verification/2026-10-10.9. Dual trigger line read: `src/autotester/stages/unified_report.py:207` is the `scrub_obj` call (real).

## Plan
Tier L (security trigger, cited line above). Checks: repair diff 56d24768..fb47735c in full (3 files: manifest, `stages/unified_report.py`, new `tests/test_unified_report_secrets.py`); whole-unit scan 00fae668..fb47735c (12 files, all in the manifest's What-changed); DC4 re-run; own adversarial pass on "can any Redactor secret reach any output"; one own falsification; affected tests, ruff, doctor in a clean `git archive` copy. DC1-DC3 keep their cycle-0 results; the affected-test run below also re-ran them green.

VERDICT: FAIL
SCOREBOARD: 3/4 criteria met (DC1-DC3 met; DC4 met as written, but see F1), invariant C5 not held on the error path (F1)
TIER: L (security: redaction of report output, unified_report.py:207)

## DC4 (as written)
Met. In a clean copy of fb47735c the scanner subprocess reports `0 leak(s)` on the artifact for a secret `p&ss<w>o'rdQ9` planted in every text field; raw and HTML-escaped forms are absent from the HTML, the CLI output and the report object. `tests/test_unified_report.py tests/test_unified_report_secrets.py tests/test_goal_contract_registration.py`: 16 passed. `uv run ruff check src tests scripts`: clean. `uv run autotester doctor`: clean (clean copy).

## FAILURES
- [C5 via DC4] sev: medium - F1: the changed route and CLI echo an exception message built from stored data without scrubbing it, so a secret held in a stored file reaches the output.
  Reproduced (my own test, `qa/evidence/t168-damage-control-report-r1b/attacks.py.txt`, test_a3): a stored `release.json` whose `finished` field holds `p&ss<w>o'rdQ9`. `autotester release-report demo --out o.html` prints pydantic's `input_value="p&ss<w>o'rdQ9"` raw (exit 1); `GET /projects/demo/damage-report` returns HTTP 200 with the escaped form `p&amp;ss&lt;w&gt;o&#x27;rdQ9` in the page.
  Cited lines read in this check: `src/autotester/ui/routes_unified_report.py:30-33` (`escape(str(exc))`), `src/autotester/cli_release.py:105-106` (`typer.secho(str(exc))`). `ValidationError` is a `ValueError`, so both `except ValueError` blocks catch it. Same class of failure as cycle 0 (the redactor runs only on the success path). Fix direction: scrub `str(exc)` with `_load_redactor(store)` in both places, or print a fixed message for any ValueError that is not the `_pick_run` one.
  Honest limit: it needs a stored file with a secret in a wrongly typed field, so the trigger is rare. I defend it because the report's premise is that stored data may hold a raw secret, and this is an output channel of the feature that skips the scrub.

## Attack results (question: can any Redactor secret reach any output?)
| Attack | Result |
|---|---|
| UI route, with and without `?run=`, secret in every text field | clean (raw and escaped) |
| CLI `release-report`, scanner on the artifact | clean |
| Loader/validation exception text on route and CLI | LEAK, F1 |
| Redactor load raises | fails closed (exit 1, no file written) |
| `.env` missing, so an empty Redactor | report renders values as stored (nothing is known to scrub; same as every other export) |
| Secret used as flow id / case id / slug | scrubbed (value fields). `scrub_obj` does not scrub dict keys, but the report holds only fixed keys (`counts`), so no reachable key |
| Short secret that is a substring of an enum value (`fail`) | build raises `ValidationError` (scrub rewrites an enum field); no leak, fails closed, report unbuildable. P2 |
| Percent-encoded secret in a stored first-party URL (`?pw=p%26ss%3Cw%3Eo%27rdQ9`) | present in the HTML (exact-byte scrub cannot match it). Upstream T-170 `network_capture.py` scrubs by exact bytes only. P1 |
| Secret equal to two adjacent items joined by the renderer (`alpha, beta` from `_listed`) | present in the HTML (the join happens after the scrub). Needs a secret equal to the join. P3 (low) |
| Data added after the scrub (renderer, route, environment) | none found: render uses only report fields; no log lines in the new modules |

## Falsification (DC4, own mutant, one hunk, copy outside the bound tree)
Green before: clean copy, `-k dc4` 4 passed (affected set 16 passed). Mutant: `build_report` line 207 `_load_redactor(store).scrub_obj(` replaced by `type(_load_redactor(store))({}).scrub_obj(` (an empty redactor). After: 2 failed (`test_dc4_special_character_secret_is_absent_raw_and_escaped_in_html_and_cli`, `test_dc4_report_object_is_clean_before_it_is_rendered`) on `AssertionError: p&ss<w>o'rdQ9`; the other 2 stay green. Copy discarded.

## Diff scope (4c)
Repair diff: only `stages/unified_report.py` (13 lines; scrub moved to the object, post-render scrub removed), the new test file, the manifest. Nothing else removed. Whole-unit diff 00fae668..fb47735c: 12 files, all named in the manifest.

PROPOSED-ISSUE: {"severity":"medium","feature":"damage-control-report","title":"Percent-encoded secret in a stored first-party network URL reaches the report; exact-byte scrub cannot match it","evidence":"qa/evidence/t168-damage-control-report-r1b/attacks.py.txt test_a2; stages/network_capture.py scrubs by exact bytes","status":"open"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"A declared secret that is a substring of an enum value (e.g. 'fail') makes build_report raise ValidationError after scrub_obj","evidence":"attacks.py.txt test_a7; stages/unified_report.py:206-207","status":"open"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"Renderer joins fields after the scrub (_listed ', '.join), so a secret equal to the join reaches the HTML","evidence":"attacks.py.txt test_a6; stages/unified_report_render.py:57","status":"open"}

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: DC1-DC4 as written hold and the cycle-0 defect is fixed, but the error path of the new route and CLI prints stored-data exception text unscrubbed, so a secret can still reach an output of this feature. Attacks ran in a clean archive copy; no full suite (coordinator A owns it). The session was cut once by a usage limit, so wall time includes that gap.
Metrics: start=2026-10-10T20:49:21Z end=2026-10-10T23:50:00Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=0 defects_unit=1 defects_6c=0
