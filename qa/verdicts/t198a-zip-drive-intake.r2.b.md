# Verdict - t198a-zip-drive-intake, seat B (blind coordinator), repair check, fix cycle 2

Cycle checked: 2
Head checked: dba80100 (`git rev-parse --short=8 wave/t198a-zip-drive-intake`); product sha 39533108 (src unchanged since a765c4dd). Repair base 3918a8aa, checked as an ancestor.
Policy-Version: proportional-verification/2026-10-10.9. Tier L, dual check (dual-trigger line present in the manifest). No full suite run (seat A owns it).
Date: 2026-10-11.

## Check plan
Failed criterion list from cycle 1 (one item): a zip with the UTF-8 flag and a non-UTF-8 name made the stdlib raise `UnicodeDecodeError` in `expand_zip`, a 500 on the upload route; the class "no archive may make `expand_zip` raise, answer 5xx, leave a staged file or a source row without its file".
Steps: (1) repair diff in full + whole-unit scope scan; (2) the failed criterion's own tests; (3) one falsification in a throwaway copy; (4) own hostile-archive generator, `expand_zip` + upload route; (5) catch-site audit (BaseException classes, our-bug surfacing, containment); (6) entry points + upload limits (one Sonnet read-only sub-checker, text only).

## Result
VERDICT: PASS
SCOREBOARD: C-cycle1-failure (no archive may make expand_zip raise / route 5xx / leave staging or a row without its file) met; TI1-TI6 and TI9 inputs untouched by the repair and keep their recorded results; TI10 is HELD on T-204 as the manifest says (not judged met, not a FAIL of this repair).
TIER: L (security: `zip_names.py:77 ensure_inside`, `zip_intake.py` `expand_zip` untrusted archive intake; cited in the manifest dual-trigger line)

### 1. Repair diff and scope
- `git log 3918a8aa..dba80100`: fix commits a765c4dd (product), fbb7ddff (style), 39533108 (test), dba80100 (manifest); 388bd5a0 is the merge of master 09828f2d (qa verdicts/evidence only).
- `git diff 3918a8aa..dba80100 -- src tests scripts docs .env.example pyproject.toml uv.lock`: exactly 4 files: `src/autotester/sources/zip_intake.py` (+36), `tests/test_zip_intake_register.py` (+69), `tests/test_ui_intake.py` (+11), `tests/zip_fixtures.py` (+12). All inside the unit's declared scope; nothing removed (only `-` lines: two import lines and one return restructure in `_inflate`). Upload-limit files (`upload_stream.py`, `intake_upload.py`, `routes_intake.py`, `routes_sources.py`) are byte-identical across 3918a8aa..dba80100.
- Read in full: `_Unreadable`, `_NAMED`, `_guarded` (`zip_intake.py:138-157`), `_inflate` (:160-167), new handler (:209-210), the `expand_zip` constructor catch (:261-273). Only the stdlib calls that parse/inflate untrusted bytes are inside a guard: `ZipFile(archive)`, `zf.open(info)`, `raw.read(n)`. `_classify`, `ensure_inside`, `copy_bounded` writing, hashing and `commit_video` are outside every guard.

### 2. Failed criterion's own tests (re-run by me)
`uv run --project <worktree> pytest -p no:xdist -o addopts= --rootdir=<worktree> tests/test_zip_intake_register.py tests/test_ui_intake.py tests/test_zip_intake_atomic.py tests/test_zip_intake_limits.py tests/test_zip_intake_names.py` -> 133 passed in 11.79 s (includes `test_ti5_utf8_flag_with_an_invalid_utf8_name_...`, the four-exception member test, the fuzz, and the upload-route case).

### 3. Falsification (one per repaired criterion), throwaway copy outside the tree
Copy of src/tests/scripts under the scratchpad (import path checked: `autotester.sources.zip_intake.__file__` is the copy). Selection `-k "utf8 or no_mutation or invalid_utf8"`: green before (3 passed); after deleting the `except MemoryError: raise / except Exception:` block in `expand_zip`: 2 failed (`UnicodeDecodeError` out of `expand_zip` and out of the upload route, `zipfile.py:1430`). Copy deleted. (First attempt used `python -I`, which ignores PYTHONPATH and would have imported the bound tree; discarded and redone without `-I`, import path printed.)

