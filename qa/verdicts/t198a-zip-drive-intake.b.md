# Verdict B -- t198a-zip-drive-intake (dual check, seat B, blind)

Cycle checked: 0
Head checked: 894549ee (product sha 642575ce; master 81f63ce9 merged at 76eba8c1). Verified with `git rev-parse --short=8` on `wave/t198a-zip-drive-intake` = 894549ee.
Policy-Version: proportional-verification/2026-10-10.9 (pinned). Date: 2026-10-11. Fix cycle 0. Resume 0 of 2; Retry 1 (API network error, no finding).
Bound to D:/autoTesting. Did not read any seat A verdict, checkpoint or evidence.
Evidence: qa/evidence/t198a-zip-drive-intake-B/ (scripts/, results/). Checkpoint: qa/checkpoints/t198a-zip-drive-intake.b.md.

## Check plan
Tier L, security class (untrusted archive, upload stream, Drive link, gate seam; dual-trigger in the manifest). Signals: logic (13 test files re-run once, one falsification per criterion in a copy), security (own hostile-input scripts against the real code paths, ~45 zip cases, ASGI upload and Drive-link attacks, gws seam, concurrency and fault injection), data write (registration atomicity, cleanup). No full suite and no browser (seat A owns both). No real Drive call; the unit's fake runner and a local recorder script stood in for `gws`. TI10 is declared HELD on T-204: judged as held, only the seam proved.

## Result
VERDICT: PASS
SCOREBOARD: 10/11 TI criteria met (TI1-TI9, TI11), HO30, HO32, HO33 met; TI10 HELD on T-204 (seam proved, not claimed met).
TIER: L (security). Not raised, not lowered.
FAILURES: none at >80% confidence against a stated criterion (findings below are PROPOSED-ISSUE only).
LIVE-BROWSER: not-applicable to this coordinator (seat A owns the browser check)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Per-criterion (verify commands re-run once by me on 894549ee)
One pytest process, worktree .venv, `-p no:xdist -p no:cacheprovider`, 13 named files (union of the builder commands): 297 passed, 1 warning (21.6 s). The builder Pre-check lines carry no `t=`/`blobs=`, so not reusable under .9-5; I re-ran.
Falsification: one edit per criterion in its own copy of src/tests under scratch, PYTHONPATH proven into the copy, green before, red after (results/falsify.out).
| C | Falsification (copy) | green -> red |
|---|---|---|
| TI1 | `vet_member_name` stops normalising backslash | 65 passed -> 12 failed |
| TI2 | ratio check forced off (`if False`) | 9 passed -> 1 failed |
| TI3 | non-video members registered instead of skipped | 22 passed -> 4 failed |
| TI4 | staging/target name built from the member name | 40 passed -> 11 failed |
| TI5 | `overall_status` returns OK when any member registered | 22 passed -> 4 failed |
| TI6 | `add_source` before `_place` in `commit_video` | 5 passed -> 1 failed |
| TI7 | md5 compare disabled | 39 passed -> 3 failed |
| TI8 | `classify_gws_failure` collapsed to one kind | 39 passed -> 8 failed |
| TI9 | limit hard-coded to 2 GiB in `GwsDrive` | 60 passed -> 2 failed |
| TI10 seam | `recheck` removed in `_run_job` | 12 passed -> 2 failed (HELD; only the seam) |
| TI11 | `uploaded_by` taken from a form field | 20 passed -> 1 failed |
| HO30 | stream limit check disabled in `_Reader._data` | 20 passed -> 3 failed |
| HO32 | host check loosened to `startswith("drive.google.com")` | 33 passed -> 3 failed |
| HO33 | gws byte watcher limit x10,000 | 10 passed -> 1 failed (62.7 s) |
14/14 falsifications red on the intended assertions; none was an import failure.

