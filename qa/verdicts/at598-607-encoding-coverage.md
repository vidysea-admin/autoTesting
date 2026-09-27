# Verdict — at598-607-encoding-coverage

**Date:** 2026-09-26
**Cycle checked:** 1
**Checker:** /checker (standing checker session, orchestrator plus 5 parallel fresh-context lenses: rows, diff scope, adversary, perf, route)
**Contract:** qa/contracts/core-invariants.md C5 (secrets never reach a model or artifact), C2, C3, C7; issues AT-598, AT-607
**Branch / code commit:** at598-607-encoding-coverage · 8e24e39 (manifest f186f59), base 7f08a3f

```
VERDICT: PASS
SCOREBOARD: 3/3 criteria met (AT-598 double-b64 needles, AT-598 UTF-16-LE/BE hex needles, AT-607 floor + b32 offset-1 gap documented and pinned), 4/4 invariants hold (C2 caps, C3 one mechanism, C5 no regression, C7 sabotage rows)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced in own copies (10 red / 8 red on the named tests)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/core/redact.py, core/redact_encodings.py, tests/test_redact_encoding_coverage.py; no UI surface)
ISSUES-WRITTEN: AT-617 (medium, pre-existing on master: base64 of UTF-16 bytes, PowerShell -EncodedCommand, bypasses both doors; not charged to this unit)
EXECUTOR: maker builder (checker: claude-opus orchestrator + sonnet subagents)
EXPLANATION: Both new needle families are additive. The extracted _isolated_variant_needles is behaviour-identical: old needle set ⊆ new in 768/768 fake secrets. There are 0 false positives over a 211 KB clean corpus, and perf is 1.06x master and still linear. AT-607's issue text explicitly allows route (b), and the empty-core math at offset 1 was re-derived. The single full-suite failure is the AT-518 flake, which fails identically on master.
```

## What the checker re-ran itself

- Full suite on the tip, run serially: `uv run pytest` gave `1 failed, 1934 passed, 5 skipped, 32 xfailed in 853.46s`. The one failure is `tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild`, the known **AT-518** flake. It failed on master in 2 of 3 isolated runs this session, with the identical `child.pid` FileNotFoundError. This unit does not touch flake_probe.
- `tests/test_redact_encoding_coverage.py` gave 25 passed. `pytest tests/ -k redact` gave 113 passed. The existing `tests/test_redact_obfuscation.py` gave 56 passed. ruff reported `All checks passed!` and doctor reported `doctor: clean`.
- Perf (AT-606/AT-599): `tests/test_redact_wrap_perf.py` gave 18 passed on the branch.
  - 500 KB corpus, min of 3, with the same venv against a git-archive copy of master: combined 1.631 s vs 1.541 s (1.06x).
  - Doubling from 250 to 500 KB: 1.885x on the branch vs 1.993x on master. Both are linear.

## Capability rows (own copies `<scratch>/at598-row<k>`)

| row | edit (single hunk, redact_encodings.py) | before | after |
|---|---|---|---|
| 1 | `_double_b64_needles` returns `[]` | 25 passed | 10 failed: `test_contains_folded_catches_double_base64[*]` x4, `test_assert_no_raw_secrets_blocks_double_base64[*]` x3, `..._at_outer_byte_alignment[*]` x3 |
| 2 | `_utf16_hex_needles` returns `[]` | 25 passed | 8 failed: `test_contains_folded_catches_utf16_hex[*]` x6, `test_assert_no_raw_secrets_blocks_utf16_hex[*]` x2 |

All of them are real AssertionError or DID NOT RAISE failures on the named tests, not import errors. The AT-607 pin tests assert a documented absence rather than a guard, so C7's sabotage duty does not apply to them. That follows the same reasoning as the checker-PASSed at599-606 precedent.

## Diff scope (4c)

- The diff touches exactly 4 files: the manifest, redact.py (a docstring-only AT-607 paragraph), redact_encodings.py (+65/-5) and the new test file.
- The 5 removed lines moved verbatim into `_isolated_variant_needles`. Nothing was deleted or renamed.
- redact_fold.py is untouched.
- Caps: redact_encodings.py is 186 lines, redact.py 159, the test file 200. The largest function, `declared_secret_encodings`, is 49 lines.

## Adversarial probe (fake secrets only)

- 500 checks, with 0 misses against the unit's claimed coverage. The checks covered:
  - double-b64, every std/urlsafe inner x outer combination, padded and unpadded, embedded at 3 text alignments and 3 byte offsets;
  - UTF-16-LE/BE hex, upper and lower case, with and without a BOM;
  - a single-level regression.
- The disclosed std-only inner-layer residual never went dark for any probe secret, because the alphabets diverge only on `+` and `/` bytes.
- **Outside the claim:** base64 of the UTF-16 bytes is missed 8/8 on master **and** on the branch, including as `powershell -EncodedCommand <b64>`. The gap is pre-existing, so it is filed as AT-617 and not charged.

## AT-607 route (b)

- The issue's `expected` says "Either document ... or cover". The maker documented the gap and pinned it with tests.
- An 8-byte secret at base32 offset 1 produces an empty core in `_alignment_needles` (re-derived). A fix needs bit-precise trimming in the shared helper that carries AT-352's history, so the choice is credible.
- The docstring claims were reproduced:
  - ≤7 characters get no encoding protection (MIN_FOLDED_LEN);
  - an 8-character secret misses 100% at offset 1 and 0% at other offsets (500 trials);
  - 9 or more characters had 0 misses (4704 cases).

## Low notes (no fix required)

- The manifest's What changed table says redact_encodings.py went 144→186. The base was 126 lines; 144 is redact.py's count.
- The `_double_b64_needles` docstring does not state the std-only inner-layer limit. It is disclosed only in the manifest.
