# Verdict - t168-damage-control-report (checker A, single check)

Cycle checked: 0 | Resume: 0 of 2 | Retry: 0 | Policy-Version: proportional-verification/2026-10-10.9 | Date: 2026-10-10 (UTC) | Bound to D:/autoTesting
Checked: worktree `.worktrees/t168-damage-control-report` HEAD 56d24768 (product cdb0ae53), diff 00fae668..56d24768.

## Check plan
Logic and shared-module change (M): affected tests plus 1 falsification per criterion; UI surface changed (project-page button, new route): live browser check; honesty probes on records the checker built; secret probes (plain, and with HTML-special characters, 15 fields); XSS probe. Not applicable: persona walk beyond the lead's 2-step path (done in the browser), data audit, rubric grading. Lane check: not run (lane off in adapter; unit has 4 new files).

VERDICT: FAIL
SCOREBOARD: 3/4 criteria met (DC1, DC2, DC3 met; DC4 not met), invariants: C12 partly (see issue 2), others none-touched
TIER: M (multi-file behaviour, 4 new modules, shared files cli.py / routes_report.py / project_view.py edited; no tier raise). Observation for the maker: the finding below sits in the unit's one secret-handling point (`src/autotester/stages/unified_report.py:207`); the repair touches secret handling, so consider `dual-trigger: security src/autotester/stages/unified_report.py:207` for cycle 1. I did not raise the tier.
FAILURES:
- [DC4] sev: high - a project secret containing `&`, `<`, `>` or `'` reaches the artifact HTML-escaped (15 of 15 planted fields: flow id, issue detail, flagged reason, baseline note, git sha, verdict reason/fix_hint, API url, persona summary, crawl hole name, stop reason, case title) and `scripts/check_no_secrets.py` exits 0 "0 leak(s)" on that file. Cause: `unified_report.py:207` scrubs after `render_html` escapes (`unified_report_render.py` `_e`); `Redactor.scrub` matches exact bytes (verified: `scrub(html.escape(secret))` does not mask). Command: `.venv/Scripts/python qa/evidence/t168-damage-control-report/probe_secret.py` (redactor holds the value, probe_env.py). Plain secret: clean. Fix: scrub the report object before render (`scrub_obj`) and keep the final scrub; test with a special-character secret. issue: ISS-t168-damage-control-report-1
CAPABILITY-COVERAGE: 4/4 reproduced in own copies (single hunk, green before in the copy, red after on the named assertion): DC1 `incomplete=False` -> red `incomplete is True`; DC2 history loader bypassed -> red SENTINEL-HISTORY; DC3 history section dropped -> red `<section id="history"`; DC4 `_load_redactor` stubbed -> red (secret in artifact). The builder's DC4 edit is two hunks; single-layer mutants (final scrub only, workflow redactor only) survive: low, issue 3.
LIVE-BROWSER: qa/evidence/browser-t168-2026-10-11-checker/ (report.json + 7 screenshots). Headless Playwright, one context, 127.0.0.1:8765, scratch data root under the worktree `.work/`, server PID 65352 stopped. Project page shows the button; click lands on /projects/demo/damage-report with 5 sections; regression lists c1 as regressed against rel0; project with one release shows "No trusted baseline, so no regression claim" and no Regressed/Fixed; project with no runs shows the empty state (0 sections, no PASS); ?run=../../etc -> 400, unknown project -> 404; `<script>`/`<img onerror>` in issue detail rendered as text, window.__xss undefined, 0 dialogs, 0 script elements; bounded crawl shows the amber "Incomplete" banner, `40% of controls (2 of 5)` and `not_visited: 1`. Console errors: only my two deliberate 400/404 navigations. Low: horizontal page scroll at 390 px (issue 4).
ISSUES-WRITTEN: ISS-t168-damage-control-report-1 (high), -2 (medium, C12: API section reads clean when a run stored results but no NETWORK evidence at all, `unified_report_render.py:95`), -3 (low), -4 (low, process notes)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence summary
- Tests: `pytest tests/test_unified_report.py -p no:xdist` 12 passed (own run); same on the merge-tree with T-167 `102a4b91` 12 passed; shared-file nodes 71 passed; ruff clean; doctor clean.
- Honesty probes (probe_honesty.py): 24 of 25 pass. No baseline -> no regression claim; not-run case `not run`, ungraded `no verdict`, planless flow `not run`; every non-completed crawl status, a bounded crawl at 100%, and a completed crawl with no coverage record all read Incomplete; missing release/persona/crawl/cases read `Unavailable: <reason>`; persona counts equal rows. The one miss is issue 2.
- Diff scope (4c): nothing removed; 11 files, all listed in "What changed" plus docs/MAP.md; cli.py 300, routes_report.py 297.

## Rulings
1. New modules: neither the brief (section 5 "Proposed ... to be confirmed", section 8 "OPEN until the owner confirms") nor the contract names them, and D-081's Changes-authorized says no src change rides on it; `new-module-authorization.md` answered AT-710 only. So the builder's "D-081 covers it" is not supported. No design rule is broken (doctor clean), so it is not a FAIL ground; the owner must confirm once before merge (finding for the owner, issue 4).
2. Private helper imports: acceptable debt, not a violation (doctor clean; `ui.helpers._load_project_or_404` has the same shape); low row, public re-export belongs to AT-582's owner.
3. Route permission: when T-204 lands add `require_permission("report.view")` to `damage_report` in `ui/routes_unified_report.py` and a test for a user without it.
4. ARCHITECTURE: the file has no per-module rows by design (MAP.md is generated and was regenerated); a prose row needs a DECISIONS entry. Not a defect.
- T-167 rebase: trivial. T-167's later commits touch only `orchestrate_gate.py`, `release.py`, `test_release_gate.py`; `git merge-tree` of the two branches is clean and the 12 tests pass on the merged tree. Merge order: T-167 first.
- Process: wall exceeded the 10-min hard checkpoint (probes and browser were mandated by the dispatch); all mandatory evidence completed. slow: secret/honesty probes + browser 12 min.

Metrics: start=2026-10-10T20:22:59Z end=2026-10-10T20:44:00Z wall_min=21 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1260 mutants=2 defects_unit=1 defects_6c=0
