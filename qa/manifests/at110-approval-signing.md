# Manifest — at110-approval-signing
**Contract:** qa/contracts/consent.md (CN3)
**Goal task:** none (issue-fix unit, not a `.goal` task)
**Date:** 2026-09-24
**Fix cycle:** 2 of 3
**Dual check:** no
**Issues addressed:** AT-110
**Executor:** claude-sonnet-subagent
**Executor rationale:** security-critical, HMAC/consent-boundary code — never a delegation lane per SKILL.md 4b ("schema/security/auth units... stay Claude subagents").

## What changed

- `src/autotester/core/ids.py` — `APPROVAL_KEY_ENV`, `SigningKeyMissing`, `_canonical_json` (factored out of `content_hash`, now shared), `_signing_key`, `sign_payload`, `verify_payload`. The one place `RunApproval` is signed/verified; reuses `content_hash`'s canonical-JSON encoding rather than duplicating it.
- `src/autotester/schema/approval.py` — new `signature: str = ""` field; `RunApproval.sign()` (explicit, grant-time-only HMAC); `RunApproval.is_signed_and_verified` property (fails closed, raises `SigningKeyMissing` on a missing key, `False` on an empty/invalid signature — never raises for that case). Module docstring rewritten: states the honest guarantee (tamper-proof against anyone without the `.env` key; not proof against an agent that can edit `core/consent.py` itself).
- `src/autotester/core/consent.py` — `_reject_reason` gains the signature check, right after the existing `is_intact` check: missing key → refused ("cannot verify"); no signature → refused ("no signature ... re-grant"); signature present but wrong → refused ("does not verify"). All three fail CLOSED (raise/refuse, never silently accept).
- `src/autotester/cli_crawl.py` — `approve_cmd` signs the candidate via a new `_signed_or_refuse` helper (extracted to stay under the 50-line/function cap) before writing it; refuses with `SigningKeyMissing`'s message on a missing key, writing nothing. Docstring corrected (no longer says "tamper EVIDENCE, not tamper proofing" — that framing describes the pre-fix state).
- `src/autotester/ui/routes_crawl_approval.py` — `crawl_approval_submit` signs the candidate the same way, returning the existing `_approval_error` themed page (no new markup) on a missing key. `_in_force` (the "Approvals in force" card) now also requires `is_signed_and_verified`, fail-closed on a missing key, so the UI never shows a row the actual gate would refuse.
- `scripts/check_crawl_approval.py`, `scripts/explore_proof.py` — both now call `core.env.load_repo_env()` at the top of `main()`/`crawl()`'s caller, matching `cli.py`'s and `ui/app.py`'s existing convention; `explore_proof.py`'s fixture grant now calls `.sign()`. Without this, T-145's `done_check` would refuse every real (correctly signed) approval it's ever handed, since the key would never be loaded into that standalone process's environment.
- `.env.example` — new `AUTOTESTER_APPROVAL_KEY=` entry with a comment, empty value (never a real one, matching every other key in the file).
- `tests/conftest.py` — new session-scoped, autouse `_approval_signing_key` fixture (plain `os.environ`, not `monkeypatch`, which is function-scoped only and ran too late for the suite's `scope="module"` fixtures — see the fixture's own docstring for the measured failure).
- Ten existing test call sites across `tests/crawl_fake.py`, `tests/test_consent.py`, `tests/test_crawl_inventory_live.py`, `tests/test_explore_consent.py`, `tests/test_explore_live.py`, `tests/test_explore_login_spa_live.py`, `tests/test_explore_modal.py`, `tests/test_explore_typing.py`, `tests/test_ui_crawl_approval_list.py`, `tests/test_ui_crawl_login.py` — each construction of a fixture `RunApproval` gains `.sign()` so it still verifies under the new gate. No assertion in any of these files changed.
- `tests/test_approval_signing.py` — new file, 12 tests (see Capability coverage).

## How to verify (commands + expected)

- `uv run pytest tests/test_approval_signing.py tests/test_consent.py tests/test_approve_cli.py tests/test_approve_target_match.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_crawl_real_cli.py tests/test_explore_consent.py` → all pass
- `uv run pytest tests/test_explore_live.py tests/test_explore_modal.py tests/test_explore_typing.py tests/test_explore_login_spa_live.py tests/test_crawl_inventory_live.py tests/test_ui_crawl_login.py tests/test_explore.py` (real-browser fixtures, several `scope="module"`) → all pass or skip (no chromium)
- `uv run ruff check src tests scripts` → exit 0
- `uv run autotester doctor` → `doctor: clean`
- `uv run pytest` (full suite, no CLI `-q`, AT-503) → see "Full suite" below

