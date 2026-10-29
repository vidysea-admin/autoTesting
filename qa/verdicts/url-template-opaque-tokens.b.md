# Verdict — url-template-opaque-tokens (Checker B, adversarial, combined A+B seat)

**Checked by:** /checker (Mode A, fresh context, no builder reasoning)
**Date:** 2026-10-29
**Branch / head:** `fix/url-template-opaque-tokens` @ `7c82e92f` (worktree `.claude/worktrees/urls-opaque`)
**Contract:** `qa/contracts/core-invariants.md` C1, C7; `qa/contracts/explore.md` X3
**Manifest:** `qa/manifests/url-template-opaque-tokens.md` — `Status: ready-for-check`, Fix cycle 0
**Source:** warning 3 / finding 4 of `qa/verdicts/crawl-record-gaps.b.md` (`:46`, followup `:57`)

**Cycle checked: 0**

## Verdict: PASS (7 non-blocking warnings; none breaks a stated criterion)

Every manifest criterion holds as written. The warnings are heuristic edges that the manifest either
discloses (W1, W3 partly) or that sit outside what criterion 1 promises (W4-W6). W2 is an undisclosed
narrow regression with a one-line fix; it does not meet the bar for FAIL (needs a mixed-case 20+ char
hex id, none exists in any committed fixture) but should be folded into the next touch of `urls.py`.

## What I re-ran myself (worktree, one pytest at a time, `-o addopts=`, max two files)

