# Verdict - mongo-store-u5b

**Verdict:** PASS
**Cycle checked:** 2
**Checker:** chk-mongo-u5b-a (fresh, independent; did not read any other checker's verdict on this unit)
**Code SHA checked:** `fdb4baa8` (manifest commit `e2fb613f` on `feat/mongo-store-u5b`; master `2d350794` merged as `e0033f0b`)
**Criteria judged:** M24, M25, M51, M54, M55, the U5b row, and the `core/image_privacy.py:_sanitize_one:stat` baseline row. Cycle-1 findings F1 (Drive video recorded the blob-cache path) and W1 (process-local `_LOGICAL` dict) re-judged.

## Findings

No Block. Two Warnings (both already recorded by the maker; neither falsifies a criterion).

1. **F1 (cycle 1 BLOCK) CLOSED.** `store_media` now returns the logical `target` in blob mode (`src/autotester/store/run_store.py:197-209`); the cache copy is never returned. Every adapter reads bytes through `local_blob(path)` and records `str(path.resolve())`: `sources/adapters.py:98-111` (`register_document`), `:180` and `:191-193` (`register_audio`, `_require_audio_file`), `:222` (transcriber gets `local_blob(path)`); `stages/ingest.py:114-118` (`register_source`), `:217` (`verify_source_bytes`), `:266` (`see_video`); `sources/drive_register.py:173` (unreadable-type hash). My own probes (below) show the Drive `.webm/.mp4/.mov` path no longer lands under `blob-cache`.
2. **W1 (cycle 1 WARNING) CLOSED.** `grep -rn "_LOGICAL\|source_path" src` finds nothing relevant (only the unrelated `schema/ledger.py:101` `_citation_source_path`). No module-global map; `_BLOBS` (`run_store.py:44`) only caches the store handle.
3. **Source constructor audit (done by me with `grep -rn "Source(" src`).** `git diff 2d350794 HEAD` shows zero change at every `Source(... path=...)` constructor versus master. Sites: `sources/adapters.py:69` (text, no path), `:116`, `:224` (`str(path.resolve())`, bytes via `local_blob`); `drive_register.py:82,150` (no path), `:169` (`path.resolve()`, path from `_write_bytes` = logical); `email_register.py:106` (no path), `:133` (user's local mbox, never passes `store_media`), `:191` (attachment, logical); `intake_commit.py:135` (`str(target)`, `place_media` logical); `stages/ingest.py:122` (`path.resolve()`, reads via `local_blob`); `acceptance_baseline.py:128` (project-relative, out of media scope); `read_context.py:128` (repo-relative reference); `ui/routes_sources.py:78,94` (user text or reference). Readers of `Source.path` all go through `local_blob`: `cli_video_review.py:249`, `media_prep.py:57,138`, `source_material.py:28,147`, `ingest.py:217,266`, `routes_video_review.py:78`, `video_access.py:174`; `narration.py:51` uses the logical path for the sidecar only. I found no raw reader left.
4. **Merge `e0033f0b` kept U3d.** Parents `a3f15955` and `2d350794`. `git diff 2d350794 HEAD --stat` outside `src/` shows only U5b files plus `pyproject.toml` (6 deletions) and `tests/test_sweep_u3a.py` (LEFT table: drive/email entries removed, `intake_commit.py` `os.replace` 2 -> 0). `intake_commit.py:32,96-99,140,146` still use U3d's `exists_path` / `delete_path` / `list_children`; `report_export.py:28,44` keeps `list_children`; `drive_register.py:46,195` and `email_register.py:43,217` keep `exists_path`. `_copy_in`/`_place` deleted, their logic moved into `place_media` (`run_store.py:212-235`).
5. **Baseline: exactly 6 rows dropped, none added** (`git diff 2d350794 HEAD -- pyproject.toml`): `image_privacy:_sanitize_one:stat`, `drive_register:_write_bytes:write_bytes`, `email_register:_write_attachment_to_disk:write_bytes`, `intake_commit:_copy_in:os.replace`, `_place:mkdir`, `_place:os.replace`. No media row moved to `permanent`; the remaining U3d/M53-gated rows (`mkdir`, `read_bytes`, lock) are untouched. Doctor clean, no `state-bypass-stale`.
6. **M24 holds.** Writers put through `put_file`/`write_blob_file` with `masked=True` only for post-`MASK_CSS` captures (`browser/evidence.py:160`, `stages/leak_evidence.py` `write_blob_file(..., masked=True)`); frames are `kind="frame"` (`stages/media_prep.py`); `RunStoreMixin.save_result` (`run_store.py:53-58`) syncs blobs before writing the result JSON (mutants b3/b4 killed). Evidence schema untouched. M23 mirror: my probe `test_m23` shows an unmasked screenshot refused with nothing stored.
7. **M25 holds.** A fresh interpreter importing `run_store`, `drive_register`, `email_register`, `intake_commit`, `ingest` with no `AUTOTESTER_STORE*` env has no `pymongo`/`gridfs` in `sys.modules` (my probe `test_m25_no_pymongo`). The driver is imported lazily in `blob_store()` (`run_store.py`, the `from autotester.store import mongo_backend, mongo_guard` inside the function).
8. **M54 holds.** My probe stores nothing and raises `BlobRefused` for a secret in bodies typed ndjson, jsonl, sql, toml, x-sh, text/csv, multipart/form-data, message/rfc822, rtf, empty, bare `text`, and also `image/png`, `application/octet-stream`, `video/mp4` (UTF-8 decodable), on both `FileBlobStore` and `MongoBlobStore`.
9. **M55 holds.** My probe over 14 hostile keys (`PROFIL~1/x`, `a::$INDEX_ALLOCATION`, `foo:bar`, `nul`, `con`, `aux`, `prn`, `com1`, `lpt1`, `p/NUL.txt`, `p/WORK~2.TXT`, `p/a:b/c`, `x/..`, `C:/x`): put/get/stat/delete/materialize raise only `UnsafeName` on both stores and the tree is unchanged.
10. **Line cap and split.** `tests/test_media_sources_logical.py` 143 lines, `tests/test_media_sources_blobs.py` 200, `store/run_store.py` 235, `stages/ingest.py` 299 (at the cap, line-neutral); the doctor's line and function rules are clean. The split is legitimate: shared helpers are imported from the sibling (`from test_media_sources_blobs import VIDEO, _commit, _store`), no copies.
11. **WARNING (recorded by maker; not a criterion failure).** `place_media` reads a whole recording into memory for the put, and a blob orphan is possible if `add_source` fails after `place_media` (`commit_video` only deletes the local path). `prune_old_videos` does not delete blobs. These belong on the M52 readiness table for `blobs`.
12. **WARNING (design note).** Screenshots and kept videos stay on local disk as well as in GridFS (write-through; `local_blob` is local-first). Source media (M51) leaves nothing under the data root, as the criterion requires; M24 does not forbid the local copy. A blobs-area flip at G1 should state that run evidence is still mirrored on the container disk.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u5b`, `PYTHONPATH=<worktree>\src`, two files per call, `env -u ANTHROPIC_BASE_URL`)

| Command | Result |
|---|---|
| `pytest tests/test_media_sources_blobs.py tests/test_media_sources_logical.py -o addopts=` | 17 passed |
| `pytest tests/test_ingest.py tests/test_source_adapters_drive.py -o addopts=` | 15 passed |
| `pytest tests/test_state_bypass_rule.py tests/test_sweep_u3a.py -o addopts=` | 84 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor` (redirected to `.work/chk-doctor.txt`) | exit 0, `doctor: clean` (only the 2 advisory D-087 known-disputed warnings) |
| my probe `scratchpad/probe/test_chk_probe.py` (blob mode via `blob_area`, file mode via `file_area`) | 13 passed: Drive `.txt .png .mp3 .webm .mp4 .mov .pdf .xyz` and email `.txt .png .mp4 .docx` each register, cache wiped, `Source.path` has no `blob-cache`, `local_blob` returns the bytes, no media file under the data root; `register_source` on a Drive video then `verify_source_bytes` after a wiped cache passes and a second register dedupes; two folders `A`/`B` with identical name and bytes keep their own logical paths, same folder with different bytes gets a digest-prefixed name; file mode `Source.path == str(path.resolve())`; a local upload outside the data root in blob mode records its own path |
| my probe `scratchpad/probe/test_chk_probe2.py` | 30 passed (M55 x14, M54 x14, M23, M25) |
| `scripts/mutation_check.py qa/evidence/mongo-store-u5b/mutations-{a,b,c,d,e}.json` | a 5/5, b 10/10, c 9/9, d 2/2, e 6/6 killed (32/32), each exit 0 |

The full suite was not run (instruction). `tests/test_safe_names_windows.py::test_ordinary_names_still_pass[lpt0]` is the known U4 failure and was not touched. No `.env` value was printed.

## Result

U5b cycle 2 satisfies M24, M25, M51, M54 and M55. F1 and W1 are closed by a stateless redesign whose property (logical path in both modes, bytes via `local_blob`) I verified with independent blob-mode probes and 32/32 killed mutants. PASS.
