# Verdict - mongo-store-u5b (checker A)

**Verdict: FAIL**
**Cycle checked: 0**
**Unit:** U5b, media blob write-through. **Manifest:** `qa/manifests/mongo-store-u5b.md` (code `cee2f25b`, manifest `a398f1a9`).
**Contract:** `qa/contracts/mongo-store.md` M24, M25, M51, M54, M55 and the `_sanitize_one:stat` baseline row.
**Checker:** fresh, independent (chk-mongo-u5b-a). Read-only toward `src/` and `tests/`. No Mongo connection; the in-repo fake only.

Two Blocks (F1 against M51, F2 against M24/M51). Everything else the brief named holds. Fix cycle 1 should be small: F1 and F2 are both "a
reader or a registered reference still points at a path that exists only when the file is on disk", and each is demonstrated below.

## Findings

### F1 - BLOCK (M51 falsifier: "a stored `Source` reference does not `materialize`")
Drive and email registrations in blob mode store a `Source.path` that points into the **blob cache**, not at the logical key.
- `store/run_store.py:197-207` `store_media` ends `return local_blob(target)`, i.e. `.work/blob-cache/<sha>/<name>`.
- `sources/drive_register.py:197` and `sources/email_register.py:219` return that path; the callers then store `str(path.resolve())`
  (`sources/adapters.py:117`, `:224`; `sources/email_register.py:135`, `:193`; `sources/drive_register.py:171`).
- The cache path is not a blob key (`.work` is in `NOT_BLOB_SEGMENTS`, `store/blobs.py:40`), so once the cache is evicted (512 MB LRU) or the
  instance is replaced, the source cannot be read. The maker disclosed this as judgment call 5; the contract does not permit it.
- Reproduced (scratchpad `probe1.py`, fake GridFS, `AUTOTESTER_STORE_AREAS=blobs=mongo`): register an email attachment through
  `_write_attachment_to_disk` then `_register_unrecognised_attachment`; output:
  `Source.path under blob cache: True` / `gridfs keys: ['projects/pathlynks/sources/m1/attachments/pic.png']` /
  `Source readable after cache wipe: False`. The logical path (`.../attachments/n.txt`) does materialize (`True`), so the data is safe; the reference is wrong.
- Test gap: `tests/test_media_sources_blobs.py::test_a_drive_file_is_put_in_gridfs_not_on_disk_and_a_clash_is_kept_apart` and
  `test_an_email_attachment_is_put_in_gridfs_not_on_disk` assert only the returned path's bytes, never a registered `Source`.
  The 24/24 mutants killed cannot see this because no test pins it.
