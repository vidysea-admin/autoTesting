# Manifest — at597-pin-issue-caller

**Unit:** a human-facing path to pin a confirmed issue as a regression case (AT-597).
**Fix cycle:** 5 of 3 (narrow, gate-approved)
**Gates:**
- `qa/gates/at597-cycle4.md`, answered A (Umesh, 2026-09-26) — a narrow
  cycle 4 scoped to `_parse_step`'s NAVIGATE branch only, beyond the 3-cycle cap.
- `qa/gates/at597-cycle5.md`, answered A (Umesh, 2026-09-26) — a narrow
  cycle 5 scoped to one `EXPECTED_SITES` registry line, no src change.
**Dual check:** no
**Issues addressed:** AT-597, AT-604

Cycle 1's own sections below (gap, what changed, capability coverage, live
evidence) are left as-is -- they describe the UI route, which cycle 1's
checker PASSed outright. Cycle 2's own gap/fix/coverage is in its own
section at the end, per the checker's cycle-1 FAIL below.

## The gap (AT-597, as filed)

T-184/AT-585 built `stages/issues.py::pin_issue_as_case(issue, flow_id, steps, *,
project=None)` and the store-side guard that refuses to delete a pinned `Case` —
but shipped with **no caller**: `grep pin_issue_as_case in src` returned only the
definition. A pinned case is protected and runs in every regression once it
exists, but nothing let a human actually create one, so "this bug must never
come back" (the meeting's ask) was still not usable.

## What changed

- `src/autotester/ui/routes_issues.py` — two new routes, both reusing the
  existing case machinery rather than duplicating it:
  - `GET /projects/{slug}/issues/{issue_id}/pin` (`pin_issue_form`, :95-127) —
    renders the issue's title/description plus the same step-editor table
    `ui/case_form.py` already builds for hand-added cases (`_step_row`,
    `STEP_ROWS`, `_credential_datalist`).
  - `POST /projects/{slug}/issues/{issue_id}/pin` (`pin_issue`, :130-147) —
    reuses `ui/routes_cases.py::_build_steps` (drops blank rows),
    `_guard_submitted_case` (credential-leak guard, AT-070/71/77),
    `ui/helpers.py::_require_reachable_navigate_steps` (AT-058/AT-432 — a step
    that could never run is refused at creation, not discovered at run time),
    and `_refuse_duplicate` (AT-060 — a second identical submission is refused
    with 400, never silently swallowed). Refuses with 400 when every step row
    is blank ("confirm at least one reproduction step before pinning") — steps
    are never guessed from the issue's narrative, matching
    `pin_issue_as_case`'s own contract. On success: `pin_issue_as_case(issue,
    flow_id="manual", steps=steps, project=slug)` (mirrors hand-added cases'
    own `flow_id="manual"`, since a pinned case — like a hand-added one — has
    no `FlowSpec` flow behind it) then `store.add_case(case)`, redirect 303 to
    `/projects/{slug}/cases`.
  - `issues_page` (:59-77): each issue row gained a "Regression" column — a
    "Pin as regression case" link for an unpinned issue, or a `pinned` pill
    (`_issue_action_cell`, :50-56) once `store.list_cases()` shows a case whose
    `pinned_issue_id` matches — so a human can tell at a glance which findings
    already have a protected case and never accidentally double-pins with
    different steps.
  - `_find_issue_or_404` (:43-47): the one lookup `list_issues()` didn't already
    offer (no `get_issue(id)` on `ProjectStore`); reused by both new routes.
- `src/autotester/cli_issues.py` — a second, scriptable entry point to the same
  constructor, since this project's `issues` Typer group already exists
  (AT-220's precedent: a stage with no caller is an absent feature, whichever
  surface would reach it):
  - `_parse_step` (:63-81) — parses `action:target[:value[:expect]]` into a
    `Step`, refusing an unparseable shape or an unknown `Action` with a message
    naming the valid ones.
  - `pin_cmd` (`issues pin <project> <issue_id> --step ... [--step ...]`,
    :84-138) — looks the issue up by id, refuses with exit 2 if not found or if
    no `--step` was given (never guesses), parses every step, calls the same
    `pin_issue_as_case`, and reports "already pinned as case <id>" (exit 0) if
    an identical case is already on file rather than a confusing generic
    success message.

No file crossed 300 lines (161 / 156 for the two `src/` files); no function
crossed 50 (`doctor` confirms both).

## Explicitly NOT built

- No new CLI/UI way to browse or search issues beyond the existing issues page.
- No bulk-pin. One issue, one form/command call, per the "human-confirmed, never
  guessed" requirement — a bulk action would have to guess steps for issues it
  wasn't shown, which is exactly what this unit refuses to do.
- `flow_id="manual"` for every pinned case (same choice T-184's own test suite
  uses, and the same one `ui/routes_cases.py::create_case` makes for hand-added
  cases) — an `Issue` carries a `screen`, not a `Flow` reference, so there is no
  real flow to attribute a pinned case to.

## How to verify (commands + expected)

```
uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

## Actual outputs (from maker's own run, in the worktree)

