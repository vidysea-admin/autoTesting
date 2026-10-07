# Manifest — t151-target-discovery
**Contract:** qa/contracts/ai-target.md (AI1, AI8 bind T-151; core-invariants C5/C7)
**Goal task:** T-151
**Date:** 2026-10-07
**Fix cycle:** 3 (narrow, Umesh-authorized D-071, X17 only)
**Dual check:** required   <!-- credential refusal, path-escape and approval gating are a security boundary -->
**Persona walk:** skip (backend-only: no human screen; Track C below-the-UI discovery)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** gate answered; merge of master + manifest close-out by a maker subagent in the t151 worktree; no external executor worthy.

## What changed
Cycle 3 (narrow, Umesh-authorized D-071 via qa/gates/t151-cycle2-stalled.md answer A; X17 only): one committed test added to tests/test_discover_hardening.py (`test_deadline_is_checked_inside_the_scan_emission_loop`, +18 lines, now 176; 28 cases); no product file changed. It defends the per-Signal deadline check in `discover.py::_emit`, the one cycle-2 survivor in B's verdict.
Cycle-2 fixes (both cycle-1 FAILs, fix list items 1-7). Complete list from `git diff --name-only 2fae2504...HEAD` follows the fixes.
- Merge of master into the branch (D-065, D-063/D-066 gate files, issues row now present; `qa/.last-tick` not committed). Dangling-citation doctor violations for D-065 and `tests/test_citations.py::test_the_real_tree_has_no_dangling_citation` are green.
- src/autotester/stages/text_lines.py (new, 18) — one shared line splitter (`split_lines`, `first_nonblank_line`): lines are counted by 
, 

 and 
 only. Replaces the three `str.splitlines()` call sites in read_context.py and discover.py (U+2028/U+2029/U+0085///- no longer shift Signal lines).
- src/autotester/stages/credential_files.py (new, 16) — credential denylist moved out of discover.py (which would otherwise exceed 300 lines) and extended: .envrc .npmrc .netrc .pypirc .htpasswd *.jks *.keystore *.p8 id_ecdsa credentials.yml secrets.yaml service-account.json token.json.
- src/autotester/stages/discover.py (286) — `_emit` enforces `max_signals` (refusal `signal_budget`) and the deadline per Signal; `scan` refuses a file with `parse_depth` on RecursionError/MemoryError and continues; the final deadline check now runs after `redactor.assert_clean`.
- src/autotester/stages/read_context.py (164) — `_guard` (signal budget + deadline inside the tag/frontmatter emission loop), final deadline after `assert_clean`, per-file `parse_depth` refusal, `_metadata` refuses a cyclic structure as `yaml_alias` instead of recursing.
- src/autotester/schema/ai_target.py — `ScanLimits.max_signals` (default 2000, ge=1, le=20000; `extra="forbid"` kept).
- tests/test_discover_hardening.py (new, 158 at cycle 2, 176 and 28 cases at cycle 3) — committed defenders. NOTE: tests/test_discover.py is already at the 300-line cap (doctor C2 counts tests/), so the new cases could not be appended to it; they live in this sibling file instead of test_discover.py (deviation from fix-list wording, forced by the file-size rule).
- docs/MAP.md, docs/SNAPSHOT.md — regenerated (`autotester map`, `autotester snapshot`).
- Carried from cycle 1 (already on the branch): src/autotester/prompts/ai_target_classify_v1.md, src/autotester/providers/mock.py (`act` hunk), pyproject.toml / uv.lock (`pyyaml==6.0.3`), tests/test_discover.py (63 cases), docs/DECISIONS.md (D-065 via master), qa/gates/d063-cn5-vs-cn11.md, qa/gates/d063-self-grant-csrf.md, qa/gates/t151-dependency-authorization.md, qa/gates/t196-l10-coverage.md, qa/issues.jsonl (all from master), qa/checkpoints/t151-target-discovery.md and .b.md, qa/verdicts/t151-target-discovery.md, .b.md, -scoped-cycle1.md, -repair-scoped-cycle1.md (checker records), qa/evidence/t151-independent-cycle1-2026-10-05/ (alias-independent-results.json, results.json, t151_checker_mutations.py, t151_checker_probe.py, t151_checker_yaml_proof.py), qa/evidence/t151-independent-rebind-cycle1-2026-10-05/ (results.json, t151_checker_rebind_mutations.py, test_checker_yaml.py), qa/evidence/t151-independent-repair-cycle1-2026-10-05/ (repair-results.json, t151_checker_repair_mutations.py, t151_checker_repair_probe.py), qa/evidence/t151-maker-cycle1-2026-10-05/ (native-tool-receipt.md, t151_maker_filesystem_probe.py), qa/manifests/t151-target-discovery.md (this file).

## Verification scope
Policy-Version: proportional-verification/2026-10-06.6
Tier: L (dependency bump + credential, path-escape and approval boundary)
Base SHA: master 2fae2504 merged (merge commits on the branch; D-065 present). Checked state: branch codex/t151-target-discovery HEAD at ready-for-check (re-bind SHA and dirty diff hash at Mode A)
Gate answers (qa/gates/t151-dependency-authorization.md, verbatim): "Answered: 2026-10-07 — A — chat (Umesh): approve all three (pyyaml==6.0.3, the target-discovery prompt file, the mock.py act hunk). DECISIONS entry to follow." Recorded as D-065 (docs/DECISIONS.md, Approved-by Umesh); Changes-authorized: pyproject.toml / uv.lock (pyyaml==6.0.3) · src/autotester/prompts/ai_target_classify_v1.md · src/autotester/providers/mock.py `act` hunk.
Affected tests / full-suite trigger: tests/test_discover.py (63) + tests/test_discover_hardening.py (28) + tests/test_citations.py. The builder runs no full suite (suite_runs=0); the checker decides on the full-suite trigger (new dependency touches uv.lock).
Metrics: start=2026-10-07T03:00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=14 cycle=3 resumes=2 tokens=unavailable policy=2026-10-06.6

## How to verify (commands + expected)
- `uv run ruff check src tests scripts` → expected: All checks passed
- `uv run pytest tests/test_discover.py tests/test_discover_hardening.py tests/test_citations.py` → expected: 102 passed (test_citations carries the D-071 caveat below)
- `uv run autotester doctor` → expected: `doctor: clean`
- `grep -rniE obsidian pyproject.toml` → expected: no output, exit 1

## Actual outputs (from maker's own run, 2026-10-07)
- ruff: `All checks passed!`
- pytest (three files above): `101 passed in 94.38s (0:01:34)`
- Cycle 3 (2026-10-07): `uv run pytest tests/test_discover.py tests/test_discover_hardening.py` -> `91 passed in 13.38s` (63 + 28); `ruff check src tests scripts` -> `All checks passed!`. X17 falsification, throwaway copy (git archive HEAD) outside the worktree, the single new node: `1 passed` -> `1 failed` (mutant `_emit` per-Signal check -> `if False`; `len(result.signals) < 50` assertion fails) -> `1 passed` (`discover.py` restored from HEAD). No full suite, no test_citations run.
- Cycle 3 doctor: 1 pre-existing violation outside this change, `decision-citation-dangling qa/verdicts/t151-target-discovery.md:26` (the checker's own text quotes the mutant the `## D-065` heading with a trailing 0 appended); and D-071, cited above per the coordinator, has no entry on this branch (it is on master, c2ebfdc6) so the same rule flags it until master is merged. Neither is caused by the test file.
- doctor (cycle 2, after `autotester map` and `autotester snapshot`): `doctor: clean`. Caps: discover.py 286, read_context.py 164, text_lines.py 18, credential_files.py 16, ai_target.py 123, test_discover.py 300, test_discover_hardening.py 158.

## Capability coverage (each claim -> a committed test and its isolating falsification)
Every defender below is a node in tests/. Each row's runner line is from a throwaway copy of the tree outside the bound worktree (the maker's scratch driver is not committed), the single named node only: baseline -> mutant -> restored.

| Criterion | capability | the committed check | the falsifying edit | observed (baseline -> mutant -> restored) |
|---|---|---|---|---|
| AI1 | Signal lines are physical 
/
/ lines (U+2028,  no shift) | tests/test_discover_hardening.py::test_unicode_and_formfeed_separators_do_not_shift_reader_lines and ::test_unicode_and_formfeed_separators_do_not_shift_scan_lines | text_lines.split_lines returns `text.splitlines()` | `2 passed` -> `2 failed` -> `2 passed` |
| AI1 | reader tag Signal cites the exact file:line | tests/test_discover_hardening.py::test_reader_signal_lines_match_exact_source | read_context Markdown-tag `line=line` -> `line=line + 1` | `1 passed` -> `1 failed` -> `1 passed` |
| AI1 | reader frontmatter Signal cites the exact file:line | same node | frontmatter `line=line` -> `line=line + 1` | `1 passed` -> `1 failed` -> `1 passed` |
| AI1 | scanned Python is parsed, never executed | tests/test_discover_hardening.py::test_scanned_python_is_never_executed (sentinel file absent) | `exec(compile(text, ...))` before `ast.parse` in `_python_facts` | `1 passed` -> `1 failed` -> `1 passed` |
| AI8 | Markdown only: a .txt context file yields no document | tests/test_discover_hardening.py::test_non_markdown_context_files_yield_no_document | `suffix.lower() != ".md"` -> `not in {".md", ".txt"}` | `1 passed` -> `1 failed` -> `1 passed` |
| C5 / YAML | non-cyclic and cyclic alias refused as `yaml_alias`, complete=False, generous limits | tests/test_discover_hardening.py::test_yaml_alias_is_refused_under_generous_limits | `if isinstance(event, AliasEvent)` -> `if False` | `2 passed` -> `1 failed, 1 passed` (the non-cyclic case dies; the cyclic case is also caught by the `_metadata` cycle guard) -> `2 passed` |
| C5 / bounds | tag flood ends in visible `signal_budget`, no Signals | tests/test_discover_hardening.py::test_tag_flood_is_a_visible_signal_budget_refusal | `_guard` cap `emitted >= max_signals` -> `>= 10**9` | `1 passed` -> `1 failed` -> `1 passed` |
| C5 / bounds | import flood ends in visible `signal_budget` | tests/test_discover_hardening.py::test_import_flood_is_a_visible_signal_budget_refusal | `_emit` cap -> `> 10**9` | `1 passed` -> `1 failed` -> `1 passed` |
| C5 / bounds | deadline is checked inside the emission loop | tests/test_discover_hardening.py::test_deadline_is_checked_inside_the_tag_emission_loop | `_guard` deadline body -> `pass` | `1 passed` -> `1 failed` -> `1 passed` |
| C5 / bounds | scan emits Signals under a per-Signal deadline (500-line `import openai` file, clock +1 per scrub, `wall_clock_s=5`): scan stops early with a visible `wall_clock_s` refusal, `complete=False`, fewer than 50 Signals and scrub calls | tests/test_discover_hardening.py::test_deadline_is_checked_inside_the_scan_emission_loop | `discover.py::_emit` per-Signal `if time.monotonic() - started >= scope.limits.wall_clock_s:` -> `if False:` | `1 passed` -> `1 failed` -> `1 passed` |
| C5 / bounds | deadline is rechecked after the final redaction (reader) | tests/test_discover_hardening.py::test_deadline_is_rechecked_after_the_final_redaction | reader post-assert_clean deadline check -> `if False` | `2 passed` -> `1 failed, 1 passed` -> `2 passed` |
| C5 / bounds | same, scan | same node | scan post-assert_clean deadline check -> `if False` | `2 passed` -> `1 failed, 1 passed` -> `2 passed` |
| C5 / bounds | deep binop and decorator chains are a per-file `parse_depth` refusal and the scan continues | tests/test_discover_hardening.py::test_deep_binop_chain_is_a_per_file_refusal_and_scan_continues and ::test_deep_decorator_chain_is_a_per_file_refusal_and_scan_continues | `except (RecursionError, MemoryError)` -> `except KeyError` | `2 passed` -> `2 failed` -> `2 passed` |
| C5 / credentials | .envrc .npmrc .netrc .pypirc .htpasswd *.jks *.keystore *.p8 id_ecdsa credentials.yml secrets.yaml service-account.json token.json refused, never opened | tests/test_discover_hardening.py::test_more_credential_files_are_refused_without_being_opened (13 params) | credential_files `_NAMES`/`_SUFFIXES` reverted to the cycle-1 lists | `13 passed` -> `13 failed` -> `13 passed` |
| AI1 | no Provider call on the signal-emission path | tests/test_discover.py::test_discovery_never_calls_provider | not re-run this cycle (unchanged); cycle-1 checker record | see verdicts; checker re-verifies |
| AI8 | frontmatter and tags only, secrets scrubbed | tests/test_discover.py::test_context_is_metadata_only_and_secrets_are_scrubbed | not re-run this cycle (unchanged) | checker re-verifies |
| C5 / path-escape | symlink and junction escape refused | tests/test_discover.py::test_symlink_escape_is_refused | not re-run this cycle (unchanged; cycle-1 proof recorded `2 passed -> 2 failed -> 2 passed`) | checker re-verifies |
| (dependency) | pyyaml==6.0.3 is the only new dependency | pyproject.toml:26 | n/a | authorized by D-065; `grep -n pyyaml pyproject.toml` -> `26:    "pyyaml==6.0.3",` |

Claims dropped from cycle 1 because their defenders were checker scratch oracles, not tests/ nodes: Dataview/backlink/body exclusion "28/28 mutants" (G4-22..24), approval-exception sanitation (test_denial_class_and_formatted_chain_are_safe), and the cycle-1 reader/exec/alias names (now the committed nodes above).

## Live browser evidence
Not UI-touching — no surface changed (src/autotester/schema/ai_target.py, stages/discover.py, stages/read_context.py, prompts/ai_target_classify_v1.md, providers/mock.py, tests/test_discover.py, pyproject.toml). Discovery reads local Markdown and code files only; no browser, network or live model.

## Evidence kept / removed
Kept: results.json per run, probe/mutation scripts, native-tool-receipt.md and the verdicts. Removed (git rm, commit e7033787): 87 raw per-test XML/txt dumps from the four t151-* evidence directories.

## Status: checked-PASS

Closed out 2026-10-07 (Tier L, dual check, both coordinators PASS): coordinator A PASS at b18e4ea6 (qa/verdicts/t151-target-discovery.md, cycle 2); coordinator B PASS at f0282ce5 (qa/verdicts/t151-target-discovery.b.md, cycle 3, X17 only per D-071). Goal task T-151 closed. Follow-up PROPOSED-ISSUEs filed in qa/issues.jsonl as AT-765..AT-769.
