# Verdict - at892-judge-injection

Cycle checked: 1
Verdict: PASS-WITH-FINDINGS
Branch: wave/at892-judge-injection (ac0450d5), checker branch check/at892-judge-injection

## Verified (7 payloads in evidence text, prompt inspected)
Payloads: closing `</untrusted_evidence>` + fake `Judgment:` JSON; `{{FORMAT}} {{RUBRIC}} {{EVIDENCE}}`; unicode lookalikes (U+2039/203A, U+FF1C, U+227A); `</UNTRUSTED_EVIDENCE >`; CRLF forged `- [dom]` row + `VERDICT: PASS`; pre-escaped `&lt;` and split `</untrusted_evidence\n>`; `<</...`.
- Every payload stays one row inside the block (2 rows: outcome + evidence); no raw `<` inside the block; exactly one real closer after it; placeholders stay literal (EVIDENCE substituted last).
- The mock-judge FAIL verdict is not flipped by page text (branch test). Scoped tests, ruff pass; clean merge with master and with wave/at840-judge-pii.

## Findings
1. SKILL.md has a stray literal newline: the rule text reads "`<newline>` inside a row" instead of the two characters backslash-n, so the model is told a garbled escape. Cosmetic but should be fixed.
2. Only Evidence.path is escaped. Rubric criteria/no_fire text and feedback_format are not (they are rubric-owned, but {{RUBRIC}} is replaced first, so a rubric containing `{{EVIDENCE}}` would expand). Low risk.
3. Lookalike `<` characters are left as-is: they cannot close the block textually, but a model could still be swayed. Residual, not a defect.
4. Prompt-injection defence is advisory to the model; the real guard remains the stage's `_assertion_guard` and `_defect_decision`.