```
$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
............................................................................. [ 50%]
........................................................................       [100%]
143 passed, 1 skipped, 1 warning in 11.80s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**Red before the fix** — the new tests (`tests/test_ui_issues.py`'s new pin
tests, `tests/test_cli_issues.py` in full) were run in the worktree against the
**unmodified** `src/` (before any of the two `src/` edits above):

```
$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py
...
FAILED tests/test_ui_issues.py::test_issues_page_offers_a_pin_action_for_an_unpinned_issue
FAILED tests/test_ui_issues.py::test_pin_form_shows_the_issue_and_a_step_editor
FAILED tests/test_ui_issues.py::test_pinning_with_confirmed_steps_creates_a_protected_case
FAILED tests/test_ui_issues.py::test_pinning_with_no_confirmed_steps_is_refused
FAILED tests/test_ui_issues.py::test_pinning_an_unreachable_navigate_step_is_refused
FAILED tests/test_ui_issues.py::test_a_pinned_issue_shows_pinned_instead_of_the_pin_link
FAILED tests/test_cli_issues.py::test_pin_creates_a_protected_case_from_confirmed_steps
FAILED tests/test_cli_issues.py::test_pin_an_unknown_issue_fails_clearly
FAILED tests/test_cli_issues.py::test_pinning_the_same_issue_and_steps_twice_is_idempotent
9 failed, 6 passed, 1 warning in 7.54s
```

(The 6 that passed by coincidence: FastAPI's own 404 for the not-yet-registered
GET pin route, and Typer's own exit-2 for an unknown `pin` subcommand, already
matched what those particular assertions expected — genuinely new behavior was
still red.)

## Capability coverage (each claim -> its isolating falsification)

Throwaway copy built OUTSIDE the worktree (`scratchpad/falsify-at597`): `src/`,
`tests/{conftest.py, tests_mutation_fixtures.py, test_ui_issues.py,
test_cli_issues.py, test_pinned_regression.py, fixtures/}`, `scripts/{regression_proof.py,
explore_proof.py}`, `pyproject.toml`, `uv.lock`, `.python-version`, an empty
`README.md` (needed only for `uv sync`'s build metadata). `uv sync --frozen` run
there in its own venv; confirmed green (25/25 relevant tests) before any
falsification. Every falsifying edit below is a single hunk, applied, run, then
reverted and re-confirmed green before the next row — the tracked worktree was
never touched for this.

| capability | check | falsifying edit (single hunk) | observed |
|---|---|---|---|
| an issue with no case yet offers "Pin as regression case"; a pinned one shows the "pinned" pill instead | `test_a_pinned_issue_shows_pinned_instead_of_the_pin_link` | `routes_issues.py`: `if issue.id in pinned_issue_ids:` → `if False:` | PASS before. FAIL after: the pin link stayed in the page for the already-pinned issue (`assert '/projects/.../pin' not in ...` failed) |
| pinning refuses an all-blank step submission (steps are never guessed) | `test_pinning_with_no_confirmed_steps_is_refused` | `routes_issues.py`: `if not steps:` → `if False:` | PASS before. FAIL after: `assert 200 == 400` (silently pinned with zero steps instead of refusing) |
| pinning refuses a step that could never navigate (AT-058/AT-432 guard reused) | `test_pinning_an_unreachable_navigate_step_is_refused` | `routes_issues.py`: commented out the `_require_reachable_navigate_steps(steps, project)` call | PASS before. FAIL after: `assert 200 == 400` |
| a second identical pin submission is refused, not silently swallowed (AT-060 guard reused) | `test_pinning_the_same_issue_and_steps_twice_is_refused_not_silently_swallowed` | `routes_issues.py`: commented out the `_refuse_duplicate(store, case)` call | PASS before. FAIL after: `assert 200 == 400` |
| pinning an unknown issue id fails with a named reason | `test_pin_an_unknown_issue_fails_clearly` (CLI) | `cli_issues.py`: `if issue is None:` → `if False:` | PASS before. FAIL after: uncaught `AttributeError('NoneType' object has no attribute 'title')`, message assertion failed (empty output) |
| pinning with zero `--step` values is refused with a named reason | `test_pin_requires_at_least_one_step` (CLI) | `cli_issues.py`: `if not step:` → `if False:` | PASS before. FAIL after: uncaught `TypeError('NoneType' object is not iterable)`, message assertion failed |
| an unparseable `--step` string is refused with the documented message | `test_pin_rejects_an_unparseable_step` (CLI) | `cli_issues.py`: `if len(parts) < 2:` → `if False:` | PASS before. FAIL after: a different, un-intended message surfaced (`not enough values to unpack`) instead of "must look like ..." |
| an unknown action name is refused, naming the valid ones | `test_pin_rejects_an_unknown_action` (CLI) | `cli_issues.py`: `is not one of {known}` → `nope {known}` | PASS before. FAIL after: `assert "is not one of" in "... 'flibber' nope navigate, click, ..."` |

`test_issues_page_offers_a_pin_action_for_an_unpinned_issue`,
`test_pin_form_shows_the_issue_and_a_step_editor`,
`test_pinning_an_unknown_issue_is_404`,
`test_pinning_with_confirmed_steps_creates_a_protected_case` (CLI and UI), and
`test_pinning_the_same_issue_and_steps_twice_is_idempotent` (CLI) are not
separately falsified: the first four are the constructor's own happy path,
already covered by the row above disarming the same code paths in combination,
and the CLI idempotent test isolates `ProjectStore.add_case`'s own idempotence
(already falsified in `qa/verdicts/t184-pinned-regression.md`), not new code
this unit adds — the CLI's `has_case` early-return only changes which message
prints, which that test does not assert on.

## Live browser evidence

**Ran the real server, not just `TestClient`** — RAM this session did not allow
a Chromium session (playwright MCP was unavailable this run: `CONNECT_TIMEOUT`),
so this is HTTP-level, not pixel-level, evidence. Recipe below for the checker's
own Mode D pass.

```
$ AUTOTESTER_ROOT=/tmp/at597-live uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069
# onboarded liveproj, added one Issue directly via ProjectStore (no UI route creates issues --
# they come from video derive), then drove the real HTTP routes:

