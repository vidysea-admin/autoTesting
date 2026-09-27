# Verdict — at597-pin-issue-caller

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (Mode A + Mode D) + orchestrator reproduction

```
VERDICT: FAIL
SCOREBOARD: the UI pin route is sound and fully guarded; the CLI `issues pin` path fails C5 and AT-597's "human-confirmed steps" purpose
FAILURES:
- [C5 / B2, AT-597] sev: high · cli_issues.py::pin_cmd (line 101) runs no credential guard (no SecretStore, _guard_submitted_case or _refuse_unsafe_submission equivalent). `autotester issues pin demo <id> --step "fill:#password:SuperSecretRaw123"` exits 0 and writes "value":"SuperSecretRaw123" in plain text to cases.jsonl, a git-tracked file in a public repo. The UI route refuses the same input with a 400. · Fix: pin_cmd loads the project's SecretStore and runs the same guard the UI uses over every parsed step's target, value and expect before pin_issue_as_case; add a CLI test with a raw declared value → non-zero exit and nothing written. · issue: AT-597
- [AT-597] sev: high · _parse_step (cli_issues.py:83) does raw.split(":", 3), so a URL target is corrupted and still reported as success: "navigate:https://example.com/login" becomes target='https', value='//example.com/login' (orchestrator reproduced by calling _parse_step directly). The pinned "repro" can never navigate to the bug, and the CLI does not run _require_reachable_navigate_steps either. · Fix: split the action off first and parse target so an embedded "scheme://" survives (or take --target/--value/--expect per step); run the same reachable-navigate check as the UI; add tests with https:// targets and values. · issue: AT-597
CAPABILITY-COVERAGE: 8/8 rows reproduced (copy c597-1; each single-hunk mutation red on its named test; restored 16/16)
LIVE-BROWSER: qa/evidence/browser-at597-pin-issue-caller-2026-09-26-checker (visible Chromium against the real uvicorn app: pin link → form → 303 → case pinned with pinned_issue_id; the pill replaces the link; delete gives 409 and the case survives; a truly blank form gives 400 (row-0 Target is pre-filled with base_url like the case form, so it must be cleared); 1 console line = the expected 409 log, AT-596)
ISSUES-WRITTEN: AT-604 (medium: re-pinning an already-pinned issue with different steps creates a second pinned case)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: UI probes all hold: a raw secret is refused 400, a declared {{SECRET:KEY}} is stored as the placeholder, an undeclared placeholder is refused, an XSS title is escaped, path traversal in issue_id gives 404, another project's issue gives 404, and an identical double pin is refused. No CSRF guard, but no existing POST route has one either, so it is not a regression. 4c clean: every removed line has a successor, and the issues page renders the same 13 columns in order plus "Regression" at the end (base vs branch rendered side by side). Files 161/156 lines.
```

Evidence: 143 passed, 1 skipped · ruff clean · doctor clean (c597-1) · CLI probes: unknown project/issue, zero --step, malformed step and unknown action all exit 2 cleanly; the URL target and the raw secret exit 0 with wrong data.

---

# Verdict — at597-pin-issue-caller, cycle 2

**Date:** 2026-09-26 · **Cycle checked:** 2 · **Checked commit:** d26ecbf (code), 28bf391 (manifest) · **Checker:** orchestrator (checker seat), direct re-run

