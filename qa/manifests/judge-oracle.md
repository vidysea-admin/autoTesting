# Manifest - judge-oracle

Status: ready-for-check
Fix cycle: 0
Issues: AT-773, AT-892
Branch: wave/judge-oracle

## AT-773
Already fixed on master by wave at773-judge-rule: D-074(b) amended D-032, and `grade._assertion_guard` downgrades a judge PASS to INCONCLUSIVE for ASSERTION_FAILED or unmet-assert evidence (tests/test_grade_assertion_rule.py). No code change in this wave; the issue row only needs closing by the checker.

## AT-892
`stages/ai_judge.py::_one_line` escapes the backslash and every non-printable character (all line breaks) in each evidence row text, so target text stays on one row. Tests: tests/test_ai_evidence_escape.py.
