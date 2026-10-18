# Checkpoint B - t209-leak-severity (cycle 0 + cycle 1)

Interpreter: worktree .venv python (-I), TMP/TEMP=D:/autoTesting/.work/tmp. pyproject/uv.lock unchanged since base.

## Cycle 0 (code 7746a2b8, base 722bf3df)
| check | command / scope | result |
|---|---|---|
| verify cmd 1 | pytest 5 named files (49 collected) | 49 passed |
| verify cmd 2 | git diff --name-only 722bf3df..7746a2b8 | no forbidden file |
| ruff | ruff check src tests scripts | clean |
| render equivalence | render_html(report) base vs candidate | identical sha f77b37a13b9ec138 |
| MP7/MP8/MP9/MP10 falsification | run_falsify.py, copies D:/chk-scratch-t209b/r2/* | green before, red after on the named node |
| leak probe | probe_leak.py, probe_ids.py | F1 reproduced (opaque ids kept in url_template) |

## Cycle 1 (code b7370722, manifest 49be6484, previous checked state 36a87037)
Changed inputs since 36a87037 (git diff --stat 36a87037..HEAD -- src tests): schema/leak_evidence.py, schema/multi_role_finding.py, stages/leak_evidence.py, tests/test_leak_evidence.py, tests/test_leak_url_ids.py (new). Unchanged: finding_priority.py, report_banner.py, unified_report_render.py, core/image_privacy.py (MP7, MP8 and the render equivalence keep their cycle-0 evidence by identity).

| check | command / scope | result |
|---|---|---|
| verify cmd 1 | pytest tests/test_finding_priority.py tests/test_report_banner.py tests/test_leak_evidence.py tests/test_leak_url_ids.py tests/test_leak_repro_replay.py tests/test_unified_report.py (90 collected) at HEAD 49be6484 | 90 passed (57.7 s) |
| verify cmd 2 | git diff --name-only 722bf3df..b7370722 \| grep unified_report.py\|multi_role_enums\|enums.py\|image_privacy | no match |
| ruff | ruff check src tests scripts | All checks passed |
| id probe | qa/evidence/t209-leak-severity/b/probe_ids_c1.py (17 formats x 1000; 40 written findings each) | 0 kept in url_template, 0 accepted by validate_url_template, 0 raw ids in written files |
| leak probe | probe_leak.py (fake name/email/phone/secret/master key) | no needle in run-dir files or log; secret in URL path now {id} |
| MP9 falsification | run_falsify_c1.py, copy D:/chk-scratch-t209b/c1/mp9 (predicate reverted to cycle-0 regex) | green 2 passed -> red 2 failed on the id assertion and the written-file assertion |
| MP10 falsification | copy c1/mp10 (write_finding drops last step) | green -> red `assert 0 == 3` |
| steps probe | D:/chk-scratch-t209b/c1/probe_steps.py | goto step with a raw id and a fill value persist (named residual, low) |

Attribution: coordinator B (this agent). Nothing from coordinator A read or counted.