```
VERDICT: FAIL
SCOREBOARD: 3/4 cycle-1 findings closed (CLI credential guard, reachable-navigate guard, AT-604 on both surfaces); 1 not closed (URL parsing)
FAILURES:
- [AT-597 / C5 "the CLI never writes what the UI would refuse"] sev: high · `_STEP_SPLIT_RE = re.compile(r":(?!//)")` (cli_issues.py) still splits at a URL's PORT colon, so any URL with a port -- every local dev server -- is silently corrupted and the command reports success. Reproduced end to end (CliRunner, scratch root, project base_url http://localhost:8069, allowed_domains ["localhost"]): `pin local <id> --step navigate:http://localhost:8069/signup --step click:#go` -> exit 0, "pinned ... as regression case", stored step ('navigate', 'http://localhost', '8069/signup'). The pinned case navigates to the wrong URL forever. Same defect class as the cycle-1 FAIL, one character further along. · Do not split a URL at all: take the action off the first `:`, and for NAVIGATE use the whole remainder as the target (navigate has no value). For other actions, make URL-bearing values unambiguous (a scheme-aware tokenizer that keeps `scheme://host[:port]/...` whole, or an explicit escape). Add tests for `navigate:http://localhost:8069/signup` and `fill:#url:https://x.com:8080/a`, each with a falsification row. · issue: AT-597 (stays open)
CAPABILITY-COVERAGE: 5/5 cycle-2 rows reproduced (own copies, green before, named test red after)
LIVE-BROWSER: SKIP (deliberate, not a pass) -- the only UI change is routes_issues.py's AT-604 409, verified by row 5 via TestClient. The live check of the re-pin 409 page is owed at cycle 3 (it renders through at596's handler once that merges).
ISSUES-WRITTEN: none (AT-597 stays open with the port detail above)
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: The credential guard, the reachable check and one-pin-per-issue all hold end to end. A raw secret exits 2 with nothing on disk, an off-site navigate exits 2, and a second pin with different steps exits 2 and leaves 1 pinned case. The `(?!//)` lookahead fixes only the scheme colon, not the port colon, so the parsing half of the cycle-1 FAIL is still open. Cycle 3 is the last under the cap.
```

## Re-run evidence

- Parser probe (worktree, read-only): `navigate:http://localhost:8069/signup` -> target 'http://localhost', value '8069/signup';
  `navigate:https://app.example.com:8443/login` -> 'https://app.example.com' + '8443/login';
  `fill:#url:https://x.com:8080/a` -> value 'https://x.com', expect ['8080/a']; `navigate:https://example.com/login` -> intact.
- End-to-end CLI probe (scratch AUTOTESTER_ROOT with `.env` LOCAL_PASS=<fake>):
  - PORT: exit 0, corrupted step stored.
  - SECRET `fill:#password:<fake>`: exit 2 ("looks like it contains a real credential"), and no .jsonl under the root contains the value.
  - DUP: first pin exit 0, second (different steps) exit 2 "already pinned as case ...", pinned count 1.
  - OFFSITE `navigate:https://evil.example/x`: exit 2 "not covered by allowed domains".

## Capability rows (own copies `<scratch>/at597c2-row<k>`, each green before)

| row | edit | named test | red after |
|---|---|---|---|
| 1 | `_guard_pin_steps`: `_refuse_unsafe_submission(...)` -> `pass` | test_pin_refuses_a_raw_secret_value | `assert 0 != 0` |
| 2 | `_parse_step`: regex split -> `raw.split(":", 3)` | test_pin_preserves_a_url_scheme_in_the_navigate_target | "step 1 needs a full URL", `assert 2 == 0` |
| 3 | `_guard_pin_steps`: `_require_reachable_navigate_steps(...)` -> `pass` | test_pin_refuses_an_out_of_scope_navigate_step | `assert 0 != 0` |
| 4 | `pin_cmd`: `refuse_if_issue_already_pinned(...)` -> `pass` | test_pin_refuses_a_second_pin_of_the_same_issue_with_different_steps | `assert 0 != 0` |
| 5 | `routes_issues.pin_issue`: `refuse_if_issue_already_pinned(...)` -> `pass` | test_repinning_an_issue_with_different_steps_is_refused_409 | `assert 200 == 409` |

## Diff scope (4c)

`git diff 7e67ce4..d26ecbf --stat`: cli_issues.py, stages/issues.py, ui/routes_issues.py, tests/test_cli_issues.py,
tests/test_ui_issues.py, all named in the manifest. Removed pre-existing lines: the `store` fixture's
`return ProjectStore("demo", tmp_path)` (replaced by a fixture that also saves the Project) and two `navigate:/signup`
targets changed to absolute URLs. Both are justified: the reachable check now refuses relative targets, as the UI
already did. No assertion was weakened.

## Non-blocking note

`cli_issues.py` now imports `fastapi.HTTPException` and two underscore-private helpers from `ui.helpers`, so the CLI
depends on the UI layer. Reuse beats a copy (C5). If a later unit moves the two guards to a non-UI module, both callers
can share them without the layering inversion. Question for the maker, not a failure.

Full suite not re-run this cycle: at347's full suite held the RAM (1.2 GB free), and the reproduced FAIL stands
independently of it. Cycle 3 gets a full run.