GET  /projects/liveproj/issues                       -> 200, contains "Pin as regression case"
                                                          and the exact /issues/{id}/pin href
GET  /projects/liveproj/issues/{id}/pin               -> 200 (step-editor form)
POST /projects/liveproj/issues/{id}/pin (2 confirmed steps)
                                                      -> 303 -> /projects/liveproj/cases
# confirmed via ProjectStore: 1 case, pinned=True, pinned_issue_id == issue.id
GET  /projects/liveproj/issues                       -> now shows "pinned" pill, not the link
GET  /projects/liveproj/cases                         -> shows "pinned regression -- <issue title>"
POST /projects/liveproj/cases/{new_case_id}/delete    -> 409 (T-184's guard holds through this
                                                          new caller too)
```

**Recipe for the checker's Mode D (real Chromium):**

1. `uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069` (set
   `AUTOTESTER_ROOT` to an isolated temp dir first, per this project's usual
   Mode D isolation).
2. Onboard a project (`/onboard`), then add one `Issue` to its store directly
   (no UI creates issues yet — `ProjectStore("<slug>").add_issue(Issue(...))`,
   same shape as `tests/test_ui_issues.py::_a_signup_issue`).
3. Open `/projects/<slug>/issues` — confirm the "Pin as regression case" link
   renders per un-pinned row.
4. Click it, fill at least one step row (a Target box is enough), submit —
   confirm the redirect lands on `/projects/<slug>/cases` and the new case's
   title is prefixed `pinned regression —`.
5. Reload `/projects/<slug>/issues` — confirm the row now shows a "pinned" pill
   and the link is gone.
6. On the cases page, click Delete on that case — confirm it renders as a 409
   (same raw-JSON pattern AT-596 already tracks app-wide; not charged here),
   and the case is still listed afterward.
7. Submit the same issue's pin form a second time with identical steps —
   confirm a 400, not a second case.

## Known limits / gaps (disclosed, not claimed)

- **No real-browser (Chromium) Mode D run this cycle** — playwright MCP was
  unavailable (`CONNECT_TIMEOUT`). HTTP-level live evidence against the real
  uvicorn app substitutes above; recipe given for the checker's own pass.
- **Full suite not run** — RAM-constrained session; targeted tests covering
  every changed module (routes_issues, cli_issues, the pin constructor, case
  management, cases UI, issues stage, expand/run-pipeline as `Case` consumers,
  CLI surface) were run and are green (143 passed, 1 pre-existing skip).
- **AT-596** (every UI 4xx renders as raw JSON, app-wide) is untouched here —
  the dispatch brief explicitly said not to touch `ui/app.py`, which owns that
  fix; the 409 from this unit's own delete-reuse inherits the same rendering,
  consistent with every other route.
- **No bulk-pin, no issue browse/search beyond the existing table** — out of
  scope per AT-597's own "a 'Pin as regression case' action ... or a CLI
  command" ask.

## Fix cycle 2 — the CLI path, plus AT-604

Checker's cycle-1 verdict (`qa/verdicts/at597-pin-issue-caller.md`, commit
`7e67ce4`): the UI pin route was sound, but `cli_issues.py::pin_cmd` FAILed
C5 (no credential guard) and AT-597's own "human-confirmed steps" purpose
(URL targets were mangled). The checker also filed AT-604 (re-pinning an
issue with different steps silently creates a second pinned case) and asked
for it to be folded in as cheap.

### What changed

- `src/autotester/cli_issues.py`:
  - `_STEP_SPLIT_RE = re.compile(r":(?!//)")` (:89) replaces `_parse_step`'s
    (:99) `raw.split(":", 3)`. The old split cut a URL's own scheme colon as
    a field separator — `"navigate:https://example.com/login"` became
    `target='https', value='//example.com/login'`. Splitting on every `:`
    except one immediately followed by `//` lets `scheme://host/path` survive
    as one field while every other `:`-separated field still splits exactly
    as before (verified against the existing `click:#google-sign-in::signup
    form still has my email` double-colon case, still green).
  - `_guard_pin_steps` (:121, new) runs the same two guards the UI pin route
    already ran on its form submission, reused rather than duplicated: `ui.
    helpers._refuse_unsafe_submission` (C5 — every parsed step's target,
    value, and each line of `expected.visible_text`, labelled `step N
    target/value/expect` so a refusal names the field) then `ui.helpers.
    _require_reachable_navigate_steps` (AT-058/AT-432 — a navigate step
    outside the project's allowed domains is refused at pin time, same as
    creation-time case-adding). Both are already in `ui/helpers.py`'s
    `__all__` — a shared module, not private to `routes_issues.py` — so this
    is an import, not a duplication or a move.
  - `pin_cmd` (:137) now: loads the project via `store.load_project()`
    (needed for the guards above; refuses cleanly if the project does not
    exist yet — a gap the CLI never had a reason to hit before this cycle),
    loads `SecretStore.load(proj, ProjectPaths(project).env_file,
    strict=False)`, and folds `_guard_pin_steps` plus the new
    `refuse_if_issue_already_pinned` (AT-604, below) into the same
    `try/except (ValueError, HTTPException, PinnedCaseError)` that already
    caught `_parse_step`'s `ValueError` — one place translates a guard's own
    exception into a CLI message and a non-zero exit, whichever guard raised
    it.
