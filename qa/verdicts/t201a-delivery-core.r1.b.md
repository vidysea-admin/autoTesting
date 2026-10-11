# Verdict - t201a-delivery-core, repair coordinator B (blind dual check, fix cycle 1)

Cycle checked: 1
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Head judged: 7dd225d4 (code 477f4089), `Repair base: 9b6d44c1` (verified ancestor of HEAD; whole-unit base 6504de03).
Checkpoint: qa/checkpoints/t201a-delivery-core.r1.b.md. Evidence: qa/evidence/t201a-delivery-core-r1-B/ (scripts `h.py`, `fal.py`, `mkmut.py`, `stray.py` and the JSON outputs).
Emphasis of this coordinator: behaviour under real concurrency and a real loopback SMTP server. The other coordinator reads code and runs the suite; I read neither its verdict nor its evidence. No earlier verdict, checkpoint or evidence of this unit was opened.

## Check plan (step 0)

Tier L, dual-trigger security (`email.py:149`, unchanged by the repair). Signals: concurrency/race (L), security. Checks: (1) send-once matrix through public `deliver_once` against a real in-process SMTP sink on 127.0.0.1; (2) multi-process x multi-thread concurrency, 200 rounds, with and without clock skew; (3) stale-close race with real timing; (4) failure paths and over-long ids; (5) `report_url` table; (6) repair diff read in full (9b6d44c1..7dd225d4) plus whole-unit scope scan; (7) ruff, doctor, size rules, affected tests; (8) one falsification per repaired item in throwaway copies. No full suite (unit is L via security, but the other coordinator owns it: A 1 + B 1 is the policy; I was told not to run it). No UI surface changed: Mode D not applicable. No SERIAL needed.

Workspace: `git archive 7dd225d4` extracted to a uniquely named folder on C: with its own venv; `autotester.__file__` printed and asserted inside that copy on every run. Only `example.com` addresses, only 127.0.0.1, no `.env` read.

VERDICT: PASS
SCOREBOARD: 3/3 failed items repaired and re-evidenced (F1 C11, F2 C8, F3 C10); criteria whose inputs the repair touched (C6, C8, C10, C11, C12 test lines) hold; invariants none touched beyond the above.
TIER: L (security dual-trigger email.py:149; concurrency/race in inbox.py; unchanged tier)

## Observation tables (all from my own runs)

