# Manifest - t207-multirole-schema (T-207, G11-1)

**Status:** checked-PASS (qa/verdicts/t207-multirole-schema.md, cycle 0)
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP1, MP2, MP3, MPI3; invariants MPI1-MPI6 held)
**Goal task:** T-207
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** no (schema shapes only: no auth, tenancy or data-write logic; the models validate key *shapes* and never read a value; `core/redact.py` and `browser/secrets.py` untouched)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 4df66032 (worktree .worktrees/t207-multirole-schema, branch wave/t207-multirole-schema)
**Code SHA:** a9d07602

## Criteria (quoted verbatim from the contract)
- **MP1 - Platform and PlatformLink are closed shapes.** `schema/platform.py::Platform` and `schema/platform_link.py::PlatformLink` are Pydantic with `extra="forbid"`; link kind is the closed set `redirect | sso | shared_account | handoff`; a link naming an undeclared platform id fails validation. Verify: round-trip plus one unknown-field and one dangling-link rejection test. serves: intent#O16 · closes T-207
- **MP2 - A RoleAccount holds keys, never values.** `RoleAccount` and `MailboxRef` carry only `SecretRef`-shaped keys matching `^[A-Z][A-Z0-9_]*$`; a field holding a value-shaped string (contains `@` with a password, or any non-key text in a key field) is rejected. Verify: schema test plus `core.redact.assert_no_raw_secrets` over a serialised project. serves: intent#O17 · closes T-207
- **MP3 - Old projects still load.** A project.json with one `base_url` and no `platforms` loads as exactly one implicit platform whose allowed_domains equal the project's; writing it back does not add the new fields. Verify: round-trip of a real pre-G11 fixture byte-compared. serves: intent#O16 · closes T-207
- **MPI3 - One enums file, one editor (A2).** `schema/multi_role_enums.py` holds every G11 enum (LinkKind, AccountOrigin, Priority, FindingClass, AssertChannel, Expectation, OracleName) and is created and edited by T-207 only. (Later-unit check: `git diff --name-only <base>..<candidate>` does not list it.) `schema/enums.py` (300-line cap) is not touched.

## What changed
- `src/autotester/schema/multi_role_enums.py` (new, 90 lines): LinkKind, AccountOrigin, Priority (P0/P1/P2), FindingClass (15 values), AssertChannel, Expectation, OracleName (13 values; the value is the `stages/oracle_<value>.py` suffix so the T-211 registry can import by name).
- `schema/platform.py` (new, 41): `Platform` (id, name, base_url, allowed_domains, include_subdomains strict, login_case_id); `IMPLICIT_PLATFORM_ID = "primary"`.
- `schema/platform_link.py` (new, 41): `PlatformLink` (from/to platform, kind, url_template or control_name (at least one), expected_landing_host (bare host[:port]), carries_session strict).
- `schema/role_account.py` (new, 34): `RoleAccount` (id, free-text role, platform_id, username_key, password_key, tenant_label, mailbox_ref, user_persona_ref, provided_by).
- `schema/mailbox_ref.py` (new, 29): `MailboxRef` (host_key, user_key, password_key, folder) and the single `SECRET_KEY_PATTERN` / `SecretKey` rule.
- `schema/project.py` (edited in place, 238 -> 278): `Project.platforms` (:226), `platform_links`, `role_accounts`, all `... | None = None` so `write_json`'s `exclude_none` never emits them for an old project (MP3); `_platform_references_resolve` model validator (:246, duplicate ids, dangling link ends, dangling role-account platform); `effective_platforms()` (:262) builds the implicit platform on read only. `SecretRef.key` now imports `SECRET_KEY_PATTERN` instead of repeating the regex (same behaviour, one concept one place).
- `tests/test_multi_role_schema.py` (new, 244 lines, 63 cases) and `tests/golden/pre_g11_project.json` (real `projects/pathlynks/project.json`, normalised once through the BASE-commit `write_json` so it is the exact byte output of the pre-G11 writer).
- falsified (unchanged): none.