- `src/autotester/stages/issues.py::refuse_if_issue_already_pinned` (:99,
  new) — the stage-level, shared guard AT-604 asked for: looks up whether
  `store.list_cases()` already has a case whose `pinned_issue_id` matches
  this issue, and raises `PinnedCaseError` (T-184/AT-585's own class, reused
  rather than inventing a second "protected case" exception) only when that
  existing case's id **differs** from the one about to be created. An
  identical resubmission (same steps, same id) is deliberately left alone
  here — that is the pre-existing duplicate-case guard's job
  (`ui/routes_cases.py::_refuse_duplicate` on the UI side, the CLI's own
  `has_case` check below it), which already has its own message; this guard
  only fires for a genuinely different set of steps.
  - `ui/routes_issues.py::pin_issue` (:159) calls it right after building the
    candidate `Case`, catching `PinnedCaseError` into `HTTPException(409,
    ...)` — the same 409 pattern `routes_cases.py::delete_case` already uses
    for a pinned case (AT-585).
  - `cli_issues.py::pin_cmd` calls the same function; a `PinnedCaseError`
    there is a non-zero exit with the guard's own message (via the shared
    except block above).

### Explicitly NOT built (cycle 2)

- No "unpin" action — `refuse_if_issue_already_pinned`'s message says to
  unpin first, but there is still no route or command that does it (T-184's
  own scope, unchanged; a pinned case can only be created, never edited or
  unpinned, in this codebase today).
- No change to the exact wording of cycle 1's UI-side duplicate message
  (`_refuse_duplicate`) — AT-604 is a distinct failure mode (different
  steps, not identical ones) and gets its own message.

### How to verify (commands + expected)

