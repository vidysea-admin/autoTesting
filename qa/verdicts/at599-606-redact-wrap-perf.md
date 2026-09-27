# Verdict — at599-606-redact-wrap-perf

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checked commit:** 885fb2a (code), e7d66a0 (manifest)
**Checker:** /checker session (claude-opus) + a fresh claude-opus security subagent (adversarial probes in scratch copies)

```
VERDICT: FAIL
SCOREBOARD: the newline/CR/MIME wrap forms of AT-599 are closed and AT-606's linear-time expectation is met; 2 failure lines
FAILURES:
- [AT-599 expected: "line breaks (and whitespace inside base64-alphabet runs) removed, or disclose it as a named residual"] sev: medium · A declared secret's encoding split by a SPACE, a TAB, or a newline followed by indentation still evades `contains_folded` / `assert_no_raw_secrets`, and the manifest neither closes nor discloses this. Checker repro (worktree, fake secret 'FakeSecretValue-12345', base64 split at offset 10): newline -> caught True; space -> False; newline+4-space indent -> False. The subagent's full matrix: every offset, all 4 declared encodings, lengths 8/12/20/40 -- unchanged from master. Realistic carriers are YAML/PEM blocks in config, RFC 5322 header folding and indented log dumps. · In redact_wrap.py, strip `\s+` (not just `\r\n|\r|\n`) from the searched copy; the subagent's what-if found 0 false positives on 9.3 MB of benign corpora. Or disclose the residual in the contract via the checker. Add tests for space, tab and indent splits. · issue: AT-599 (stays open)
- [capability claim: lru_cache on `declared_secret_encodings` is part of the speed-up] sev: low · No row kills it. Removing ONLY that cache leaves every test green (row 4, 1 passed), so the speed-up is entirely the `_is_ignorable` cache (row 3: 6.04 s vs the 3 s bound). The cache also retains up to 256 raw secret values plus encodings in process memory for the process lifetime. That is not a C5 breach, since it is memory only and `cache_info` exposes counts only, but it costs retention for no measured gain. · Drop the `declared_secret_encodings` cache (preferred; this also removes the retention), or add a row that isolates it. · issue: AT-599/AT-606 unit claim
CAPABILITY-COVERAGE: 4/5 rows kill as named. Row 1 (wrap branch -> `if False:`) fails exactly the 8 AT-599 detection tests. Row 2 (both caches removed) fails the bound test (6.37 s). Row 3 (`_is_ignorable` cache only) fails the bound (6.04 s). Row 5 (checker's own, a quadratic strip) fails the ratio test (3.70x). Row 4 (encodings cache only) SURVIVES -> the FAIL line above. Disclosure (a) is accurate: the ratio test is a non-vacuous guard for a property the pre-fix code already had (master scaled ~9x for 10x size), so INCONCLUSIVE is honest labelling, not a hidden gap.
LIVE-BROWSER: not-applicable (changed paths: core/redact_encodings.py, core/redact_fold.py, core/redact_wrap.py, tests, docs/MAP.md; no UI surface)
ISSUES-WRITTEN: none new for this unit (AT-599 stays open; AT-606 judged met, flips on merge of a passing cycle)
EXECUTOR: maker builder (checker: claude-opus session + claude-opus security subagent)
EXPLANATION: The wrap fix is correct for the forms it claims: 0 leaks at every offset for LF, CRLF and CR, for 64/76-char wraps and for MIME blobs, where master leaked nearly everywhere. It only changes what is searched, never the returned text (6 benign corpora, byte-identical, newlines kept), and the scan is now near-linear at ~5x faster. But AT-599's own expected clause names whitespace inside base64 runs, and those forms still leak undisclosed. Separately, one of the two claimed caches does nothing measurable while holding secret values.
```

## What I re-ran