---

# Verdict — at597-pin-issue-caller, cycle 3 (last under the cap)

**Date:** 2026-09-26 · **Cycle checked:** 3 · **Checked commit:** bae5d48 (code), 2f5ca34 (manifest) · **Checker:** orchestrator (checker seat), direct re-run

```
VERDICT: FAIL
SCOREBOARD: the cycle-2 finding (port colon) is closed for every case it named; cycle 3 introduced one regression in the same function
FAILURES:
- [AT-597 / "never a guess"; the documented `action:target[:value[:expect]]` form] sev: medium · The new NAVIGATE branch (`target, value, expect = remainder, None, ""`) swallows a navigate step's EXPECT into its URL. `pin p3 <id> --step navigate:https://x.com/signup::Welcome` exits 0 and stores target 'https://x.com/signup::Welcome' with expected []; `navigate:https://x.com/signup:Welcome` stores 'https://x.com/signup:Welcome'. At cycle 2 (ddb747d) the same input parsed correctly: target 'https://x.com/signup', value None, expect ['Welcome']. A navigate expectation is live behaviour, not an unused field: execute.py:132 settles after NAVIGATE, and E1 evaluates a step's declared expectation post-settle. The help text (cli_issues.py:192) still documents the 4-field form for every action. So the pinned case silently navigates to a wrong path and loses its check. · Parse NAVIGATE's target with the same URL-aware `_take_step_field` (the URL is taken whole, port included), then accept the optional `[:value[:expect]]` tail. Refuse a non-empty value for navigate, and keep the expect. Add tests for `navigate:<ported url>::Welcome` and `navigate:<plain url>::Welcome`, each with a falsification row. · issue: AT-597 (stays open)
CAPABILITY-COVERAGE: 6/6 cycle-3 rows reproduced via the manifest's 2 edits (own copies, 6/6 green before). Edit A (NAVIGATE -> `remainder.split(":", 1)[0]`) fails rows 1/2/5/6; edit B (drop `(?::\d+)?`) fails rows 3/4.
LIVE-BROWSER: SKIP (deliberate, not a pass) -- a parser FAIL stands without it, and RAM was 0.36 GB with at596's full suite running. The re-pin 409 page is still owed before any PASS.
ISSUES-WRITTEN: none (AT-597 stays open)
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: The port fix works for every case cycle 2 named: navigate with a port, an https port, a ported fill value, and a ported value plus expect. It holds end to end through the reachable guard. But making NAVIGATE take the whole remainder broke the navigate-with-expect form that cycle 2 handled, and the CLI still exits 0 with a corrupted target. The fix is to reuse the URL-aware field tokenizer for navigate's target.
```

## Re-run evidence

- Parser probe (worktree, read-only), cycle 3:
  - `navigate:http://localhost:8069/signup` -> target 'http://localhost:8069/signup' OK.
  - `navigate:https://app.example.com:8443/login` -> OK.
  - `fill:#url:https://x.com:8080/a` -> value 'https://x.com:8080/a' OK.
  - `fill:#url:https://x.com:8080/a:Saved` -> value OK, expect ['Saved'] OK.
  - `navigate:https://x.com/signup:Welcome` -> target 'https://x.com/signup:Welcome' **(corrupted)**.
  - `click:#go::Welcome back` -> expect OK.
- End-to-end CLI probe (scratch AUTOTESTER_ROOT, project allowed_domains ['x.com']):
  - `navigate:https://x.com/signup::Welcome` -> exit 0; stored ('navigate', 'https://x.com/signup::Welcome', None, []).
  - `navigate:https://x.com/signup:Welcome` -> exit 0; stored ('navigate', 'https://x.com/signup:Welcome', None, []).
- Cycle-2 comparison (`git show ddb747d:src/autotester/cli_issues.py`, loaded directly):
  - `navigate:https://x.com/signup::Welcome` -> target 'https://x.com/signup', value None, expect ['Welcome'].
