# Verdict - d110-near-miss-test (cycle 0)
Verdict: PASS
Cycle checked: 0
Head tested: dfe1b3e6 (code be42bb8c on fix/d110-near-miss-test). Base 0f89becc. Judged against D-110 criterion C4 and qa/contracts/auth.md AU18/AU19. Fresh context; maker reasoning not read beyond the manifest.

## Findings
1. PASS - C-scope: no src change. `git diff master..HEAD -- src` is empty (0 bytes); the branch touches only `tests/test_ui_origin_guard.py` (+17) and the manifest (+32).
2. PASS - C1/C2: `tests/test_ui_origin_guard.py:256-271` pins 8 near-miss tokens as False (`**`, `*.evil.com`, `https://*`, `*:443`, `'*'`, `"*"`, `%2A`, U+FF0A) and 4 whole-token forms as True (` * `, `*,a.com`, `a.com *`, `a.com,*`), matching the manifest list exactly. It asserts `_allow_all(...) is expected` against `src/autotester/ui/helpers.py:201-203`.
3. PASS - passes on real code: 12 new cases pass; the whole file is 140 passed.
4. PASS - C3 load-bearing: own reproduction in a full scratch copy (src, tests, scripts, pyproject under `.work/mutrepo_chk`) with the mutation `return "*" in os.environ.get(name, "")` at helpers.py:203. Module confirmed loaded from the copy (`__file__` printed the scratch path). Result: 6 failed, 6 passed. Failed: `[**-False]`, `[*.evil.com-False]`, `[https://*-False]`, `[*:443-False]`, `['*'-False]`, `["*"-False]`. Unmutated copy: 12 passed (control). Closes checker-B finding 1 of d110-allow-all.
5. NOTE (non-blocking) - `%2A` and U+FF0A pass under the substring mutant; they guard decode/normalise mutants only. This was disclosed in the manifest and is not a gap in the criterion.
6. PASS - hygiene: test file is 271 lines (cap 300); function is 16 lines; no secrets or .env values touched.

## Commands run
- `git -C <wt> diff master..HEAD -- src | wc -c` -> 0; `wc -l tests/test_ui_origin_guard.py` -> 271
- `uv run pytest tests/test_ui_origin_guard.py -o addopts= -k allow_all_matches` -> `12 passed, 128 deselected`
- `uv run pytest tests/test_ui_origin_guard.py -o addopts=` -> `140 passed, 2 warnings`
- `uv run ruff check tests/test_ui_origin_guard.py` -> `All checks passed!`
- `uv run autotester doctor` (redirected to .work/doctor_chk.txt) -> exit 0, `doctor: clean` (2 known-disputed advisories, non-blocking)
- Mutant run: `PYTHONPATH=<copy>/src .venv/Scripts/python.exe -m pytest tests/test_ui_origin_guard.py -o addopts= -k allow_all_matches` -> `6 failed, 6 passed`; control `12 passed`. Scratch copy deleted afterwards.
- Full suite not run (low-memory machine; test-only unit, one test file touched).

Residual: none blocking. Merge/push left to the maker per instruction.
