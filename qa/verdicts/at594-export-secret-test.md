# Verdict — at594-export-secret-test

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checked commit:** 03494cf (code), 9ad6ccb (manifest)
**Checker:** /checker session (claude-opus) + a fresh claude-sonnet subagent (Mode A + adversarial field sweep)

```
VERDICT: PASS
SCOREBOARD: AT-594's ask is met (exported repro steps carry only placeholders; a raw declared value is scrubbed in both exports), and the real leak the builder found is fixed
FAILURES: none
CAPABILITY-COVERAGE: 3/3 mutable rows reproduced in own copy (5/5 green before). Dropping `redactor.scrub(...)` in `_repro_steps` fails exactly the 3 raw-value tests (Excel cell, HTML page, any workbook cell), each on `'hunter2-super-secret' not in ...`; the 2 placeholder-passthrough tests stay green. Rows 1-2 are declared n/a: regression pins on pre-existing safe behaviour, honestly labelled.
LIVE-BROWSER: not-applicable (changed paths: stages/report_export.py + tests; no UI route or template changed)
ISSUES-WRITTEN: AT-609 (title/figcaption fields, pre-existing, outside AT-594's steps scope); AT-612 (environmental flake seen in this unit's full-suite run)
EXECUTOR: maker builder (checker: claude-opus session + claude-sonnet subagent)
EXPLANATION: `_repro_steps` now scrubs through `SecretStore.load(project, env, strict=False).redactor()`, built once per export (not per row), which is the same loader every other stage uses. A missing .env or unknown project degrades to an empty redactor without crashing. The adversarial sweep confirmed steps are clean in both exports, and found Case.title and the screenshot figcaption still unscrubbed. Those fields are outside AT-594's stated scope and pre-date this unit, so they are filed as AT-609 rather than charged here.
```

## What I re-ran

- `uv run pytest` (full, no -q): 1 failed, 1854 passed, 6 skipped, 32 xfailed in 693 s. The single failure, `tests/test_browser_scroll_invariance.py::test_what_is_reported_does_not_change_when_anything_is_scrolled[auto-hidden-hidden]`, died in `Page.goto: net::ERR_NO_BUFFER_SPACE`: Windows socket-buffer exhaustion while 5 checker agents and the suite shared the machine.
  - Re-run alone: 18 passed, 32 xfailed, 3/3 in this worktree and 3/3 on master.
  - The unit touches only report_export.py and its own test file.
  - Environmental and not the unit's -> filed as AT-612, not charged.
- Ruff: All checks passed. Doctor: clean. Targeted (subagent): 23 passed.

## Diff scope (4c)

Merge-base fc3e07f. The unit changes src/autotester/stages/report_export.py (+38/-10) and adds tests/test_report_export_secrets.py (+133), both listed in "What changed". The only replaced line is the old parameterless `_repro_steps` signature; `redactor` is threaded through `_case_section` -> `_failure_detail_html` -> `_repro_steps`. Nothing removed.

## Adversarial field sweep (fake secret in every free-text field; Excel read back via openpyxl, plus HTML)

| field | Excel | HTML |
|---|---|---|
| step target / value / expect | clean | clean |
| Case.title | raw | raw (`<h2>`) -> AT-609 |
| screenshot Evidence.label | n/a | raw (`<figcaption>`) -> AT-609 |
| Verdict.scoreboard, Failure.reason / fix_hint | raw at the export layer | raw at the export layer |

The scoreboard and failure fields are the manifest's disclosed scope-out and are safe by the upstream masking RE5 relies on (execute.py:208 scrubs, and the judge only sees masked evidence). Noted, not charged.

A missing .env or unknown project gives no crash and an empty redactor.