| Command | Result |
|---|---|
| `tests/test_urls_opaque_tokens.py tests/test_urls.py` | 76 passed |
| `tests/test_crawl_record_gaps.py tests/test_migrate_url_patterns.py` | 40 passed |
| `tests/test_leak_url_ids.py tests/test_screen_identity.py` | 51 passed |
| `tests/test_coverage.py tests/test_explore_merge.py` | 32 passed |
| neighbours the manifest did NOT list: `test_authz_probe_schema`+`test_consent_followups` | 94 passed |
| `test_imap_mailbox`+`test_oracle_credential_mail` (their URLs now template to `{token}`) | 30 passed |
| `test_reachability_warning`+`test_ui_case_navigate_reachability` (`reachability.py:27` caller) | 14 passed |
| `test_leak_evidence`+`test_merge_flowspec`; `test_product_map`+`test_oracle_registry` | 21 passed; 15 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor` | 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (pre-existing; not from this diff) |
| `wc -l` | `core/urls.py` 235, `tests/test_urls_opaque_tokens.py` 147 (both under 300); longest new function 12 lines |

Diff scope `git diff f4acf9b8 7c82e92f --stat`: `core/urls.py`, new test module, manifest. No second
normaliser (C1 holds); `url_template` stays the one place.

## Criterion by criterion

1. **Opaque tokens templated in place: PASS.** Probe `.work/probe_urls_b.py` and the 12 positive cases
   give the manifest's outputs. End to end through `network_capture.api_inventory` (probe
   `.work/probe_urls_b2.py`, real `make_project`, `SafetyPolicy`, `Redactor({})`): JWT path ->
   `/api/auth/verify/{token}`, email -> `/api/users/{email}/profile`, base64 invite -> `/api/invite/{token}`,
   `;jsessionid=` -> `/api/session`, `ORD-2024-00081` -> `/api/orders/{id}`, query token dropped. None of the
   raw values reach `ApiCall.path`. Placeholders match `schema/leak_evidence.py:37` `_PLACEHOLDER`
   (`^\{[a-z_]+\}$`) and re-templating is stable (test + probe). `validate_url_template` (`leak_evidence.py:56`)
   rejects `@` in the URL, so `{email}` is also the only form that can pass it.
2. **Plain words keep their template: PASS for every pinned and every common shape I tried**, with the
   exceptions in W1-W3 below. Unchanged in my probe (old vs new, 60+ shapes): `/COVID-19`, `/COVID-19-Update`,
   `/FY2024`, `/en-US`, `/zh-CN`, `/es-419`, `/utf-8`, `/sha256`, `/HTML5`, `/ES2015`, `/OAuth2`,
   `/wiki/Albert_Einstein`, `/wiki/List_of_Presidents_2024`, `/Annual-Report-2024-Final`, `/JIRA-1234`,
   `/RFC-2616`, `/user-12345`, `/ord-2024-00081`, `/Fall2024-Scholarships-Application`,
   `/Master_of_Science_in_Computer_Science_2024`, `/users/john.doe`, `/file.tar.gz`, dates, 20-digit numerics.
3. **Drift proof over committed fixtures: PASS, and wider than the manifest's.** I re-ran the manifest's
   two drift tests (inside the 76 passed). I then widened the net: every `git ls-files` file under
   `projects/ tests/ qa/ docs/ src/ scripts/` (.md .py .json .jsonl .txt .html .yml), regexing every URL-like
   string, 4,906 distinct strings (`.work/probe_urls_b4.py`). 93 change. Zero are in `projects/`. All are
   crawl/run ULIDs in `qa/evidence`, emails, JWTs, base64 invite tokens, matrix params in checker attack
   probes, or the three items in W1/W5. Nothing the user would call a normal screen path moved.
4. **Design rules: PASS** (line counts above).

## Falsification (each fix reverted in memory, then the tests run)

Probes `.work/probe_urls_b2.py` (module-attribute mutants against the 12 positive + 23 plain + 2 shape
cases) and `.work/probe_urls_b3.py` (same mutants against `test_urls.py` + the new file under pytest):

| Mutant | Result |
|---|---|
| `_template_opaque` -> None | 10 positives + stability red |
| `_EMAIL` off / `_JWT` off / base64 off / `_is_prefixed_id` off / `_is_prefixed_opaque_id` off | each turns exactly its own cases red |
| matrix-param cut removed (source rewritten in memory) | 3 red: both `;jsessionid` cases and `test_a_matrix_only_segment_...` |
| `_is_prefixed_id` ignores the group rule or lowers 5 -> 4 digits | `/FY-2024` red |
| base64 accepts any 20+ run | 3 plain cases red |
| base64 drops the words rule | `/Introduction-to-Python-3-Programming` red |
| base64 drops uppercase or lowercase requirement | red, but only in `tests/test_urls.py` (uuid/ulid/hex tests), not in the new file |
| base64 drops the DIGIT requirement | SURVIVES: all 76 tests still pass (W6) |

## Warnings (non-blocking)

**W1. Single-token CamelCase routes with a digit and 20+ chars become `{token}` (disclosed in the manifest
for `iPhone15ProMax...`, understated).** Old vs new: `/Student/ViewAdmissionApplication2024` ->
`/Student/{token}`; `/api/getUserProfileByIdV2Handler` -> `/api/{token}`; `/BTechCSE2024BatchAdmissionForm` ->
`{token}`; `/Engineering2024Admissions-Guide` -> `{token}`; `/Q3-2024-Report-FinalVersion1` -> `{token}`;
and from the repo itself `/aios-shards/autoTesting-20261011-123232` -> `/aios-shards/{token}`. Cause:
`_is_base64_token` (`urls.py:37-47`) has no length floor that separates a tokenised word run from random
bytes, and "fewer than two alpha words" is true for any CamelCase word. ASP.NET/Salesforce-style portals
use exactly this naming; the cost is two distinct screens collapsing to one template. Mitigation to
consider: require at least 3 case transitions inside a run of letters to count as a word boundary, or
require the segment to contain no lower-to-upper-to-lower word shape.

**W2. UNDISCLOSED: ids that already templated to `{id}` now template to `{token}` when mixed case.**
`_template_opaque` runs before `_UUID`/`_HEX` in `_template_segment` (`urls.py:81` vs `:86`), so
`/0123456789abcdefABCDEF` (hex, 22 chars) and `/550e8400-E29B-41d4-a716-446655440000` (mixed-case UUID,
36 chars) moved from `/{id}` to `/{token}`. Stored templates and a fresh crawl will disagree on those
screens (X3 identity). Fix: test `_NUMERIC/_UUID/_ULID/_HEX` before `_template_opaque`, or have
`_is_base64_token` return False when the segment matches `_UUID` or `_HEX`.

**W3. Uppercase-prefixed codes that are names collapse to `{id}`:** `/ISO-27001`, `/ISO-9001-2015`,
`/CVE-2024-12345`, `/ABC-12345`, `/ABC_2024_01`. The rule (two digit groups or one 5+ digit group) is
the documented trade-off; the manifest pins `/FY-2024` and `/top-10` but not these. Also inconsistent:
`/projects/p/runs/run-<ULID>` (hyphen) -> `{token}` while `crawl_<ULID>` (underscore) -> `{id}`, because
`_is_prefixed_opaque_id` (`urls.py:58`) only splits on `_`. Both are AutoTester's own UI addresses.

**W4. Percent-encoded forms are only half-handled.** The email branch calls `unquote`; the base64 and
matrix branches do not. `/a/Zm9vYmFyQmF6MTIzNDU2Nzg5MA%3D%3D` (padding is routinely `%3D` in URLs) and
`/s/a%3Bjsessionid%3DABC` survive verbatim. The unpadded and `==` forms template correctly.

**W5. Token shapes that still survive** (outside the documented rule, so not a criterion breach, but the
intent of followup 3 is "no opaque token in a stored template"): lowercase-plus-digit ids such as cuid
`/inv/cjld2cjxh0000qzrmn831i7rn` and nanoid-lowercase `/inv/x7k2m9p4q1w8z3n5v6b0`; upper-plus-digit-only
`/inv/ABCD1234EFGH5678IJKL`; all-letter mixed case `/inv/aBcDeFgHiJkLmNoPqRsTuV`; a base64url token whose
`-`/`_` split leaves two all-alpha chunks `/reset/abCdEf-ghIjKl_mnOpQr1234xyz` (the "fewer than two words"
rule rejects it); 2-part unsigned JWT `eyJ...<payload>` with no trailing dot; vendor keys
`sk_live_...`, `AKIA...`; short tokens (`/x/dQw4w9WgXcQ`, 11 chars); a token embedded in a filename
(`report-<token>.pdf`). Query/fragment secrets and userinfo are dropped as before (test + probe).

**W6. Weak pin on the digit requirement.** Removing `any(c.isdigit())` from `_is_base64_token` leaves all
76 tests green, so a pure-letter CamelCase segment such as `/internationalBusinessAdministration` would
turn into `{token}` with no test red. Add one plain case (a 22+ letter mixed-case word) to
`test_plain_word_segments_keep_the_exact_template`.

**W7. Matrix cut is applied to every segment but not to the host.** `https://host.test;jsessionid=1/x`
with `keep_host=True` keeps `host.test;jsessionid=1` as the host part (`keep_host=False`, the stored
shape, is clean). Cosmetic, no stored path affected today.

## Re-check for the maker (optional, no re-verdict required unless W2 is changed)

Fold W2 and W6 into the next edit of `core/urls.py`; if W2 is fixed, re-run `tests/test_urls_opaque_tokens.py`
and `tests/test_urls.py`.
