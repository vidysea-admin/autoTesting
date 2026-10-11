# Verdict (checker A, blind dual check) — at780-harden

**Date:** 2026-10-07
**Policy:** proportional-verification/2026-10-07.7, tier L, security trigger (PII masking before model calls)
**Unit:** AT-780 hardening, branch `wave/at780-harden`, head `84f3e522`
**Cycle checked:** 0
**Verdict:** PASS (no criterion failed; 5 low-severity PROPOSED-ISSUE lines below)
**Full suite:** NOT RUN here. It is deferred to the combined integration head (host short on RAM, dual-check policy).

## Check plan (written first)

1. ReDoS: my own adversarial 200 KB inputs (about 90 shapes) against `mask_pii`, plus a 100k/200k/400k doubling check to prove linear growth, covering the email scan, all five phone regexes and the label regexes.
2. Leaks: about 90 PII strings (emails, STD, grouped/dotted/bracketed phones) and about 90 label variants through `mask_name_value`, plus nested dict/list/tuple.
3. Over-masking: about 110 non-person labels and about 55 ordinary-text strings (dates, prices, years, paths, short codes).
4. Compatibility: grep callers; differential run of the old `redact.py` (13f37c3c) against the new one on all my corpora; idempotence fuzz (60,000 strings); `build_judge_prompt` path.
5. Tests: affected files, one pytest process at a time, `-p no:xdist`; ruff; `autotester doctor`. No full suite.
6. Falsification in a throwaway `git archive` copy (never the worktree): at least one per criterion plus up to 7 product-line mutants, each with a timeout on my own child process.

## Criteria and evidence

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | ReDoS: linear, under `1.0 * timing_scale()` s on 200 KB | About 90 adversarial inputs of 200 KB, worst 0.36 s (`"@"*200000`), most under 0.15 s. Shapes: `@` alone, `a@` and `@a` repeats, `a.@`, dot runs, digit runs, digit+`-`/`.`/space groups, `+9`/`+1 ` repeats, `+91`+separators, `(9` repeats, `0 `/`011-`/`(011) ` repeats, nested labels, 50k-deep `(`..`9`..`)`..`-`, `a@b`+`-`*N, `a@b`+`.-_!`*N/4, `a.@` chains, whitespace runs after `+1`/`91`/`011`/`(+1`, Arabic and Devanagari digit runs. Doubling check (100k, 200k, 400k): every ratio 400k/200k is 1.5 to 2.9, never near 4, so no quadratic term. Reasoning: both scans stop at the next `@`, so each char is visited at most twice; the phone regexes have no ambiguous nested quantifier (`(?:[\s().-]*\d){7,14}` needs a digit per iteration). | holds |
| 2 | Leaks masked | About 85 of 89 strings fully masked with no `@` and no 5-digit run left. Covered: IDN and non-ASCII (`josé@exämple.com`, `अनु@example.com`, `李雷@例え.jp`, punycode), plus-addressing, `bob@localhost`, `jane@192.168.0.1`, apostrophe local part, trailing punctuation, quotes, `mailto:`, URL query; STD `011-2345 6789`, `0141 2345678`, `(011) 2345 6789`, `080-23456789`, `+91-11-23456789`; mobiles `+91 (98765) 43210`, `98765.43210`, `+91-98765-43210`, `9876543210`, `(+91) 98765 43210`, `+91 98 76 54 32 10`, NBSP-separated, Devanagari digits; international US, UK, DE, AE, AU. Misses (all outside the stated criteria) are in PROPOSED-ISSUE 2. | holds |
| 2n | Names | All of नाम, पिता का नाम, माता का नाम, fname, lname, first_name, firstName, Dad, Mother, Father, guardian masked to `<name>`, plus about 60 more variants of my own (Father's Name, Guardian name, Applicant's Name, पति का नाम, name_of_father, name.first, Your Name *, Full name (as per Aadhaar), Name 1, Mom, Papa, Child name, छात्र का नाम, Sponsor name...). Nested dict/list/tuple strings masked (`mask_pii_obj` probe). Gaps in PROPOSED-ISSUE 1. | holds |
| 3 | Over-masking stops | Bank, Business, Plan, Course, University name and Student country/course/type/program/university stay unmasked, as do about 70 more org-name labels, Hindi org labels (विश्वविद्यालय का नाम, कॉलेज का नाम, पाठ्यक्रम का नाम, बैंक का नाम), नामांकन, "Parent ID", "Guardian consent checkbox", "Student dashboard". Ordinary text unchanged: ₹4,999, `$1,299.00`, dates, `2024-25`, URL paths with 5 to 7 digit ids, PIN 110001, IPs, versions, `@mention`, `a @ b`, `price @ ₹4,999`, `email@`, `x@`, `@`, IFSC. Differential against old `redact.py`: no string the old code masked as PII is now unmasked, and no label masked as a name before (my MASKED list) is now unmasked; the only changes are the intended un-masks of org labels. Over-mask residue in PROPOSED-ISSUE 4. | holds |
| 4 | Compatibility | Callers: `core/redact.py`, `stages/reconcile.py` (`mask_name_value`, `mask_pii_obj`), `tests/test_redact_pii.py`. Signatures unchanged, `__all__` unchanged, `stages/reconcile.py` untouched. `mask_pii` is idempotent: 0 failures in 60,000 random strings (alphabet includes `@`, digits, `+`, parens, Devanagari, `<email>`, `<phone>`). Idempotence and determinism hold (RC11). `build_judge_prompt` still masks: `test_reconcile_pii.py` (RC12 cases) passes and mutant C5 (below) breaks it. | holds |
| 5 | Tests, lint, doctor | See below. | holds |

