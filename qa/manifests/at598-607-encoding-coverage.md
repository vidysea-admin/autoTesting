# Manifest — at598-607-encoding-coverage (AT-598 + AT-607)

**Unit:** AT-598 (double base64 and hex-of-UTF-16 spellings are missed at every secret length) +
AT-607 (a raw secret of ≤7 characters gets no encoding protection by design; an exactly-8-character
secret misses base32 at byte-alignment offset 1). Both filed against
`qa/verdicts/at347-352-356-redact-fold.md`. Both low severity.

**Contract:** `qa/contracts/core-invariants.md` (project-wide; C5 secrets, C7 verification, C2 line
caps).
**Fix cycle:** 1 of max 3
**Dual check:** no
**Persona walk: skip (backend-only redaction)**
**Issues addressed:** AT-598 (low, open → fixed here), AT-607 (low, open → part fixed / part
documented here). Neither flipped by me — `qa/issues.jsonl` is the checker's write surface.
**Executor:** claude-opus-subagent

## File ownership respected

Did not touch `src/autotester/core/redact_fold.py` (owned by the parallel `at611-cjk-perf` unit;
exactly 300/300 lines, off-limits). Both new needle families reach `Redactor.contains_folded` and
`assert_no_raw_secrets` transparently, because both already call
`redact_encodings.declared_secret_encodings` from inside `redact_fold.py`'s
`_contains_folded_secret` (the exact-encoding branch) and `redact_wrap.py`'s
`contains_wrapped_encoding` — neither of those two call sites needed to change.

## AT-598 — double base64 and UTF-16 hex needles (route (a): precompute them)

`redact_encodings.declared_secret_encodings` only ever encoded the secret's UTF-8 bytes one level
deep. Added two new needle families in `src/autotester/core/redact_encodings.py`:

- **`_double_b64_needles(raw)`** — base64-of-base64: `raw` base64-encoded once (the isolated inner
  layer — a log-scrubbing double-encode operates on the secret alone, not a byte run sharing
  neighbours before the FIRST pass), then base64-encoded AGAIN, standard and URL-safe, at the OUTER
  layer's 3 byte-alignment offsets via the existing `_alignment_needles` helper (unchanged, reused
  as-is) — so a double-encoded blob sitting inside a longer base64 stream is caught too, not only an
  isolated one. Isolated whole-blob spellings (real `=` padding) are included as well.
- **`_utf16_hex_needles(value)`** — hex of `value` encoded as UTF-16-LE and UTF-16-BE bytes
  (realistic in Windows/PowerShell logs, which are UTF-16 internally). No alignment needed: hex is a
  1-byte group, so — like the existing plain-UTF-8 hex needles — it has no cross-byte adjacency to
  lose.

**Kept `declared_secret_encodings` under its 50-line C2 cap without growing it**, per the fix brief:
its existing isolated base32/hex computation (5 lines) was extracted into a third new helper,
`_isolated_variant_needles(raw)`, unchanged in behaviour, called from one line. Net effect: 2 new
`needles.extend(...)` calls added, 4 lines freed by the extraction — the function actually **shrinks
from 50 to 48 lines** (confirmed via the same AST measure `autotester doctor` uses,
`end_lineno - lineno`).

## AT-607 — two boundaries, two different routes

