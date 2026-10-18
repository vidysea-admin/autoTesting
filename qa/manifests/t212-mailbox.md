# Manifest - t212-mailbox (T-212, G11-6)

**Status:** checked-PASS build leg (qa/verdicts/t212-mailbox.md; MP34 live leg credential-gated, goal task stays open)
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP16, MP17; MP34 is the gated live leg; invariants MPI1, MPI2, MPI3, MPI5 held) and qa/contracts/source-adapters.md SA9
**Goal task:** T-212
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (read-only IMAP: the reader has no write verb and sends no mail; no auth, tenancy or data-write trigger. A lone checker may raise it)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t212-mailbox, branch wave/t212-mailbox; the T-211 head, stacked on T-209 36a87037 and T-207)
**Code SHA:** 3b64dd3a

## Criteria (quoted verbatim from the contract)
- **MP16 - Read-only mailbox.** The IMAP reader uses `EXAMINE` and `BODY.PEEK` only; no STORE, COPY, MOVE, EXPUNGE or APPEND command is ever sent. Verify: fake IMAP server records the command list. serves: intent#O18, intent#O7 - closes T-212
- **MP17 - Bounded and scrubbed.** The fetch is bounded by since-time, recipient and a message cap; bodies pass `Redactor.scrub`; a credential-shaped token in a body is recorded as present, never its value. Verify (A1, replaces the earlier text): a fixture mailbox with credential-shaped tokens of several synthetic shapes (numeric code, mixed token, URL-embedded token); none is stored, each is recorded as present. serves: intent#O18, intent#O7 - closes T-212
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only cff3ffe6..3b64dd3a`.
- Not claimed here: **MP34 [GATED]** (live mailbox read). credential-gate: the IMAP host, user and password KEY NAMES the onboarder declares for a role mailbox (the three keys of a `MailboxRef`, e.g. `<PROJECT>_<ROLE>_IMAP_HOST`, `_IMAP_USER`, `_IMAP_PASS`) and their values in the repo-root `.env`; Umesh supplies the IMAP host and mailboxes. The build criteria pass on the fake server without them.

## What changed
- `src/autotester/schema/mail_observation.py` (new, 164 lines): `MailQuery` (since-time with timezone, recipient, `max_messages` 1..50, timeout), `MailObservation` (uid, scrubbed subject, time, which token kinds and how many; no body field), `MailReadResult` (`read | unavailable` with a closed `MailUnavailableReason`, key NAMES when missing, `capped`, `command_log`), `CredentialTokenKind`, and `mask_credential_tokens` (numeric code, mixed token, URL-embedded token: returns masked text, kinds, count).
- `src/autotester/sources/imap_mailbox.py` (new, 205): `read_mailbox(ref, query, credentials, declared_keys=..., connector=...)`. `_Session` is the only door to the server; it has no write method and checks every verb against `ALLOWED_COMMANDS` (LOGIN, EXAMINE, UID SEARCH, UID FETCH BODY.PEEK, LOGOUT). `select(readonly=True)` sends EXAMINE. Search carries SINCE and TO; newest `max_messages` fetched with `BODY.PEEK[]<0.262144>`; results filtered again locally by recipient and Date; subject and body pass `Redactor` (mailbox host/user/password plus `extra_secrets`), the subject also `mask_pii`. Body parsed with the existing `sources/email.py::parse_eml_bytes`. `credentials_from_store` resolves only keys the project DECLARED. Production connector is IMAP4_SSL with certificate checks.
- `src/autotester/stages/oracle_mailbox.py` (new, 94): `observation_from_read` (raises when the read did not happen or hit the cap with no match, so the runner cannot count it as absence), `mailbox_findings` exposed as `run` (a failed `present` mailbox assertion that has a last observation becomes a `MAIL_NOT_DELIVERED` finding; P1 by `priority_for`).
- test files: `tests/imap_fake.py` (helper, not a test module) (loopback fake IMAP server recording the command list; answers write verbs so a violation would be seen; plain `BODY[]` marks `\Seen`), `tests/test_imap_mailbox.py` (23), `tests/test_oracle_mailbox.py` (14).
- falsified (unchanged): none. No T-207, T-209, T-210, T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py` or `stages/oracle_registry.py` touched.