## Attack families (my own scripts, scripts/ and results/)
- Zip: ~45 hostile archives. All refused cleanly with nothing written outside the project root, sentinels intact, no staging or lock left: traversal (/ and \ and mid-path), absolute, drive-letter, UNC, ADS, reserved device names, NUL byte, bidi and control characters, symlink/device/fifo/socket entries, nested archives (name and signature), encrypted member, 1028:1 ratio bomb refused before extraction, understated and overstated central-directory sizes, over-cap entries, archive, total and video count, local-vs-central name mismatch. Per-file cap and bad-CRC member leave the others registered with status partial; garbage, empty and truncated inputs give one failed row. Duplicate names register as distinct sources; identical bytes dedupe. Zip64 works. Skipped: `.env`, `.exe`, `.ps1`, `.pdf`, no extension, trailing dot/space. Odd names (HTML, unicode, 5000 chars) register with a label only and never reach a path.
- Upload stream: gate refusal reads 0 body bytes (upload and Drive routes). An endless body, with or without a lying Content-Length, stops at limit + overhead (5,308,607 bytes read) with 413 and no row. Exactly 5 MiB accepted; 5 MiB + 1 gives 413; a real 6 MiB body gives 413 and 0 rows. Truncated body, oversized part header, bad content types give 400. Form fields `uploaded_by`/`origin`/`sha256`/`path`/`id` are ignored (stored `uploaded_by` is the gate identity). Cross-origin and hostile Host give 403 before any body is read. Slug and job-id attacks give 400/404. No unescaped `<script>`/`<img>` on the sources page, zip result, refusal pages or job page. Defect found: boundary longer than 256 characters gives HTTP 500 (PROPOSED-ISSUE 2).
- Drive link: non-https, look-alike hosts, userinfo, odd ports, backslash, `%2F`, shell metacharacters, duplicate `id`, IDN and homoglyph ids, `169.254.169.254` all refused 400, not echoed, no job, no Drive call. Through the job route: gate recheck refusal ends `refused` with no `open` call and no row; typed PERMISSION_DENIED shows a fixed message; gws error text with `<script>` and a canary never reaches a report. Real `SubprocessGwsRunner` with a local recorder: argv is a list, the id appears only inside the `--params` JSON, injection ids refused, marker file not created. Folder listing with hostile ids/names: bad ids refused, no metacharacters in argv, label is the basename only. Wrong md5 and short read both give failed, 0 rows, no leftovers, downloads closed.
- Concurrency and cleanup: six same-name same-bytes uploads give 1 new row; six different-bytes give 6 rows, every row has its file with matching sha256. Fault injection (`add_source` raising on member 2) leaves 2 rows, 2 files, no staging; a re-run converges to 3; an orphan file is swept by the next intake. Job-file finding (PROPOSED-ISSUE 3).
- Gate seam: `recheck` runs in the worker before `intake_drive`; a refused recheck stops the job (falsification TI10 seam confirms the test notices). The default gate is open until T-204 (already in the manifest).
- Resource: the 1000-entry cap is applied only after `zipfile.ZipFile` parses the whole central directory (PROPOSED-ISSUE 1).

## Findings
PROPOSED-ISSUE: {"severity":"medium","class":"security-hardening","title":"Zip entry cap applies only after the full central directory is parsed","detail":"expand_zip checks len(infos) > max_entries after zipfile.ZipFile() has built every ZipInfo. Measured: 300,000 entries (29.8 MB zip) took 25.9 s and raised peak working set 97 -> 270 MB (~575 B/entry); a zip64 archive near the 2 GiB default limit could hold ~20M entries (several GB). Reachable by anyone who passes the gate (open until T-204). TI2 bytes-written criterion is met; this is memory/CPU only.","file":"src/autotester/sources/zip_intake.py","fix":"read the EOCD/zip64 total-entries count first and refuse before parsing","evidence":"qa/evidence/t198a-zip-drive-intake-B/results/misc-attack.json"}
PROPOSED-ISSUE: {"severity":"low","class":"robustness","title":"Multipart boundary over 256 characters gives HTTP 500","detail":"MultipartParser(...) is constructed outside the try block in stream_upload, so FormParserError escapes. 257 and 5000 character boundaries give a 500 page (no stack trace leaks); 256 gives 400.","file":"src/autotester/ui/upload_stream.py","fix":"catch FormParserError around construction and return 400","evidence":"results/drive-attack.json (boundary_257, boundary_5000)"}
PROPOSED-ISSUE: {"severity":"low","class":"robustness","title":"Drive job file write can fail on Windows while the page polls","detail":"save_job retries os.replace 5 times; with one writer and one polling reader, 3 of 400 writes still raised PermissionError and load_job returned None 94 times (job page then reads as 404). The fixed per-job .tmp name also breaks a second writer (not reachable today).","file":"src/autotester/sources/drive_jobs.py","fix":"unique tmp name plus a longer or backoff retry; let load_job retry once on a transient miss","evidence":"results/misc-attack.json (job_single_writer)"}
PROPOSED-ISSUE: {"severity":"low","class":"observation","title":"Drive download limit is polled (0.1 s) rather than limit-plus-one-chunk; gws stdout/stderr tempfiles are not size-watched","detail":"TI9 wording says the cap holds at limit plus one chunk; the implementation kills the process on the next 0.1 s poll, so the overshoot is time-bounded, not chunk-bounded. GwsDrive also reads read_max_upload_bytes() with no root argument (consistent only if process root equals env root).","file":"src/autotester/sources/gws_runner.py","evidence":"code read; HO33 falsification red"}
PROPOSED-ISSUE: {"severity":"low","class":"observation","title":"Reserved name with trailing space (LPT1 .mp4) passes vet_member_name","detail":"Harmless today because the member name never reaches a path (generated m000000.mp4 names); noted for defence in depth.","file":"src/autotester/sources/zip_names.py","evidence":"results/zip-attack.json (h_lpt1_sp)"}
PROPOSED-ISSUE: {"severity":"low","class":"observation","title":"Echo of builder-listed gaps","detail":"Two surviving mutants (central-directory per-file size pre-check, HEADER_CAP), no cap on concurrent Drive worker threads, open default gate until T-204, and the ungated drive_job_page GET (TI10 held) are already in the manifest; I confirm them and add nothing new.","evidence":"manifest t198a-zip-drive-intake.md"}

Metrics: start=2026-10-11T00:29:57Z end=2026-10-11T00:58:00Z wall_min=28 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=14 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1680 mutants=14 defects_unit=0 defects_6c=0
