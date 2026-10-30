# Manifest - mongo-store-u5b

**Status:** ready-for-check
**Fix cycle:** 1
**Contract:** `qa/contracts/mongo-store.md` (amended on master 001d10d6), unit U5b. **Criteria judged by U5b:** M24, M25, M51, M54, M55, plus the U5a checker W1 body-scan widening (= M54) and the `core/image_privacy.py:_sanitize_one:stat` baseline row (U3c verdict).
**Branch:** `feat/mongo-store-u5b`. **Base SHA:** `001d10d6` (master at the contract amendment; master `30db1b7a` (U9) was merged into this branch for cycle 1, merge commit `e6442a6e`). Not merged to master, not pushed.
**Code SHA:** `2a1f9fc392b0bf7217b28fc7f04710cbd1f5e6a8` (cycle-1 code commit; cycle-0 code was `cee2f25b`; this manifest is a separate commit on top).
**Authority:** D-122/D-123 module list untouched: NO new `src/` module (the media helpers live in the existing `store/run_store.py`; see judgment call 1). `store/mongo_guard.py`, `store/mongo_backend.py`, `auth/`, `core/env.py`, `ui/error_pages.py`, `ui/routes_live.py` are not edited.

## What changed (src)

| File | Kind | Change |
|---|---|---|
| `src/autotester/store/run_store.py` (234 lines) | E in place | media helpers appended to the module: `blob_store` `:126`, `_key` `:139`, `put_file` `:147`, `write_blob_file` `:161`, `local_blob` `:171`, `sync_run_blobs` `:185`, `store_media` `:197`, `place_media` `:212`; `RunStoreMixin.save_result` `:53` (moved here from `ProjectStore`, which is at the 300-line cap) |
| `src/autotester/store/project_store.py` (297) | E in place | `save_result` removed (now inherited from `RunStoreMixin`, same signature); no public change |
| `src/autotester/store/blobs.py` (278) | E in place | M54: `BINARY_PREFIXES`/`BINARY_TYPES` `:44-45`, `_scan_text` `:48`, used in `_vet` `:115` |
| `src/autotester/core/safe_names.py` | E in place | M55: `_SHORT` `:28`, rule in `_bad_segment` `:87` (so `safe_key`, which FileBlobStore and the cache both use, refuses `PROFIL~1`) |
| `src/autotester/store/mongo_routes.py` | E in place | `UNROUTED` `:28` no longer lists `blobs`, so `AUTOTESTER_STORE_AREAS=blobs=mongo` is selectable |
| `src/autotester/core/image_privacy.py` | E in place | `_sanitize_one` `:179-188`: bounded read of `MAX_IMAGE_BYTES+1` bytes, `Image.open(io.BytesIO(raw))`; no `.stat()` |
| `pyproject.toml` | E in place | 7 baseline rows removed (listed below); nothing added |

### Writers (the M24 list) - file:line

| Media | Writer | Write-through |
|---|---|---|
| Run and crawl screenshots | `browser/evidence.py:152/157` (Playwright capture after `MASK_CSS`, B7) then `_recapture_blank` | `browser/evidence.py:160` `put_file(full, kind="screenshot", masked=True)`. Crawl shots use the same `session.screenshot` (`stages/explore_node.py:42`) |
| Kept run video | `browser/video.py` `end_case_video` (rename to `<case>.webm`), kept only for non-PASS by `stages/run_case_pipeline.py:107` `_finalize_video` | `RunStoreMixin.save_result` `store/run_store.py:53` -> `sync_run_blobs` `:185` (screenshots + videos the result names, BEFORE the result file) |
| Leak and responsive masked shots | `stages/leak_evidence.py:100` (`store_masked_screenshot`, called by `stages/oracle_responsive.py:69`) | `write_blob_file(..., kind="screenshot", masked=True)` `store/run_store.py:161` (only the masked copy; the raw scratch `raw.write_bytes` `:96` is a temp file and stays) |
| Teaching-video frames | `stages/media_prep.py:150-160` `extract_frames` | `stages/media_prep.py:162` `put_file(png, kind="frame", masked=False)` |
| Source video bytes (M51) | `sources/intake_commit.py:140` | `place_media` `store/run_store.py:212` |
| Drive file bytes (M51) | `sources/drive_register.py:197` (`_write_bytes`) | `store_media` `store/run_store.py:197` |
| Email attachment bytes (M51) | `sources/email_register.py:219` (`_write_attachment_to_disk`) | `store_media` |