- Fix direction (maker's call, edit in place): the file-based adapters can read the cache copy, but the `Source.path` they record must be the
  logical `target` (as `commit_video` already does at `sources/intake_commit.py:140-142`); add a test that registers a drive file and an email
  attachment, wipes the cache, and reads the `Source` back through `local_blob`.

### F2 - BLOCK (M24: "no reader opens a state path directly"; M51: bytes readable through `materialize`)
`stages/source_material.py` reads `source.path` directly, so a GridFS-only recording is reported unavailable. This reader is not in the manifest's
list of the "untouched readers" (judgment call 12).
- `stages/source_material.py:145` `file_sha256(Path(source.path))` (opens the path); `:27` `extract_document_text(Path(source.path))`;
  `:100-101` the `.transcript.json` sidecar beside the path.
- Reproduced (scratchpad `probe2.py`): `commit_video` with the blobs area on mongo, then `resolve_teaching_material(store, src, [src])`:
  `on disk: False | in gridfs: 1` / `unavailable: True ['material unavailable (FileNotFoundError); re-register source']`.
  This is the teaching-material identity/fingerprint path, not a CLI convenience.
- The manifest named `cli_video_review.py:248`, `media/narration.py:50`, `ui/routes_video_review.py:77` as left; a grep of `source.path` readers also finds
  `stages/source_material.py:27,100,145`, `stages/ingest.py:195` (sidecar), `cli_video.py:81`/`stages/issues.py:92` (label only, harmless). Enumerate and
  route every reader that opens bytes, or state in the manifest, per reader, why it is out of M24.

### W1 - WARNING (not a criterion; must close before G1 flips `blobs`)
`stages/video_retention.py:81-90` `prune_old_videos` unlinks the local file and drops the `Evidence` row only; the GridFS blob stays. In a blob-backed
area the D-048 "at most N videos" retention is not enforced and GridFS grows without bound. Manifest call 7 discloses it. Add it to the M52 per-area
readiness table for `blobs`.

### W2 - WARNING (call 4, full in-memory video read)
`store/run_store.py:216` `Path(staged).read_bytes()` then `store.put` holds the whole recording. The default upload cap is 2 GiB
(`schema/server_settings.py` `DEFAULT_MAX_UPLOAD_BYTES`), so peak RSS can reach several GiB in one request on a small Cloud Run instance. Accepted for
cycle 0 because `BlobStore.put` takes `bytes` (a U5a interface), but a streaming put or a lower blob-mode cap must be a recorded follow-up before the flip.

### W3 - WARNING (call 6, blob orphan)
`sources/intake_commit.py:139-148`: if `add_source` fails after `place_media`, the `except` unlinks the local path only. The id and key are content-derived, so a
retry re-puts the same key (equal-sha no-op) and the orphan is bounded to one blob per failed digest. Accepted; note it for the janitor/retention work.

### W4 - WARNING (module job)
`store/run_store.py` (234 lines) now has two jobs (advisory UX persistence and media write-through). The docstring states both and doctor is clean, so the
design rule is met in letter. The move was the only way to stay inside the 300-line cap with no new module (D-122/D-123 list), so I accept judgment call 1; a
later split needs a D-entry.

### O1 - OBSERVATION (M54 meets the contract as written)
The scan skips a body only when it is not UTF-8 and the declared type is `image/*`, `video/*`, `audio/*`, `application/octet-stream`, `pdf` or `zip`. A caller that
declares `application/octet-stream` and prepends one invalid byte (`b"\xff"+secret`) stores it (probed: `application/octet-stream STORED`, `image/png STORED`;
`application/x-weird` refused). That is the deny-list the contract specifies. `put_file` defaults the type to `application/octet-stream` for an unknown suffix
(`store/run_store.py:156`), so non-UTF-8 text with an unknown suffix goes unscanned; low risk, noted for the next M8 dual check.

### Judgment call: `tests/test_safe_names_windows.py::test_ordinary_names_still_pass[lpt0]` - the CODE is right, the TEST is stale
- Fails identically at the unit base `001d10d6` (`core/safe_names.py:21` `_DIGITS` includes `"0"` there too) and at HEAD; U5b did not touch `safe_name`/`_DIGITS`
  and did not touch the test. Introduced when U4 cycle 1 (`7a835857`) added the device-name rule.
- Microsoft's "Naming Files, Paths, and Namespaces" lists COM0 and LPT0 among the reserved device names. U4's own newer tests agree: `tests/test_safe_key.py:18`
  lists `"a/LPT0"`, `"a/lpt0.txt"`, `"a/COM0"` as hostile; `tests/test_state_backend_contract.py:252` lists `"a/COM0"`, `"a/lpt0.txt"`. Only the older
  `tests/test_safe_names_windows.py:62` (from `57cec910`, T205) lists `"lpt0"` as ordinary. The rule is deliberately platform-independent ("the same answer on
  Windows and Linux", `core/safe_names.py` docstring); this Windows 11 host creating `lpt0` is not evidence against it (it also created `con` and `lpt1`).
- Ruling: remove `"lpt0"` from the ordinary list at `tests/test_safe_names_windows.py:62` and add it to the hostile list. Do not loosen `_DIGITS`.
- Routing: **U4 owner**, not U5b. Not a reason to fail U5b. Feedback text for `qa/feedback-inbox.md`: "tests/test_safe_names_windows.py:62 lists lpt0 as an ordinary
  name but safe_names._DIGITS (U4 7a835857) and tests/test_safe_key.py:18 treat LPT0/COM0 as reserved; fix the stale test, one line."

## Criteria

| Crit | Result | Evidence |
|---|---|---|
| M24 write-through (screenshot masked first, kept video, leak/responsive, frames) | PASS | `browser/evidence.py:160` puts after `MASK_CSS` and `_recapture_blank`, `masked=True` always (`_record` sets `masked=True`); `run_store.py:53-57` `save_result` -> `sync_run_blobs` then `write_json`; `leak_evidence.py:100` `write_blob_file(kind="screenshot", masked=True)`; `media_prep.py:162` frames. Tests `test_media_blobs.py` (all green) |
| M24 result only after blobs; unmasked screenshot leaves neither | PASS | `test_a_refused_screenshot_means_the_result_is_not_saved` (result file absent, `blob_area.files == []`) |
| M24 readers via `materialize` when the file is gone | PARTIAL, FAIL via F2 | the 12 switched sites work (`test_a_screenshot_whose_local_file_is_gone_is_still_embedded_from_the_blob_store`, `test_a_run_video_with_no_local_file_is_served_from_the_blob_store`); `source_material.py` does not |
| M25 file mode byte-identical, no driver | PASS | `local_blob` returns the path itself when the file exists; fresh interpreter importing evidence, intake_commit, drive/email_register, media_prep, leak_evidence, routes_video, grade, report_export: `blob_store: None`, driver modules `[]` |
| M51 video bytes only in GridFS | PASS | `test_a_committed_video_lives_only_in_gridfs_and_reads_back_through_materialize` |
| M51 drive/email bytes only in GridFS; Source reference materializes | FAIL via F1 | bytes yes, reference no (probe1) |
| M54 deny-list covers any UTF-8 body | PASS | `store/blobs.py:48-58`, `:115`; 13 odd types refused; my extra probes: `APPLICATION/NDJSON ; x=y`, `application/x-weird` + invalid byte, utf-16 body: refused. See O1 |
| M55 8.3 + hostile names on both stores | PASS | `core/safe_names.py:28,87`; my probe refused `PROFIL~1`, `PROGRA~1`, `a~1`, `CONIN$`, `CLOCK$`, `COM0`, `lpt0`, `com1` superscripts, `x.png::$DATA`, `ntfs~1:x`; allowed `abcdefg~1`, `report~final.png`, `PROFIL~1.txt.bak` (not aliases) |
| `_sanitize_one:stat` row | PASS | `core/image_privacy.py:179-188` bounded read; row gone from `pyproject.toml` (7 rows removed, none added); doctor clean |
| Files <= 300 lines, functions <= 50 | PASS | doctor `clean`; `run_store.py` 234, `blobs.py` 278, `project_store.py` 297 |

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u5b`, `PYTHONPATH=src`, `-o addopts=`, at most two files per call)

| Command | Output |
|---|---|
| `uv run pytest tests/test_media_blobs.py tests/test_media_sources_blobs.py` | `19 passed` |
| `uv run pytest tests/test_blob_scan_names.py tests/test_sweep_u3a.py` | `112 passed` |
| `uv run pytest tests/test_safe_names_windows.py` | `1 failed, 518 passed` (`[lpt0]`, base-identical, see above) |
| `uv run pytest tests/test_blobs.py tests/test_blobs_cache.py` | `137 passed` |
| `uv run pytest tests/test_state_bypass_rule.py tests/test_state_selection.py` | `82 passed` |
| `uv run pytest tests/test_ui_video_route.py tests/test_report_export.py` | `21 passed` |
| `uv run pytest tests/test_drive_intake.py tests/test_source_adapters_email.py` | `26 passed` |
| `uv run pytest tests/test_grade_evidence.py tests/test_media_prep.py` | `45 passed` |
| `uv run pytest tests/test_image_privacy.py tests/test_leak_evidence.py` | `48 passed` |
| `uv run pytest tests/test_zip_intake_register.py tests/test_cli_intake.py` | `38 passed` |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor > file` | exit 0, `doctor: clean` |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u5b/mutations-a.json` | `5/5 mutations killed` |
| `... mutations-b.json` | `10/10 mutations killed` |
| `... mutations-c.json` | `9/9 mutations killed` |
| scratchpad `probe1.py` (email attachment -> Source -> wipe cache) | F1 output above |
| scratchpad `probe2.py` (commit_video -> `resolve_teaching_material`) | F2 output above |

The full suite was not run (machine low on memory, brief). No `.env` value was read or printed. No file under `src/` or `tests/` was edited; the mutation
harness works on a temporary copy.

## For fix cycle 1
1. F1: record the logical key path in `Source.path` for drive and email; test through a registered `Source` with the cache wiped.
2. F2: route `stages/source_material.py:27,100,145` (and the other `source.path` byte readers found by grep) through `local_blob`, or list each as out of scope
   with a reason; test with a GridFS-only video and document.
3. Add W1 (retention) and W2 (memory) to the blobs-area readiness row for M52/G1.
4. The `lpt0` test is U4's.
