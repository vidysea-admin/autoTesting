# Manifest — at299b-hostless-url

**Contract:** qa/contracts/core-invariants.md (I7 — `url_template`/`absolute_url` are the ONLY
place a URL is normalised into a screen-identity path)
**Fix cycle:** 2 of 3
**Dual check:** no
**Issues addressed:** AT-299b

## Cycle 2 — fix for verdict `qa/verdicts/at299b-hostless-url.md` (Cycle checked: 1, FAIL)

**Finding:** `url_template(absolute_url(x), keep_host=False)` — the exact composition all three
producers used — still turned a schemeless, slash-free, dotted/ported token (`file.html`,
`sitemap.xml`, `report.pdf`, `robots.txt`, `a.b`, `example.com`) into `"/"`: a false claim that the
site ROOT is covered. `absolute_url`'s cycle-1 fix correctly stopped hostless multi-segment paths
from losing their first segment, but a bare dotted/ported token with NO path at all is genuinely
ambiguous by shape (`file.html` vs `example.com` — AT-287's own "indistinguishable" example) and
that ambiguity was never resolved; it just happened to not affect the cycle-1 test set, which only
covered dot-free prose (`"Sign in page"`).

**What changed** — added `core/urls.py::screen_url_pattern(raw)` (new, `urls.py:108-149`) as the
ONE shared boundary between an observed url and a stored `url_pattern`. It still calls
`url_template(absolute_url(raw), keep_host=False)` internally (so every cycle-1 fix is preserved
unchanged), but when that result is exactly `"/"`, it now asks whether the raw string actually
asked for a root:

```python
    if not raw:
        return None
    templated = url_template(absolute_url(raw), keep_host=False)
    if templated != "/":
        return templated
    before_query = raw.split("?", 1)[0]
    if raw.startswith("/") or "//" in before_query[:8]:
        return "/"  # already-absolute path, or a genuine scheme/scheme-relative input
    if "/" in before_query:
        return "/"  # e.g. "example.com/" -- an explicit trailing slash after the host
    return None  # a bare token ("file.html", "example.com") -- ambiguous, AT-287/AT-299b
```

`absolute_url` itself is UNCHANGED — it must keep promoting a bare dotted/ported token to a host
(stopping that would misfile a real bare host like `example.com` as a path segment,
`/example.com`, which the checker explicitly warned against). The fix is entirely in what
`screen_url_pattern` does with a `"/"` result: `None` (I7's already-honest "no pattern is
knowable" outcome) unless the raw string itself was unambiguous about wanting the root — `raw ==
"/"`, a real scheme/scheme-relative input (`absolute_url` left those untouched precisely because
they already had one), or an explicit trailing slash after the promoted host (`"example.com/"`).

**Wired all three producers onto the one function**, replacing each one's own
`url_template(absolute_url(x), keep_host=False)` composition:

- `src/autotester/stages/ingest.py:137` — `Screen.url_pattern=screen_url_pattern(observed.url)`
- `src/autotester/stages/product_map.py:40` (`_new_screen`) and `:59` (`_fold_screen`) —
  `MappedScreen.url_pattern` via the same function, both call sites
- `src/autotester/stages/explore_status.py:52` (`login_template`) — `return
  screen_url_pattern(step.target)`

**Checked that a None `url_pattern` is already safe downstream** (grep across `stages/`): every
consumer already guards on truthiness before using `url_pattern` —
`stages/coverage.py:34,93,125` (`if s.url_pattern`), `stages/explore_merge.py:83,142,150` (`or
incoming.id`, `if s.url_pattern`), `stages/merge_flowspec.py:62,66,83,96,170` (`if not
screen.url_pattern`, `if s.url_pattern`). `login_template`'s own caller
(`explore_status.py::never_left_login:113`) already had `if template is None or not reached:
return None` before this change (the same `"/"` ambiguity previously bit AT-462 there too, per its
own docstring). No caller needed an additional change beyond the swap above.

**Docstring correction** (checker's low-severity note): `urls.py`'s `absolute_url` docstring
claimed `localhost/students` "still reads as a host" as part of the residual-gap list. That was
wrong — `localhost` alone has neither a dot nor a colon, so the guard leaves the whole string as a
path (`/localhost/students`), never promoting it. Corrected; the genuine residual gap
(`v1.2/foo`, `settings.json/edit` — a first segment that ITSELF contains a dot) is unchanged and
still documented. The same wrong claim also appeared in this manifest's cycle-1 Gaps section
below and has been left as written there for history — see the note prepended to that bullet.

### Cycle 2 TDD — red first, in a scratch copy

Same rule as cycle 1: the tracked worktree file was never edited to fake red. Copied the
cycle-1-committed `urls.py` (`git show 5073fe4:src/autotester/core/urls.py`) into the scratch dir
and ran the checker's exact failing shapes against the literal caller composition:

```
$ python3 red_check_cycle2.py
FAIL  'bare filename': caller composition on 'file.html' -> '/' (expected None)
FAIL  'bare filename 2': caller composition on 'sitemap.xml' -> '/' (expected None)
FAIL  'bare filename 3': caller composition on 'report.pdf' -> '/' (expected None)
FAIL  'bare filename 4': caller composition on 'robots.txt' -> '/' (expected None)
FAIL  'bare short token': caller composition on 'a.b' -> '/' (expected None)
FAIL  'bare dotted host, no slash': caller composition on 'example.com' -> '/' (expected None)
PASS  'explicit trailing slash on host': caller composition on 'example.com/' -> '/' (expected '/')
PASS  'already-absolute root path': caller composition on '/' -> '/' (expected '/')
PASS  'real scheme, no path': caller composition on 'https://app.test' -> '/' (expected '/')

6 failing / 9 total
```

Matches the checker's finding exactly (6 false-root cases red, the 3 genuine-root cases already
correct). After implementing `screen_url_pattern` in the real worktree file, all 18 of the cases
above plus the cycle-1 shapes pass (verified directly against `src/autotester/core/urls.py`).

### Cycle 2 capability coverage table

| Claim | Falsifying single-hunk edit (scratch-dir mutant only) | Check that goes red |
|---|---|---|
| A bare ambiguous token (`file.html`, `example.com`, …) reports `None`, not a false root | Remove the whole ambiguity guard — `screen_url_pattern` just returns the raw `url_template(absolute_url(raw), ...)` composition (`mutant_no_none_guard.py`) | `test_screen_url_pattern_reports_none_for_a_bare_ambiguous_token` |
| A genuine root (`raw == "/"`, a real scheme, or an explicit trailing slash) still reports `"/"` | Remove both explicit-root branches, so any `"/"` result becomes `None` unconditionally (`mutant_overzealous_none.py`) | `test_screen_url_pattern_keeps_root_when_the_raw_string_actually_said_so` |
| A real, non-root templated path is untouched by the guard | Drop the `templated != "/"` early return, so every input is re-decided by the ambiguity branches (`mutant_always_ambiguity.py`) | `test_screen_url_pattern_is_unaffected_when_a_real_path_survives` |

```
$ python3 capability_check_cycle2.py
Claim: bare ambiguous token -> None (not a false root claim)
  fixed module -> PASS (expected)
  mutant mutant_no_none_guard     -> FAIL/red (expected)
Claim: genuine root (explicit slash / real scheme / absolute path) still kept
  fixed module -> PASS (expected)
  mutant mutant_overzealous_none  -> FAIL/red (expected)
Claim: a real templated path is untouched by the None guard
  fixed module -> PASS (expected)
  mutant mutant_always_ambiguity  -> FAIL/red (expected)

ALL CYCLE-2 CAPABILITY ROWS OK
```

### Cycle 2 verify run (this worktree)

```
$ uv run pytest tests/test_urls.py tests/test_ingest_persist.py tests/test_product_map.py tests/test_ui_product_map.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py tests/test_crawl_liveness.py tests/test_crawl_status_surfaces.py
........................................................................ [ 90%]
........                                                                 [100%]
80 passed, 1 warning in 6.45s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(`uv run autotester doctor` briefly flagged `function-too-long: absolute_url is 51 lines > 50`
after the first docstring edit; trimmed the docstring — re-run above is clean.)

Free RAM re-measured before this cycle's run: ~1.32 GB (`FreePhysicalMemory` 1321448 KB) — still
under the 3.5 GB floor, so the same targeted set as cycle 1 was used, not the full suite.

### Cycle 2 gaps

- Full `uv run pytest` still not run (RAM below 3.5 GB floor both times measured this unit).
- The `v1.2/foo` / `settings.json/edit` residual gap from cycle 1 is unchanged by this cycle (it
  isn't a `"/"`-shaped result, so `screen_url_pattern`'s new guard doesn't touch it) — still
  documented, still not asserted against, still not exercised by any caller per grep.
- A bare token that is ALSO ambiguous but has no dot/colon at all (pure prose, e.g. `"Sign in
  page"`) is unaffected by this cycle: it never templates to `"/"` in the first place (it becomes
  `"/Sign in page"`, a real non-root path), so it was already outside this cycle's fix surface and
  outside cycle 1's — still the harmless-junk pre-AT-294 behaviour, not a regression target here.

---

## Cycle 1

## The bug

`core/urls.py::absolute_url` prepended `https://` to ANY hostless input unconditionally. `urlsplit`
then always reads the first `/`-delimited segment of a scheme-relative-looking string as the host,
so `url_template(..., keep_host=False)` silently DELETED it even when it was genuine path:

- `"erp/trainers"` -> `absolute_url` -> `"https://erp/trainers"` -> templated -> `"/trainers"`
  (lost "erp" — cycle-2 code, without `absolute_url`, produced the correct `"/erp/trainers"`)
- `"students/1"` -> `"/{id}"` (lost "students")
- prose the model returns, e.g. `"Sign in page"` -> `"/"` — a false claim that the site ROOT is
  covered (pre-AT-294 behaviour produced the harmless junk `"/Sign in page"` instead)

## What changed

`src/autotester/core/urls.py:37-79` (`absolute_url`) — added a guard before the unconditional
`https://` prepend: the first `/`-delimited segment is only treated as a host when it carries a
signal an address-bar host actually has — a domain dot (`vidysea.com`) or a port colon
(`localhost:3000`). Otherwise the string is returned unchanged, so `url_template` keeps every
segment as path.

```python
    first_segment = url.split("/", 1)[0].split("?", 1)[0]   # urls.py:76
    if "." not in first_segment and ":" not in first_segment:  # urls.py:77
        return url
    return f"https://{url}"                                   # urls.py:79
```

This is deliberately narrower than the AT-287 whole-string host-shape guessing that was already
rejected as unwinnable (`settings.json` vs `example.com` are the same shape). Here the question is
only "does the first segment of an already-multi-part string carry a host-only signal", and a bare
relative path built from real segments (`erp/trainers`, `students/1`) carries neither. Full
reasoning is in the updated docstring at `urls.py:38-71`.

Callers (`stages/explore_status.py:52`, `stages/ingest.py:137`, `stages/product_map.py:40,61`) are
unchanged — they all call `url_template(absolute_url(x), keep_host=False)`, so fixing
`absolute_url` once fixes all three call sites uniformly.

**Known residual gap, accepted rather than guessed around further** (documented in the docstring):
a bare hostname with no dot and no port (`localhost/students`) or a first path segment that itself
contains a dot (`v1.2/foo`, `settings.json/edit`) still reads as a host. No existing test (direct
or via any of the three callers) exercises that shape through `absolute_url`; `url_template` called
directly (bypassing `absolute_url`) already handles `v1.2/foo`/`settings.json` correctly and is
untouched by this change.

## TDD — red first, in a scratch copy outside the worktree

Per the hard rule, the tracked worktree file was never edited to falsify or red-test. All red-first
and mutation work ran against throwaway copies in
`C:/Users/Lenovo/AppData/Local/Temp/claude/.../scratchpad/at299b_redcheck/` (plain-Python scripts,
no pytest needed — `urls.py` has no third-party deps).

**1. Red against the original (pre-fix) code**, copied verbatim before any edit:

```
$ python3 red_check.py
FAIL  'hostless multi-segment path': absolute_url('erp/trainers') -> url_template -> '/trainers' (expected '/erp/trainers')
FAIL  'hostless path with id segment': absolute_url('students/1') -> url_template -> '/{id}' (expected '/students/{id}')
PASS  'dotted host still stripped': absolute_url('vidysea.com/erp/trainers') -> url_template -> '/erp/trainers' (expected '/erp/trainers')
PASS  'port host still stripped': absolute_url('localhost:3000/students/1') -> url_template -> '/students/{id}' (expected '/students/{id}')
PASS  'scheme-relative host still stripped': absolute_url('//host/x') -> url_template -> '/x' (expected '/x')
PASS  'already-absolute path unchanged': absolute_url('/erp/trainers') -> url_template -> '/erp/trainers' (expected '/erp/trainers')

2 failing / 6 total
```

Confirms the two regression shapes were red and the four already-working shapes were untouched by
the bug, before any fix code was written.

**2. Fix applied to the real worktree file** (`urls.py:76-79` above), plus new pytest tests added
to `tests/test_urls.py` (5 new test functions covering the same shapes, `absolute_url` now imported
directly).

## Capability coverage table

Each row: claim -> single-hunk falsifying mutation (applied only to a throwaway copy in the scratch
dir, `mutants/*.py`) -> the check that goes red on the mutant and stays green on the fixed copy.
Full harness + output: `capability_check.py` in the scratch dir.

| Claim | Falsifying single-hunk edit | Check that goes red |
|---|---|---|
| Hostless multi-segment path is not eaten (`erp/trainers`, `students/1`) | Delete the `first_segment` guard entirely (revert to unconditional `https://` prepend — the original bug) | `test_absolute_url_leaves_a_genuine_hostless_relative_path_alone` |
| Dotted host (`vidysea.com`) is still recognised & stripped | Narrow the guard to check only `:` (drop the `.` check) | `test_absolute_url_still_restores_scheme_for_a_dotted_or_ported_host` |
| Ported host (`localhost:3000`) is still recognised & stripped | Narrow the guard to check only `.` (drop the `:` check) | `test_absolute_url_still_restores_scheme_for_a_dotted_or_ported_host` |
| Scheme-ful / scheme-relative / absolute-path input passes through unchanged | Remove the leading `"//" in url.split("?", 1)[0][:8]` early-return | `test_absolute_url_passes_through_scheme_ful_and_absolute_path_input` |
| Prose input no longer falsely claims the site root | Same as row 1 (revert to unconditional prepend reproduces `"Sign in page"` -> `"/"`) | `test_a_non_url_transcription_no_longer_falsely_claims_the_site_root` |

Actual run of the harness (fixed copy green, each mutant red):

```
$ python3 capability_check.py
Claim 1: hostless multi-segment path not eaten (erp/trainers, students/1)
  fixed module  -> PASS (expected)
  mutant mutant_no_guard        -> FAIL/red (expected)
Claim 2: dotted host (vidysea.com) still recognised & stripped
  fixed module  -> PASS (expected)
  mutant mutant_dot_only        -> FAIL/red (expected)
Claim 3: ported host (localhost:3000) still recognised & stripped
  fixed module  -> PASS (expected)
  mutant mutant_colon_only      -> FAIL/red (expected)
Claim 4: scheme-ful / scheme-relative / absolute-path input passthrough
  fixed module  -> PASS (expected)
  mutant mutant_no_scheme_guard -> FAIL/red (expected)
Claim 5: prose input no longer falsely claims the site root
  fixed module  -> PASS (expected)
  mutant mutant_no_guard        -> FAIL/red (expected)

ALL CAPABILITY ROWS OK
```

## How to verify (targeted — see Gaps for why not the full adapter command)

- `uv run pytest tests/test_urls.py tests/test_ingest_persist.py tests/test_product_map.py tests/test_ui_product_map.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py tests/test_crawl_liveness.py tests/test_crawl_status_surfaces.py`
- `uv run ruff check src tests scripts`
- `uv run autotester doctor`

## Actual outputs (from maker's own run, this worktree)

```
$ uv run pytest tests/test_urls.py tests/test_ingest_persist.py tests/test_product_map.py tests/test_ui_product_map.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py tests/test_crawl_liveness.py tests/test_crawl_status_surfaces.py
........................................................................ [ 94%]
....                                                                     [100%]
76 passed, 1 warning in 8.22s
(warning is a pre-existing starlette/anyio DeprecationWarning, unrelated to this change)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

LIVE-BROWSER: not-applicable (no browser/network code touched — pure string templating).

## Gaps

- **Full suite not run.** Free RAM measured ~416 MB (`Get-CimInstance Win32_OperatingSystem` ->
  FreePhysicalMemory 426072 KB) at the start of this unit, well under the 3.5 GB floor for
  `uv run pytest` (full). Ran the targeted set above instead: `tests/test_urls.py` (the function's
  own tests, both old and new) plus every test file that references `url_pattern` /
  `absolute_url` / `url_template` through the three real callers (`ingest`, `product_map`,
  `explore_status` via its login-wall/crawl-status consumers) — 76 tests, all green. Not run:
  test files with no textual reference to these symbols (unlikely to exercise this path, but not
  independently confirmed).
- **Residual host/path ambiguity** — CORRECTED in cycle 2 (see above): this originally also
  claimed `localhost/students` is misread as a host. It is not — `localhost` alone has no dot or
  colon, so the guard leaves it as a path. The genuine residual gap is a first segment that itself
  contains a dot (`v1.2/foo`, `settings.json/edit`), still not exercised by any caller per grep.
- "Optionally reject an observed url containing whitespace" (issue's suggested extra guard) was
  NOT implemented — out of scope for the segment-eating bug this cycle targeted; the prose case is
  already improved (no longer claims root) without it.
- **What cycle 1 missed, found by the checker**: a bare, slash-free, dotted/ported token
  (`file.html`, `example.com`) still collapsed to `"/"` through the same caller composition — see
  the Cycle 2 section above for the fix.

Status: checked-PASS (cycle 2, 094609b)
