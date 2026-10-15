# Verdict - at840-judge-pii

Cycle checked: 1
Verdict: FAIL (doctor design-rule violation introduced by this branch; fix cycle needed)
Branch: wave/at840-judge-pii (795d325d), checker branch check/at840-judge-pii

## Verified
- mask_pii runs after `_withheld` (Redactor.assert_clean + guard_prompt) and before `judge.judge`; a secret in evidence returns BLOCKED with 0 provider calls.
- Recording-mock probe: emails (incl. plus-tags), +91 / dashed / bracketed / bare 10-digit and fullwidth-digit phones all become `<email>` / `<phone>` in the prompt.
- stages/ai_judge.py has no second path: it calls grade() with a private _ComputedJudge (no model call). Scoped tests (grade, redact, ai_capture, ai_judge) pass; ruff clean.
- Merges cleanly with master and with wave/at892-judge-injection (git merge-tree, no conflicts).

## Findings (not fixed by this branch)
1. Name-like values reach the provider: "Ravi Kumar" and `first_name: Ravi Kumar` in an evidence label are unmasked. mask_name_value exists but is not applied in grade.
2. Obfuscated emails (`ravi [at] school.edu`, `ravi%40x.com`, fullwidth `＠`, spaced) pass through.
3. Screenshots are sent unmasked. The manifest documents this as a HUMAN_GATE, but AT-840 in qa/issues.jsonl is still `open` (correct); the branch must not close it.
4. Other judge callers (ux_advisory, video_review, reconcile partly) are separate paths; ux_advisory and video_review have no mask_pii. Out of scope, but worth an issue.

## Blocker
5. `uv run autotester doctor` reports `function-too-long: stages/grade.py:179 grade is 51 lines > 50`. The manifest calls this "likely stale MAP.md"; it is not, the +4 comment/mask lines pushed grade() over the limit (master and at892 doctor are clean). Fix: move the mask into a helper or trim comments. Tests 599 passed, ruff clean.

---
# Cycle 2 (head 1eebac77)

Cycle checked: 2
Verdict: PASS (image PII remains open under AT-840)

- Probes: `[at]/[dot]`, `%40`, `%2540`, fullwidth at-sign, spoken "at/dot", `first_name:`, `name=`, `Student Name:` all masked; `course_name:` left alone; free-text "Ravi Kumar" not masked (by design). Residual: `%252540` (triple-encoded) not masked, low.
- Every Provider call carrying target content is now masked: grade, ux_advisory, video_review, expand; reconcile already used mask_pii_obj. ledger/relitigation takes no target content.
- Advisory: redact_pii_forms imports private `_View` from redact_escaped. Doctor does not forbid it (clean); make it public (`View`).
- Duplication: it reuses `_View` for decoding and only adds spellings/labelled-name regexes on top of redact.mask_pii; one concept, no duplicate decoder.
- Tests 848 passed (grade/redact/ai_*/pii/ux/video/expand), ruff clean, doctor clean (grade-length violation gone). merge-tree vs local master clean; branch is rebased on master.
- Image PII: documented gap, AT-840 stays open for images only.
