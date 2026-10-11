# Checkpoint — t198a-zip-drive-intake, coordinator A, cycle 0

Head 894549ee (product 642575ce). Checker: claude-sonnet-subagent (seat A). Policy .9. Verdict: FAIL (qa/verdicts/t198a-zip-drive-intake.a.md).

| Check | Command / scope | Code hash | Result |
|---|---|---|---|
| Criterion tests + falsification | worktree .venv python, `-p no:xdist`, named test files only; 14 mutants, one throwaway copy each; sub-checker T1 (zip core), T2 (Drive, limits), T3 (gate, provenance); notes t1-zip-core.md, t2-drive-limits.md, t3-gate-provenance.md, t3-pytest-run1.log | commit 894549ee | 14 red on intended assertion; 2 mutants survive (ruled) |
| TI5 reproduction | probe-ti5-lzma-and-zipversion.py (own, `-I`) | zip_intake.py @894549ee | 60/60 LZMA flips unhandled `_lzma.LZMAError`; extract_version 99 unhandled `NotImplementedError` |
| Zero-inflate probe | probe-ti2-declared-oversize-zero-inflate.py | same | 0 inflate calls for a declared-oversize member |
| Multipart memory | probe-upload-field-memory.py (and R3 probes) | upload_stream.py @894549ee | 61.6 MiB at a 64 MiB limit; 80 MB peak for a 40 MB body |
| Full suite | `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref 894549ee --shards 4 -- -o addopts=`; root .venv python | same | 3748 collected, 3722 passed, 7 failed (4 known, 2 load/flake, 1 this unit's test_ti6), 19 skipped; suite-summary.json, suite-run.log |
| Browser walk | sub-checker, 1 lane, persona walk | same | qa/evidence/browser-t198a-zip-drive-intake-2026-10-11-checker/ |
| Diff scope, credentials, adversarial | sub-checkers R1, R2, R3 | same | r1-diffscope-rulings.md, r2-credentials-stderr.md, r3-adversarial-read.md |

Environment: Windows 11, python 3.11 (uv), python-multipart 0.0.32. No real Drive call, nothing sent to an external service.
Attribution: seven read-only Sonnet sub-checkers (T1-T3, R1-R3, browser); coordinator reproduced F1, F2, F3 and wrote the verdict.
