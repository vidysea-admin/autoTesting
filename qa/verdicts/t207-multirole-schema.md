# Verdict - t207-multirole-schema (T-207, G11-1)

Cycle checked: 0
Checker: claude-sonnet-subagent, bound to D:/autoTesting/.worktrees/t207-multirole-schema, HEAD 722bf3df (code a9d07602), base 4df66032 (= `git merge-base HEAD int/1017`, verified).
Policy-Version: proportional-verification/2026-10-17.13 (manifest pin)

## Check plan (step 0)
Diff: 5 new schema files, `schema/project.py` edited in place (+44/-2), 1 test file, 1 golden. No UI, no auth/tenancy/data-write, no prompt. Signals: logic changed -> affected tests + falsification floor; schema read + shared module -> tier M. One check type, so no coordinator fan-out. SERIAL: checks were cheap and shared no port or DB.

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (MP1, MP2, MP3, MPI3), 6/6 invariants hold or untouched (MPI3 and MPI5 evidenced; MPI1, MPI2, MPI4, MPI6 not touched by a schema-only unit)
TIER: M (shared `schema/project.py` plus a schema read; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 4/4 rows reproduced (own mutants, below)
LIVE-BROWSER: not-applicable (schema files only, no UI path)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (builder: claude-sonnet-subagent)
full-suite trigger: conftest-import (shard_suite `--affected` returns integration-required because tests/conftest.py imports `schema/project.py`); not run here, left for the pre-push 6c check (.13-1)

## Evidence I produced (all re-run by me)
- MP1: `pytest tests/test_multi_role_schema.py` 63 passed. Closed `LinkKind` = redirect|sso|shared_account|handoff (`multi_role_enums.py:16-21`); `extra="forbid"` on all five models (`platform_link.py:21`, `role_account.py:24`, plus mailbox_ref.py and platform.py); a dangling link end is rejected by `Project._platform_references_resolve` (`project.py:246`), read in this check.
- MP2: `RoleAccount.username_key/password_key` and `MailboxRef.host_key/user_key/password_key` are `SecretKey` (`^[A-Z][A-Z0-9_]*$`, max 64). Value-shaped inputs (password, spaces, email, lower-case, leading digit, trailing newline, empty, 65 chars) are rejected on every key field; `assert_no_raw_secrets` over the serialised and the written project passes and still bites on a leaked value.
- MP3 (own probe, scratchpad/t207chk/probe_mp3.py): the golden loads and writes back byte-identical under BOTH the base source (`git archive 4df66032`) and HEAD source; no `platforms|platform_links|role_accounts` key is written; the implicit platform id is `primary` and its `allowed_domains` equal the project's. All 10 committed projects load without the new fields.
- Hint 2 (no secret rule widened): `SecretRef.model_json_schema()["properties"]["key"]` is identical on base and HEAD (pattern `^[A-Z][A-Z0-9_]*$`), and 9 probe keys (hunter2, ab, A, A_1, 200x A, `A\n`, `_A`, `1A`, a@b.c) get the same accept/reject on both. `SecretRef.key` gained no `max_length`; the 64 cap is only on the new `SecretKey`.
- Hint 1 (role_accounts): in scope, not creep. It is optional (`| None = None`), closed, validated against platform ids, and narrows or removes nothing; MP2 names `RoleAccount` as a project-carried shape and MP4 needs a home for it. Accepted.
- MPI3: `enums.py` is not in `git diff --name-only 4df66032..HEAD` (still 300 lines); `multi_role_enums.py` holds exactly the 7 enums.
- Related set (12 existing test files that import `Project`/`SecretRef`, plus the new file): 225 passed, 1 skipped.
- `ruff check src tests scripts`: all checks passed. `autotester doctor`: 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md), not this unit. Sizes: project.py 278, multi_role_enums.py 90 (<= 300).
- Step 4c diff scope: only the `SecretRef.key` pattern line is replaced (same string via the shared constant) plus additions; nothing deleted or renamed; every changed file is in the manifest's What changed.

## Falsification (floor: 1 per criterion; green before, red after, each in its own copy under scratchpad/t207chk/row*, outside the worktree)
- MP1: `platform_link.py` `extra="forbid"` -> `"ignore"`: `test_unknown_field_is_rejected_on_every_model` 5 passed -> 1 failed (`[<lambda>1]`).
- MP2: `role_account.py` `password_key: SecretKey` -> `str`: `test_role_account_key_fields_reject_value_shaped_text` 16 passed -> 8 failed (every value-shaped input on `password_key`).
- MP3: `Project.platforms` `default=None` -> `default_factory=list` (always emit): `test_pre_g11_fixture_is_byte_identical_after_round_trip` 1 passed -> 1 failed.
- MPI3: delete `Priority.P2`: `test_every_g11_enum_lives_in_the_one_enums_file` 1 passed -> 1 failed.
Each red fired on the named assertion, not an import error; the green ran first in the same copy.

## Notes (non-blocking)
- Pre-existing, not this unit: `projects/pathlynks/project.json` is not byte-identical to current writer output, so the MP3 fixture is a writer-normalised copy (builder judgement 5; consistent with my base-vs-HEAD probe).
- No dual-check trigger applies: the models validate key shapes only and read no value.

EXPLANATION: All four criteria hold on evidence I produced: closed shapes with dangling-end rejection, key-only accounts with value-shaped text rejected, a pre-G11 project that loads as one implicit platform and writes back byte-identical under both base and HEAD code, and a single G11 enums file with `enums.py` untouched. The secret-key rule is unchanged and `role_accounts` is additive and inside MP2/MP4 scope.
Metrics: start=2026-10-17T21:02:57Z end=2026-10-17T21:20:56Z wall_min=18 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=1079 mutants=0 defects_unit=0 defects_6c=0
slow: reading the checker protocol and fixing the copy harness (conftest needs scripts/) 10 min
