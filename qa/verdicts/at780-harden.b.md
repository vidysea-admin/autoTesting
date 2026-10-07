# Verdict — at780-harden (coordinator B, blind dual check, adversarial angle)

**Verdict: PASS** (no side effects: dual check; nothing flipped, no issue rows, no push)
**Cycle checked:** 0
**Tier:** L (security trigger: PII masking before model calls)
**Policy-Version:** proportional-verification/2026-10-07.7
**Bound head:** wave/at780-harden @ 84f3e522 (worktree D:/autoTesting/.worktrees/at780h, left clean)
**Contract:** `qa/contracts/reconcile.md` RC11, RC12, RC14; `core-invariants.md` C1/C2/C3. RC12 says only that "only redacted text" goes to the model. It has no PII-shape list, no spoken-number rule and no Aadhaar rule. Spoken numbers, Aadhaar, PAN, passport and DOB are therefore out of contract, so they appear below as PROPOSED-ISSUE and not as FAIL.
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=18 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

## Check plan

I did not read A's verdict, checkpoint or evidence. The plan, in order:

1. Leak hunt with a 97-case corpus plus a 6,000-input shape-by-context fuzz.
2. ReDoS timing at 200 KB, with scaling checks.
3. Over-masking probes.
4. Fail-open analysis of `build_judge_prompt` and its callers.
5. Targeted tests, ruff and doctor.
6. 18 mutants in a throwaway copy (`git archive HEAD`, never the bound tree).

All scripts are in the session scratchpad. No full suite: it is deferred to the combined head.

## Evidence per criterion

| # | Criterion (manifest) | Result | Evidence |
|---|---|---|---|
| 1 | ReDoS, `mask_pii` linear, 200 KB < 1.0 * timing_scale() | PASS | About 60 hand-built adversarial shapes at 200 KB: `@`*N, `a@`*N, `a@b`+dots/dashes, zero-width-space and Unicode runs, `+1`+spaces, `91`+spaces, `(`/`+(` runs, STD shapes, digit groups. Plus 60 random token-alphabet fuzzes and 200 periodic-unit fuzzes. Best of 3, the worst case was 0.29 s (`"@"*200k`); everything else was 0.26 s or less. Scaling 50k, 100k, 200k, 400k doubles each step (email scan 0.018, 0.039, 0.061, 0.135 s), so it is linear. Caveat: a single un-repeated first run under host load measured 0.94 s on `a@b`+`.`*200k and 0.06 s when repeated, so the margin under load is thinner than the median suggests, but the shape is linear. `mask_pii_obj`, wide: 20,000 strings (720 KB) took 0.8 s. The 9 linear tests in `test_redact_pii.py` pass. |
| 2a | non-ASCII / IDN email | PASS | `josé@exämple.com`, `अनु@example.com`, `jane@münchen.de` are masked (corpus). Weak test: mutant M9 survived (see below). |
| 2b | plus addressing, dotless host, non-emails keep `@` | PASS | `jane.doe+tag@sub.example.co.in`, `a@localhost`, `Ph.D. @ MIT`, `Tue @ 10 - 11`, `5 @ 3.50 each`, `@username` and `Follow @vidysea on X` are all handled correctly. Contiguous multi-email lists (`a,b;c`) are all masked. |
| 2c | Indian STD landlines | PASS | `011-23456789`, `(011) 2345 6789`, `022 2345 6789` and `+91 11 2345 6789` are masked. |
| 2d | dotted / grouped / bracketed phones, Devanagari digits, 12-digit anchor, short numbers | PASS | The shape-by-context fuzz covered 23 phone shapes by 28 prefixes by 20 suffixes. Every leak it found is a letter or digit glued directly to the number (`ID9876543210`, `9876543210x`), which is the intended `(?<![\w+])` / `(?!\w)` anchor, apart from the items in PROPOSED-ISSUE. Ten Devanagari digits are masked (`९८७६५४३२१०` becomes `<phone>`). |
| 3 | name labels | PASS | `नाम`, `पिता का नाम`, `माता का नाम`, `छात्र का नाम`, fname, lname, first_name, firstName, FIRST_NAME, `input[name=firstName]`, Dad, Mom, Papa, Mother, Father, guardian, Applicant, Nominee, Spouse, Referee and Candidate all mask. Placeholder, `[REDACTED]`, letterless and None values are untouched. |
| 4 | no over-masking | PASS with notes | Not masked, as intended: dates, ISO timestamps, INR/Rs/USD/EUR amounts (including `1,250,000` and `12,50,000/-`), years, `CS-101`, `MATH 2010`, IELTS 7.5, `110001`, ISBN, IPs, versions, GST, `Bank name: HDFC Bank`, University of Melbourne, and the Bank/University/Course/Company/School/Event/Plan name labels. Over-masking that remains is in PROPOSED-ISSUE. |
| 5 | nested strings in candidate and prompt | PASS | See fail-open analysis below. M11 and M13 are killed. |
| RC11 | determinism | PASS | `mask_pii` and `mask_name_value` are pure with no clock or iteration-order dependence. Idempotence holds on realistic text. |
| RC14 | design rules | PASS | `uv run autotester doctor` reports `doctor: clean`; `redact.py` is 260 lines; ruff is clean. |