- Diff scope (4c): `git diff ddb747d..bae5d48 --stat` touches cli_issues.py (+67/-15) and tests/test_cli_issues.py (+77/-1). The removed source lines are the cycle-2 `_STEP_SPLIT_RE` block and parse lines, which this fix replaces as intended. The one removed test line is the `from autotester.cli_issues import app` import, now widened. `pin_cmd`'s tail moved into `_finish_pin` unchanged, to stay under the 50-line cap.
- Full suite: not re-run for this cycle (RAM 0.36 GB, at596's full suite in flight). The reproduced FAIL stands without it.

## Non-blocking notes (not failures)

- A bracketed IPv6 host is still split: `fill:#u:http://[::1]:8080/a` -> value 'http://['. `_URL_FIELD_RE`'s host class `[^/:]*` cannot hold `[::1]`. It's a rare input for a repro step, so include it in the fix only if it's cheap.
- A non-URL value containing `:` still splits, e.g. `fill:#t:10:30 AM` -> value '10', expect ['30 AM']. That is the documented pre-existing behaviour. An escape would make such values expressible.
- The CLI importing the private `ui.helpers` guards is deferred by the maker's manifest (noted at cycle 2).

**Cycle cap:** this is fix cycle 3 of 3. What happens next (a gated narrow cycle 4, or a HUMAN_GATE) is the maker's protocol decision, as with at347.

---

# Verdict — at597-pin-issue-caller, cycle 4 (gated extra cycle, qa/gates/at597-cycle4.md answer A)

**Date:** 2026-09-26 · **Cycle checked:** 4 · **Checked commit:** 5cdabc1 (code), 71146ac (manifest) · **Checker:** /checker session (claude-opus), own browser

```
VERDICT: FAIL
SCOREBOARD: the cycle-3 navigate-expect regression is closed, and every parser, CLI and UI behaviour holds live; one verify command is red
FAILURES:
- [verify: `uv run pytest`] sev: medium · The full suite fails deterministically in the unit's own tree: `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` -> "advice sites changed. gone: [] new: [('cli_issues.py', 'issues list')]" (1 failed, 1793 passed; reproduced alone: 1 failed, 27 passed). The new advice at cli_issues.py:223 ("try `autotester issues list {project}`"), introduced in cycle 1 (0323329), was never registered in the AT-210 guard's EXPECTED_SITES. Cycles 1-3 never ran the full suite, so it went unseen. The sibling test that the advice resolves to a real command passes, so the advice itself is fine. · Add `("cli_issues.py", "issues list")` to EXPECTED_SITES in tests/test_cli_advice_resolves.py, plus any count assertion that goes with it, as at575 did in 6b66de5. List the test file under "What changed". · issue: AT-597 (stays open)
CAPABILITY-COVERAGE: 2/2 cycle-4 edits reproduced (own copies, 3/3 green before each). Edit A (reinstate the cycle-3 NAVIGATE bypass) turns all 3 new tests red with the named assertions. Edit B (disable only the value guard) turns only `test_parse_step_refuses_a_navigate_with_a_value_field` red ("DID NOT RAISE").
LIVE-BROWSER: qa/evidence/browser-at597-pin-issue-caller-2026-09-26-checker-c4/ (on master) -- PASS on every step
ISSUES-WRITTEN: none
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: The cycle-4 code is right. Navigate keeps its ported target and its `::expect`, refuses a value, and the live pin/409/400 behaviour holds in a real browser and through the CLI. The FAIL is the unit's own unregistered advice site tripping an existing guard. It is a one-line test-registry fix, but a red suite cannot PASS. Whether it gets another cycle is the maker's gate call, since this was the gated extra cycle.
```

## What I re-ran

- `uv run pytest` (full, no -q): **1 failed, 1793 passed, 5 skipped, 32 xfailed** in 669 s, exit 1 (failure above). The known flake AT-518 did not fire.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 violations, both `ledger-row-lost` for AT-604, because the branch predates master's row; they clear on merge.

## Parser probe (worktree, read-only)

| input | target | value | expect |
|---|---|---|---|
| `navigate:https://x.com/signup::Welcome` | https://x.com/signup | None | ['Welcome'] |
| `navigate:http://localhost:8069/signup::Welcome` | http://localhost:8069/signup | None | ['Welcome'] |
| `navigate:https://x.com/signup` / `...:` / `...::` | https://x.com/signup | None | [] |
| `navigate:https://x.com/signup:v:W` | ValueError "navigate has no value field" | | |
| `fill:#url:https://x.com:8080/a:Saved` | #url | https://x.com:8080/a | ['Saved'] |
| `click:#go::Welcome back` | #go | None | ['Welcome back'] |

Non-blocking, pre-existing for every action (not charged):
- `navigate:<url>::a:b` keeps expect 'a' and silently drops ':b' (the literal colon in expect, the known limit).
- A bare `navigate:` parses to an empty target.

## Diff scope (4c)

`1133e8b..5cdabc1` touches cli_issues.py (+25/-13) and tests/test_cli_issues.py (+33). The only removed code is the cycle-3 NAVIGATE bypass (`target, value, expect = remainder, None, ""` and its else-branch), which the fix replaces. No test was removed.

## Mode D (real visible Chromium, worktree on 127.0.0.1:8094, scratch AUTOTESTER_ROOT, project `demo`)

The manifest's recipe steps 3-7, driven by my own Playwright script (report.json + 6 screenshots):

1. The issues page shows 1 "Pin as regression case" link for the un-pinned issue.
2. Pin form with navigate `https://demo.test/signup` and expected "Welcome" -> 303 to `/projects/demo/cases`, showing a "pinned regression — ..." title. Stored step: `('navigate','https://demo.test/signup',None,['Welcome'])`.
3. Issues page afterwards: the pin link is gone and a "pinned" pill shows.
4. Delete on the pinned case -> **409** "case ... is pinned ... and cannot be pruned"; the case is still listed.
5. Re-pin with identical steps -> **400** (duplicate case).
6. Re-pin with different steps (POST) -> **409** "issue ... is already pinned as case ...".

Error bodies render as raw JSON because this branch forked before at596's themed handler merged (55deae4). This is not charged here; it resolves on merge.

Console: exactly 2 Chromium network lines (the 409 and the 400 documents); no page-script errors.

CLI end to end (`.venv/Scripts/autotester.exe issues pin demo <issue_b> ...`), in cli-and-409-probes.txt:
- `navigate:https://demo.test:443/signup::Welcome` + `click:#yes::Saved` -> exit 0, both stored with their expects.
- Re-pin -> exit 2 "already pinned".
- `navigate:<url>:v:X` -> exit 2 "navigate has no value field".

---

# Verdict — at597-pin-issue-caller, cycle 5 (gated, qa/gates/at597-cycle5.md answer A)

**Date:** 2026-09-26 · **Cycle checked:** 5 · **Checked commit:** cbaf486 (code), c83dc54 (manifest) · **Checker:** /checker session (claude-opus)

```
VERDICT: PASS
SCOREBOARD: the cycle-4 FAIL (unregistered advice site) is closed; every cycle-4 behaviour stands (src unchanged since 5cdabc1)
FAILURES: none
CAPABILITY-COVERAGE: 1/1. The registry row: without the line, the guard fails with "new: [('cli_issues.py', 'issues list')]" (observed at cycle 4 on 5cdabc1, 27 passed / 1 failed); with it, 28 passed. Cycle-4 rows 2/2 stand unchanged.
LIVE-BROWSER: qa/evidence/browser-at597-pin-issue-caller-2026-09-26-checker-c4/ (on master, a9eb1f1). Not re-run: `git diff 2e57296..cbaf486` touches only tests/test_cli_advice_resolves.py, with no src change since that run.
ISSUES-WRITTEN: none
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: Cycle 5 adds exactly `("cli_issues.py", "issues list")` to EXPECTED_SITES and moves EXPECTED_SITE_COUNT from 18 to 19, the at575 pattern. The advice's resolve test already passed at cycle 4, so the hint points at a real command. The full suite is now green. With cycle 4's parser, CLI and live-browser evidence, AT-597 and AT-604 are closed on merge.
```

## What I re-ran

- `tests/test_cli_advice_resolves.py`: 28 passed.
- `uv run pytest` (full, no -q): **1793 passed, 6 skipped, 32 xfailed, 0 failed** in 724 s, exit 0.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 violations, both `ledger-row-lost` for AT-604. The AT-604 row was filed on master in b7e79be after this branch forked (`git merge-base --is-ancestor b7e79be HEAD` -> not an ancestor), so they clear on merge. This is the same pattern as cycles 1-4, not a unit defect.

## Diff scope (4c)

`2e57296..cbaf486` changes tests/test_cli_advice_resolves.py only (+2/-1): one tuple added, and the count constant changed from 18 to 19. Nothing removed.
