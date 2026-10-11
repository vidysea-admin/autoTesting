# t198a-zip-drive-intake r3 adversarial read (head 894549ee) - sub-checker A, findings only

Probe scripts: C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/r3/probes/p1..p5 (outputs p1_out.txt .. p5_out.txt one level up).
All probes used a temp AUTOTESTER_ROOT under scratchpad/r3/data; the repo projects/ dir was never touched. No pytest run.

## DEFECTS (changed code)

### D1 - hostile archive crashes expand_zip with an unhandled exception (MEDIUM, blocks)
- zip_intake.py:233-235 catches only `BadZipFile, OSError` around `zipfile.ZipFile(archive)`.
  Python raises `NotImplementedError("zip file version N.M")` from `_RealGetContents` when a central-directory
  entry carries extract_version > 6.3. Probe p3: 13 distinct byte-flip mutants of a 2-member zip -> `NotImplementedError` out of expand_zip (p3_out.txt).
- zip_intake.py:178-183 per-member handler catches `BadZipFile, zlib.error, EOFError`, `NotImplementedError`, `OSError`, but NOT `lzma.LZMAError`.
  Probe p2: 300 LZMA-payload flips -> 176 raised `_lzma.LZMAError` out of expand_zip (p2_out.txt). bz2 is OK (OSError) but the message says "the write failed".
- Effect: no report (contract TI5 "failed, never a crash"); earlier members of the same zip are already registered but the user sees a 500 / traceback; CLI exit is a traceback. Lock and staging ARE released (finally blocks), so no stuck state.
- Fix hint: catch `Exception` per member (after the specific ones) and `(BadZipFile, NotImplementedError, OSError)` at open; add `lzma.LZMAError`.

### D2 - stale-lock takeover is a TOCTOU; two intakes can hold the lock at once (MEDIUM, blocks TI6 "two intakes at the same time")
- intake_commit.py:67-70: `_lock_is_stale` then `path.unlink` then `continue` is not atomic. Probe p4 case 2 forces B to pause after deciding "stale"; A takes over and creates a fresh lock; B then unlinks A's fresh lock and creates its own. Holder order printed: `['A', 'B', 'A-done']` - overlap.
- Same file :76-77: the `finally` unlinks the lock unconditionally, so a holder whose lock was taken over (slow beat) deletes the new holder's lock on exit.
- Only reachable when a stale lock exists (after a kill + 30 min, or a holder that did not beat for 30 min), so probability is low, severity is for the integrity of rows/sweep (the new holder's `sweep_orphans` also deletes the live holder's staging and row-less `recording.*`).

### D3 - memory grows with text form fields and part count, up to limit + 256 KiB (= ~2 GiB default) (MEDIUM)
- upload_stream.py:146-154 caps each text field at 16 KiB but nothing caps the number of fields or their total; `self.fields` keeps every one. The body guard (:184) is `limit + FORM_OVERHEAD`, so the budget for text is the whole upload limit.
- Probe p5: 2500 x 16 KB fields (40 MB body, no file) -> retained, peak traced 80 MB, then refused 400 "Choose a file". Scaled to the 2 GiB default that is ~4 GB of RSS from one request by any member with `video.upload`. Contradicts HO30 "memory does not grow with the file" in spirit (module docstring claims "limit plus form overhead" for what was read, and nothing bounds what is held).
- Fix hint: FORM_CAP-style total cap on non-file bytes and a max part count (e.g. 64 KiB / 50 parts) checked in `_data`/`_begin`.

### D4 - oversize multipart boundary gives an unhandled 500 (LOW)
- upload_stream.py:179 `MultipartParser(_boundary(request), ...)` is outside the `try`. Probe p5 "huge boundary" (60 KB boundary): `FormParserError: Boundary length 60010 exceeds maximum of 256` escapes stream_upload (UNHANDLED) -> 500 instead of 400. Needs no auth beyond the gate.

## HARDENING (non-blocking)