## Fail-open analysis (security angle)

- The only caller is `stages/reconcile.py::build_judge_prompt` (L98-105), reached from `reconcile()` L272. Masking runs before `json.dumps`, then `redactor.scrub`, then `assert_no_raw_secrets`, then `provider.judge`.
- `build_judge_prompt` is called outside any `try`. The `try` blocks in `_judged` (L119, L124) only wrap `assert_no_raw_secrets` and `provider.judge`. If masking raised, `reconcile` would raise and no prompt would be sent. That is fail-closed, so I found no path where an exception in masking lets raw text reach the model.
- The dict handed to `mask_pii_obj` is built by `build_judge_prompt` with fixed depth (at most 3), so the recursion limit cannot be reached from reconcile.
- Unmasked free text still reaches the model by design (disclosed in the manifest "Known limits"): names in `said`, `cues` and `title`, and any value under an unrecognised label.
- AT-780's original `fix_direction` (drop `value`) is replaced by the masking direction. The earlier dual check already accepted this, and RC12 does not forbid it. Typed values under non-name labels, such as marks, school and address, therefore still leave the machine as heuristic-masked text. I raise this as a policy note only.
- `grade.py:178` also sends prompts and images to a judge model without `mask_pii`. That is out of this unit's scope, but it is the same boundary for real student screens.

## Tests run

All single-process, `uv run --directory D:/autoTesting/.worktrees/at780h pytest ... -p no:xdist`.

- Redact, reconcile and perf tests together: `tests/test_redact_pii.py`, `test_reconcile_pii.py`, `test_reconcile.py`, `test_redact_encoding_coverage.py`, `test_redact_ignorable_perf.py`, `test_redact_obfuscation.py`, `test_redact_wrap_perf.py`, `test_timing_scale.py`.
  - First run: 1 failed, 340 passed in 103.7 s. The failure was `test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` (7.84 s > 3 s).
  - That test exercises `assert_no_raw_secrets` and `contains_folded`. The diff does not touch them (checked with `git diff 13f37c3c 84f3e522` on the redact scrub and fold names).
  - Re-run alone: `18 passed in 7.97 s`. I attribute the failure to host load while another session was running, and not to this change.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: doctor: clean.
- Full suite not run (deferred to the combined head).

## Falsification (throwaway copy only; targets `test_redact_pii.py` + `test_reconcile_pii.py` + `test_reconcile.py`, 198 tests)

**Killed (14 of 18):**

- M1 left-scan ignores stop chars (quadratic)
- M2 only the first email masked
- M3 `mask_pii_obj` skips tuples
- M4 `mask_pii_obj` skips dict values
- M6 10-digit pattern needs a 91/0 prefix
- M7 role label ignores `_NOT_A_NAME_FIELD`
- M8 placeholders get masked
- M10 `mask_pii` skips phones
- M11 reconcile: candidate not masked
- M12 reconcile: name masking dropped
- M13 reconcile: no masking at all
- M14 STD landline last group 4 to 3
- M16 drop the Devanagari नाम label
- M18 drop the Indian grouped-mobile pattern

**Survived (4), which are test gaps and not product bugs:**

- M5 drop `(?!\w)` on the intl pattern. It only over-masks more.
- M9 require an ASCII first char after `@`. No test has a non-ASCII first host char, such as `a@éxample.com`. The Unicode claim (2a) is only partly pinned.
- M15 drop the `+` from the intl lookbehind. This relates to the `+91..+91..` leak below.
- M17 remove the `isalnum` guard after `@`. No test pins `a@.b` or `a@-x` as non-emails.

## PROPOSED-ISSUE lines

- PROPOSED-ISSUE: severity=medium, type=pii-leak, feature=redact — URL-encoded email and phone are not masked, so a query string built with `urlencode` leaks. Inputs: `https://x.com/p?email=jane.doe%40gmail.com&phone=%2B919876543210` returned unchanged; `jane%40gmail.com` returned unchanged. The plain-text `?email=jane.doe@gmail.com&phone=9876543210` is masked. Fix direction: percent-decode a copy before the scan, or add a `%40` pattern.
- PROPOSED-ISSUE: severity=low, type=pii-leak, feature=redact — phone shapes still leak:
  - Grouped Devanagari digits: `मोबाइल नंबर: ९८७६५ ४३२१०` (ten contiguous Devanagari digits are masked, the grouped form is not).
  - A digit run glued to a word or underscore on either side: `Mob9876543210`, `phone_9876543210`, `tel_9876543210`, `9876543210ext`.
  - Second number after a plus: `+919876543210+919876543211` masks only the first.
  - `00919876543210` (glued 0091), `987654.3210`, `1800 123 4567` (toll-free), `9876<TAB>543210` (tab group separator).
