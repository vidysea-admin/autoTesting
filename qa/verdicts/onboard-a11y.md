# Verdict - onboard-a11y
Cycle checked: 1
Verdict: PASS
Head checked: fad39da7

- AT-994: every /onboard input/select/textarea has `<label for>` (fixed fields) or `aria-label` (repeater rows). The JS clone path is `insertAdjacentHTML(firstElementChild.outerHTML)`, so cloned rows copy the first row's aria-labels. Verified by reading the code; the test inspects static markup, not the cloned DOM (minor gap, not a defect; identical labels on repeated rows are acceptable).
- AT-995: auth pages carry `<link rel='icon' href='data:,'>`; test asserts no `/favicon.ico` in the page AND anonymous `/favicon.ico` is still 401, so AU16's closed set is not widened.
- Ran: test_ui_onboard_a11y, test_ui_auth_escalation, test_ui_auth_policy_table, test_ui, test_ui_auth_surface -> 58 passed; ruff clean; doctor clean.
- AU16 ruling: inline icon stands; a 204 `/favicon.ico` is NOT accepted into the public set. Pure clarification folded into qa/contracts/auth.md AU16 (no widening).