### 4. Hostile archives (my own crafter `zipcraft.py`: struct-level, not the stdlib writer, not byte flips)
1773 distinct archives, each run through `expand_zip` (in-process, fresh store) AND through `POST /projects/demo/sources/upload` (TestClient). Invariants per case: no exception from `expand_zip`; route status < 500 and not 403/404/405/422, no "Traceback"; no file left in `.work/intake` or `.work/uploads`; no new file outside `sources/`; every source row's file exists, lies under `sources/`, and its sha256 matches. Result: 1773/1773 passed on `expand_zip` (18 m 32 s) and 1773/1773 on the route (12 m 04 s). Evidence: `qa/evidence/t198a-zip-drive-intake-r2-B/`.
Classes (count of archives):
| class | n | what |
|---|---|---|
| UTF-8 flag + invalid UTF-8 / surrogate-bytes / overlong names, in central only, local only, both | 15 | utf8 failed (archive-level) |
| general-purpose flag bits, 21 values x (cd+local, cd only, local only) | 63 | encrypted/strong/masked/data-descriptor/0xFFFF |
| extra fields: zip64 short/empty/full/sentinel, length overruns, truncated headers, 2000 fields, 65 KB, cd/local/both x sentinel sizes | 66 | |
| EOCD: every field x boundary values, comment-length lies, fake EOCD/zip64 locators in comment, no CD, prefix/tail garbage | ~70 | |
| CDH and LFH: every field x 8-9 boundary values x 4 members, bad signatures, version-needed/made 13 values each | ~880 | |
| compression methods 1-99 and 0xFFFF x 6 garbage bodies; LZMA props/dict-size 0..0xFFFFFFFF x 5 pb x 5 prop sizes | 144 + 200 | |
| deflate bomb (understated and honest size), stored size disagreements (cd only / both), zero length, empty / 1-byte / sig-only files | ~30 | |
| names: 42 hostile names (empty, `/`, `..`, drive letters, UNC, ADS, device names, NUL positions, 65535-byte, 30000-segment, surrogate bytes, bidi) x flag 0/0x800 x stored/deflate; duplicates; modes (symlink/device/fifo/socket/dir) x 4 version-made | ~230 | |
| nested zip by name / by content (stored, deflate) / gz / 7z / short head | 7 | |
| header offsets: out of file, 0, into central directory, all members at one offset (overlap bomb) | 16 | |
| encrypted: flag, AES, local-only, central-only, strong | 5 | |
| ratio / 1200 entries / 30 videos / 900 dirs | 4 | |
The generator has teeth: against the unfixed code (3918a8aa `zip_intake.py` in a scratch overlay) 19 of the 1773 raise `UnicodeDecodeError` (the utf8 class); against the fixed code 0 raise. Outcomes on the fixed code are sane (failed / partial / ok per class; table in `diff.py` output).
Two targeted probes (`probe2.py`, `probe4.py`): (a) local header name invalid UTF-8 while the central name is valid ASCII with flag 0x800: unfixed code RAISES `UnicodeDecodeError` from `zf.open` (a second real path, member level, which the builder's tests only reach by monkeypatch); fixed code returns `partial`, member `failed` "corrupt member (the data could not be read)", the other member registered; through the route: 200, "Partial" page, 1 row, no staged file. (b) valid LZMA stream with header dict size up to 0xFFFFFFFF: registers fine on both versions, no MemoryError on this host.
Findings in this class: none.

### 5. Catch sites (`probe3.py`, patched in-process)
KeyboardInterrupt, SystemExit and MemoryError raised from `ZipFile(...)` and from `ZipExtFile.read`: all six propagate out of `expand_zip`, staging 0 files, 0 rows. A `ValueError` from `zf.open`: member `failed`, run `failed`, nothing registered. Our own code: `commit_video` -> RuntimeError, `copy_bounded` -> ValueError, `ensure_inside` -> `UnsafePath`, `_classify` -> TypeError: all four propagate (not turned into a failed row and not into a pass), staging cleaned in each. So the broad catches cover only the stdlib calls and do not hide containment refusals or our bugs.

### 6. Other entry points and limits (Sonnet sub-checker, text only; I re-read the cited lines for the two that matter)
- `zipfile.ZipFile(` appears in `src/` at `sources/zip_intake.py:262` (intake) and `sources/extract.py:17,83` (office-document text, never called from upload, CLI or Drive). Upload (`ui/intake_upload.py:127`), CLI (`cli_intake.py:58`, `ingest zip`) and Drive (`drive_intake.py:139`, and the CLI `fetch-drive`/job path through `intake_drive`) all reach archives only through `expand_zip`. None has a second ZipFile call.
- `MAX_FIELDS = 8`, `FIELDS_TOTAL_CAP = 32 KiB` still enforced in `upload_stream.py:161-167`; file is unchanged by the merge; the three `test_f2_*` tests pass in the 133 above.

## PROPOSED-ISSUE (none blocks; all low)
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"MemoryError raised while parsing or inflating a zip is deliberately re-raised, so it still escapes expand_zip and is a 500 on the upload route","file":"src/autotester/sources/zip_intake.py:142,268","fix":"decide whether an allocation failure on a hostile archive should be a failed member/archive row (the cycle-1 criterion says 'however malformed'); I could not trigger one on this host (LZMA dict 0xFFFFFFFF decodes fine), so this is a question, not a defect"}
PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"A bzip2 member that fails to decompress is worded 'could not be staged (the write failed)' because bz2 raises OSError; an OSError on the read side is indistinguishable from a write failure","file":"src/autotester/sources/zip_intake.py:205-212","fix":"wrap raw.read OSError into _Unreadable (read side only) so the reason names the data (already known to the maker as a low item)"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"CLI `ingest fetch-drive` does not catch IntakeBusy or an unexpected exception from intake_drive (traceback); the web job path does catch","file":"src/autotester/cli_intake.py:66-78","fix":"mirror the zip_cmd IntakeBusy exit-2 handling"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"The only test of the member-level read guard is a monkeypatch; a real archive reaches it (local-name invalid UTF-8 with flag 0x800, see qa/evidence/t198a-zip-drive-intake-r2-B/probe2.py)","file":"tests/test_zip_intake_register.py","fix":"add the local-name-mismatch archive as a real fixture next to bad_utf8_name"}
Not re-raised (already ruled acceptable by both earlier checkers): a zip needing a version above 6.3 fails as a whole archive with nothing registered.

## EXPLANATION
The repair closes the class it claims: on 1773 structurally hostile archives of my own making, the fixed `expand_zip` never raised, the upload route never answered 5xx, and no staged file, stray file or row without its file remained, while the same generator makes the unfixed code raise 19 times; a second real path (invalid UTF-8 in a local header only) is raised by the old code and a clean `partial` on the new. The broad catches wrap only stdlib parse/read calls, let KeyboardInterrupt/SystemExit/MemoryError and our own errors (including `ensure_inside`) through, and every intake door goes through `expand_zip`. Upload limits from cycle 1 are intact. Limits of this check: Windows only, MemoryError could not be provoked, no browser (no UI file changed), full suite is seat A's.

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent, blind coordinator B)
CAPABILITY-COVERAGE: 1 repaired criterion, 1 falsification reproduced (green in copy, red after edit on the named UnicodeDecodeError assertions)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/sources/zip_intake.py and tests only)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
Metrics: start=2026-10-11T02:42:07Z end=2026-10-11T03:22:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2400 mutants=0 defects_unit=0 defects_6c=0
slow: hostile sweeps (expand + route, 1773 archives each, ~30 min of wall clock on a busy shared host)