- `uv run pytest` (full, no -q) in the worktree: **1861 passed, 6 skipped, 32 xfailed, 0 failed** in 703.66 s, exit 0.
- `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean.
- Targeted run (subagent): 103 passed across test_redact_wrap_perf / test_redact_obfuscation / test_core / test_secrets.
- Line counts: redact_fold.py 300/300 (at the cap), redact_wrap.py 61, redact_encodings.py 127.

## False negatives: master vs worktree (subagent matrix, fake secrets, public entry points)

| form | master | worktree |
|---|---|---|
| `\n` / `\r\n` / `\r` at every offset (b64, b64url, b32, hex) | leaks almost everywhere | **0 leaks** |
| wrap every 64 / 76 chars, every 8 chars; MIME `encodebytes` blobs | leaks | **0 leaks** |
| space or tab at every offset | leaks | **still leaks** (FAIL line 1) |
| newline + indent at every offset; 76-wrap + indent | leaks | **still leaks** (FAIL line 1) |
| split across two scrub calls; `%XX` URL-encoding (not a declared encoding) | leaks | leaks (inherent / not claimed; note only) |

No regression against master in any form.

## False positives

6 benign corpora, 9.3 MB in total: a 2 MB wrapped base64 image, 20k JSON log lines, 10k HTML blocks, 300 stack traces, 20k sha256 lines, 20k hex lines. Result: **0 hits, 0 gate raises**, on both master and the worktree, and scrub output unchanged. The `\s+` what-if also gave 0 false positives.

## Perf (fresh process, 3 fake secrets, `contains_folded` + `assert_no_raw_secrets`)

| input | 100 KB | 250 KB | 500 KB | 1 MB |
|---|---|---|---|---|
| mixed, worktree | 0.15 s | 0.45 s | 0.84-1.03 s | 1.88-2.17 s |
| mixed, master | 1.04 s | 2.31 s | 5.88 s | 9.01 s |
| CJK-heavy, worktree | 0.86 s | 2.51 s | 4.13 s | 8.36 s |

Near-linear (~2.0-2.5x per doubling). AT-606's linear-time expectation is met. The bound test uses 500 KB rather than the ~1 MB AT-606 names; that is an approximate figure, so it is not charged.

Note: CJK-heavy text still costs ~8.4 s/MB because the 4096-entry `_is_ignorable` cache thrashes. It is linear but slow, a follow-up candidate, not charged here.

## Diff scope (4c)

Merge-base fc3e07f. The unit touches docs/MAP.md (+1 row), the 3 core files, the new test file, the manifest and the evidence log; all are in "What changed". The only removed line is the `redact_fold.py` docstring's closing line, re-added without its closing quotes so the AT-606 note can follow (lines 107-110). No function, test or key removed. Trivial: redact_wrap.py is LF while its siblings are CRLF.

---

# Verdict — at599-606-redact-wrap-perf, cycle 2

**Date:** 2026-09-26 · **Cycle checked:** 2 · **Checked commit:** 6cd6416 (code), 54cfd7f (manifest) · **Checker:** /checker session (claude-opus)

```
VERDICT: PASS
SCOREBOARD: both cycle-1 failure lines closed; AT-599 (all whitespace splits) and AT-606 (linear-time scan) met
FAILURES: none
CAPABILITY-COVERAGE: The new row reproduced in my own copy (18/18 green before). Setting `_WHITESPACE_RE` back to `r"\r\n|\r|\n"` fails exactly the 6 new split tests (space, tab and newline+indent, each via contains_folded and assert_no_raw_secrets); the benign space-prose test stays green. The cycle-1 rows still stand (wrap branch -> 8 AT-599 tests; `_is_ignorable` cache -> bound test). The encodings cache is removed, so FAIL line 2 no longer applies.
LIVE-BROWSER: not-applicable (changed paths: core/redact_encodings.py, core/redact_wrap.py, tests, docs/MAP.md; no UI surface)
ISSUES-WRITTEN: none (AT-611, CJK perf, stays a separate low follow-up)
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: redact_wrap.py now strips `\s+` from the searched copy only. My own probe (fake 21-char secret; base64, base32 and hex; separators space, tab, `\n    ` and `\r\n  ` at every offset) finds 0 misses. The declared_secret_encodings lru_cache and its functools import are gone, removing the in-memory retention of secret values with no timing change (builder: 0.63 s vs 0.62 s). The perf tests pass 3/3 on my runs.
```

## What I re-ran

- Whitespace probe (worktree, read-only): b64 0 misses, b32 0 misses, hex 0 misses, across 5 separator forms at every split offset.
- Row reproduction in scratch copy `at599c2-row1`: 18 passed before -> 6 failed / 12 passed after the edit, each failure being a new split test.
  - My first attempt used an unquoted heredoc, which mangled the regex in the COPY. That was my error, not the unit's. I discarded it and redid the row with a quoted heredoc. The worktree was never touched.
- `tests/test_redact_wrap_perf.py` 3 consecutive runs: 18 passed each (2.2-2.4 s).
- `uv run pytest` (full, no -q): **1869 passed, 5 skipped, 32 xfailed, 0 failed** in 697 s, exit 0. Ruff: All checks passed. Doctor: clean.

## False-positive surface

Stripping all whitespace can join adjacent words, but the needle is still an exact, case-significant substring of a declared secret's own computed encoding. Cycle 1's what-if on the same `\s+` strip found 0 false positives across 9.3 MB of benign corpora (a wrapped base64 image, JSON logs, HTML, stack traces, sha256 and hex lines), and the new benign space-prose test pins the common case.

## Diff scope (4c)

`6ec5702..6cd6416` changes docs/MAP.md (the redact_wrap row text), redact_encodings.py (removes `import functools`, `@functools.lru_cache(maxsize=256)` and its docstring line, as FAIL line 2 required), redact_wrap.py (the regex rename and widening; docstrings rewritten are this unit's own cycle-1 text), tests/test_redact_wrap_perf.py (+7 tests, none removed) and the manifest. All are listed in "What changed". redact_fold.py is untouched (300/300).

AT-599 and AT-606 flip to fixed only after the merge is verified on master.
