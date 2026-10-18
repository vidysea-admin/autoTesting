# Verdict - t212-mailbox (T-212, G11-6)

Cycle checked: 0
Date: 2026-10-18 (checker, Mode A, bound to D:/autoTesting/.worktrees/t212-mailbox)
Checked state: code 3b64dd3a (HEAD 95ffd971 adds only the manifest). Base cff3ffe6 = `git merge-base HEAD int/1017` (verified).

## Plan
Tier M (new external-mailbox source adapter, 3 src + 3 test files, additions only). No UI, no persona walk. Checks: (1) re-run the manifest pytest, (2) MPI3 diff check, (3) read MP16 and MP17 against the code and the wire-level fake, (4) one falsification per criterion in a copy outside the repo, (5) own counterexample probe of the token detector, (6) step 4c diff-scope read. MP34 is credential-gated, not claimed, not a FAIL.

## Block
VERDICT: PASS
SCOREBOARD: 3/3 criteria met (MP16, MP17, MPI3), 2/2 invariants hold (MPI2 synthetic fixtures, MPI5 keys only and read-only mailbox); MP34 [GATED] not claimed
TIER: M (new read-only source adapter plus oracle; no auth, tenancy or data-write trigger; Dual check: no accepted)
FAILURES: none
CAPABILITY-COVERAGE: 4 falsifying edits reproduced by my own copies (MP16 x2, MP17 x2); the other manifest rows' tests re-ran green inside the 93; floor (1 per criterion) met
LIVE-BROWSER: not-applicable (no route, template or static asset changed)
ISSUES-WRITTEN: AT-1301, AT-1302, AT-1303 (all low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: MP16 and MP17 are evidenced by commands I ran: the loopback fake IMAP server records the verbs on the wire (LOGIN, EXAMINE, UID SEARCH, UID FETCH with BODY.PEEK, LOGOUT, plus imaplib's own CAPABILITY; none of STORE/COPY/MOVE/EXPUNGE/APPEND/DELETE/SELECT; `seen` empty), and the since/recipient/cap bounds and token handling hold. The detector gaps below are heuristics the manifest discloses (judgement call 4), not a miss of the contract's fixture shapes, so they are non-blocking ledger rows.
Metrics: start=2026-10-18T20:27:00Z end=2026-10-18T20:39:00Z wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=720 mutants=2 defects_unit=0 defects_6c=0
slow: protocol read (1261-line checker SKILL.md) plus source read, about 7 of the 12 min; tests and the four copies took about 2 min. Filed as AT-1303.

## Evidence
1. Verify command 1 (own run, worktree venv, TMP/TEMP=D:/autoTesting/.work/tmp): `uv run pytest tests/test_imap_mailbox.py tests/test_oracle_mailbox.py tests/test_oracle_registry.py tests/test_cross_role_runner.py tests/test_cross_role_schema.py` -> 93 passed in 15.3 s (matches the expected 93). `uv run ruff check src tests scripts` -> All checks passed. I did not reuse the pre-check lines; I re-ran.
2. Verify command 2 and MPI3: `git diff --name-status cff3ffe6..3b64dd3a` -> 6 additions only (schema/mail_observation.py, sources/imap_mailbox.py, stages/oracle_mailbox.py, tests/imap_fake.py, tests/test_imap_mailbox.py, tests/test_oracle_mailbox.py). `schema/multi_role_enums.py` and `schema/enums.py` are not in the diff. MPI3 holds.
3. MP16 read: `src/autotester/sources/imap_mailbox.py:73-117` `_Session` is the only door to the server; `_note` (:80-83) raises on any verb outside `ALLOWED_COMMANDS` (:49) with an explicit raise, not `assert`; `examine` (:92-96) calls `select(..., readonly=True)`, which imaplib sends as EXAMINE; `fetch` (:107-112) sends `(BODY.PEEK[]<0.262144>)`. The wire test (`tests/test_imap_mailbox.py:53-66`) reads the commands the SERVER received, not the reader's own log, and asserts `server.seen == set()`.
4. MP17 read: bounds at `imap_mailbox.py:98-105` (SINCE and TO in the search), :171 (newest `max_messages`, `capped` flag), :137-141 (local recipient and date filter), :60 (TLS with certificate checks), :191 (timeout). A body is never a field (`schema/mail_observation.py:72-82`); subject and body pass `Redactor.scrub` (:146) before `mask_credential_tokens`; the stored subject also passes `mask_pii` (:150). `MailQuery` caps `max_messages` at 50 and validates the recipient pattern.
5. SA9 honesty: unavailable reasons come from the exception type only (:199-204); `stages/oracle_mailbox.py:51-63` `observation_from_read` raises for an unread mailbox or a capped read with no match, so a failed read is never absence. grep for `environ|getenv|load_repo_env|dotenv|open(` in the three source files -> no hits. Credentials arrive as a mapping.
6. Falsification (floor 1 per criterion, plus one extra each, inside the .9-4 cap of 3). Copies of `git archive 3b64dd3a` under `C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/mut_*`, python importing from the copy (path printed), runner `.../scratchpad/falsify.py`. Each named node was green in its copy first, then one edit:
   - MP16 `readonly=True` -> `False`: green (1 passed) -> RED `test_mp16_wire_commands_are_examine_and_peek_only` (1 failed).
   - MP16 `BODY.PEEK[]` -> `BODY[]`: green -> RED, same test (1 failed).
   - MP17 token masking disabled (`if sum(hits):` -> `if False:`): green (5 passed) -> RED `test_mp17_each_token_shape_is_recorded_as_present_and_its_value_is_stored_nowhere[numeric code]` (first failure, -x).
   - MP17 cap removed (`newest = found[-query.max_messages:]` -> `found`): green -> RED `test_mp17_message_cap_keeps_the_newest_and_says_it_capped`.
7. Own counterexample probe of `mask_credential_tokens` (`.../scratchpad/probe.py`). Detected: "verification code is 482913", "Code: 482913", "OTP 123456", "PIN: 7731", "temporary password is Xk9#mP2qLw", "Password: Welcome2026!", "temp pass is hunter22", a URL `?token=` value, a 24-character URL path token. Correctly not flagged: "Invoice 2026101912", "Call 9876543210", plain text. MISSED: "482913 is your verification code" (number before the cue) and "password: abcdefghij" (all lowercase). Both are disclosed heuristic limits; the body is never stored, so only the stored subject could carry such a value; the contract's fixture shapes all pass. Filed as AT-1301 (low), not a FAIL. A second low row, AT-1302: the recipient bound is a substring match (`imap_mailbox.py:128-130`).
8. Step 4c diff scope: all 6 files are additions; no function, class, export, route, test or config key is deleted or renamed; no file outside "What changed". The manifest's CORE-REQUEST (doctor exemption for `oracle_*::run`) is not applied in this unit, and `run = mailbox_findings` (`oracle_mailbox.py:92`) is a correct registry entry point.
9. Design rules by inspection: largest new file 205 lines, no function over 50. `autotester doctor` was not re-run by me (the manifest reports 2 stale-generated MAP/SNAPSHOT violations for the merge-queue owner; no criterion names it).

## Not checked
MP34 (live mailbox read) is credential-gated (IMAP host, user and password key names and values from Umesh). The production `ssl_connector` was read, not run against a real server. No full suite (not required at tier M, rule .13).