```
uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

### Actual outputs (cycle 2, in the worktree)

```
$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
............................................................................. [ 51%]
........................................................................ [100%]
148 passed, 1 skipped, 1 warning in 6-9s (RAM-varying, 3 runs during this cycle)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/verdicts/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
1 violation(s)
```

**The doctor violation above is pre-existing, not introduced by cycle 2** —
it fires because the checker's own cycle-1 verdict (already committed at
`7e67ce4`, before any cycle-2 edit) names AT-604 with no matching row yet in
`qa/issues.jsonl`. Confirmed via `grep -c AT-604 qa/issues.jsonl` -> 0 hits,
unchanged by this cycle. `qa/issues.jsonl` is checker-owned (this project's
maker-checker contract: "maker never edits it"; feedback goes to
`qa/feedback-inbox.md`) and outside cycle 2's HARD RULES (no editing
`qa/issues.jsonl`) — left for the checker to fold in on its own pass.

144 -> 148 tests: 143 pre-existing (1 skip) + 5 new (`test_cli_issues.py`
gains 4: URL-scheme preservation, out-of-scope-navigate refusal, raw-secret
refusal, AT-604 re-pin refusal; `test_ui_issues.py` gains 1: the AT-604 409).
The `test_cli_issues.py` fixture also now saves a `Project` (previously it
saved none) — required for the new guards, which need `allowed_domains` and
`secrets` to check against; two pre-existing tests
(`test_pin_creates_a_protected_case_from_confirmed_steps`,
`test_pinning_the_same_issue_and_steps_twice_is_idempotent`) had their
`navigate:/signup`-style relative targets changed to
`navigate:https://demo.test/signup` full URLs, because a relative navigate
target now correctly fails the same reachable-navigate check the UI's own
case-creation form has always enforced (a relative target was never a
capability this unit claimed — cycle 1's own tests just hadn't exercised the
reachable check yet, since the CLI didn't run it).

### Capability coverage (cycle 2 fixes, each with an isolating falsification)

Throwaway copy built OUTSIDE the worktree
(`scratchpad/falsify-at597`, same recipe as cycle 1): `src/` (whole tree,
needed for package imports), `tests/{conftest.py,
tests_mutation_fixtures.py, test_ui_issues.py, test_cli_issues.py,
test_pinned_regression.py, fixtures/}`, `scripts/{regression_proof.py,
explore_proof.py}`, `pyproject.toml`, `uv.lock`, `.python-version`,
`README.md`. `uv sync --frozen` in its own venv (cache-hit, no network);
confirmed green (30/30 relevant tests) before any falsification. Every
falsifying edit is a single hunk, applied, the one named test run, then
reverted and the same test re-confirmed green before the next row — the
tracked worktree was never touched.

| capability | check | falsifying edit (single hunk) | observed |
|---|---|---|---|
| a raw declared secret in a `--step` value is refused, nothing written | `test_pin_refuses_a_raw_secret_value` | `cli_issues.py` `_guard_pin_steps`: `_refuse_unsafe_submission(texts, project, secrets)` -> `pass` | PASS before (exit != 0). FAIL after: `assert 0 != 0` (the CLI exited 0 and would have pinned the raw secret) |
| a `navigate:` target keeps its `scheme://` intact | `test_pin_preserves_a_url_scheme_in_the_navigate_target` | `cli_issues.py` `_parse_step`: `_STEP_SPLIT_RE.split(raw, maxsplit=3)` -> `raw.split(":", 3)` | PASS before. FAIL after: target became `'https'`, so the (still-active) reachable-navigate guard refused it with "needs a full URL" — the mangled parse surfaces immediately, not silently |
| an out-of-scope/unreachable `navigate:` step is refused (CLI) | `test_pin_refuses_an_out_of_scope_navigate_step` | `cli_issues.py` `_guard_pin_steps`: `_require_reachable_navigate_steps(steps, project)` -> `pass` | PASS before. FAIL after: `assert 0 != 0` (exited 0, would have pinned an unreachable step) |
| re-pinning an issue with different steps is refused (CLI, AT-604) | `test_pin_refuses_a_second_pin_of_the_same_issue_with_different_steps` | `cli_issues.py` `pin_cmd`: `refuse_if_issue_already_pinned(store, issue.id, case.id)` -> `pass` | PASS before. FAIL after: `assert 0 != 0` (a second pinned case would have been silently created) |
| re-pinning an issue with different steps is refused 409 (UI, AT-604) | `test_repinning_an_issue_with_different_steps_is_refused_409` | `routes_issues.py` `pin_issue`: `refuse_if_issue_already_pinned(store, issue_id, case.id)` -> `pass` | PASS before. FAIL after: `assert 200 == 409` (the resubmission redirected through to `/cases` and pinned a second case instead of being refused) |

### Known limits / gaps (cycle 2, disclosed)

- **No real-browser (Chromium) Mode D run this cycle either** — playwright
  MCP was unavailable in this session too (same `CONNECT_TIMEOUT` cycle 1
  hit). Cycle 1's live-evidence recipe above still applies to the UI route;
  the CLI path has no browser surface to demonstrate (it never opens one).
- **Full suite not run** — RAM-gated, same constraint as cycle 1; the
  targeted set above covers every module this cycle touched
  (`cli_issues.py`, `stages/issues.py`, `ui/routes_issues.py`) plus every
  consumer of `Case`/`ProjectStore.list_cases` in the run list.
- **`qa/issues.jsonl` has no AT-604 row** — confirmed pre-existing (see
  Actual outputs above), left for the checker; this cycle only fixed the
  code AT-604 described.
- **No `--target/--value/--expect`-per-flag alternative CLI syntax** — the
  fix kept the existing compact `action:target[:value[:expect]]` form per
  the dispatch brief's "or add another clean approach that keeps the
  existing CLI syntax working"; the compact form still has the pre-existing,
  out-of-scope limitation that a literal `:` inside a value or expect box
  (not part of a `scheme://`) still splits fields, same as before this
  cycle.

## Fix cycle 3 — the port colon still split a URL (ddb747d)

Checker's cycle-2 verdict (`qa/verdicts/at597-pin-issue-caller.md`, commit
`ddb747d`): cycle 2's `_STEP_SPLIT_RE = re.compile(r":(?!//)")` lookahead
protected only the scheme's own colon. A URL with an explicit port still
split at the PORT colon — `navigate:http://localhost:8069/signup` became
`target='http://localhost'`, `value='8069/signup'`; `https://app.example.
com:8443/login` broke the same way; `fill:#url:https://x.com:8080/a` gave
`value='https://x.com'` with `'8080/a'` left over as the (wrong) expect
field. This is cycle 3, the last one under the cap.

### What changed

- `src/autotester/cli_issues.py::_parse_step` (:134): the action is now
  split off at the FIRST `:` only (`raw.partition(":")`), same as before.
  What happens to the remainder now differs by action:
  - **NAVIGATE** takes the whole remainder as its target with no further
    split at all — navigate has no value or expect field (T-184's `Step`
    shape leaves them unused for it), so there is nothing left for a URL's
    own scheme or port colon to be mistaken for a field separator.
  - **Every other action** tokenizes the remainder field-by-field via the
    new `_split_step_fields`/`_take_step_field` (:102, :119), which in turn
    uses a new `_URL_FIELD_RE` (:91): `^[A-Za-z][A-Za-z0-9+.-]*://[^/:]*
    (?::\d+)?[^:]*` — a field that starts with a scheme consumes the
    authority (host, no `:` or `/` in it) plus an OPTIONAL `:digits` port,
    then the path up to whichever `:` comes next. A non-URL field still
    splits on its first remaining `:`, exactly as cycle 2 already did.
  - Old `_STEP_SPLIT_RE` (the single scheme-only lookahead) is removed
    entirely, replaced by the field-at-a-time tokenizer above.
