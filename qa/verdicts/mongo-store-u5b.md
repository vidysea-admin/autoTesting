# Verdict - mongo-store-u5b (media blob write-through)

**Verdict:** FAIL
**Cycle checked:** 1
**Checker:** checker-A (fresh context, read-only toward src/ and tests/; did not read any other checker's verdict for this cycle)
**Unit / branch:** U5b, `feat/mongo-store-u5b`, code SHA `2a1f9fc3`, manifest commit `1af91f3e`
**Criteria judged:** M24, M25, M51, M54, M55 (+ the `_sanitize_one:stat` baseline row)

## Summary

Cycle-0 F1 (drive/email documents) and F2 (`source_material` readers) are fixed for the shapes the maker tested.
F1 is **not closed**: a **Drive-fetched video** (`.mp4 .webm .mov .mkv .avi`) still records a `.work/blob-cache` path in
`Source.path`, and the manifest explicitly (and wrongly) excluded that call site. One BLOCK; the rest holds.

## Findings

### F1 (BLOCK, M51 / M24): a Drive video still records the blob-cache copy as `Source.path`

- `src/autotester/sources/drive_register.py:111` `_write_bytes` -> `store_media` (returns the **cache copy**, `store/run_store.py:208-210`) ->
  `_dispatch_by_suffix` `drive_register.py:135-139`: `if suffix in RECORDING_SUFFIXES: source = register_source(store, path, ...)` ->
  `src/autotester/stages/ingest.py:123`: `path=str(path.resolve())`. `source_path()` is not applied on this line, so the cache path is recorded.
- The manifest says `stages/ingest.py:123 (register_source, a user's local video path) is not a store_media product and is unchanged`.
  That is false for the Drive path: `register_drive` hands `register_source` exactly the `store_media` product.
- Own probe (scratchpad `test_probe_u5b.py`: blob area on mongo, `_write_bytes` then `_dispatch_by_suffix`, wipe `rig.cache`, then `local_blob(Path(source.path))`):

  ```
  RECORDED rec.mp4  ...\cache\ee2573cf...\rec.mp4       (a blob-cache path)
  RECORDED rec.webm ...\cache\ad195e69...\rec.webm      (a blob-cache path)
  RECORDED a.mp3    ...\root\projects\pathlynks\sources\p\files\a.mp3   (logical, OK)
  FAILED rec.mp4  - FileNotFoundError: ...\cache\ee2573cf...\rec.mp4
  FAILED rec.webm - FileNotFoundError: ...\cache\ad195e69...\rec.webm
  ```
  After a cache wipe or a restart on Cloud Run (ephemeral disk) a Drive-registered teaching video is unreadable: `local_blob` cannot map a
  cache path back to a blob key (`_key` derives the key from the data-root-relative path). Same defect class as cycle-0 F1, on the most
  important Drive media type (the teaching recording).
- Why the tests and the cycle-1 mutants miss it: `tests/test_media_sources_blobs.py` drives Drive only with `.txt` and `.png`
  (`:152-158`) and email with `.txt` and `.png`; there is no `.mp4/.webm` Drive case; no mutant in `mutations-a..d.json` touches `register_source`.
- Fix direction (maker's call, in place): `ingest.py:123` `path=source_path(path)` (file mode unchanged: same `str(path.resolve())`), plus a Drive-video
  case (`.webm` through `_dispatch_by_suffix`) with a wiped cache, plus a mutant dropping it. `ingest.py` already imports `run_store` (`:34`).

### W1 (Warning): `_LOGICAL` is process-global mutable state, unbounded, and race-prone

`store/run_store.py:44` `_LOGICAL: dict[Path, Path]`, written `:209`, read `:218`.
- **Restart / multi-process:** safe for what it is used for. The map is only read in the call chain that wrote it; the persisted `Source.path` is the
  logical path, so a restart or a second instance does not need the map (verified: the wipe-cache tests read back with no map entry needed).
- **Same-sha collision:** the key is the cache path `<sha>/<name>`, so two logical targets with the same bytes and name collide.
  Probe: `_write_bytes(store,"A",f1,body)`, `_write_bytes(store,"B",f2,body)` (same body and name), then register A -> `Source.path` ends
  `.../sources/B/files/n.txt` (A's source recorded B's logical path). Sequential flows are fine (the last `store_media` is the one being registered, and
  `register_document` dedupes by digest first), but intake jobs run in concurrent daemon threads (`ui/routes_intake.py:82`), so two Drive jobs with
  identical bytes and file name can interleave `store_media` and `source_path`. Impact: a wrong (but byte-identical) logical path, not data loss; low probability.
- **Growth:** one entry per stored medium for the life of the process, never evicted (probe: 50 stores grew the dict by 50). Small per entry; a long-lived process leaks slowly.
- **Second home of a concept:** it is the inverse of the key derivation (`_key` / `materialize`) held in a module-level dict; "logical path of a stored
  medium" now lives both in the map and in the `Source` row. A stateless design (adapters keep the logical `target` and read `local_blob(target)`) would remove the map.
  Not a Block on its own; it is why F1 was easy to miss (every `Source(path=...)` site must remember to call `source_path`).

### W2 (carried, M52 readiness for `blobs`, no code here)
Retention does not delete blobs (`stages/video_retention.py:81-90`); `place_media` reads the whole video into memory (`store/run_store.py:225`). Agree with the maker's W1/W2; both must be closed before G1 flips `blobs`.

### O1 (pre-existing, not U5b)
`tests/test_safe_names_windows.py::test_ordinary_names_still_pass[lpt0]` fails. `git diff 001d10d6 HEAD -- src/autotester/core/safe_names.py` touches only
`_SHORT` and the `_bad_segment` clause; `_DIGITS`/`_device` are unchanged, so U5b did not cause it. Owner: U4.

## Verified OK (not regressed after merge `e6442a6e`)

- **F1 for documents/audio:** Drive `.txt`, `.png`, `.mp3` and email `.txt`, `.png` record the logical path and read back after a cache wipe (probe plus
  `test_a_registered_*_records_the_logical_path_and_survives_a_cache_wipe`). File mode records the same string as before (`source_path` falls back to
  `Path(path).resolve()`; `test_drive_and_email_sources_in_file_mode_record_the_same_path_as_today`).
- **F2:** grep of every `source.path` / `Path(...path)` byte reader under `src/`.
  Routed through `local_blob`: `stages/source_material.py:28` (document text), `:146` (sha256 bytes-changed check), `stages/ingest.py:217,266`,
  `stages/media_prep.py:57,138`, `stages/video_access.py:174`, `media/narration.py:52`, `cli_video_review.py:249`, `ui/routes_video_review.py:78`.
  Not readers (print/compare only): `cli_video.py:81`, `stages/issues.py:92`, `ui/app.py:148`, `ui/routes_sources.py:48`, `cli_video_review.py:161,233`.
  `analyze_video.py:122` uses derived chunk paths (M25). `ingest.py:123` register_source is a reader/writer for local videos but see F1 for the Drive call.
  **Sidecar exemption (`ingest.py:195`, `source_material.py:102`, `media/narration.py:53`) judged justified:** a `<video>.transcript.json` is a user-supplied file
  beside a local recording; no writer (`place_media`, `store_media`) puts a sidecar in the blob store and `intake_commit` does not copy one, so `materialize`
  would have nothing to return; a blob-backed source has no sidecar, as before.
- **commit_video then resolve_teaching_material with the cache wiped is available:** `test_teaching_material_of_a_gridfs_only_video_and_document_is_available` passes.
- **M25:** `test_a_default_selection_run_never_imports_a_database_driver` (fresh interpreter, empty driver list) passes; file-mode writers byte-identical tests pass.
- **M54 / M55:** `tests/test_blob_scan_names.py` all green (621 passed together with `test_safe_names_windows.py`, the 1 failure being O1).
- Files <= 300 lines (`run_store.py` 243, `blobs.py` 278, `cli_video_review.py` 300, `source_material.py` 172); `autotester doctor` clean (enforces functions <= 50).

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u5b`, `PYTHONPATH=src`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`)

| Command | Result |
|---|---|
| `tests/test_media_sources_blobs.py tests/test_media_blobs.py` | 24 passed |
| `tests/test_teaching_documents.py tests/test_teaching_inputs.py` | 13 passed |
| `tests/test_source_adapters_drive.py tests/test_source_adapters_email.py` | 11 passed |
| `tests/test_blob_scan_names.py tests/test_sweep_u3a.py` | 112 passed |
| `tests/test_safe_names_windows.py tests/test_blob_scan_names.py` | 621 passed, 1 failed (O1, pre-existing) |
| own probe `test_probe_u5b.py` (scratchpad, `-p media_blob_support`) | Drive `.mp4`, `.webm` FAIL (F1); `.mp3` ok; same-sha collision recorded B's path (W1); growth 50 (W1) |
| `uv run ruff check src tests scripts` | exit 0, `All checks passed!` |
| `uv run autotester doctor > .work/doctor-chk.txt` | exit 0, `doctor: clean` |
| `scripts/mutation_check.py` `mutations-a.json` | 5/5 killed |
| `mutations-b.json` | 10/10 killed |
| `mutations-c.json` | 9/9 killed |
| `mutations-d.json` | 4/4 killed |

Full suite not run (brief). No `.env` value printed; no network; no Mongo connection (hand-written fake only).

## Required for cycle 2

1. F1: `stages/ingest.py:123` records `source_path(path)`; add a Drive `.webm`/`.mp4` case (register, wipe cache, `local_blob(Path(source.path))` returns the bytes) and a mutant for it; re-run the file-mode pin.
2. Re-enumerate every `Source(... path=...)` constructor under `src/` and state each as logical-path-safe. W1 is optional, but the stateless design would close the class.