## Judgement calls for the checker
1. `Project.role_accounts` was added although the T-207 brief names only `platforms` and `platform_links`: T-208 (MP4 "saved project lists role/platform/tenant label") owns no `project.py` edit (T-207 is its sole editor in G11), so without this field the accounts have no home. It is optional, closed, and validated against the platform ids. Reversible by deleting one field.
2. `SECRET_KEY_PATTERN` lives in `mailbox_ref.py`, not `project.py`: `project.py` imports `role_account.py`, so a definition in `project.py` would be a circular import. `tests/test_multi_role_schema.py::test_secretref_key_rule_is_shared_not_copied` pins that `SecretRef` uses the same pattern object.
3. `MailboxRef` holds `host_key` as a KEY too (the brief says "host, user and password keys"), so no mailbox host value is ever in a tracked project.json.
4. `Platform.base_url` / `name` allow an empty string because an existing caller (`ui/error_pages.py:43`) builds a `Project` with `base_url=""`; a `min_length=1` on the implicit platform broke every test at conftest import (found and fixed in this unit).
5. Pre-existing, not this unit: `projects/pathlynks/project.json` on disk is not byte-identical to current `write_json` output (it predates `vision_allow_gemini_fallback`, `test_id_attributes`, `ux_policy`), which is why the MP3 fixture is normalised through the base-commit writer. Verified: base-writer output == post-change output, byte for byte.
6. `autotester doctor` reports 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md). Per the wave plan the merge-queue owner regenerates once per merge; not hand-edited here. Nothing else (file/function size, docstring, one-concept) fires.