### Read sites switched to `local_blob` (-> `materialize`, file wins while it exists)

`stages/report_export.py:180` (`png_base64`, shared by the UI and the export) · `ui/routes_video.py:60` (`_safe_video_path`; the "run dir must exist" early return dropped) · `ui/routes_product_map.py:87` · `stages/grade.py:136` · `stages/run_artifacts.py:43` · `stages/ux_advisory.py:112` · `stages/media_prep.py:57,138` · `stages/ingest.py:217,266` · `stages/video_access.py:174`.

### M51 - exact lines touched in the three files U3d also edits (for the merge)

- `sources/intake_commit.py`: deleted `_copy_in` and `_place` (old `:120-138`); `:140` now `place_media(staged, target, digest)`; import `:33` `place_media`; removed now-unused imports `errno` and `copy_bounded, read_chunks`. `os` stays (used by the lock).
- `sources/drive_register.py`: `:197` `return store_media(target, content)` replaces `target.write_bytes(content); return target`; import `:47`.
- `sources/email_register.py`: `:219` `return store_media(target, attachment.content)` replaces `target.write_bytes(...); return target`; import `:44`.
- Left to U3d on purpose: `mkdir`/`exists` in `_write_bytes` and `_write_attachment_to_disk` (a blob-backed run still creates an EMPTY `files/` or `attachments/` folder; no media file lands there), the lock, `rmtree`, `sweep_orphans`, `commit_video` `exists`/`unlink`/`rmdir`.

### Baseline (`pyproject.toml [tool.autotester.doctor.state-bypass]`) rows removed (7)