| # | Probe | Result |
|---|---|---|
| 1 | Send-once matrix: 20 run ids x 26 user ids = 520 pairs (dotted prefixes, `__`, `_`, `.`, `-`, `Alice`/`alice`/`ALICE`, `x_`/`x_0`, 64-char ids), 4 passes (forward, reverse, 2 shuffles) = 2080 calls to `deliver_once` | 520 distinct keys (520 case-folded); exactly 520 messages at the sink, 1 per address, 0 suppressed, 0 exceptions; `records_for_key` returned exactly its own single row for all 520; `records_for_run` returned exactly its own 26 rows for all 20 runs; 520 record files, 520 attempt files, no stray names |
| 2a | Concurrency, no skew: 6 processes x 4 threads, 200 rounds, 6 near-colliding keys per round (`rnN`/`rnN.1` x `u`/`u.1`/`U`), 28 800 `deliver_once` calls over real sockets, barrier per round | 1200 keys, 1200 messages, exactly 1 per key, 0 exceptions, 1200 record files, 0 tmp leftovers, all JSON parse, all `sent` |
| 2b | Same with 50% of threads on a clock +11 min (they close live attempts as stale) and 0-20 ms server latency | 1200 keys, 1200 messages, exactly 1 per key, 0 exceptions, 0 torn or duplicate record, 0 tmp; final: 826 `sent`, 374 `failed: outcome unknown` (mail did leave; see P2) |
| 3 | Stale close, real timing, separate processes, sink stalls A 3 s inside DATA, B starts at 1 s | S1 B(+11 min) closes while A sends: sink 1 message, A returns the on-disk `failed (outcome unknown)` record, no exception, follow-ups at +1 h/+1 d/+7 d send nothing. S2 A skewed, B normal: B returns None, record `sent`, 1 message. S3 A's connection dropped after the stall: 1 message at the sink (received before the drop), one `failed` record, no exception. S4 attempt 2 after a real refusal, A stalls, B closes: 1 message, records = attempt 1 refusal + attempt 2 `outcome unknown`, no exception. Both can never send: the claim is a hard link, atomic |
| 4 | Failure paths via `deliver_once` + `SmtpAdapter` (timeout 1 s) | RCPT refused, drop mid-DATA, drop after DATA, timeout, connection refused, a non-`TransportError` raised by the transport: each becomes one `failed` record with a class name only (`SMTPRecipientsRefused`, `SMTPServerDisconnected`, `TimeoutError`, `RuntimeError`); no exception out; the recipient address appears in no record or attempt file |
| 4b | Over-long ids | `delivery_key` raises `ValueError` and it propagates out of `deliver_once` (no mail, no record) when the encoded key exceeds 200. Reproduced: run of 63 capitals + user with 1 capital, 32+32 capitals, 64 capitals either side. Boundary: encoded parts total 191 fits (key length 200), 192 does not. Product run ids are `run-{ulid}` (`ui/routes_runs.py:220`), at most 56 encoded characters, so with any valid 64-char user id the key is at most 193: not reachable from the queue (P1) |
| 5 | `report_url` (50 refuse, 12 accept forms) | Refused as required: `//host`, `//host/a`, `///host`, `https://x//host`, ports 0, 65536, 99999, 100000, `000000`, backslash forms, `\t`, space, userinfo `@` (also `x.test:80@evil.test`), `%2F%2Fhost`, `https:/x`, `[::1]`, `javascript:`, `?`, `#`, CR/LF, U+2028, NUL. Accepted as required: `/`, `/a//b`, ports 1, 65535, `00080`, `/a/../b`. Two forms accepted that I had guessed refused: `/..//x` (a legitimate site-relative path, my expectation was wrong) and `https://x.test:١٢٣/r` (non-ASCII digits satisfy `\d`; a broken link, not a redirect: P4) |
| 6 | Repair diff read in full (src: `inbox.py`, `schema/delivery.py`; tests: three files; manifest) and whole-unit scan (13 files) | Every file is in the manifest's "What changed" or its tests; nothing deleted or renamed in src; no assertion weakened (tests only added); `email.py` untouched, so the dual-trigger line 149 still holds |
| 7 | `ruff check src tests scripts`; `autotester doctor`; sizes; affected tests | ruff: All checks passed. doctor: clean. Longest files: `tests/test_delivery_failure.py` 272, `tests/test_delivery_smtp.py` 242 (all <= 300); no function over 40 lines. `pytest` on the three delivery test files in the copy: 97 passed in 5.45 s (matches the builder's pre-check `Pre-check` line, reproduced, not reused) |

## Falsifications (one per repaired item; each in its own throwaway copy of `src`, green in the copy before, red after; probe `fal.py`, `autotester.__file__` asserted inside each copy)

| Item | Edit in the copy | Green copy | After |
|---|---|---|---|
| F1 key | `_encode_part` returns `safe_id(value)` unchanged | F1-key True | F1-key False (separator-spelling and case pairs collide); other 4 checks True |
| F1 matching | `records_for_key` regex `\.\d+\.json` -> `\..*\.json` | F1-matching True | F1-matching False only (`records_for_run`/prefix collisions); other 4 True |
| F2 | `except FileExistsError` after `log.append` in `deliver_once` -> `except ZeroDivisionError` | F2 True | F2 False (first worker raises `FileExistsError`); other 4 True |
| F3 slashes | `(?!/)` removed from `_URL` | F3-slashes True | F3-slashes False only |
| F3 ports | range check replaced by `False` | F3-ports True | F3-ports False only |

Each mutant reddens exactly the check named for it. These are independent of the builder's tests (my probe uses its own assertions).

FAILURES: none

## PROPOSED-ISSUE lines (none blocks; the maker mints ids)

PROPOSED-ISSUE: {"severity":"low","feature":"team-test-button","title":"delivery_key raises ValueError for valid but very long mixed-case ids and it propagates out of deliver_once","evidence":"src/autotester/delivery/inbox.py:71-73 and :167; h.py longids: run of 63 capitals + user with 1 capital -> ValueError out of deliver_once, no mail, no record. Not reachable from the queue: run ids are run-{ulid} (ui/routes_runs.py:220), max encoded key 193 with any 64-char user id","fix":"catch ValueError in deliver_once and return a failed record, or cap run/user id length so the encoded key always fits (e.g. SAFE_ID 64 -> 48 for ids that reach delivery)"}
PROPOSED-ISSUE: {"severity":"medium","feature":"team-test-button","title":"a clock-skewed stale close records 'failed (outcome unknown)' for a mail that was delivered","evidence":"h.py concurrent_skew: 374 of 1200 keys ended failed/outcome unknown while the sink received exactly 1 message for each; stale.json S1. No duplicate send, the text is hedged, but the run page would show failure for delivered mail. Builder disclosed this residual","fix":"let the first worker's true outcome win (e.g. write the outcome to a second per-attempt 'outcome' file read by the latest-state reader) or base staleness on file mtime of the claim, not on the caller's now"}
PROPOSED-ISSUE: {"severity":"medium","feature":"team-test-button","title":"a send that reached the server but whose reply was lost is retried: up to 4 copies","evidence":"h.py failures: sink drop_after_data (message fully received, connection closed before 250) -> failed/SMTPServerDisconnected, retried through 4 attempts, copies_at_sink 4; same for a read timeout after DATA. Known P7, unchanged this cycle","fix":"state in the contract that C11 is at-most-once per attempt, or stop retrying after an ambiguous failure (error after DATA was sent)"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-test-button","title":"records_for_run raises ValidationError on a stray file whose name looks like another user's record","evidence":"stray.py: records/<key>.01.02.json containing {} -> records_for_key returns [] but records_for_run('run-1') raises pydantic ValidationError (src/autotester/delivery/inbox.py:121-122 validates every name-matching file)","fix":"skip and report unparsable record files instead of raising, so one bad file cannot blank the run page"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-test-button","title":"report_url port accepts non-ASCII digits","evidence":"url.json: https://x.test:١٢٣/r is accepted (schema/delivery.py _URL uses \\d)","fix":"use [0-9] in the port group"}

CAPABILITY-COVERAGE: 5/5 repaired-item falsifications reproduced by me (key, matching, race, slashes, ports).
LIVE-BROWSER: not-applicable (changed paths are src/autotester/delivery/*, src/autotester/schema/delivery.py and tests; no UI surface)
ISSUES-WRITTEN: none (dual check: findings above only; no ledger write, no manifest flip, no merge, no push)
EXECUTOR: claude-sonnet-subagent (manifest Executor: claude-sonnet-subagent maker build subagent; checker is a separate fresh subagent)
EXPLANATION: The three repaired items hold under real sockets and real processes: across 2080 matrix calls and 57 600 concurrent calls there were exactly as many messages as keys, no suppression, no exception, no torn record, and a real stalled-send race never produced a second message or an exception in the first worker. What remains are disclosed residuals (outcome-unknown shown as failed, ambiguous-failure retries, an unreachable ValueError for hand-fed over-long ids), all non-blocking under the evidence-to-block rule. The wall time includes one 8.5-minute matrix run that was slow only because the first version of my probe let smtplib resolve the host name for every connection (fixed in the probe, product untouched).
Metrics: start=2026-10-11T19:35:00Z end=2026-10-11T20:05:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=200 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1800 mutants=0 defects_unit=0 defects_6c=0
slow: matrix first run 8.5 min (probe's own per-connection DNS lookup, rewritten); start time is an estimate within a few minutes (no clock was read at dispatch)