- `pin_cmd` (:187) grew past the 50-line cap once the parse logic above was
  wired in; the idempotent tail (already-pinned no-op, success message) was
  pulled out into a new `_finish_pin` helper (:233) rather than trimming any
  docstring. `pin_cmd` is 44 lines now; the file is 260 lines total; no
  function in it is over 50 lines (checked with an ast-based line counter,
  same method cycle 1/2 used).
- `tests/test_cli_issues.py`: imports `_parse_step` directly (precedent:
  `tests/test_cli_orchestrate_resume.py` already imports a private
  `_persist_proposal` the same way) and adds 6 tests under a new "AT-597
  cycle 3" section — see capability coverage below.

### Explicitly NOT built (cycle 3)

- The `fastapi.HTTPException` import and the private `ui.helpers` guard
  imports (`_refuse_unsafe_submission`, `_require_reachable_navigate_steps`)
  stay in `cli_issues.py` across the CLI/UI layer boundary, per the
  dispatch's explicit scope: not moved this cycle. Left under Known limits
  below as a follow-up unit.
- No change to the pre-existing, out-of-scope limitation (noted in cycle 2)
  that a literal `:` inside a non-URL value or expect field still splits —
  only a `scheme://` field is now colon-safe, by design.

### How to verify (commands + expected)

