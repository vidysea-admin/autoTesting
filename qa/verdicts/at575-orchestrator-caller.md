# Verdict — at575-orchestrator-caller

**Date:** 2026-09-25 · **Head checked:** 9bfcd8e (code 26d7d93, base master 76dfbde) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-575

```
VERDICT: FAIL
SCOREBOARD: AT-575 expected clause met (a real CLI entry point drives run_or_resume, tested through the CLI; secrets reach StageContext; resume after interruption proven through the entry point; D-018 consent before any trace); C3 / design rule "one concept, one place" not met
FAILURES:
- [C3 / design rule "a class or function defined in two modules is a bug"] sev: medium · cli_orchestrate.py::_require_crawl_consent is a statement-for-statement copy of cli_crawl.py::_preflight_consent (checker AST comparison: statement bodies identical, same parameters; only the name and docstring differ). It's the D-018 consent gate, a security check, now in two copies that will drift the first time one is tightened. The module docstring also claims the existing primitives are "reused as-is", which isn't true of this one. doctor misses it because its duplicate rule matches public names only and these are private and differently named. · fix: delete _require_crawl_consent and call cli_crawl._preflight_consent (import it, or move it to a shared spot both commands import); keep test 4 as is, it will still pin exit 2 with no trace. · issue: AT-575 (stays open)
CAPABILITY-COVERAGE: 3/3 re-run rows reproduced (2, 3, 4), each in its own throwaway copy; green before, red on the named assertion after. Row 1 (command unmounted) is self-evident and wasn't re-run.
LIVE-BROWSER: not-applicable (changed paths: src/autotester/cli.py, src/autotester/cli_orchestrate.py, tests/test_cli_orchestrate.py, docs/MAP.md; no UI route, no template)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: Everything AT-575 asks for works and is proven through the real CLI entry point. The one defect is a copied security gate where the existing one should be called, which is cheap to fix. Nothing else blocks.
```

## Questions (not failures)

1. **Resume in explore mode re-runs the consent preflight** even when DISCOVER is already done and only MODEL remains. `require_consent` doesn't use up the approval, so it costs nothing while the approval is valid, but an expired approval would block a resume that will never open a browser. Intended?
2. **Mode is recomputed on resume.** `choose_mode(sources)` builds the runner dict from the current sources, while `run_or_resume` resumes from the stored state's mode. If a teaching source is added or removed between two invocations with the same `--run-id`, the runners can mismatch the stored stages. Worth a guard: build runners from the stored state's mode when resuming.

## The maker's flags

- **(a) Capability rows done in place in the committed worktree:** the tree is clean at 9bfcd8e (`git status` empty), but this is the third time (at560, at576-577, at575). I reproduced rows 2-4 myself in separate copies. Rows belong in throwaway copies only.
- **(b) Two consent seams:** confirmed. Row 4 (preflight removed) goes from exit 2 to exit 1, with "discover failed — ApprovalRequired" as a failed checkpoint. The deeper `run_crawl` gate still refuses, but AT-111's "a refused run leaves no trace" is lost. So the preflight is load-bearing, which is exactly why it must be the one shared function and not a copy.
- **(c) Full suite:** I ran it; see below.

## What I re-ran

- `ruff` clean · `doctor` clean (copy).
- Targeted: `test_cli_orchestrate.py` + `test_orchestrate.py` + `test_orchestrate_runners.py` -> `14 passed`.
- **Every non-browser test file** (copy): `1 failed, 1570 passed, 5 skipped`; the one failure is the `.git`-dependent `test_uploaded_recordings_are_gitignored`. Net: all green.
- Row 2 (`run_id or` dropped): `assert None is not None` (state.json never lands at the requested run dir), in the resume test and the fresh-run test.
- Row 3 (`secrets=` dropped): "StageContext fell back to an unredacted Redactor({}) — RT6 gate is dark".
- Row 4 (preflight removed): `assert 1 == 2`, "discover failed — ApprovalRequired … no approval exists".
- Duplicate check: AST statement bodies of `cli_crawl._preflight_consent` and `cli_orchestrate._require_crawl_consent` are identical.
- Diff scope 76dfbde..26d7d93: 4 files + MAP regeneration, all listed; the only removed line is cli.py's import line (widened).

## Status: FAIL (cycle 1) — maker fix cycle 2.

---

# Cycle 2 — /checker verdict

**Date:** 2026-09-25 · **Head checked:** a81dee1 (fix e65b8f0, base master 76dfbde) · **Cycle checked: 2** (manifest Fix cycle: 2 of 3)

