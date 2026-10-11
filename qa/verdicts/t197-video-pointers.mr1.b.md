# Verdict: t197-video-pointers (merge-reconcile 1, coordinator B)

VERDICT: PASS
TIER: L (dual check, trigger `security src/autotester/cli_video_review.py:75`); this is coordinator B, blind to A
Policy-Version: proportional-verification/2026-10-10.9
Cycle checked: 2
Merge-reconcile: 1
Repair base: b59dda0d (dual PASS, cycle 2). Merge: 89371ca4 (parents b59dda0d, master d42e9445). Head: df5d6f5b (manifest-only over the merge).
Scope: the reconcile only. Earlier verdicts, checkpoints and any `.a` / `-A` evidence were not opened.

## Plan
Three `git archive` copies on C: (b59dda0d, d42e9445, df5d6f5b), each with its own venv and a random suffix; `autotester.__file__` confirmed on the first line of every probe log. Every row ran as a subprocess of the copy's own python (`-I`). Only fakes: a `Provider` subclass patched over `providers.get`, and `FakeDrive` patched over `cli_intake.default_drive`. Fake canary secrets only; no `.env` read; no network, browser or model call; no full suite, no suite lock.

## Diff scope (set analysis against merge-base 09828f2d)
- Unit changed 30 files, master 751. Overlap: `docs/MAP.md`, `src/autotester/cli_video.py`, `src/autotester/core/paths.py`, `tests/test_cli_advice_resolves.py`.
- Unit-only files whose merged content differs from b59dda0d: `stages/video_review_render.py`, `tests/test_video_review.py`, `tests/test_video_review_gates.py`, `tests/test_video_review_guards.py` (all the `render_html` to `render_review_html` rename).
- Master-only files whose merged content differs from d42e9445: `docs/SNAPSHOT.md` (generated).
- Files touched by neither side: none. Head vs merge: `qa/manifests/t197-video-pointers.md` only.

## Table 1: unit surface, head vs b59dda0d (`ingest review`, 75 rows)
Rows covered: ok, dry-run, partial by cost cap, failed, pointer errors incl. the 32768/32769-byte boundary, refused without approval, unreadable source, usage errors (json and text), provider exception, bad `--redact`, nan/inf/negative cap. Compared: exit code, JSON (status, `exit_code`), stderr shape, files left under `reviews/`.
- Rows: 75 vs 75, ids equal. Identical: 74. Different: 1.
- r21a-provider-unknown-json: the "known providers" list on head is `anthropic, gemini, langchain-fallback, litellm, mock`; on b59dda0d it lacks `litellm`. `litellm` is master's provider (d42e9445 registers it), so this is inherited from master, not a reconcile defect. Exit code (1) and JSON shape are the same.

## Table 2: master surface, head vs d42e9445 (`cli_video.py` + `cli_intake.py`, 43 rows)
Rows: register (ok, missing, not a recording, dir, twice, no project), list, zip (ok text/json, mixed, missing, not a zip, twice, empty, corrupt member), fetch-drive (hostile links, file, folder partial, no project, twice, via FakeDrive), prep, frames, run, analyze, map, and the three `--help` outputs.
- Rows: 43 vs 43, ids equal. Identical: 40. Different: 3.
- h01-ingest-help: head's `ingest --help` lists the added `review` command (expected, the unit's command).
- u01-run-mock, u04-run-unknown-provider: stderr is a rich traceback (the mock/unknown provider raises an uncaught error by design). The only difference is the copy name in the path and `cli_video.py` line numbers shifted by +2 (the added import and registration). Same exception text, same exit code (1).
- Exit codes, stdout JSON and the files left on disk are equal in all 43 rows. A first run of this table (v1) had a harness bug (it used `ApprovalKind.VIDEO_REVIEW`, which master lacks); it is kept as `INVALID-v1-*` only, and the verdict rests on the corrected re-run.

## Table 3: whole CLI tree, head vs master vs unit
- Commands on head = master (42) plus `ingest review`, nothing removed. Head vs unit: only the commands master added (`ingest zip`, `ingest fetch-drive`, `release-report`) differ, nothing missing.
- `--help` byte-compare, master vs head: differs in two places only. `ingest` (the added `review` line) and `approve` (the `--kind` choices gain `video_review`, a unit change; head's text equals the unit's).
- Root and `expand` help differ unit vs head only through master's additions. `review --help` is byte-identical unit vs head.
- `tests/golden/cli_commands.json` is not tracked in any of the three commits (it exists untracked in the D: working tree), so no golden pins the tree. The tree comparison above is the pin.

## Render equality
- Review HTML and Markdown for ok, partial and failed reviews: sha256 equal, b59dda0d vs head (6 of 6). The rename is the only change in `stages/video_review_render.py`.
- Master's unified-report render (empty and full): sha256 equal, d42e9445 vs head (2 of 2).

## core/paths.py
- Head is 298 lines. Directory trees from `ensure()` are identical across master, unit, head and a plain three-way-merged variant. The variant's 48 property values equal head's (0 diffs).
- `review_path` and `review_work_dir` on head equal the unit's; `case_proposals` on head equals master's. The only differences against a single side are the properties that side lacks.

## Gates on head
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean.

## Falsifications (throwaway copies, discarded)
1. Removed the `app.command("review", cls=ReviewCommand)(review_cmd)` registration in `cli_video.py`. Green before: 146 passed. Red after: 61 failed, 84 passed; failures in `tests/test_cli_video_review.py` (19) and `tests/test_cli_video_review_exits.py` (42). The pass total fell by one, a tree-parametrised case.
2. Removed `register_intake_commands(app)`. Green before: 58 passed. Red after: 7 failed, 49 passed, all in `tests/test_cli_intake.py` (for example `test_ti1_the_cli_refuses_a_hostile_member_and_writes_nothing_outside`, `test_ti7_fetch_drive_registers_through_the_fake_and_exits_0`). A diff confirmed exactly one line was removed in each copy.

## PROPOSED-ISSUE (no ledger write; the maker files them after both coordinators PASS)
- PROPOSED-ISSUE low (docs): `docs/SNAPSHOT.md` in the merge differs from master's in the generated decisions list (D-085 appears). Generated file; regenerate on the next `autotester snapshot`.
- PROPOSED-ISSUE low (wording): the manifest's earlier "paths.py exactly 300 lines" claim is superseded; the file is 298 lines after the reflow.
- PROPOSED-ISSUE low (test): no tracked golden pins the CLI command tree (`tests/golden/cli_commands.json` is untracked in the working tree). A dropped registration is caught only by behavioural tests (the falsifications above show they do catch it).
- PROPOSED-ISSUE low (security, inherited): text-mode `internal_error` of `ingest review` prints the exception message, which may include secret-like text the redactor does not know. Identical at b59dda0d, so not a reconcile defect.

## Harness note
One compound Bash command (an in-place `sed` plus background subshells) was denied by the permission system. It was not worked around; the script was rewritten as a heredoc and run with `run_in_background`.

## Evidence
`qa/evidence/t197-video-pointers-mr1-B/` (probes, result JSONs, render hashes, paths, ruff/doctor/falsification logs). Checkpoint: `qa/checkpoints/t197-video-pointers.mr1.b.md`.

Metrics: lane=full tier=L coordinator=B start=2026-10-11T20:58:33Z end=2026-10-11T22:06:00Z check_s=4050 mutants=2 defects_unit=0 defects_6c=0 slow="falsification-1 green run 340s" full_suite=no