## Verification scope
Policy-Version: proportional-verification/2026-10-17.13
Tier: M (schema read + shared `schema/project.py`; no auth/tenancy/data-write trigger)
Round: 8 files (6 src, 1 test, 1 golden), 3 criteria (+MPI3), est 25 min, schema-only
Owners: OG-SCHEMA
Base / checked state: 4df66032 / a9d07602, clean tree
Gate answers: none apply (no gate in qa/gates touches schema shapes); D-104 opens the build.
Affected tests / full-suite trigger: `shard_suite.py --repo <worktree> --affected 4df66032..HEAD --list --candidates` returns `integration-required` with `full_run_reason: tests/acceptance/conftest.py, tests/conftest.py imports or is a changed module and runs for every test (conftest/package __init__)`, so a full suite is an integration obligation for the checker; the builder ran none. The pinpoint selection is the 63 new cases (Tests[] lines below). As an extra safety net the builder also ran 44 test files chosen by name (schema, project, secret, credential, redact, store, doctor, team_enums_home, env_editor, provider_migration) plus the new file: 1055 passed, 2 skipped, 2 failed. The 2 failures are wall-clock ratio tests in untouched redact code (`test_redact_ignorable_perf.py::test_cjk_heavy_scan_stays_within_a_generous_multiple_of_ascii`, `test_redact_wrap_perf.py::test_redact_scan_time_roughly_doubles_not_quadruples_with_input_size`); rerun in isolation a DIFFERENT one of the same two files failed (`test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus`) while 29 passed: load-sensitive timing, not related to this diff (no `core/` file changed).
Tests[MP1]: tests/test_multi_role_schema.py::test_link_kind_is_the_closed_set, ::test_g11_project_round_trips, ::test_unknown_field_is_rejected_on_every_model, ::test_dangling_link_is_rejected_on_either_end, ::test_link_with_platforms_undeclared_only_sees_the_implicit_one, ::test_duplicate_ids_are_rejected, ::test_link_needs_a_trigger_and_a_bare_host, ::test_platform_blank_domain_is_rejected_but_empty_list_is_allowed, ::test_strict_bools_and_defaults - round-trip, unknown field on all 5 models, dangling on both link ends, closed kind set.
Tests[MP2]: tests/test_multi_role_schema.py::test_role_account_key_fields_reject_value_shaped_text, ::test_mailbox_ref_key_fields_reject_value_shaped_text, ::test_nested_mailbox_ref_is_checked_through_role_account, ::test_secretref_key_rule_is_shared_not_copied, ::test_serialised_project_carries_no_value_and_passes_the_prompt_gate - every key field x 8 value-shaped inputs (password, spaces, email, lower-case, leading digit, trailing newline, empty, 65 chars); `assert_no_raw_secrets` over the serialised and the written project.
Tests[MP3]: tests/test_multi_role_schema.py::test_pre_g11_fixture_is_byte_identical_after_round_trip, ::test_pre_g11_project_is_one_implicit_platform, ::test_every_committed_project_loads_without_the_new_fields, ::test_effective_platforms_copies_domains_not_aliases_them - byte compare plus no new key written plus implicit platform equals the project's domains, over the real fixture and all 10 committed projects.
Tests[MPI3]: tests/test_multi_role_schema.py::test_every_g11_enum_lives_in_the_one_enums_file - exact set of 7 enum classes and their closed values. (`schema/enums.py` is not in `git diff --name-only 4df66032..HEAD`.)
Sibling: qa/evidence/**/test_*.py referencing `SecretRef` / `Project` - not affected because they are archived checker evidence from earlier units, not part of the suite's contract; `tests/test_project_schema_team.py`, `tests/test_store.py`, `tests/test_schema.py` ran green above.
Falsification[MP1]: copy-mutant outside the worktree (scratchpad/t207-multirole-schema/mut, `if dangling:` -> `if False:`): red `test_dangling_link_is_rejected_on_either_end`, `test_dangling_role_account_platform_is_rejected`, `test_link_with_platforms_undeclared_only_sees_the_implicit_one` (3 failed, 60 passed); restored tree 63 passed.
Falsification[MP2]: copy-mutant (`SECRET_KEY_PATTERN = r".*"`): red on `test_mailbox_ref_key_fields_reject_value_shaped_text[...]` and the role-account twin for every non-key input (many failed); restored 63 passed.
Falsification[MP3]: copy-mutant (`platforms` default `None` -> `default_factory=list`, i.e. always emit it): red `test_pre_g11_fixture_is_byte_identical_after_round_trip`, `test_pre_g11_project_is_one_implicit_platform`, `test_every_committed_project_loads_without_the_new_fields` (3 failed, 60 passed); restored 63 passed.
MPI3 (an invariant, not counted against the tier-M cap of 3 mutants): a probe copy-mutant (delete `OracleName.PAYMENT`) also went red on `test_every_g11_enum_lives_in_the_one_enums_file` (1 failed, 62 passed).
Pre-check[MP1]: a9d07602 uv run --directory <worktree> pytest tests/test_multi_role_schema.py -k "link_kind or g11_project_round_trips or unknown_field or dangling or duplicate or needs_a_trigger or blank_domain or strict_bools or undeclared" -> 14 passed t=5 blobs=tests/test_multi_role_schema.py:78e8e6b,tests/golden/pre_g11_project.json:5f7d233
Pre-check[MP2]: a9d07602 uv run --directory <worktree> pytest tests/test_multi_role_schema.py -k "value_shaped or nested_mailbox or persona or secretref or serialised" -> 44 passed t=3 blobs=tests/test_multi_role_schema.py:78e8e6b
Pre-check[MP3]: a9d07602 uv run --directory <worktree> pytest tests/test_multi_role_schema.py -k "pre_g11 or committed_project or copies_domains" -> 4 passed t=2 blobs=tests/test_multi_role_schema.py:78e8e6b,tests/golden/pre_g11_project.json:5f7d233
Pre-check[MPI3]: a9d07602 uv run --directory <worktree> pytest tests/test_multi_role_schema.py -k "enums_file" -> 1 passed t=2 blobs=tests/test_multi_role_schema.py:78e8e6b
Lint: a9d07602 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both pre-existing-class stale-generated (docs/MAP.md, docs/SNAPSHOT.md), see judgement call 6.
Metrics: start=2026-10-17T20:20:00Z end=2026-10-17T21:05:00Z wall_min=45 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=63 tests_min=1