## Actual outputs (from maker's own run)

```
$ uv run pytest tests/test_approval_signing.py tests/test_consent.py tests/test_approve_cli.py \
    tests/test_approve_target_match.py tests/test_env_loading.py tests/test_ui_crawl_approval.py \
    tests/test_ui_crawl_approval_list.py tests/test_crawl_real_cli.py tests/test_explore_consent.py
........................................................................ [ 84%]
.............                                                            [100%]
85 passed, 1 warning in 36.49s
```

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

```
$ uv run pytest tests/test_explore_modal.py
......                                                                   [100%]
6 passed in 52.10s

$ uv run pytest tests/test_explore_live.py
........                                                                 [100%]
8 passed in 82.46s (0:01:22)

$ uv run pytest tests/test_explore_typing.py tests/test_explore_login_spa_live.py \
    tests/test_crawl_inventory_live.py tests/test_ui_crawl_login.py tests/test_explore.py
............................................                             [100%]
44 passed, 1 warning in 401.84s (0:06:41)
```

All 7 live/module-scoped files: **58/58 passed**, 0 skipped for missing chromium (real browser was
available on this run), 0 failed.

### Live/module-scoped test run

First attempt (before the conftest fix below) failed with `SigningKeyMissing` from inside
`test_explore_modal.py::panel_crawl` (a `scope="module"` fixture) — the function-scoped
`monkeypatch`-based signing-key fixture in `tests/conftest.py` had not run yet, because pytest
instantiates higher-scoped fixtures before function-scoped ones for the same test. Fixed by making
the fixture `scope="session"` and setting `os.environ` directly (see `tests/conftest.py`'s
`_approval_signing_key` docstring).

Re-run after the fix, split across runs because this machine is also running other projects'
pytest/Chromium (measured: `at086-087-exemption`, a sibling `D:/autoTesting` worktree, plus
unrelated repos) and free RAM is tight — `test_explore_modal.py` and `test_explore_live.py` are
exactly the two files with `scope="module"`/`scope="session"` fixtures that constructed the
fixture approval during their OWN setup, i.e. the two files that actually exercise the fix; both
ran to completion alone and are pasted above (6 passed / 8 passed). The remaining five files
(`test_explore_typing.py`, `test_explore_login_spa_live.py`, `test_crawl_inventory_live.py`,
`test_ui_crawl_login.py`, `test_explore.py`) use function-scoped fixtures, which the ORIGINAL
function-scoped `monkeypatch` fixture would already have covered correctly — their result is
confirmatory, not diagnostic, and completed green (44 passed, pasted above). All 7 files: 58/58.

## Capability coverage (each new claim -> its isolating falsification)

