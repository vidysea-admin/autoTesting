# Gate — AT-520: should C2 (file/function-length cap) and the duplicate-definition
check extend from `src/`+`tests/` to `scripts/`?

**Why this gate exists, not a rule change:** `scripts/` holds three load-bearing but
ungoverned instruments (AT-488 `mutation_check.py` erosion, AT-502 `flake_probe.py`
churn, AT-520 total doc invisibility, filed independently across a week). The
temptation is to fold `scripts/` into the same governance as `src/`+`tests/` in one
move. Measuring first (below) shows that move is not safe as a single step — it
would turn `doctor` red over one pre-existing file and manufacture 17 false
positives out of a completely ordinary CLI-script idiom. This project has twice
this week nearly shipped a rule that accused the innocent (AT-504, AT-511); this
gate exists so a third near-miss doesn't happen by acting on AT-520's real, narrow
finding (docs) as if it also justified widening the other three rules.

## Measurement — every file in `scripts/` (2026-09-18)

| File | Lines | > 300 (C2 if extended)? |
|---|---:|---|
| `check_crawl_approval.py` | 61 | no |
| `check_deliverable.py` | 79 | no |
| `check_no_secrets.py` | 98 | no |
| `score_video_issues.py` | 125 | no |
| `onboard_pathlynks.py` | 142 | no |
| `append_decision.ps1` | 144 | no |
| `explore_proof.py` | 181 | no |
| `bench_trial.py` | 184 | no |
| `regression_proof.py` | 199 | no |
| `migrate_url_patterns.py` | 207 | no |
| `run_pathlynks_first_cases.py` | 214 | no |
| `flake_probe.py` | 244 | no |
| `mutation_check.py` | 416 | **yes — already known (AT-488)** |

**check_file_sizes (300-line cap) if extended:** 1 violation out of 13 files —
`mutation_check.py` (416 lines), already flagged as a structural-erosion signal by
AT-488, not a new finding. Every other script is already under budget.

**check_function_sizes (50-line cap) if extended:** 4 violations, in 4 different
files:

| File | Function | Lines |
|---|---|---:|
| `bench_trial.py` | `main` | 108–180 (72) |
| `mutation_check.py` | `_check_in` | 308–374 (66) |
| `onboard_pathlynks.py` | `_write_knowledge` | 78–134 (56) |
| `run_pathlynks_first_cases.py` | `main` | 143–210 (67) |

**check_duplicate_definitions if extended:** 17 violations, entirely from the
ordinary "every standalone script defines its own `main()`" idiom — not drift:

| Name | Defined in | Violations (all but the first) |
|---|---|---:|
| `main` | 9 of 13 scripts (`bench_trial`, `check_crawl_approval`, `check_deliverable`, `explore_proof`, `flake_probe`, `migrate_url_patterns`, `mutation_check`, `regression_proof`, `run_pathlynks_first_cases`, `score_video_issues` — 10 files, first is "seen") | 9 |
| `build_cases` | `bench_trial`, `regression_proof`, `run_pathlynks_first_cases` | 2 |
| `make_rubric` | `bench_trial`, `regression_proof`, `run_pathlynks_first_cases` | 2 |
| `start_server` | `bench_trial`, `explore_proof`, `regression_proof` | 2 |
| `run_and_grade` | `bench_trial`, `regression_proof` | 1 |
| `scan` | `check_no_secrets`, `migrate_url_patterns` | 1 |
| **Total** | | **17** |

`check_duplicate_definitions` exists to catch the same concept re-implemented in
two modules (the `d:/erp` failure mode). `scripts/` is a directory of independent,
standalone CLI entry points by design — each one's `main()` is the Python idiom for
"this file is runnable," not a duplicated concept. Extending the rule unmodified
would flag 17 instances of that idiom as drift on day one, with zero of them being
a real duplicate-concept bug.

## What already shipped (not gated — see the manifest)

Doc coverage only: `docs/MAP.md` now has a generated `## Scripts` section (every
`scripts/*.py` and `*.ps1` gets a one-job row, from its docstring or header
comment), closing AT-520's actual finding — a file's existence was undiscoverable
through any routed doc. This is additive documentation with no enforcement
behaviour change, so it carries no risk of turning `doctor` red.

## Options

1. **Extend `check_file_sizes` and `check_function_sizes` to `scripts/` as-is,
   accept `mutation_check.py` (1 file) and the 4 function-length violations as
   pre-existing debt to fix first, and fix them before turning the check on.**
   Cost: `mutation_check.py` is explicitly the repo's most safety-critical
   instrument (AT-488's own finding) — trimming it to fit a cap is real, careful
   work, not a mechanical split, and is explicitly out of scope for this unit
   per its brief.
2. **Extend `check_duplicate_definitions` to `scripts/` only after adding an
   exemption for standalone-script idioms** (e.g. skip `main` entirely, or scope
   the check per-file when a module has no `__init__.py`-style import surface).
   Cost: this is a rule-design decision, not a mechanical scope widen, and needs
   its own review so the exemption doesn't also hide a real duplicate.
3. **Do not extend the numeric caps to `scripts/` at all.** Instead, govern
   `scripts/` differently: a lighter per-script rule (e.g. "no `*_v2.py`/`*_new.py`"
   already applies path-agnostically? — no, `check_file_names` also only walks
   `src/`) or simply leave `scripts/` ungoverned by the numeric caps and rely on
   human review + the doc coverage just shipped to keep it visible.
4. **Something else that emerges from a `/grill` on how CLI-script instruments
   should be governed differently from library code.**

**Command:** `/grill "scripts/ governance — line caps and duplicate-definition
check for CLI instruments vs src/ library code"`, or a direct decision from Umesh
if the tradeoff above is already clear enough without a full interview.

**Blocks:** AT-520's remaining half (any rule change to `doctor.py`'s numeric
checks over `scripts/`); AT-488 (whether `mutation_check.py`'s length is itself
a unit to fix, and if so before or after a cap would apply to it); AT-502
(whether `flake_probe.py`'s churn rate is a symptom this gate's answer would
also address).

**Opened:** 2026-09-18 (AT-520 build unit, measured before proposing).

**Answered:** 2026-09-26T22:34:22+05:30 — Option 3 — Umesh via AskUserQuestion in the checker session. scripts/ stays outside the numeric caps (300-line file, 50-line function) and the duplicate-definition check; visibility through docs/MAP.md (already shipped). AT-520's remaining half closes as decided; AT-488 is no longer a cap violation.