```
uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

### Actual outputs (cycle 3, in the worktree)

```
$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
........................................................s............... [ 46%]
........................................................................ [ 92%]
...........                                                              [100%]
154 passed, 1 skipped, 1 warning in 5.80s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/manifests/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
2 violation(s)
```

**Both doctor violations are the same pre-existing AT-604 gap cycle 2
already flagged** — the checker's own verdicts and this manifest name
AT-604 with no matching row yet in `qa/issues.jsonl`; that ledger row is
the checker's to add, not this cycle's code fix. Confirmed via `grep -c
AT-604 qa/issues.jsonl` -> 0 hits, unchanged since cycle 2.

### Capability coverage (falsified in a throwaway copy, never the worktree)

| # | Capability | Test | Falsifying edit | Result |
|---|---|---|---|---|
| 1 | A navigate target's port survives | `test_parse_step_preserves_a_navigate_targets_port` | NAVIGATE branch reverted to `remainder.split(":", 1)[0]` | RED: `assert 'http' == 'http://localhost:8069/signup'` -> reverted -> GREEN |
| 2 | An https host's port survives | `test_parse_step_preserves_an_https_hosts_port` | same edit as #1 (same NAVIGATE-bypass code path) | RED: `assert 'https' == 'https://app.example.com:8443/login'` -> reverted -> GREEN |
| 3 | A ported URL survives whole as a fill value | `test_parse_step_keeps_a_ported_url_whole_as_a_fill_value` | `_URL_FIELD_RE`'s `(?::\d+)?` port group removed | RED: `assert 'https://x.com' == 'https://x.com:8080/a'` -> reverted -> GREEN |
| 4 | A ported URL value keeps its own trailing expect | `test_parse_step_keeps_a_ported_url_value_and_its_own_expect` | same edit as #3 (same tokenizer path) | RED: `assert 'https://x.com' == 'https://x.com:8080/a'` -> reverted -> GREEN |
| 5 | A plain no-port URL still parses (regression) | `test_parse_step_still_parses_a_plain_url_with_no_port` | same edit as #1 (NAVIGATE bypass) | RED: target truncated to `'https'` -> reverted -> GREEN |
| 6 | Full CLI pin round-trip keeps a ported navigate target | `test_pin_a_local_dev_server_navigate_target_end_to_end` | same edit as #1 (NAVIGATE bypass) | RED: reachable-navigate guard rejected the truncated target ("needs a full URL") -> reverted -> GREEN |

Each row's falsifying edit was applied to a throwaway copy outside the
worktree (own `uv sync --frozen` venv), confirmed red with the exact
assertion shown, then reverted and confirmed green again before moving to
the next row — the worktree itself was never touched by any falsifying
edit. Two edits cover six rows because rows 1/2/5/6 all exercise the same
NAVIGATE-bypass branch and rows 3/4 both exercise the same
`_URL_FIELD_RE`-driven tokenizer branch; each edit is a single, independent
hunk that would falsify every row sharing that code path.

### Known limits (cycle 3)

- **`cli_issues.py` still imports `fastapi.HTTPException` and private
  `ui.helpers` guard functions** (`_refuse_unsafe_submission`,
  `_require_reachable_navigate_steps`) across what would otherwise be a
  clean CLI/UI layer boundary. Raised as a non-blocking question in the
  cycle-2 checker verdict; left in place this cycle per the dispatch's
  explicit scope ("do NOT move them this cycle"). Follow-up: a shared
  `stages/` or `core/`-level home for these guards (and for
  `PinnedCaseError`-style exceptions) so neither `cli_issues.py` nor
  `routes_issues.py` needs to reach into the other layer's private helpers
  or into `fastapi` from a non-HTTP entry point.
- Cycle 2's known limits (no unpin action, pre-existing literal-colon
  splitting inside a non-URL value/expect field, no browser-based Mode D
  run, full suite not run for RAM reasons, `qa/issues.jsonl` missing an
  AT-604 row) all still apply unchanged — see the Fix cycle 2 section
  above.

## Fix cycle 4 — narrow, gate-approved (qa/gates/at597-cycle4.md, answer A)

Checker's cycle-3 verdict (`qa/verdicts/at597-pin-issue-caller.md`, commit
`1133e8b`): cycle 3's port fix held for every case it named, but its
NAVIGATE branch (`target, value, expect = remainder, None, ""`) took the
whole remainder as the target with no further split, on the reasoning that
navigate has no value. It does have a live **expect**, though — `execute.py`
:132 settles the page after NAVIGATE and E1 evaluates a step's declared
`expected` post-settle — so a trailing `::Welcome` was silently swallowed
into the target instead of becoming the expect: `navigate:https://x.com/
signup::Welcome` stored target `'https://x.com/signup::Welcome'`, expected
`[]`. Cycle 2 parsed the same input correctly. This is a narrow, gate-
approved cycle 4 (3-cycle cap already spent at cycle 3; Umesh answered
option A on `qa/gates/at597-cycle4.md`, scope: the NAVIGATE branch of
`_parse_step` only).

### What changed

- `src/autotester/cli_issues.py::_parse_step` (:134): the NAVIGATE-only
  bypass is removed. Every action now tokenizes the remainder through the
  same `_split_step_fields(remainder)` call, so NAVIGATE's target still gets
  the URL-aware, port-safe `_take_step_field` treatment cycle 3 built,
  exactly like every other action's target/value/expect fields. After the
  generic split, `if action is Action.NAVIGATE and value: raise ValueError`
  refuses a non-empty value field — navigate has nowhere to put one — with
  a message naming both valid forms (`'navigate:<url>'` and
  `'navigate:<url>::<expect>'`); the (already-empty) `value` is then forced
  to `None` for NAVIGATE so it's never confused with the general case's
  `""` vs `None` handling.
  - `navigate:<url>::<expect>` (empty value field, non-empty expect field)
    now parses to target=url, value=None, expect=the expect text — kept.
  - `navigate:<url>:<value>:<expect>` (non-empty value field) is refused
    with a clear error instead of corrupting the target (cycle 3's bug) or
    silently dropping data.
- Docstring on `_parse_step` rewritten (not trimmed) to describe the
  unified tokenization and explain why cycle 3's bypass was wrong (navigate
  has a live expect, not "no value or expect" as cycle 3's docstring
  claimed).
- `tests/test_cli_issues.py`: 3 new tests under a new "AT-597 cycle 4"
  section — see capability coverage below. All 6 cycle-3 tests (port
  preservation for navigate and fill values, no-port regression, full CLI
  round-trip) re-run unchanged and stay green.

### Explicitly NOT built (cycle 4)

- IPv6 bracketed hosts (`[::1]`) still split on their own colons — flagged
  as a non-blocking note in the cycle-3 verdict and confirmed out of scope
  by the gate answer; left as a Known limit below.
- The `fastapi.HTTPException` / private `ui.helpers` guard imports are
  unchanged — still deferred, unrelated to this cycle's scope (the NAVIGATE
  branch of `_parse_step` only).
- No change to `pin_cmd`'s `--step` help text — it already documents the
  generic `action:target[:value[:expect]]` form without claiming navigate
  accepts a value, so nothing there was inaccurate.

### How to verify (commands + expected)

```
uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

### Actual outputs (cycle 4, in the worktree)

```
$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py
...........................................................s............ [ 45%]
........................................................................ [ 91%]
..............                                                           [100%]
157 passed, 1 skipped, 1 warning in 4.16s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/manifests/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
2 violation(s)
```

**Both doctor violations are the same pre-existing AT-604 gap** flagged in
cycles 2 and 3 — unchanged, checker-owned, not introduced by this cycle.

### Capability coverage (falsified in a throwaway copy, never the worktree)

| # | Capability | Test | Falsifying edit | Result |
|---|---|---|---|---|
| 1 | A navigate target's port AND its expect both survive | `test_parse_step_keeps_a_navigate_ports_target_and_its_expect` | NAVIGATE branch reverted to cycle 3's bypass (`target, value, expect = remainder, None, ""`) | RED: `assert 'http://localhost:8069/signup::Welcome' == 'http://localhost:8069/signup'` -> reverted -> GREEN |
| 2 | A plain (no-port) navigate target keeps its expect too | `test_parse_step_keeps_a_navigates_expect_with_no_port_too` | same edit as #1 (same bypass) | RED: `assert 'https://x.com/signup::Welcome' == 'https://x.com/signup'` -> reverted -> GREEN |
| 3 | A navigate step with a value field is refused | `test_parse_step_refuses_a_navigate_with_a_value_field` | same edit as #1 (bypass never reaches the refuse check) | RED: "DID NOT RAISE ValueError" -> reverted -> GREEN |
| 3b | (independent isolation) the refuse-on-value guard alone | same test as #3 | narrower edit: kept the unified split, dropped only the `if ... and value: raise` block (`value = None` unconditionally) | RED: only this test failed ("DID NOT RAISE ValueError"), rows #1/#2 stayed GREEN -> reverted -> all GREEN |