`core/image_privacy.py:_sanitize_one:stat` · `sources/drive_register.py:_write_bytes:write_bytes` · `sources/email_register.py:_write_attachment_to_disk:write_bytes` · `sources/intake_commit.py:_copy_in:os.replace` · `_copy_in:unlink` · `_place:mkdir` · `_place:os.replace`. Doctor reports no stale row.
`tests/test_sweep_u3a.py` `LEFT` table updated: `sources/drive_register.py` and `sources/email_register.py` entries removed; `sources/intake_commit.py` is now `{"shutil.rmtree": 2, "os.open": 1}`.

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M24 write-through | writers table above; `put_file` `store/run_store.py:147` carries sha256 (via `BlobStore.put`), `kind`, `masked`, `content_type` | `tests/test_media_blobs.py::test_a_screenshot_is_kept_on_disk_and_put_masked_in_the_blob_store`; `test_save_result_puts_the_screenshot_and_the_kept_video_before_the_result`; `test_a_masked_leak_shot_is_put_masked_through_write_blob_file`; `tests/test_media_sources_blobs.py::test_frames_of_a_gridfs_only_video_are_extracted_and_put_as_unmasked_frames` |
| M24 RawResult only after blobs stored | `store/run_store.py:53-58` | `test_a_refused_screenshot_means_the_result_is_not_saved` (result file absent, no blob) |
| M23 unmasked screenshot refused, never bypassed | every screenshot put passes `masked=True` from a capture made after `MASK_CSS`; nothing passes `masked=False` for a screenshot | `test_an_unmasked_screenshot_is_refused_and_nothing_is_stored` |
| M24 readers via `materialize` | read sites above | `test_a_screenshot_whose_local_file_is_gone_is_still_embedded_from_the_blob_store`, `test_local_blob_is_the_path_itself_while_the_file_exists_and_when_nothing_is_stored`, `tests/test_media_sources_blobs.py::test_a_run_video_with_no_local_file_is_served_from_the_blob_store` |
| M25 file mode byte-identical, no driver | `blob_store` returns `None` unless `store_selection()["blobs"] == "mongo"`; the driver is imported lazily | `test_with_the_area_on_file_a_screenshot_is_the_same_file_and_no_blob_is_put`, `test_save_result_in_file_mode_puts_nothing`, `test_a_committed_video_in_file_mode_is_the_same_file_as_today`, `test_drive_and_email_writers_in_file_mode_write_the_file_as_before`, `test_a_default_selection_run_never_imports_a_database_driver` (fresh interpreter, prints `[]`) |
| M51 | `place_media` / `store_media` | `test_a_committed_video_lives_only_in_gridfs_and_reads_back_through_materialize`, `test_a_drive_file_is_put_in_gridfs_not_on_disk_and_a_clash_is_kept_apart`, `test_an_email_attachment_is_put_in_gridfs_not_on_disk`, `test_a_recording_whose_bytes_do_not_match_its_digest_is_not_stored`, `test_a_secret_value_in_an_ingested_text_is_refused_and_nothing_is_stored` |
| M54 | `store/blobs.py:48` | `tests/test_blob_scan_names.py::test_a_secret_in_a_text_like_body_is_refused_whatever_the_declared_type` (13 types: ndjson, jsonl, sql, toml, x-sh, text/csv, multipart/form-data, message/rfc822, rtf, empty, bare `text`, ...), `test_a_utf8_body_is_scanned_even_under_a_binary_type`, `test_a_binary_body_under_a_binary_type_is_not_text_scanned`, `test_an_undecodable_body_under_a_text_like_type_is_still_scanned` |
| M55 | `core/safe_names.py:28,87` | `test_every_blob_entry_point_refuses_a_hostile_name_before_any_io` (16 names x put/get/stat/delete/materialize x File/Mongo store: tree unchanged, only `UnsafeName`), `test_an_8_3_short_name_is_unsafe`, `test_a_name_that_is_not_an_8_3_alias_is_still_safe` |
| M16 `_sanitize_one:stat` row | `core/image_privacy.py:179-188` | doctor (a stale row is an error); `tests/test_image_privacy.py`, `test_image_privacy_engine.py` (60 passed) |

## Verification (run in `D:/autoTesting/.claude/worktrees/mongo-u5b`, `PYTHONPATH=src uv run pytest <2 files> -o addopts=`)

| Command | Result |
|---|---|
| `tests/test_media_blobs.py tests/test_media_sources_blobs.py` | 19 passed |
| `tests/test_blob_scan_names.py tests/test_sweep_u3a.py` | 112 passed |
| `tests/test_blobs.py tests/test_blobs_cache.py` | 137 passed |
| `tests/test_blobs_mongo.py tests/test_state_selection.py` | 43 passed |
| `tests/test_state_bypass_rule.py tests/test_zip_intake_atomic.py` | 62 passed |
| `tests/test_image_privacy.py tests/test_image_privacy_engine.py` | 60 passed |
| `tests/test_image_privacy_reocr.py tests/test_leak_evidence.py` | 21 passed |
| `tests/test_media_prep.py tests/test_media_frames.py` | 18 passed |
| `tests/test_ui_video_route.py tests/test_ui_video_route_traversal.py` | 16 passed |
| `tests/test_report_export.py tests/test_video_report_export.py` | 17 passed |
| `tests/test_ux_advisory_wiring.py tests/test_oracle_responsive.py` | 15 passed |
| `tests/test_ui_product_map.py tests/test_ingest.py` | 11 passed |
| `tests/test_grade_evidence.py tests/test_grade_visual.py` | 52 passed |
| `tests/test_cli_intake.py tests/test_drive_verify.py` | 26 passed |
| `tests/test_run_failure_artifacts.py tests/test_video_retention.py` | 9 passed |
| `tests/test_video_review_route.py tests/test_user_persona.py` | 17 passed |
| `tests/test_ui_report.py tests/test_grade.py` | 28 passed |
| `tests/test_source_adapters_drive.py tests/test_source_adapters_email.py` | 11 passed |
| `tests/test_drive_intake.py tests/test_ui_intake.py` | 45 passed |
| `tests/test_ui_intake_drive.py tests/test_ui_project_intake.py` | 27 passed |
| `tests/test_zip_intake_register.py tests/test_zip_intake_limits.py` | 39 passed |
| `tests/test_safe_names_windows.py tests/test_blob_scan_names.py` | 621 passed, **1 failed**: `test_ordinary_names_still_pass[lpt0]` (see "Pre-existing failure") |