| capability (one line) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| AT-110's exact forged-row repro (id removed, max_actions=9999, production=True, no signature) is refused | `test_the_at110_forgery_repro_is_now_refused`, `test_a_legacy_approval_granted_before_signing_existed_is_refused_to_re_grant`, `test_verifying_without_a_key_refuses_even_a_validly_signed_row` | `core/consent.py::_reject_reason`: replace the `try/except SigningKeyMissing` + `if not signed_and_verified:` block with `signed_and_verified = True  # SABOTAGE` (single hunk) | before: `3 passed, 9 deselected in 0.22s`. after: `3 failed` — `test_the_at110_forgery_repro_is_now_refused`: `Failed: DID NOT RAISE ApprovalRequired`; `test_a_legacy_approval_granted_before_signing_existed_is_refused_to_re_grant`: `Failed: DID NOT RAISE ApprovalRequired`; `test_verifying_without_a_key_refuses_even_a_validly_signed_row`: `Failed: DID NOT RAISE ApprovalRequired`. Reverted; re-run: `3 passed, 9 deselected in 0.20s` |
| A missing key refuses GRANTING (CLI `approve` and the bare `.sign()` call), with an actionable message, and writes nothing | `test_granting_without_a_key_refuses_with_an_actionable_message`, `test_the_grant_cli_refuses_without_a_key_and_writes_nothing` | `core/ids.py::_signing_key`: replace the `if not key: raise SigningKeyMissing(...)` guard with `key = os.environ.get(APPROVAL_KEY_ENV) or "SABOTAGE-default-key"` (single hunk — silently falls back to a default key instead of refusing) | before: `2 passed, 10 deselected in 0.62s`. after: `2 failed` — `test_granting_without_a_key_refuses_with_an_actionable_message`: `Failed: DID NOT RAISE SigningKeyMissing`; `test_the_grant_cli_refuses_without_a_key_and_writes_nothing`: `assert 0 == 1` (`exit_code`) — the grant silently succeeded instead of refusing. Reverted; re-run: `12 passed in 1.42s` (full new-file run) |
| The naive-edit case (id kept, one bound field changed) is still refused — CN3's original guarantee, now defended in depth by BOTH `is_intact` and the signature | `test_the_naive_edit_case_stays_refused` (new), `test_an_approval_edited_to_widen_itself_is_refused` (pre-existing, `tests/test_consent.py`) | `core/consent.py::_reject_reason`: `if False and not approval.is_intact:` (single hunk — disables the id-mismatch check) | before: `2 passed in 0.38s`. after: `2 failed`, both via the INDEPENDENT signature check instead (`signature does not verify — the row was edited or forged` where the test expected `edited after it was granted` — proves the two checks are genuinely redundant defenses, not one check wearing two names). Reverted; re-run: `2 passed in 0.19s` |
| The signing key VALUE never appears in CLI output, the stored approval's JSON, or the file on disk (only the signature — a derived hex digest — is ever written) | `test_the_signing_key_value_never_appears_in_any_cli_output_or_artifact` | `cli_crawl.py::approve_cmd`'s success `typer.secho(...)`: append an f-string interpolating `os.environ.get('AUTOTESTER_APPROVAL_KEY')` into the printed line (single hunk) | before: `1 passed in 2.07s`. after: `1 failed` — `AssertionError: assert 'unit-test-s...-real-secret' not in 'appr_0f1ed9...eal-secret\n'` (the printed key value found verbatim in `result.output`). Reverted; re-run: `12 passed in 0.99s` (full new-file run) |
| The AT-110 overclaiming prose ("cannot be edited on disk to widen itself" / "editing the row afterwards to widen it invalidates it" / the now-stale "tamper EVIDENCE, not tamper proofing" framing) does not exist anywhere under `src/` | `test_no_overclaiming_tamper_proof_prose_remains_anywhere_in_src` | `cli_crawl.py::approve_cmd`'s docstring: reintroduce the literal stale phrase "editing the row afterwards to widen it invalidates it" (single hunk) | before: `1 passed in 0.28s`. after: `1 failed` — `AssertionError: assert ['...cli_crawl.py'] == []`. Reverted; re-run: `80 passed, 1 warning in 12.56s` (full targeted set) |
| `.env.example` declares `AUTOTESTER_APPROVAL_KEY` with no real value | `test_env_example_declares_the_key_with_no_real_value` | Non-executable data claim (a single committed file's content) — `NO ISOLATING FALSIFICATION beyond the assertion itself; the test IS the falsifier` (removing/changing the line in `.env.example` fails it directly, verified by inspection: the test's own regex-free equality check `lines == ["AUTOTESTER_APPROVAL_KEY="]` fails on any deviation, including a real-looking value) | `1 passed` in the full new-file run; manually confirmed the assertion trips on any non-empty value by construction (equality check, not a substring match) |
| Loading a legacy/forged row (no `signature` key) from disk never attempts to auto-sign it, even when a key IS configured — so a forger's row is never quietly re-signed by the reader | `test_loading_a_legacy_row_never_auto_signs_it` | Would require re-adding auto-signing to `model_post_init` guarded on `if not self.id` (the exact hole `sign()`'s docstring names) — the property is architectural (signing is called explicitly, nowhere near `model_post_init`), so there is no single-hunk mutation of the SHIPPED code that flips it without first reintroducing that removed code path | `1 passed` in the full new-file run (`RunApproval.model_validate(legacy)` with `AUTOTESTER_APPROVAL_KEY` deleted from the environment does not raise) |

## Live browser evidence