## Judgement calls for the checker
1. **`run` is an alias.** The registry needs `run(context)`; `doctor.py` already defines a top-level `def run`, so a second one trips `duplicate-concept`. The function is `mailbox_findings` and `run = mailbox_findings`. Every other G11 oracle will meet the same rule. CORE-REQUEST: src/autotester/doctor.py exempt `stages/oracle_*.py::run` from `check_duplicate_definitions` (owner: the doctor's owner; not edited here).
2. **Unavailable is never absence (SA9).** `observation_from_read` raises `MailboxUnavailableError` for an unread mailbox and `MailboxIncompleteError` when the message cap was hit with no match. In the runner an observation that raised fails an `absent` assertion ("absence is not proven"). If every failed mailbox assertion was never observed, `mailbox_findings` raises, so the registry shows the oracle `errored` (type name only) instead of a clean `ran`; if some were proven, those findings are returned and the unobserved ones stay visible as failed outcomes.
3. **No body, no subject text in `Observation`.** The detail is counts only. A body is read in memory, scrubbed, scanned for token shapes and dropped; the stored subject has tokens masked and passes `mask_pii`.
4. **The token detector is a heuristic.** It is cue-based for codes and mixed tokens (cue words: password, passcode, token, secret, code, otp, pin, key) plus any 20+ character letter-and-digit run and URL query/path tokens. It over-flags rather than under-flags (a flagged non-secret costs a note; a stored secret is a leak). The A1 matrix covers five shapes; the checker may add shapes.
5. **Several models in one schema file.** OG-MAIL fixes `schema/mail_observation.py` as the one schema file, so the query, observation, result and their closed vocabularies share it (same call as T-211 judgement 5).
6. **Credentials arrive as a mapping.** `SecretStore` has no public accessor outside host-scoped typing, so the reader takes `credentials: Mapping` plus `declared_keys`; `credentials_from_store(store, ref)` builds it from `scrub_values()` filtered to declared keys. No `.env` read happens inside the reader (`load_repo_env` refuses to run under tests and does not export project keys, AU21).
7. **Host key value.** `host` or `host:port`, port default 993. The value is never reported, even on failure (reason is the closed enum from the exception type only).
8. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge-queue owner regenerates.
9. TDD: both test files were written before the modules and fail at collection without them (`ModuleNotFoundError: autotester.schema.mail_observation`, 2 errors in the base copy).

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M (new source adapter reading an external mailbox, read-only)
Round: 3 src files + 3 test files, 2 criteria, est 40 min
slow-plan: the fake IMAP server, the reader and the oracle are one concept (the oracle's only input is the reader's result), so splitting them would leave an untestable half
mutant-cap-raise: 16 falsifying copy-edits, one per distinct behaviour (MP16 x3, MP17 x6, SA9 x2, oracle x4) rather than per criterion; each is a one-line scratch edit and a 5-15 s run, and the checker needs to re-run only the floor (one per criterion)
Owners: OG-MAIL
Base / checked state: cff3ffe6 / 3b64dd3a, clean tree (manifest only added after)
Gate answers: qa/contracts/source-adapters.md SA9 (read-only IMAP, 2026-10-18 amendment); live leg MP34 gated on Umesh's IMAP host and mailbox keys (credential-gate above).
Affected tests / full-suite trigger: tests/test_oracle_registry.py and tests/test_cross_role_runner.py re-run because the registry now finds a real `oracle_mailbox` module (93 passed with the unit's own files); the builder ran no full suite.
Tests[MP16]: tests/test_imap_mailbox.py::test_mp16_wire_commands_are_examine_and_peek_only (verbs on the wire: EXAMINE present, no STORE/COPY/MOVE/EXPUNGE/APPEND/DELETE/SELECT/CREATE/RENAME, every FETCH has BODY.PEEK, server `seen` set empty), ::test_mp16_the_reader_logs_the_verbs_it_sent_for_the_live_evidence_of_mp34, ::test_mp16_a_write_verb_cannot_be_sent_even_by_mistake; tests/test_oracle_mailbox.py::test_e2e_the_invite_mail_arrives_so_the_assertion_passes_and_there_is_no_finding (the same verb set through the runner).
Tests[MP17]: tests/test_imap_mailbox.py -k "mp17 or sa9" - message cap keeps the newest and says capped; recipient (search carries TO, a server that ignores it is filtered locally); since-time (SINCE in the search, older mail dropped); timeout passed to the connector; query refuses unbounded/injecting input; five token shapes parametrised (numeric code, mixed temporary password, URL query token, URL path token, long standalone token) each recorded as present with its value absent from the dumped result; token in a subject masked and counted; a plain mail not flagged; mailbox user/password and an address never survive in a stored subject; SA9 honest failure (missing key, undeclared key, refused login, unreachable host, refused folder, empty window is a read) with no key value or host in the result; only declared keys resolve and a canary `.env` value is absent from the run directory. tests/test_oracle_mailbox.py - `observation_from_read` and `run` over the unavailable, capped and proven cases, registry wiring, and four end-to-end runs through `run_scenario` against the fake server.
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..3b64dd3a` lists only the 6 files above.
Falsification[MP16]: copy-mutants in scratchpad/t212-mailbox (mut.py): `readonly=True` -> `False` (EXAMINE becomes SELECT): red `test_mp16_wire_commands_are_examine_and_peek_only` (1 failed, 21 passed); `BODY.PEEK[]` -> `BODY[]`: red the same test (1 failed); the verb guard `if verb not in ALLOWED_COMMANDS` -> `if False`: red `test_mp16_a_write_verb_cannot_be_sent_even_by_mistake` (1 failed); unmutated control 36 passed.
Falsification[MP17]: copy-mutants: cap `found[-max_messages:]` -> `found`: red `test_mp17_message_cap_keeps_the_newest_and_says_it_capped`; recipient check -> `False`: red `test_mp17_recipient_bounds_the_search_and_a_server_that_ignores_it_is_filtered`; since filter -> `False`: red `test_mp17_since_time_bounds_the_search_and_older_mail_is_dropped`; token masking loop disabled: red 6 (five shapes + the subject test); URL query cue names renamed: red `...stored_nowhere[url query token]` only; `redactor.scrub(subject)` -> `subject`: red `test_mp17_the_mailbox_password_and_addresses_never_survive_in_a_stored_subject`; missing-key guard -> `False`: red `test_sa9_a_missing_key_is_unavailable_and_names_only_the_key`; refused login swallowed: red `test_sa9_a_refused_login_is_unavailable_and_the_password_is_not_reported`; oracle: unread mailbox returned as "no match" instead of raising: red `test_an_unavailable_read_raises_so_the_runner_cannot_count_it_as_absence` and the e2e broken-login test; cap guard -> `False`: red `test_a_capped_read_with_no_match_is_incomplete_not_absent`; unobserved failures counted as proven: red 4. Each mutant is 1 edit in the scratch copy; one surviving mutant (the first `mp17-scrub`, whose canary was itself token-shaped) was caught by strengthening the test, then red.
Pre-check[MP16]: 3b64dd3a uv run --directory <worktree> pytest tests/test_imap_mailbox.py tests/test_oracle_mailbox.py -k "mp16 or invite_mail_arrives" -> 4 passed t=6 blobs=tests/test_imap_mailbox.py:3b4132f,tests/test_oracle_mailbox.py:e7f52f6
Pre-check[MP17]: 3b64dd3a uv run --directory <worktree> pytest tests/test_imap_mailbox.py tests/test_oracle_mailbox.py -k "not mp16" -> 34 passed t=17 blobs=tests/test_imap_mailbox.py:3b4132f,tests/test_oracle_mailbox.py:e7f52f6
Lint: 3b64dd3a `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 8).
Metrics: start=2026-10-19T08:30:00Z end=2026-10-19T09:30:00Z wall_min=60 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=16 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=16 defects_unit=0 defects_6c=0 tests=37 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_imap_mailbox.py tests/test_oracle_mailbox.py tests/test_oracle_registry.py tests/test_cross_role_runner.py tests/test_cross_role_schema.py` -> expected: 93 passed.
- `git diff --name-only cff3ffe6..3b64dd3a` -> expected: the 6 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP16 | only EXAMINE and BODY.PEEK reach the server; no `\Seen` side effect | tests/test_imap_mailbox.py::test_mp16_wire_commands_are_examine_and_peek_only | `readonly=True` -> `False`; `BODY.PEEK[]` -> `BODY[]` | green on tree; red on both (1 failed, 21 passed each) |
| MP16 | a write verb cannot be sent even by mistake | tests/test_imap_mailbox.py::test_mp16_a_write_verb_cannot_be_sent_even_by_mistake | verb guard -> `if False` | green; red (1 failed) |
| MP17 | bounded by cap, recipient, since-time | tests/test_imap_mailbox.py::test_mp17_message_cap_keeps_the_newest_and_says_it_capped, ::test_mp17_recipient_bounds_the_search_and_a_server_that_ignores_it_is_filtered, ::test_mp17_since_time_bounds_the_search_and_older_mail_is_dropped | drop each bound | green; red on each |
| MP17 | credential-shaped token recorded as present, never its value | tests/test_imap_mailbox.py::test_mp17_each_token_shape_is_recorded_as_present_and_its_value_is_stored_nowhere | disable the token masking loop | green; red (6 failed) |
| MP17 | subject/body pass `Redactor.scrub` | tests/test_imap_mailbox.py::test_mp17_the_mailbox_password_and_addresses_never_survive_in_a_stored_subject | `redactor.scrub(subject)` -> `subject` | green; red (1 failed) |
| SA9 | an unreadable mailbox is `unavailable`, never "no message" | tests/test_oracle_mailbox.py::test_e2e_a_broken_login_is_never_read_as_the_mail_being_absent | return "no match" instead of raising | green; red (2 failed) |

## Live browser evidence
Not UI-touching - no surface changed: only schema, source and stage modules plus tests; no route, template or static asset.

## Status: checked-PASS build leg (qa/verdicts/t212-mailbox.md; MP34 live leg credential-gated, goal task stays open)