## Commands run (worktree `D:/autoTesting/.worktrees/at780h`, one pytest process at a time)

```
uv run pytest tests/test_redact_pii.py tests/test_reconcile_pii.py tests/test_reconcile.py tests/test_redact_encoding_coverage.py tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py tests/test_redact_wrap_perf.py tests/test_timing_scale.py -p no:xdist
-> 341 passed in 95.64s
uv run pytest tests/test_core.py tests/test_secrets.py tests/test_reconcile_schema.py tests/test_prompt_skills.py tests/test_report_export_secrets.py -p no:xdist
-> 86 passed in 7.85s
uv run ruff check src tests scripts   -> All checks passed!
uv run autotester doctor              -> doctor: clean
```

Full suite: not run, deferred to the combined integration head. `git status` of the worktree was clean after all probing.

## Falsification (throwaway `git archive HEAD` copy, test run against it with `PYTHONPATH=<copy>/src`, one mutant at a time, own child process with timeout)

| Mutant | Result |
|---|---|
| C1 (criterion 1) replace `_mask_emails` with naive `[\w.+-]+@[\w-]+(\.[\w-]+)*` regex, `-k linear` | killed (timeout 170 s, genuinely quadratic on the 200 KB cases) |
| C4 (criterion 3) drop `country\|course\|type` from `_NOT_A_NAME_FIELD` | killed (`test_non_person_labels_are_not_masked[Student country]`) |
| C5 (criterion 4/nested) `mask_pii_obj` no longer recurses lists/tuples | killed (`test_mask_pii_obj_recurses_and_is_deterministic`) |
| M3 intl phone loses the optional leading `(` | killed (`(+91) 98765 43210`) |
| M5 drop Hindi roles पिता/माता | killed (`test_more_person_labels_mask_a_word_value[पिता]`) |
| M6 drop `_` to space normalisation | killed (`[first_name]`) |
| M2 drop `text[at+1].isalnum()` guard | SURVIVED (175 passed): no test has an `@` followed by a non-alnum host start such as `a@-b`, `x@.com` |
| M4 apostrophe not a host stop | SURVIVED: cosmetic only (`jane@x.com's` would swallow `'s`); no privacy effect |
| M7 no trailing-punctuation strip on the host | SURVIVED: cosmetic only (`<email>.` would become `<email>`); no privacy effect |
| M1 remove `@` from both stop sets | SURVIVED, but equivalent: with no `@` stop the right scan swallows the whole run in one go, so it is still linear; not a test gap |

Product mutants: 7 of the 7 cap (M1 to M7), plus 3 criterion falsifications.

## PROPOSED-ISSUE lines (dual check: not filed by me)

1. PROPOSED-ISSUE (low, leak, outside stated criteria): `mask_name_value` does not mask concatenated lowercase identifiers, because `_NAME_WORD` and `_PERSON_ROLE` rely on word boundaries. Repro: `mask_name_value("firstname", "Priya Sharma")`, same for `lastname`, `middlename`, `givenname`, `studentname`, `parentname`, `fathername`, `mothername`, `guardianname`, `yourname`, `FIRSTNAME`; `fullname` works because it is listed. These are the commonest HTML id/name spellings. Also unmasked: `नामः` (visarga), roles-only labels `Brother`, `Sister`, `Wife`, `Husband`, `Son`, `Daughter`, `Contact person`, `Emergency contact`, `Next of kin`.
2. PROPOSED-ISSUE (low, leak): org exclusion is too greedy for person labels. `_NOT_PERSON_NAME` matches `name of (the) <org>` anywhere, so `Name of school principal`, `Name of the university counsellor`, `Applicant Name / Business Name` return the value unmasked. Number shapes still unmasked by `mask_pii`: 12-digit Aadhaar `1234 5678 9012`, `98 7654 3210`, toll-free `1800-123-4567`, `jane@[192.168.0.1]` (IP-literal), obfuscated `j%40x.com` (already disclosed by the builder). `mask_pii_obj` also leaves dict KEYS alone (`{"jane@x.com": "v"}` unchanged); reconcile keys are fixed so no live path today.
3. PROPOSED-ISSUE (low, test gap): add a test for an `@` whose next char is not alphanumeric (`a@-b`, `x@.com`, `a@_x`) and one for trailing punctuation after an email and for `'s` after an email (mutants M2, M4, M7 survive).
4. PROPOSED-ISSUE (low, over-mask): role-only labels mask any lettered value: `Mother tongue`, `Father occupation?`, and `Tab name`, `Menu name`, `Filter by name?` are masked to `<name>`. `Marks 98 76 54 32 10` becomes `Marks <phone>` (five two-digit groups look like the Indian grouped mobile). Conservative, privacy-safe, not in the stated list.
5. PROPOSED-ISSUE (process, none for the product): the scratchpad directory of this session is shared by other coordinators. Another session overwrote `scratchpad/mutate.py` while I was working, and I ran that file once by mistake against its own `mut2` tree (it hit a console encoding error part way, so that tree may have been left with a mutant applied; the owner restores the original at the start of each mutant). I did not read any verdict or checkpoint of the other coordinator; I saw only the mutant list in that script (mutant ideas, no results). All my results above come from my own tree `scratchpad/coordA780/`.

## Known limits accepted

Heuristic masking only: free-text names, obfuscated emails, nickname/username labels, bare `Textbox 1` labels stay unmasked, as the manifest discloses. The builder's note that they ran a blanket kill of `python.exe`/`uv.exe` is a process finding for the maker, not for this verdict; I killed only PIDs I started (my own timed-out mutant child).

Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=10 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
