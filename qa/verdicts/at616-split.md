# Verdict: at616-split

Verdict: PASS
Status: PASS
Cycle checked: 0
Reviewed SHA: 9aaf1fe5 (detached worktree .worktrees/chk616; fix commit 023ffd5d)
Tier: S (regression-guard falsification only; no product code changed)
Checker: second checker, fresh context (the AT-616 request: "a second checker attempts the same red/green split on tests/test_report_export_secrets.py")

## Method
Five copies of `src tests scripts pyproject.toml` from `git archive 9aaf1fe5`, all OUTSIDE any worktree
(scratchpad `at616/{green,r609x,r609h,r609f,r608}`). Each ran with the repo `.venv` python and
`PYTHONPATH=<copy>/src;<copy>/scripts`, cwd = the copy, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`.
Each run first printed `autotester.__file__` and it resolved to the copy's own `src` (so the revert was live).
Only one fix site was reverted per variant; all four reverts are one-line removals of the `redactor.scrub(...)` call.
Command: `python -m pytest tests/test_report_export_secrets.py tests/test_ui_crawl_approval.py -rf`.

## Red/green split
| Variant | Hunk reverted (file:line at 9aaf1fe5) | Result | Node id that went red | Assertion |
|---|---|---|---|---|
| green (nothing reverted) | - | 15 passed | - | - |
| r609x | AT-609 Excel `case_title` scrub, `stages/report_export.py:136` | 1 failed, 14 passed | `tests/test_report_export_secrets.py::test_export_excel_redacts_a_raw_secret_value_in_the_case_title` | `test_report_export_secrets.py:183` raw value present in the "Case" cell |
| r609h | AT-609 HTML `<h2>` title scrub, `report_export.py:195` | 1 failed, 14 passed | `tests/test_report_export_secrets.py::test_export_html_redacts_a_raw_secret_value_in_the_case_title_and_evidence_label` | `:195` `SECRET_VALUE not in html` |
| r609f | AT-609 `<figcaption>` label scrub, `report_export.py:201` | 1 failed, 14 passed | same HTML node id | `:195` `SECRET_VALUE not in html` |
| r608 | AT-608 coverage-card scrub, `ui/routes_crawls.py:105` | 1 failed, 14 passed | `tests/test_ui_crawl_approval.py::test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error` | `test_ui_crawl_approval.py:237` `'hunter2' not in page` |

Restoring each hunk (the green variant) gives 15 passed. Every hunk has a guard that goes red on its own
revert and green when restored. r609h and r609f share one test and one assertion, but each revert alone
is caught, so neither site is unguarded.

## Why AT-616 could not reproduce at the real path (probable, not proven)
`D:/autoTesting/.venv/Lib/site-packages/autotester.pth` contains `D:\autoTesting\src`. Run from the
cwd `.worktrees/chk616`, `autotester.__file__` is `D:\autoTesting\src\autotester\__init__.py`, i.e. the MAIN
checkout, not the tree being tested. A revert applied in any other tree is invisible to pytest unless
`PYTHONPATH` puts that tree's `src` first. That matches the sweep's "standalone copy went red, real path stayed
green" observation. This verdict used the PYTHONPATH form, and confirmed the path per run.
A hardening follow-up (tests asserting `autotester.__file__` is under the repo being tested) is worth a
low row; not filed here as it was not required by the AT-616 request.

## Ledger moves
- AT-608: fixed -> verified (split holds).
- AT-609: fixed -> verified (all three scrub sites guarded).
- AT-616: open -> fixed, citing this verdict.

Metrics: start=2026-10-18T00:00Z end=2026-10-18T00:25Z wall_min=25 agent_min=unavailable blocked_min=0 suite_runs=5 repeat_runs=0 mutations=4 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=1500 mutants=4 defects_unit=0 defects_6c=0