**SKIP — RAM.** `ui/routes_crawl_approval.py` changed (`candidate.sign()` in the grant route,
`is_signed_and_verified` in `_in_force`'s display filter) but the submitted HTML form itself
(`_crawl_approval_form`) is untouched — the only new UI-visible state is the missing-key error
path, which reuses the existing `_approval_error` themed page verbatim (no new markup). Free RAM
measured at 0.74 GB (`Get-CimInstance Win32_OperatingSystem` → `FreePhysicalMemory` 772084 KB)
while the module-scoped live-browser test run (`test_explore_live.py` et al., real Chromium) was
still in flight — starting a second browser for a smoke pass on top of that was not safe on this
machine. `test_ui_crawl_approval.py::test_credentials_page_grants_a_server_scoped_crawl_approval`
and the six tests in `test_ui_crawl_approval_list.py` exercise the route through `TestClient`
(no real browser) and are green (see targeted-run output above); that is not a substitute for 5b
and is reported as exactly what it is.

## Verify results

- Targeted suite (9 files, 85 tests + 1 warning): **PASS** — pasted above.
- `ruff check src tests scripts`: **PASS** (`All checks passed!`).
- `autotester doctor`: **PASS** (`doctor: clean`).
- Live/module-scoped suite (7 files, real Chromium fixtures): **PASS** — 58/58, pasted above.
- Full `uv run pytest` (no CLI `-q`): **RAN.** `2 failed, 1617 passed, 5 skipped, 32 xfailed, 1
  warning in 910.86s (0:15:10)`. RAM was 4.6 GB free and no other `D:/autoTesting` pytest process
  was running when it was launched (checked immediately before with
  `Get-CimInstance Win32_OperatingSystem` and `Get-CimInstance Win32_Process`). Full pasted output
  below. **Both failures are confirmed pre-existing and untouched by this unit's diff** (same
  standing as AT-196/ISS-t162-drive-2b-1/ISS-t163-1/ISS-t164-1 in this ledger):
  - `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` — `assert 17 ==
    16`, a static count of CLI "advice" sites. `git diff --name-only accfa9e -- tests/test_cli_advice_resolves.py src/autotester/cli.py src/autotester/cli_issues.py src/autotester/cli_video.py`
    is empty; this unit touches none of them.
  - `tests/test_goal_criticality_vocabulary.py::test_every_base_criticality_is_a_value_the_classifier_recognises`
    — `.goal/goal.json` task `T-175` has `base_criticality: "normal"`, outside
    `CLASSIFIER_VOCABULARY`. `git diff --name-only accfa9e -- .goal/goal.json` is empty; `git log
    --oneline -1 -- .goal/goal.json` shows it was last touched at `ea6b7c3`, before this branch's
    base — T-175 predates this unit entirely (a concurrent wave's task, not this unit's).

  **No code change was forced by the full suite.** Neither failure is in this manifest's "What
  changed"; nothing was edited after the checker's PASS (`qa/verdicts/at110-approval-signing.md`,
  3ede308) — this is not a new fix cycle.

```
FAILED tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed
FAILED tests/test_goal_criticality_vocabulary.py::test_every_base_criticality_is_a_value_the_classifier_recognises
2 failed, 1617 passed, 5 skipped, 32 xfailed, 1 warning in 910.86s (0:15:10)
```

## Fix cycle 2 (maker orchestrator, 2026-09-25) -- merge-verify failure

Cycle 1 PASSed (qa/verdicts/at110-approval-signing.md, 3ede308). On merge into master
(11776d4), the merged-tree verify failed:
`tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` -- `assert 17 == 16`.
The same test PASSES on pre-merge master 11776d4 (25 passed, run in a detached worktree), so the
cycle-1 note above calling it "pre-existing" is WRONG: that check diffed cli*.py only and missed
that this unit's own `core/consent.py:81` adds a deliberate new advice site
("re-grant it with `uv run autotester approve`"). The local merge was undone (never pushed).

What changed in cycle 2:
- master 11776d4 merged INTO wave/at110-approval-signing (da6eb97), so the check runs against the current tree.
- `tests/test_cli_advice_resolves.py:185-189` -- EXPECTED_SITE_COUNT 16 -> 17 and the docstring names
  the new site. EXPECTED_SITES is unchanged: ("core/consent.py", "approve") was already a member;
  the new site repeats that command.
- No source file changed in cycle 2.

Verify (cycle 2, maker's own run in this worktree):
- `uv run pytest tests/test_cli_advice_resolves.py tests/test_approval_signing.py tests/test_consent.py tests/test_goal_criticality_vocabulary.py tests/test_goal_done_checks.py` -> `70 passed in 8.99s`
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`
- The other cycle-1 failure (`test_goal_criticality_vocabulary`, T-175 "normal") is already fixed on master and passes here.
- Full suite NOT re-run in cycle 2 -- RAM 1.9 GB (AT-558).

Capability coverage (cycle 2): the count pin is the check. Falsifying edit: EXPECTED_SITE_COUNT = 16.
Observed: before this cycle, at 16 on the merged tree -> `assert 17 == 16` FAILED (pasted above); at 17 -> passes (70 passed).

Builder note: the cycle-1 builder agent was stopped before committing. The orchestrator committed its
tree as 283edf4 after verifying that its code equals the checker-PASSed snapshot 81457e9 (empty diff;
only this manifest's full-suite note differed).

## Status: checked-PASS (qa/verdicts/at110-approval-signing.md, Cycle checked: 2, 4c3b1b3)
