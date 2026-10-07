# Checkpoint — t151-target-discovery (coordinator A), cycle 1

Env fingerprint: win32, Python 3.11.15 (bound .venv), uv 0.11.27. Base 2fae2504; HEAD 18243792 (branch codex/t151-target-discovery).
Code hashes (md5, first 12): discover.py b70a82a6a060 · read_context.py 1d9cd176dcc4 · ai_target.py 431e8c86ecd6 · mock.py 584d2f7f37f7 · prompt fa87c8d7a34b · tests/test_discover.py 0fec7aba0df9 · conftest ad7ebcecae5d · pyproject b6a5cf452b34 · uv.lock 2d4131617721.
Attribution: coordinator A (claude-sonnet-subagent) plus three read-only sub-checkers (falsification copies under C:/Users/Lenovo/AppData/Local/Temp/claude/checker-a-t151/).

| check | command / scope | result |
|---|---|---|
| ruff | uv run ruff check src tests scripts | All checks passed |
| doctor | uv run autotester doctor | 5 violations, all decision-citation-dangling D-065 in the manifest (D-065 is on master only); with master DECISIONS.md copied in, only stale docs/SNAPSHOT.md remains |
| targeted | uv run pytest tests/test_discover.py (63 collected) | 63 passed |
| obsidian grep | grep -rniE obsidian pyproject.toml | no output, exit 1 |
| falsification rows | per-copy, green-before verified | see verdict; AI1 reader-line, AI8 non-Markdown, C5 YAML alias rows not reproduced as claimed |
| full suite | uv run pytest (one run, no -x) | see verdict |
| full suite | uv run pytest, no -x; started 07:14 | INCOMPLETE at 07:57 (about 55%, 2 unattributed F); evidence neither way; rerun in cycle 2 |
Verdict FAIL cycle 1 in qa/verdicts/t151-target-discovery.md. Sub-checker copies kept in the scratch dir (outside the repo).

# Cycle 2 (coordinator A, repair checker) — 2026-10-07

Env fingerprint: win32, Python 3.11.15 (bound .venv), uv 0.11.27, host heavily loaded by unrelated pytest runs. Base 2fae2504; HEAD a9307c2e (branch codex/t151-target-discovery). Policy proportional-verification/2026-10-06.6.
Code hashes (md5, first 12): discover.py 73af00785b39 · read_context.py 0767d7d4fc7a · text_lines.py d13c0cafbab8 · credential_files.py 4652ac672952 · ai_target.py 0d6a53b4e1e9 · mock.py 584d2f7f37f7 (unchanged since cycle 1) · prompt fa87c8d7a34b (unchanged) · tests/test_discover.py 0fec7aba0df9 (unchanged) · tests/test_discover_hardening.py d7c42be3ef75 (new) · conftest ad7ebcecae5d (unchanged) · pyproject b6a5cf452b34 (unchanged) · uv.lock 2d4131617721 (unchanged) · docs/DECISIONS.md 4a4934b854c9.
Attribution: coordinator A (claude-sonnet-subagent), no sub-checkers (SERIAL: none needed; falsification rows ran as parallel processes in isolated copies). Scratch (outside repo): C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/a2bbaa41-59b6-48f1-8ec7-8aa0d97b8a5a/scratchpad/ (copy-base, row-*, probe_a2.py, falsify_a2.py, fullsuite.log).

| check | command / scope | result |
|---|---|---|
| full suite (the ONE) | `uv run pytest` bound worktree, no -x, no -q; wrapper PID 270012 (uv), python PIDs 30620/20064; 09:22:16 to 10:47:56 +05:30 | 4 failed, 2286 passed, 6 skipped, 14 xfailed in 5139.06s (2310 collected). All 4 failures attributed unrelated: crawl_inventory_live (wall_clock_s) and redact_wrap_perf and mc_sessionstart healthy_log fail identically on base 2fae2504 copy; mc_sessionstart unhealthy_line passes alone on both |
| ruff | uv run ruff check src tests scripts | All checks passed |
| doctor | uv run autotester doctor (bound tree) | doctor: clean |
| targeted | pytest tests/test_discover.py tests/test_discover_hardening.py tests/test_citations.py in copy-base (hashes equal to bound) | 101 passed in 39.60s |
| obsidian grep | grep -rniE obsidian pyproject.toml | no output, exit 1 |
| independent probe | probe_a2.py (96 checks: AI1 lines x 9 separators x 3 EOLs reader+scan, AI8 non-md and vault, C5 alias x8 shapes x 2 limit sets) in copy-base | 96/96 ok. Same probe on cycle-1 src (18243792): 59/96 fail (reader/scan lines) |
| provider probe | all Provider.act/grade patched to raise; scan + read_context on fixture | 0 calls, 4+4 signals |
| falsification AI1 | text_lines.split_lines -> text.splitlines() (row copy) | 2 passed -> 2 failed -> 2 passed |
| falsification AI8 | `.lower() != ".md"` -> `not in {".md",".txt"}` | 1 passed -> 1 failed -> 1 passed |
| falsification C5 alias | AliasEvent branch -> `if False` | 2 passed -> 1 failed (non-cyclic) -> 2 passed |
| falsification C5 alias (both guards) | AliasEvent branch and `_metadata` cycle guard -> `if False` | 2 passed -> 2 failed -> 2 passed |
| falsification dangling citation | docs/DECISIONS.md `## D-065` -> `## D-0650` | 1 passed -> 1 failed -> 1 passed |
| diff since cycle-1 head | git diff 18243792 HEAD -- src tests | read in full; no deleted/renamed public symbol (`_credential`/`_CREDENTIALS` private, moved to credential_files.is_credential, no other importer) |
Verdict PASS cycle 2 in qa/verdicts/t151-target-discovery.md (cycle-1 verdict renamed to .r1-1.md unread).