- H1 Reserved-name rule misses a space before the extension: `vet_member_name("CON .mp4")`, `"CON  .mp4"`, `"a/con .d/b.mp4"` -> None (zip_names.py:56 strips only trailing " ." of the whole part, then splits at the first "."; the stem keeps its trailing space). Also `COM\u00b9.mp4`, `CONIN$`, `CONOUT$`, `CLOCK$` pass. Names never reach a path (generated `m000001.mp4`), so this is policy only; contract TI1 says reserved names are refused. Fullwidth `CON` passes (correct on NTFS).
- H2 Control/bidi set is narrow (zip_names.py:22,34,89): U+200B, U+2028/2029, U+FEFF, U+00AD, tag chars U+E0000+ pass `vet_member_name` and `display_name` unescaped (p1_out.txt). HTML is escaped downstream so it is a spoofing nuisance in CLI/report only.
- H3 Orphan sweep does not cover the HTTP staging: intake_upload.py:119 stages in `.work/uploads/<slug>/<ulid>`; only the `finally` removes it, and `sweep_orphans` (intake_commit.py:85) only walks `.work/intake/<slug>`. A kill mid-upload leaves up to the limit of bytes forever.
- H4 After a kill the lock blocks the next intake for LOCK_STALE_S = 30 min (p4 case 1: IntakeBusy), though LOCK_TIMEOUT_S = 10 min means the user gets 503 twice before it clears. A pid/hostname in the lock file would let it clear immediately. Also the 600 s wait sleeps inside a threadpool thread (intake_upload.py:127/131), so ~40 waiters starve the app's sync routes.
- H5 Nested-archive content sniff covers zip/7z/rar/gzip only (zip_names.py:24); tar, bzip2, xz bytes named `.mp4` are registered as videos. Harmless to the host; fails later at ffmpeg.
- H6 Single-recording label is stored raw (intake_upload.py:106 `label=label or None`), only checked by `_refuse_unsafe_submission` (the same call, same project secrets, as the old route, now AFTER the whole body streams); TI11 says label passes `Redactor.scrub`. Equivalent for secrets in `.env`, not for patterns the redactor knows but the guard does not. Question-level (see Q1). Zip uploads ignore the label silently.
- H7 No cap on concurrent uploads: N x limit of disk in `.work/uploads`.
- H8 bz2 corrupt member reports "could not be staged (the write failed)" (OSError) - misleading, cosmetic.
- H9 `commit_video` can raise `ValueError` (cross-volume sha mismatch, intake_commit.py:127) and `UnsafePath`; `_store_member` (zip_intake.py:153) catches only OSError -> same crash class as D1 but needs a cross-volume fault.

## QUESTIONS (< 80% confidence)
- Q1 Is `_refuse_unsafe_submission` on the label sufficient for TI11 "label passes Redactor.scrub"? Not verified against Redactor patterns.
- Q2 `filename*=` : the parser used the plain `filename` (evil.exe -> refused). I did not determine which wins in other python-multipart versions; both vetting and storage use the same parsed name, so no mismatch seen.
- Q3 Cut-off body that ends exactly after the file's closing `\r\n--boundary` (before `--`) is accepted as complete (part_end fires on the delimiter). Content is intact in that case; I did not verify the parser fires part_end on a bare delimiter prefix.

## PROBES THAT CAME OUT CLEAN
- Names (p1): `..` in all positions, both separators, absolute, `\abs`, `C:x`, UNC and `\\?\`, ADS, CON/NUL/AUX/COM1/LPT1 with/without extension, `con.`, trailing-space-after-extension, NUL, U+202E/200E/2066, ESC, DEL, C1: refused. Nested suffix `.ZIP/.tar.gz/.TGZ/.7Z/.RAR/.Tar` refused.
- Symlink-mode entry with a benign name refused; zip-signature bytes in `x.mp4` refused; directory entries not listed; duplicate names both processed, same bytes -> duplicate; 60 000-char name ok (display truncated at 200); sentinel file intact after every probe.
- Ratio edge: 20 members declared exactly 1 MiB (ratio check skipped) all register, bounded by max_videos x 1 MiB = 20 MiB; with 1000 entries only 20 videos are ever inflated, others are skipped without reading. Total declared sum is checked before any write.
- Python's ZipExtFile truncates output at the declared size, so a header understating a member cannot inflate past it (CRC then fails); deflate64 (9), unknown (20), AES (99) -> `unsupported compression method`, flipped deflate -> `corrupt member`, truncated/garbage/empty archive -> one `failed` row.
- Upload (p5): exactly-limit accepted, limit+1 -> 413, no terminal boundary / cut mid-file -> 400, no-filename part -> 400, two file parts -> 400, bare-LF body -> 400, endless body stops at the limit (5 MiB written exactly), path/NUL filename stored under generated name, 200k headers in one part refused with small memory. Staging leftovers in these probes are removed by handle_upload's `finally` (intake_upload.py:141-142).
- Slug: `_load_project_or_404` runs `_require_slug` (`^[a-z][a-z0-9-]*$` fullmatch) before any path use (helpers.py:65,165). Result page: member, outcome, reason, notes, archive and slug are `html.escape`d (intake_upload.py:55-67); `theme.card` does not escape the title but the only dynamic title part is pre-escaped.
- Atomic order: file placed, then row appended, file removed on exception (intake_commit.py:161-168); staging removed in `finally` (:114-117); lock + sweep before staging.
