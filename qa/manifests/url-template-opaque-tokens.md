# Manifest — url-template-opaque-tokens

**Unit:** opaque path tokens (JWT, email, base64 token, `;jsessionid=` matrix params, prefixed ids
like `ORD-2024-00081`) were kept verbatim by `core.urls.url_template`, so they landed in
`nodes.jsonl` `url_template` and `api_calls`. Source: checker B warning 3 / finding 4 of
`qa/verdicts/crawl-record-gaps.b.md` (followup 3).
**Contract:** `qa/contracts/core-invariants.md` C1 (one place per shape, the normaliser stays
`core/urls.py`), C7; `qa/contracts/explore.md` X3 (identity does not drift).
**Goal task:** none (checker followup)
**Branch:** `fix/url-template-opaque-tokens` from `fix/crawl-record-gaps` @ `f4acf9b8`
(descends from `5b09e417`), worktree `.claude/worktrees/urls-opaque`
**Date:** 2026-10-29
**Fix cycle:** 0
**Status:** checked-PASS
**Dual check:** no
**Not run:** whole suite (machine low on memory); live-browser crawl; `scripts/migrate_url_patterns.py`
(behind its own gate, calls `url_template` with defaults and so also sees the new templating).

## Criteria

1. **Opaque tokens are templated in the one normaliser, in place.** `core/urls.py`:
   `_template_opaque` (`:66`) is called first by `_template_segment` (`:78`).
   - email (also `%40`-encoded) -> `{email}` (`_EMAIL`, `:31`; `unquote` first)
   - JWT (`eyJ...` three base64url parts, `_JWT` `:32`) -> `{token}`
   - long base64 token (20+ chars of `[A-Za-z0-9_+=-]`, mixes digits + upper + lower, fewer than two
     hyphen/underscore alpha words; `_is_base64_token` `:37`) -> `{token}`
   - uppercase-prefixed order id (`[A-Z]{2,10}([-_]\d+)+` with two digit groups or a 5+ digit group;
     `_is_prefixed_id` `:50`) -> `{id}`
   - `word_<ULID|UUID|hex16+>` (`crawl_01M3...`, `cus_<uuid>`; `_is_prefixed_opaque_id` `:58`) -> `{id}`
   - `;k=v` matrix params are cut off every segment before templating (`url_template` `:178`); a
     matrix-only segment disappears.
   Placeholders match `leak_evidence._PLACEHOLDER` (`^\{[a-z_]+\}$`) and are stable when re-templated.
   Tests: `test_opaque_tokens_are_templated` (12 cases), `test_placeholders_are_stable_when_re_templated`,
   `test_query_and_fragment_secrets_still_never_reach_the_template`,
   `test_a_matrix_only_segment_is_dropped_not_left_empty`.
2. **Plain word segments keep the exact same template (no screen-id drift).**
   `test_plain_word_segments_keep_the_exact_template` pins 23 inputs unchanged, including the near
   misses `/covid-19`, `/class-12/notes`, `/top-10`, `/year-2024`, `/FY-2024`, `/q3-2024-report`,
   a 40-char hyphenated slug, `/Introduction-to-Python-3-Programming`, `/docs/v1.2/guide`,
   `/internationalbusinessadministration`, `/users/me@`, `/a@b`, `/{id}/{token}`.
3. **Drift proof over every committed fixture URL.** `_fixture_urls` walks every `*.json`/`*.jsonl`
   under `projects/`, `tests/fixtures/`, `qa/`, `docs/` for the keys `url`, `url_template`,
   `url_pattern`, `url_example`, `target_url`, `start_url`, `page` (808 values on this branch) and
   compares the new `url_template(raw, keep_host=False, fold_index=True)` with a frozen copy of the
   old normaliser (`_legacy`).
   - `test_no_committed_project_or_site_fixture_url_changes_template`: ZERO changes under
     `projects/` (checkerdemo, erp, pathlynks incl. `crawl_summaries/`, regression-demo, saucedemo, …)
     and `tests/fixtures/` (crawl_site, deep_site, inventory_site, …).
   - `test_the_only_template_changes_anywhere_are_crawl_ids_in_qa_evidence`: the ONLY changes in the
     whole walk are in `qa/evidence/**/report.json` (AutoTester's own UI addresses recorded by
     checker browser runs), 12 distinct URLs, every one `/projects/<p>/crawls/crawl_<ULID>[/report.xlsx]`
     -> `/projects/<p>/crawls/{id}[/report.xlsx]`. Named: `browser-at113-crawl-completion-…-checker-a2`
     (healthy/bound/dialog), `browser-at459-crawl-states-its-coverage-…-checker-c2/c3`
     (covtwo, covthree, covdepth), `browser-live-ui-b361a16-…-checker`, `browser-t135-coverage-merge-…`
     (checkerdemo), `browser-t171-permission-surface-coverage-…-checker` (demo). These are evidence of
     runs, not stored screen identities; no `nodes.jsonl` template in the repo changes.
4. **Design rules hold.** `core/urls.py` 235 lines (was 179), longest new function 12 lines; no new src
   module; the one new file is the test module (`tests/test_urls.py` is already 293 lines, so adding
   there would break the 300-line rule). Ruff clean.

## Known limits (stated, not hidden)

- Lowercase prefixed ids (`ord-2024-00081`, `user-1234567`) are NOT templated: indistinguishable from
  slugs such as `year-2024` (criterion 2). Only an UPPERCASE prefix qualifies.
- A 20+ char, hyphen-free, mixed-case-with-digits camel slug (`iPhone15ProMaxReview2024Guide`) reads as
  a token. None exists in the fixtures; the cost of a false positive is a collapsed template.
- Stored templates written before this change keep their old text until re-crawled; no migration was
  written (`scripts/migrate_url_patterns.py` sits behind `qa/gates/t135-url-pattern-data-migration.md`).

## Files changed

`src/autotester/core/urls.py` (edited in place), `tests/test_urls_opaque_tokens.py` (new),
`qa/manifests/url-template-opaque-tokens.md` (new).

## Tests run (worktree `.claude/worktrees/urls-opaque`, `uv run pytest <files> -o addopts=`, max two files per call)

RED first (before editing `urls.py`, the new test file only): `12 failed, 25 passed` — the 12 are the
10 token cases, `test_placeholders_are_stable_when_re_templated` and
`test_a_matrix_only_segment_is_dropped_not_left_empty`; the 23 plain-word cases and the fixture test
passed (nothing had changed yet).

GREEN after the fix:

| Command | Result |
|---|---|
| `tests/test_urls_opaque_tokens.py tests/test_urls.py` | `76 passed` |
| `tests/test_crawl_record_gaps.py tests/test_migrate_url_patterns.py` | `40 passed` |
| `tests/test_leak_url_ids.py` | `42 passed` |
| `tests/test_screen_identity.py tests/test_coverage.py` | `25 passed` |
| `tests/test_product_map.py tests/test_merge_flowspec.py` | `15 passed` |
| `tests/test_oracle_registry.py tests/test_explore_merge.py` | `28 passed` |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (pre-existing, same as `qa/verdicts/crawl-record-gaps.b.md`); none from this diff |

Callers of `url_template` not individually re-run (covered by the files above through
`screen_identity`, `coverage`, `explore_merge`, `merge_flowspec`, `product_map`, `network_capture`
via `test_crawl_record_gaps`): `stages/reachability.py:27`, `stages/oracle_request_budget.py`.