The full suite was NOT run (machine low on memory; brief). `uv run ruff check src tests scripts` -> `All checks passed!` (`.work/ruff-u5b.txt`). `uv run autotester doctor` -> exit 0, `doctor: clean` (`.work/doctor-u5b.txt`, redirected, not piped).

### Mutation evidence (`scripts/mutation_check.py`, C7), `qa/evidence/mongo-store-u5b/`

| Spec | Run | Result |
|---|---|---|
| `mutations-a.json` (M54, M55) | `mutation-run-a.txt` | 5/5 killed |
| `mutations-b.json` (M24 writers, ordering, readers) | `mutation-run-b.txt` | 10/10 killed (first run: b9 SURVIVED, a vacuous test; the test now puts the file before asserting the file wins; re-run 10/10) |
| `mutations-c.json` (M51, frames, video route, no-driver) | `mutation-run-c.txt` | 9/9 killed |

## Judgment calls for the checker

1. The media helpers live in `store/run_store.py`, not `store/blobs.py` (278 lines but the helpers do not fit under 300) and not in a new module (not on the D-122/D-123 list; brief says a new file is a STOP). `ProjectStore.save_result` moved into `RunStoreMixin` for the same cap reason (`project_store.py` was exactly 300).
2. `local_blob` is local-first: while the file exists it returns that path (byte-identical in file mode); the cache copy is only for a missing file.
3. Frames are put with kind `frame`, `masked=False`: they are stills of the human's own teaching recording, not Playwright captures of the product, and the M23 unmasked refusal is for kind `screenshot` only.
4. `BlobStore.put` takes `bytes`, so a source video is read fully into memory for the put (`place_media`). A streaming put is a U5a interface change.
5. (Cycle 0 recorded a cache path here: checker F1. FIXED in cycle 1, see below.) In blob mode `store_media` still returns the verified cache copy, because the file-based adapters need a real `Path`, but every `Source(path=...)` now records the LOGICAL path through `source_path`.
6. A blob orphan is possible if `add_source` fails after `place_media`; `commit_video`'s except path only unlinks the local file. Not closed here.
7. `video_retention` pruning deletes the local file only; it does not delete blobs.
8. A secret value inside an ingested text document is refused by the M8/M54 scan in blob mode (and the register call fails); in file mode nothing scans it (unchanged).
9. With the blobs area on mongo, the leak/responsive PNG's local copy is written through a plain `FileBackend` (media never goes into the state database, whose `put` decodes UTF-8); with the area on file it still goes through `filestore.write_bytes`, so the U3a routed-backend test passes unchanged.
10. A blob-backed drive or email register still creates an empty `files/` or `attachments/` directory (U3d owns the `mkdir`).
11. `UNROUTED` now only lists `auth` and `credentials`; `tests/test_state_selection.py` passes unchanged.
12. Not in scope, not changed: `stages/acceptance_baseline.py:127` writes baseline image blobs through `write_bytes`. (The cycle-0 claim that `cli_video_review.py`, `media/narration.py` and `ui/routes_video_review.py` were out of scope is withdrawn: cycle 1 routes all three.)

## Fix cycle 1 (checker verdict FAIL cycle 0: F1, F2; W1-W4, O1 recorded)