**Part (a), the <8-char floor:** unchanged behaviour (`MIN_FOLDED_LEN` gates the exact-encoding
search on the raw secret's length, by design, per AT-352 cycle 3) — no fix needed, but a test now
pins it (`test_seven_char_secret_gets_no_encoding_protection_by_design`) so a future change touches
the docstring deliberately, not by accident.

**Part (b), the 8-char base32 offset-1 gap:** documented (route (b) of the two the issue accepts),
**not fixed**, added as a new paragraph appended to `assert_no_raw_secrets`'s docstring in
`src/autotester/core/redact.py` (pure addition — no existing docstring text trimmed or reflowed).
Reasoning for choosing documentation over a fix: at byte-alignment offset 1, `_alignment_needles`'
padded byte stream for an 8-byte secret splits into exactly 2 groups of 5 bytes, and both are edges
(the leading one carries the offset's unknown byte, the trailing one carries the tail-padding zero
byte). The helper's group-drop is deliberately **coarse** — it discards the whole 8-character group
once ANY byte in it is unknown, even though only 1-2 of those 8 characters are actually affected by
bit position — so for this one (length, offset) pair both groups are dropped and the core is empty.
A real fix requires bit-precise, sub-group character trimming in `_alignment_needles` (shared,
security-critical, used for every base64/base32 offset at every length), which is disproportionate
effort/risk for a low-severity, single-boundary gap, and this codebase has a documented history of
subtle off-by-one bugs in exactly this alignment logic (AT-352 cycles 2-3). Pinned by
`test_eight_char_secret_base32_offset_one_is_a_known_uncovered_gap` (asserts the gap as it exists
today, with an inline note to flip the assertion in the same commit that ever closes it) and
`test_eight_char_secret_base32_is_caught_at_every_other_offset` (offsets 0, 2, 3, 4 all still work —
the gap is specific to offset 1, not the whole mechanism).

## What changed

- **`src/autotester/core/redact_encodings.py`** (144 → 186 lines, under the 300-line cap) — three
  new functions (`_isolated_variant_needles`, `_double_b64_needles`, `_utf16_hex_needles`);
  `declared_secret_encodings`'s isolated-computation lines replaced with three `needles.extend(...)`
  calls (function shrinks 50 → 48 lines). No other function touched.
- **`src/autotester/core/redact.py`** (144 → 159 lines) — one paragraph appended to
  `assert_no_raw_secrets`'s docstring (AT-607). No other line changed; `assert_no_raw_secrets`
  itself is 39 lines, well under the cap.
- **`tests/test_redact_encoding_coverage.py`** (new, 200 lines) — 25 tests: double-b64 detection
  (isolated std/urlsafe outer, adjacency, outer-alignment offsets 0-2) through both
  `contains_folded` and `assert_no_raw_secrets`; UTF-16-LE/BE hex detection (isolated, case
  variants, adjacency) through both doors; the two AT-607 boundary pins; a same-offset-other-values
  regression guard (offsets 0/2/3/4 still caught for an 8-char secret); one false-positive guard over
  a ~70 KB corpus of prose, JSON, UUIDs and random hex/base64. Fake secrets only (`hunter2-*`,
  `hunter22`, `hunter2` — never a real credential; `.env` was never read or modified).

No other file touched.

## Verify — actual outputs

```
$ uv run pytest tests/test_redact_encoding_coverage.py
.........................                                                [100%]
25 passed in 0.50s

$ uv run pytest tests/ -k redact
........................................................................ [ 63%]
.........................................                                [100%]
113 passed, 1859 deselected, 1 warning in 23.00s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(The 1 warning is `starlette.testclient`'s pre-existing `anyio.abc.BlockingPortal` deprecation
notice, unrelated to this unit and present before it.) Full unfiltered suite intentionally NOT run
this cycle per the dispatch brief (RAM tight, another session running it).

## Capability coverage (falsifying edit → named test goes red)

Falsified in a throwaway copy **outside** the worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at598-falsify/`,
never `git stash`), containing only `autotester/core/{redact,redact_fold,redact_wrap,redact_encodings}.py`
and the new test file (no third-party deps in this module family, so no repo-wide venv needed).
Baseline confirmed green first (25 passed, own copy), then each new needle family's return value was
zeroed and the copy re-run, then reverted and re-confirmed green again. The scratch directory was
deleted afterward.