- PROPOSED-ISSUE: severity=low, type=pii-leak, feature=redact — email shapes the scanner stops at:
  - Full-width at: `jane＠gmail.com`.
  - Whitespace or newline around the `@`: `jane<LF>@gmail.com`, `jane@<LF>gmail.com`, `jane@ gmail.com`, `jane @gmail.com`.
  - Quoted local part: `"rahul sharma"@gmail.com` leaves `gmail.com`.
  - IP-literal host: `rahul@[192.168.1.1]`.
  - Obfuscated forms (`jane at gmail dot com`, `jane [at] gmail [dot] com`, `jane(at)gmail.com`) are disclosed in the manifest "Known limits".
- PROPOSED-ISSUE: severity=low, type=pii-leak, feature=redact/mask_name_value — person-name labels not recognised, so the value stays visible:
  - Romanised Hindi: `Aapka naam`, `Pita ka naam`, `Naam`.
  - Devanagari surname: `उपनाम` (the `(?<![\w{_DEV}])` lookbehind rejects the prefix).
  - Full-width `Ｎａｍｅ`, and `N<ZWSP>ame` with a zero-width space.
  - Non-English: `Prénom`, `Nom`, `Vorname`, `Apellido`.
  - Relatives and holders: `Brother`, `Sister`, `Sibling`, `Wife`, `Husband`, `Son`, `Daughter`, `Uncle`, `Relative`, `Friend`, `Contact person`, `Emergency contact`, `Referred by`, `Account holder`, `Cardholder`, `Signature`, `Display name`, `Username`, `Nickname`.
  - A bare `Textbox 1` with a name value is also not masked (already disclosed).
- PROPOSED-ISSUE: severity=low, type=pii-leak, feature=reconcile — names in free text (narration `said`, `cues`, titles) are never masked. For example `Name: Rahul Sharma` or `Name –<LF>Rahul Sharma` inside one string. Disclosed, but it is the largest remaining real-data exposure. Consider an AT-NNN to decide whether the judge needs `said` at all.
- PROPOSED-ISSUE: severity=low, type=over-masking, feature=redact:
  - Any `Student`/`Parent`/`Father`/`Mother`/`Counsellor` label not in the exclusion list masks a non-name value to `<name>`. Examples: `Student board/stream/city/state/nationality/gender/percentage/budget/interests/notes`, `Father occupation`, `Mother tongue`, `Parent income`, `Counsellor notes`. Also `Rule/Field/Page/Tab name`.
  - Any ten-digit number is a phone: `Application ID: 2026091512`, `Timestamp 1700000000`. A 13-digit run starting `00` (`Reference 0012345678901`) and `Code 123-456-7890-12` match the STD pattern.
  - `e.g. user@example` becomes `<email>` (dotless host, intended).
  - Dates, money, years, course codes, university names and `Bank name` are all preserved.
- PROPOSED-ISSUE: severity=low, type=robustness, feature=redact/mask_pii_obj — the public helper is not safe for general reuse:
  - Depth of about 900 or more raises RecursionError (900, 1000 and 5000 all failed; 400 was fine). That is fail-closed, and not reachable from reconcile today.
  - A namedtuple raises TypeError.
  - sets, frozensets and bytes are returned UNMASKED with no error (`mask_pii_obj({"a@b.com"})` returns the set as is). That is a silent pass-through if a future caller feeds one in.
  - An OrderedDict is returned as a plain dict.
  - Fix direction: iterative walk or an explicit unsupported-type raise.
- PROPOSED-ISSUE: severity=low, type=test-gap, feature=redact — mutants M9, M17, M15 and M5 survive. Add tests for a non-ASCII first host character, for `a@.b` and `a@-x` staying non-emails, and for `+91..+91..` adjacency.
- PROPOSED-ISSUE: severity=info, type=scope, feature=redact — spoken numbers (`nine eight seven six ...`, `nau aath saat ...`, `9876 five four three 210`), spaced digits (`9 8 7 6 5 4 3 2 1 0`), Aadhaar (`1234 5678 9012`, `123456789012`, dashed), PAN (`ABCDE1234F`), passport and DOB (`12/03/2005`) are all unmasked. The contract has no rule for them, so this is out of scope. If transcripts are to reach a model, a separate unit should decide on them.
- PROPOSED-ISSUE: severity=info, type=test-flake, feature=tests — `test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` failed once at 7.84 s against a 3 s bound under combined-run load and passes alone (18 passed in about 8 s total for the file). Unrelated to the unit but worth a look under AT-757.

## Residual risk

Masking is heuristic. The unit does what its manifest claims and nothing here breaks RC11, RC12 or RC14. Real student and parent data can still reach the model through the categories above.
