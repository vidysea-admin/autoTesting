# expand_case_v1 — turn a happy-path flow into one taxonomy-class case

You are given the steps of a working, happy-path flow. Produce a NEW set of steps that tests the
**{{CASE_CLASS}}** scenario: {{CLASS_DESCRIPTION}}.

Rules:
- Keep any step unrelated to this scenario unchanged (same action, target, value).
- Modify only what the scenario actually requires — a different value, an extra step, a
  different action on an existing target. Do not invent unrelated steps.
- If this scenario genuinely does not apply to this flow, return an EMPTY `steps` list and say
  why in `rationale` — do not force a case that doesn't make sense here.
- Never write a real-looking credential. If the scenario needs a wrong password or similar,
  invent an obviously fake one (e.g. `"wrong-test-password-123"`) — never anything that could be
  mistaken for a real secret. A field that legitimately needs the real credential keeps its
  original `{{SECRET:KEY}}` placeholder unchanged.

## Original flow: {{FLOW_NAME}}

{{ORIGINAL_STEPS}}

Answer with a JSON object matching the schema you were given (`steps[]`, `rationale`).