```
VERDICT: FAIL
SCOREBOARD: all cycle-1 findings fixed (C3 duplicate gone; consent skip on exactly "done"; mode from stored RunState; unknown --run-id starts fresh); the full non-browser suite is red on one test this cycle introduced
FAILURES:
- [suite / AT-210 advice-site guard] sev: medium · tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed fails: "advice sites changed. gone: [] new: [('cli_orchestrate.py', 'ingest register')]". Cycle 2's NoEntrySource message ("`autotester ingest register` one first") is a new advice site, and the guard requires every new site to be registered deliberately in EXPECTED_SITES. Reproduced in the bound worktree (1 failed, 26 passed); master 76dfbde is green, so the unit introduced it, and a merge would turn master's suite red. The advice itself is valid: `autotester ingest register` resolves, and the other 26 advice tests, including the resolver checks, pass. · fix: add ('cli_orchestrate.py', 'ingest register') to EXPECTED_SITES in tests/test_cli_advice_resolves.py (the deliberate act the guard asks for), then re-run that file plus every non-browser test file; the targeted 103-test set didn't include this repo-wide guard (the same miss as AT-110 cycle 1). · issue: AT-575 (stays open)
CAPABILITY-COVERAGE: 3/3 cycle-2 rows reproduced (1, 2, 3), each in its own copy with its OWN uv-synced .venv (the copy imports its own src: verified via autotester.cli_orchestrate.__file__), so the maker's junction concern doesn't apply to these reds; green before, red on the named tests after
LIVE-BROWSER: not-applicable (changed paths: src/autotester/cli_orchestrate.py and tests; no UI route or template)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: The code is right: the one shared consent gate is called, the resume logic keys on the stored state exactly, and the rows prove each piece. The only blocker is the unregistered advice site, a one-line test-data addition. Cycle 3 is the last: register the site and run the whole non-browser suite before the doorbell.
```

## What I re-ran (cycle 2)

- Duplicate check (AST): no function in cli_orchestrate.py has `_preflight_consent`'s body; it's called via `cli_crawl._preflight_consent`.
- `ruff` clean · `doctor` clean · `test_cli_orchestrate.py` + `test_cli_orchestrate_resume.py` -> `8 passed` in each copy before mutation.
- Row 1 (shared preflight call removed): `2 failed` (the fresh explore-refusal test and the failed-DISCOVER resume test, `assert 1 == 2`).
- Row 2 (`== "done"` -> `!= "pending"`): `test_resume_past_a_failed_discover_still_hits_consent` fails `assert 1 == 2`.
- Row 3 (mode always from choose_mode): `test_resume_keeps_the_stored_mode…` fails `assert 2 == 0`.
- Resume MODEL without `source_id`: equivalent. `merge_flowspec` falls back to `incoming.source_ids[0]`, and INGEST's proposal carries `source_ids=[source.id]` (ingest.py:274), used only to attribute conflicts.
- **Every non-browser test file** (copy, 1h34m under ~0.5 GB free RAM): `2 failed, 1574 passed, 5 skipped`. One is the `.git`-only test; the other is the FAILURE above.

## Status: FAIL (cycle 2) — maker fix cycle 3 (last).

---

# Cycle 3 — /checker verdict

**Date:** 2026-09-25 · **Head checked:** d8f202c (fix 6b66de5) · **Cycle checked: 3** (manifest Fix cycle: 3 of 3)

```
VERDICT: PASS
SCOREBOARD: AT-575 expected clause met (a live CLI entry point drives run_or_resume, tested through it; secrets reach StageContext; resume proven through the entry point; one shared D-018 consent gate; consent skipped only past an exactly-done entry stage; stored mode on resume; unknown --run-id starts fresh); C3 holds; the suite is green apart from one known pre-existing flaky test and the copy-only .git test
FAILURES: none
CAPABILITY-COVERAGE: cycle-3 row = the AT-210 guard itself (red on 08e0eb6 in the checker's own cycle-2 reproduction, green now); cycle-1/2 rows reproduced earlier in own-venv copies, and src is unchanged since a81dee1
LIVE-BROWSER: not-applicable (changed paths: src/autotester/cli.py, src/autotester/cli_orchestrate.py, tests; no UI route or template)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: The cycle-3 change is exactly the registration the cycle-2 verdict asked for, and it greens the AT-210 guard. The code is unchanged since the cycle-2 checks that proved every other claim.
```

## What I re-ran (cycle 3)

- Scope: 6b66de5..d8f202c is manifest only; 08e0eb6..6b66de5 is only `tests/test_cli_advice_resolves.py` (+`("cli_orchestrate.py", "ingest register")`, `EXPECTED_SITE_COUNT` 17->18); `git diff a81dee1..d8f202c -- src/` is empty. Tree clean.
- `test_cli_advice_resolves.py` + `test_cli_orchestrate.py` + `test_cli_orchestrate_resume.py` (worktree) -> `35 passed`.
- **Every non-browser test file** (copy of 6b66de5, own .venv): `2 failed, 1574 passed, 5 skipped`.
  - `test_uploaded_recordings_are_gitignored` needs `.git`, which copies lack; passes in the worktree.
  - `test_flake_probe_real_process::…kills_a_real_hung_process…` is flaky: in the worktree it went 1 failed then 3 passed on consecutive runs. It's already on the ledger as **AT-518** (open, low, "failed once in a whole-suite run"), and the unit touches no flake_probe file.
  - Net: green for this unit.
- Advice text still resolves: `autotester ingest register --help` prints its usage.

## Status: PASS (cycle 3)