Row 3b is not a required row on its own but was run to confirm the
refuse-on-value guard is independently falsifiable from the target/expect
fix (edit #1 falsifies all three at once because it removes the whole
unified code path; edit #3b isolates just the guard). Each edit was applied
to a throwaway copy outside the worktree (`uv sync --frozen`, confirmed
19/19 green before falsifying), confirmed red with the exact assertion
shown, then reverted; a final `diff` against the worktree's `cli_issues.py`
after the last revert showed no difference, and the copy was deleted
afterward. The worktree itself was never touched by any falsifying edit.

### Known limits (cycle 4)

- **IPv6 bracketed hosts (`[::1]`) still split on their own colons** —
  `fill:#u:http://[::1]:8080/a` still gives a corrupted value (`_URL_FIELD_
  RE`'s host class `[^/:]*` cannot hold `[::1]`). Confirmed out of scope by
  the gate answer (option A's scope line: "IPv6 `[::1]` stays a filed
  follow-up"). Same limitation applies to a NAVIGATE target with an IPv6
  host, unchanged by this cycle's fix (the unified tokenizer shares
  `_URL_FIELD_RE` with the general case).
- Cycle 2 and cycle 3's known limits (no unpin action, pre-existing
  literal-colon splitting inside a non-URL value/expect field,
  `fastapi.HTTPException`/private `ui.helpers` guard imports, no browser-
  based Mode D run, full suite not run for RAM reasons in cycles 2-3,
  `qa/issues.jsonl` missing an AT-604 row) all still apply unchanged.

## Fix cycle 5 — register the unlisted advice site (qa/gates/at597-cycle5.md, answer A)

Checker's cycle-4 verdict (`qa/verdicts/at597-pin-issue-caller.md`, commit
`2e57296`): every claimed behaviour passed, including a live Mode D browser
run on master (pin -> 303 with the expect stored, delete-a-pinned-case ->
409, identical re-pin -> 400, different-steps re-pin -> 409, CLI exits 0/2
correctly) — but the full suite (only cycles 1-3 ran it; cycles 1-4 of this
unit ran the targeted set) turned up one red:
`tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_
unnoticed` -> `new: [('cli_issues.py', 'issues list')]`. The advice at
`cli_issues.py:223` ("no issue '{issue_id}' -- try `autotester issues list
{project}`.") was added in cycle 1 (`0323329`) but never registered in the
AT-210 guard's `EXPECTED_SITES`. This is a second narrow, gate-approved
cycle (`qa/gates/at597-cycle5.md`, answer A): one `EXPECTED_SITES` line, no
src change, following the exact pattern at575 used in `6b66de5`.

### What changed

- `tests/test_cli_advice_resolves.py`: added `("cli_issues.py", "issues
  list")` to `EXPECTED_SITES` (:159) and bumped `EXPECTED_SITE_COUNT` (:191)
  from 18 to 19 — the same two-line pattern at575's `6b66de5` used for its
  own newly-added advice site. No source file touched this cycle.

### Explicitly NOT built (cycle 5)

- No change to `src/` — the gate's scope is the test registry only; the
  advice string itself was already correct and already resolves to a real
  command (`test_every_command_the_code_names_is_one_the_cli_exposes`
  already covered it and passed every prior cycle).

### How to verify (commands + expected)

```
uv run pytest tests/test_cli_advice_resolves.py
uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py tests/test_cli_advice_resolves.py
uv run ruff check src tests scripts
uv run autotester doctor
```

### Actual outputs (cycle 5, in the worktree)

```
$ uv run pytest tests/test_cli_advice_resolves.py
............................                                             [100%]
28 passed in 7.08s

$ uv run pytest tests/test_ui_issues.py tests/test_cli_issues.py tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_cli_surface.py tests/test_cli_advice_resolves.py
..........................................                               [100%]
185 passed, 1 skipped, 1 warning in 10.30s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/manifests/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at597-pin-issue-caller.md -- AT-604 is named here but has no row in qa/issues.jsonl
2 violation(s)
```

**Both doctor violations are the same pre-existing AT-604 gap** flagged
since cycle 2 — unchanged, checker-owned, not introduced by this cycle.
No falsification row is required this cycle: the change is a test-registry
line with no behaviour of its own to falsify (the fix's own effect is
already fully demonstrated by the before/after test result: 1 failed, 27
passed at cycle 4's full-suite run -> 28 passed here).

### Known limits (cycle 5)

No new limits. Cycle 4's known limit (IPv6 bracketed hosts `[::1]` still
split on their own colons, explicitly out of scope per the cycle-4 gate)
and every earlier cycle's known limits still apply unchanged.

## Status: checked-PASS (cycle 5, qa/verdicts/at597-pin-issue-caller.md 8b7599f)