### F1 (M51, BLOCK) - `Source.path` must be the logical path

Cause: in blob mode `store_media` returned `local_blob(target)`, a `.work/blob-cache/<sha>/<name>` path, and the adapters wrote that path into `Source.path`; once the cache was wiped the source was unreadable.
Fix (in place, no new module): `store/run_store.py` keeps a process-local `_LOGICAL` map (cache copy -> logical target), `store_media` fills it right after the put, and the new `source_path(path)` returns the logical path for a cache copy and `path.resolve()` otherwise (file mode: unchanged, the same string as before). Every place that builds a `Source` from an adapter-read path now calls it:
`sources/adapters.py` `register_document` and `register_audio`; `sources/email_register.py` `_register_unparseable_mbox` and `_register_unrecognised_attachment`; `sources/drive_register.py` `_register_unreadable_type`. `stages/ingest.py:123` (`register_source`, a user's local video path) is not a `store_media` product and is unchanged.
Tests (`tests/test_media_sources_blobs.py`): `test_a_registered_drive_source_records_the_logical_path_and_survives_a_cache_wipe` (a `.txt` through `register_document` and a `.png` through `_register_unreadable_type`), `test_a_registered_email_attachment_records_the_logical_path_and_survives_a_cache_wipe` (`.txt` through `register_document`, `.png` through `_register_unrecognised_attachment`): real `Source`s, the cache directory removed, `local_blob(Path(source.path))` returns the original bytes. `test_drive_and_email_sources_in_file_mode_record_the_same_path_as_today` pins file mode.

### F2 (M24/M51, BLOCK) - every `source.path` byte reader

Enumerated by grepping `source.path` across `src` and reading each hit. ROUTED = goes through `local_blob` (-> `materialize`).

| Reader | Disposition |
|---|---|
| `stages/source_material.py` `extract_document_text(...)` (`_material_document`) | ROUTED (cycle 1) |
| `stages/source_material.py` `file_sha256(...)` in `resolve_teaching_material` (the bytes-changed check; the checker's probe) | ROUTED (cycle 1) |
| `stages/source_material.py` `_reading_bytes` and `stages/ingest.py` `load_sidecar`: the `<path>.transcript.json` sidecar | NOT routed, by design: the sidecar is a user-supplied file beside a LOCAL recording; no writer puts it in the blob store (only the video, drive and email bytes are stored: `place_media` / `store_media`), so `materialize` has nothing to return and `local_blob` would hand back the same path. A blob-backed source has no sidecar, as before |
| `media/narration.py` `ensure_narration` | ROUTED (cycle 1): the video is `local_blob(logical)`; the sidecar is still looked up beside the logical path |
| `cli_video_review.py` `_review` | ROUTED (cycle 1), line-neutral (the file is at 300: `_secret_values` two lines folded into one) |
| `ui/routes_video_review.py` | ROUTED (cycle 1): the fallback to `Path(source.path)` goes through `local_blob` (`access.media_path` was already routed) |
| `stages/media_prep.py` (two sites), `stages/ingest.py` (two sites), `stages/video_access.py` `media_path` | ROUTED (cycle 0) |
| `cli_video.py`, `stages/issues.py`, `ui/app.py`, `ui/routes_sources.py`, `cli_video_review.py` (label lines) | NOT readers: they print or compare the path string; no bytes opened |
| `stages/ingest.py` `register_source` | writes a `Source` for a local video path: not a read |

Tests: `test_teaching_material_of_a_gridfs_only_video_and_document_is_available` (a video through `commit_video` and a DOC whose bytes are only in GridFS, cache wiped, then `resolve_teaching_material(store, src, [src])`: not `unavailable`, no "material unavailable" problem, the document unit text is read back; the checker's probe returned `['material unavailable (FileNotFoundError); re-register source']`), and `test_narration_of_a_gridfs_only_video_transcribes_the_verified_copy`.

### Verification (cycle 1)

| Command | Result |
|---|---|
| `uv run pytest tests/test_media_sources_blobs.py` | 15 passed |
| `tests/test_media_blobs.py tests/test_blob_scan_names.py` | 112 passed |
| `tests/test_source_adapters_drive.py tests/test_source_adapters_email.py` | 11 passed |
| `tests/test_sweep_u3a.py tests/test_drive_intake.py` | 30 passed |
| `tests/test_cli_video_review.py tests/test_cli_video_review_exits.py` | 62 passed |
| `tests/test_ingest_narration.py tests/test_ingest.py` | 14 passed |
| `tests/test_teaching_documents.py test_teaching_inputs.py test_teaching_media_dedupe.py test_pdf_teaching.py test_teaching_privacy.py` | 34 passed, 1 skipped |
| `tests/test_video_review_route.py tests/test_video_review_gates.py` | 32 passed |
| ruff / doctor | `ruff check src tests scripts`: All checks passed; `autotester doctor` (to `.work/doctor-u5b.txt`): exit 0, `doctor: clean` |
| `tests/test_source_adapters.py tests/test_source_adapters_audio.py` | 19 passed |
| `tests/test_zip_intake_register.py tests/test_ui_intake_drive.py` | 42 passed |
| full suite | NOT completed: a full `uv run pytest` was started and reached 19% (all passing dots) before the 590 s tool ceiling; the neighbour groups above are the evidence |

Mutation (`qa/evidence/mongo-store-u5b/mutations-d.json`, `mutation-run-d.txt`): 4/4 killed (d1 `source_path` records the cache copy; d2 `store_media` never records the logical path; d3 the sha256 reads `source.path` directly; d4 document extraction reads `source.path` directly). The first d2 (drop `.resolve()` in `source_path`) survived as an equivalent mutant and was replaced. Cycle-0 specs a/b/c are unchanged (24/24).

### Warnings and observations carried (no code in this unit)

- **W1 (M52 readiness, `blobs` area):** `stages/video_retention.py:81-90` `prune_old_videos` unlinks the local file only and does not delete the GridFS blob. Needed before G1 flips `blobs`, or retention is unbounded in GridFS.
- **W2 (M52 readiness, `blobs` area):** `place_media` reads the whole video into memory (`BlobStore.put` takes bytes; the upload cap is 2 GiB). A streaming `put` or a lower blob-mode cap is needed before G1 flips `blobs`.
- **W3:** a blob orphan if `add_source` fails after `place_media` (judgment call 6); not closed here.
- **W4:** `store/run_store.py` now has two jobs (run-result mixin plus media helpers); a split needs a D-122/D-123 module-list decision, so it stays one file for now.
- **O1:** the M54 deny-list passes non-UTF-8 bytes under `application/octet-stream`, and `put_file` defaults unknown suffixes to that type, so such bytes are stored unscanned (they cannot decode as text, so no secret in text form is in them).
- Caveat of the F1 mechanism: `_LOGICAL` is process-local and keyed by the cache path (`<sha>/<name>`), so two logical targets with the same sha and name share one entry (last write wins). The mapping is consumed in the same call chain that registers the `Source`, and the id is sha-derived, so identical bytes dedupe anyway.


## Pre-existing failure (not caused by U5b)

`tests/test_safe_names_windows.py::test_ordinary_names_still_pass[lpt0]` fails: `safe_name("lpt0")` raises because `_DIGITS` includes `"0"` (`core/safe_names.py:21`, identical at base `001d10d6`), while the test lists `lpt0` as an ordinary name. Introduced by the U4 cycle-1 device-name change (commit `7a835857`); `safe_name` and `_DIGITS` are untouched by this unit. Belongs to the U4 owner.

## Pending for the caller

`senior-software-engineer` review of the code commit (lifecycle rule "review"; the brief forbids dispatching checkers from here), and `data-engineer` is not needed. Merge note: U3d edits the same three `sources/` files; the lines above are the only ones U5b touches.