| claim | falsifying edit | test(s) | before | after |
|---|---|---|---|---|
| Double base64 (isolated + adjacent + outer-aligned) is caught by both doors (AT-598) | `redact_encodings.py::_double_b64_needles` body → `return []` (anchor matched once, own copy) | 10 double-b64 tests | 10 passed | **10 failed**, by name (`test_contains_folded_catches_double_base64[*]` ×4, `test_assert_no_raw_secrets_blocks_double_base64[*]` ×3, `test_contains_folded_catches_double_base64_at_outer_byte_alignment[*]` ×3) |
| Hex of UTF-16-LE/BE is caught by both doors (AT-598) | `redact_encodings.py::_utf16_hex_needles` body → `return []` (anchor matched once, own copy) | 8 utf16-hex tests | 8 passed | **8 failed**, by name (`test_contains_folded_catches_utf16_hex[*]` ×6, `test_assert_no_raw_secrets_blocks_utf16_hex[*]` ×2) |

Both mutations were applied and reverted entirely inside the scratch copy; `git status`/`git diff
--stat` in the worktree before and after the falsification run show no changes to
`redact_encodings.py` beyond this unit's own committed diff.

**No isolating falsification for the AT-607 boundary-pin tests**
(`test_seven_char_secret_gets_no_encoding_protection_by_design`,
`test_eight_char_secret_base32_offset_one_is_a_known_uncovered_gap`) — they assert the ABSENCE of
coverage for a documented, by-design gap, not a fix this unit makes; there is no fix hunk to revert
that would meaningfully "kill" them the way a fix-defending test is killed. They are pins against a
future accidental widening or narrowing of the boundary, not falsifiable claims about a mechanism
this unit added — the same shape core-invariants.md C7 already recognises for pure guard/negative
tests. `test_eight_char_secret_base32_is_caught_at_every_other_offset` is the falsifiable half: it
would catch a regression that widened the offset-1 gap to other offsets.

**No isolating falsification for the false-positive guard**
(`test_new_needle_families_do_not_false_positive_on_benign_corpus`) — same reasoning as every prior
cycle's benign-corpus negative test in this file family (e.g. `at599-606-redact-wrap-perf.md`): the
only mutation that would meaningfully break it is loosening an exact-substring match into something
fuzzier, which neither this unit nor any prior one does.

## Live browser evidence

Not UI-touching. Changed paths: `src/autotester/core/redact_encodings.py`,
`src/autotester/core/redact.py`, `tests/test_redact_encoding_coverage.py` (new),
`qa/manifests/at598-607-encoding-coverage.md`.

## Known limits (disclosed, not claimed)

- **AT-607's offset-1 gap is documented, not closed.** A real fix needs bit-precise character
  trimming in `_alignment_needles` (shared with every base64/base32 offset at every length); see the
  reasoning above for why that is out of proportion here. If a future unit closes it, the pin test
  named above must flip in the same commit, and `redact.py`'s new docstring paragraph must be
  corrected or removed then, not left stale.
- **`_double_b64_needles`'s inner layer is standard base64 only** (not also URL-safe-of-secret), to
  keep the combinatorial needle count — and therefore the per-scrub-call cost — proportionate; a
  log-scrubbing double-encode using URL-safe at the FIRST pass specifically is not covered. This
  mirrors the issue's own framing ("Double base64 (b64(b64(secret)))") rather than widening scope
  unasked.
- **Perf was not re-measured against the AT-606 bound test** (`tests/test_redact_wrap_perf.py`,
  owned by the parallel `at611-cjk-perf` unit) — the new needle families add a handful of extra
  `base64`/`hex` calls per `declared_secret_encodings` invocation (microseconds, per the prior
  cycle's own finding that this function's cost never showed up against `_is_ignorable`'s dominant
  cost), but this was not independently timed this cycle since `redact_fold.py`/the perf test file
  are out of scope for this unit.
- Full unfiltered `uv run pytest` was not run this cycle (RAM constraint per the dispatch brief);
  `tests/ -k redact` (113 passed) and the new file (25 passed) are the evidence presented.

## Status: checked-PASS (cycle 1, qa/verdicts/at598-607-encoding-coverage.md 31545ca)
