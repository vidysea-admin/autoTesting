# Build brief: land-integrate-combined

Written 2026-10-11 by a read-only readiness pass. Dispatchable: yes (criteria exist, no open gate). Source of the unit: `qa/QUEUE.md:18-28`, D-080 item 1 and the Result paragraph of D-080, D-081.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier L.** Trigger: security. The unit lands `src/autotester/core/redact.py` (PII masking, the data boundary before a model call; `core-invariants.md` C5) and the `build_judge_prompt` change in `src/autotester/stages/reconcile.py:92-106`, the only path where typed step values reach a model. The two source units were tier L for the same reason (`qa/manifests/at780-pii.md`, `at780-harden.md`).
- **Dual check: required.** Trigger: `security src/autotester/core/redact.py:173` (`mask_pii` on `integrate/combined`) and `security src/autotester/stages/reconcile.py:92` (`build_judge_prompt`). Both earlier checks were dual and both PASSed cycle 0, but they reviewed the code on base 7782df41, never on this merged head. The security code (`redact.py`, both test files) is byte-identical to the PASSed commit 84f3e522 (`git diff 84f3e522 integrate/combined -- <those 3 files>` is empty), so the owner may waive the second checker; that is the owner's call, not the builder's.

## 2. Root and base

- Root: `D:/autoTesting`.
- Base: current `master` = `4f8f5da100931ebda1b26836304bfbd38460764b` (2026-10-10 22:44 IST). Re-read `git -C D:/autoTesting rev-parse master` at start; if it moved, rebase the branch and say so in the manifest.
- Build in a NEW branch `wave/land-integrate-combined` in worktree `D:/autoTesting/.worktrees/land-integrate-combined`, created from master. Reason: D-080 item 1 says Codex and old worktrees are inputs, never state to merge wholesale, and `integrate/combined` (tip `c59f841a`, worktree `.worktrees/combined`, clean) must stay untouched as the record of what the PASS reviewed. Bring its content in with `git merge integrate/combined` so the reviewed commits (1856e5c4, 84f3e522) and the manifests and verdicts keep their history. A merge commit is a new commit, so a new checker cycle is needed, as D-080 says.
- The branch `wave/land-integrate-combined` does not exist yet (checked).

## 3. Acceptance criteria

Verbatim from `qa/contracts/reconcile.md` (the contract both source units were judged against) and `qa/contracts/core-invariants.md`.

**RC11** (`reconcile.md:126`): "deterministic and idempotent. *serves: O2, O3.* Reconciling the same inputs (the video observations/FlowSpecs, the crawl nodes, the same mock provider script) twice gives byte-identical saved output (same ids, same order, same report); reconciling an already-reconciled FlowSpec with the same inputs changes nothing (no version bump, nothing re-ordered). Output order never depends on dict/set iteration or wall-clock time; timestamps are not part of the compared payload. *Check:* two runs produce equal bytes; a second run over its own output produces equal bytes; the judge is called 0 times on the second run over a fully decided fixture."

**RC12** (`reconcile.md:133`): "model calls go through the seam; no secret and no original reaches a model. *serves: O7, R16.* Every model call goes through `providers.base.Provider` (no direct SDK import in the new code); the judge prompt is a file (`skills/…/SKILL.md` via `load_skill_prompt`, never an inline string); `core.redact.assert_no_raw_secrets` runs over the full prompt text before every call; only redacted text and no unredacted original (transcript sidecar, screenshot, step value) is passed. *Check:* a seeded secret in a step value, a field and a narration is replaced in the captured prompt (or the call is refused) and the recording mock never sees the raw value; the reconcile module has no `import anthropic`, `google.genai` or `requests`/`httpx`; its judge prompt file exists on disk."

**RC14** (`reconcile.md:145`): "design rules and scope hold. *serves: C1, C2, C3.* New schema models and fields live in `schema/` with `extra="forbid"`; every touched or new file stays ≤300 lines and every function ≤50 lines (if `schema/flowspec.py` would pass 300 lines the maker splits a model family out, as D-014 did, rather than raising the cap); the module has a docstring naming its one job; no second definition of any class or public function name; no `*_v2.py`/`*_new.py`. **Out of scope and untouched:** `stages/review.py` `require_reviewed` and review-gate R1 — downgrading it to status-only is a separate L unit (protected test change) and a diff of this unit that touches either fails this criterion. `docs/ARCHITECTURE.md` and `docs/MAP.md` are updated only through their own authorized paths. *Check:* `uv run autotester doctor` exits 0; `git diff --stat` shows no change to `stages/review.py` or `tests/test_review*.py`."

**C2** (`core-invariants.md:25`): "No file in `src/` or `tests/` exceeds 300 lines; no function exceeds 50 lines. Every module has a docstring stating its one job. … **Verify:** `uv run autotester doctor` exits 0."

**C3** (`core-invariants.md:36`): "No class or public top-level function name is defined in two modules. No file named `*_v2.py`, `*_new.py`, `*_old.py`, `*_copy.py`, `*_final.py`, `*_temp.py`. Changes edit existing files in place; a new module requires a stated reason in the manifest. **Verify:** `uv run autotester doctor` exits 0 (duplicate-concept + drift-filename rules)."

**C1** (`core-invariants.md:18`): "Every domain data shape is a Pydantic model under `src/autotester/schema/` … **Verify:** `uv run pytest tests/test_schema.py` exits 0." (This unit adds no model.)

The merged unit's own acceptance, from the two source manifests: `at780-pii.md` and `at780-harden.md` criteria 1 to 5 (ReDoS-linear `mask_pii`, non-ASCII/plus-address/dotless emails, Indian STD and grouped phones, name labels, no over-masking, nested strings). They are already encoded in the two test files below; do not re-derive them.

Note for the checker: the contract has no PII-shape list in RC12 (issue AT-839). Umesh's direction (recorded in the AT-780 row) replaced "drop `value`" with "keep the value, mask PII shapes", so RC12's literal "no ... step value" is read as "no unmasked step value". That reading was accepted by the four earlier verdicts; do not reopen it here.

## 4. What exists and what is missing

Exists:
- Branch `integrate/combined`, tip `c59f841a`, 8 commits ahead of master and 13 behind. Commits: `1856e5c4` fix(reconcile) mask email/phone/name in the judge prompt (AT-780); `498290c7` and `13f37c3c` at780-pii checker B and A verdicts; `84f3e522` fix(redact) AT-780 hardening; `6a912ae9` and `0f5d48b3` at780-harden checker B and A verdicts; `790973de` merge; `c59f841a` maker close-out plus issues AT-830..AT-840.
- Verdicts (all `Cycle checked: 0`, all PASS): `qa/verdicts/at780-pii.a.md` (commit 1856e5c4; full suite BLOCKED-PROCESS), `at780-pii.b.md` (1856e5c4), `at780-harden.a.md` (head 84f3e522; full suite "deferred to the combined integration head"), `at780-harden.b.md` (84f3e522). Manifests `qa/manifests/at780-pii.md` (64 lines) and `at780-harden.md` (79 lines), both `Status: checked-PASS`.
- Diff vs master (11 files, +884 -5): `src/autotester/core/redact.py` (159 -> 260), `src/autotester/stages/reconcile.py` (298 -> 302; the branch's own change is +4 lines, lines 19, 92-106), new `tests/test_redact_pii.py` (140), new `tests/test_reconcile_pii.py` (115), `qa/issues.jsonl` (+13/-1), the two manifests, four verdicts.
- Merge today: `git merge-tree --write-tree master integrate/combined` returns a tree (`5b8db7d9...`) with no conflict. (`merge-tree` wrote that tree object into the object store; no ref changed.) The merged tree's `qa/issues.jsonl` parses (865 rows, 0 bad lines). Duplicate ids in it (AT-288..291, AT-547..552, AT-710, AT-772) already exist on master; not this unit's.
- D-080 Result: merged onto master it fails `autotester doctor` because `stages/reconcile.py` reaches 302 lines (limit 300 at `src/autotester/doctor.py:20`, reported at `doctor.py:80-82`).

Missing / the defects to fix:
1. **reconcile.py is 2 lines over.** Branch change versus master: import line 19 (+0, longer), `actions` list comprehension 2 -> 3 lines (+1), `video, other = mask_pii_obj(video), mask_pii_obj(other)` (+1), docstring of `build_judge_prompt` 1 -> 3 lines (+2). Total +4 on 298 = 302.
2. **No verdict reviewed this tree.** The four PASSes reviewed commits 1856e5c4 and 84f3e522 on base 7782df41. The only file that differs between 84f3e522 and the merged tree (in the four unit files) is `stages/reconcile.py`, by master's own narration changes (AT-779/AT-785) plus the trim. Full suite was deferred twice and never run on any merged head.
3. **AT-780 is flipped to `verified` by the maker** (`c59f841a`, row in `qa/issues.jsonl`). `qa/QUEUE.md` and D-080 say the checker alone sets issue status. Restore the AT-780 row to its master text (status `open`, no fixed/verified dates, no resolution) in the merged `qa/issues.jsonl` and leave AT-830..AT-840 appended; the new checker sets AT-780 after its PASS. Also set both manifests' `Status:` line to what the new commit supports (the maker edits only its own manifests; the verdict files stay as written, they are records).

**Smallest behaviour-neutral fix for the 2 lines (recommended):** edit `stages/reconcile.py` in place, function `build_judge_prompt` (`stages/reconcile.py:92-106` on the branch; on master the function is at 92-103). Cut its 3-line docstring back to one line, for example
`"""Descriptions only, PII-masked (AT-780): never a transcript, screenshot or file (RC12)."""` (95 columns, under ruff's 100). That removes 2 lines, 302 -> 300, which satisfies "≤300". It changes no executable line, so RC11 byte-identity and every existing test are unaffected. Cost: zero headroom, but `qa/QUEUE.md:28` says this row alone owns `reconcile.py` and any other row touching it waits.
Headroom alternative, NOT recommended now: move `narration_drop_report` (`reconcile.py:146-150`, 5 lines plus 2 blank) out. It is imported at `src/autotester/cli_video.py:29`, `src/autotester/stages/orchestrate_runners.py:34` and `tests/test_ingest_transcripts.py:34`, and no existing module obviously owns narration reporting (`verify_narration` has the same shape and `stages/ingest.py:32` imports it from `reconcile`), so a move is a multi-file refactor and a design call, not a trim. Do not create a new module for it (C3, `*_v2`/`*_new` ban). If the owner wants headroom, that is a separate unit.

Out of scope, stays open (do not fix here): AT-830..AT-839 (redact residuals), **AT-840 (high, open: `stages/grade.py:178` sends prompts and images to the judge with no `mask_pii`; this unit does not touch it)**. AT-758 and AT-759 are NOT closed by this unit: they are `d063-grant-budget` security rows (Host allow-list, account-derived approvals) and belong to `wave/at758-759-security`. The only issue this unit closes is AT-780 (the checker flips it).

## 5. Files the builder will touch

Hand-edited:
- `src/autotester/stages/reconcile.py` (existing, 298 on master; 300 after the trim).
- `qa/issues.jsonl` (existing, 854 lines on master; merge-resolved: AT-780 row restored to master text, AT-830..AT-840 present once each; maker may append rows, never edit others).
- `qa/manifests/land-integrate-combined.md` (new, the maker's own manifest; the manifest names a reason because it adds no module).
- `docs/MAP.md` (existing, 349 lines): run `uv run autotester map`; commit only if it produces a diff (AT-756 says it was stale on master once). The generated section is never hand-edited.

Arrive through the merge, not hand-edited:
- `src/autotester/core/redact.py` (existing, 159 -> 260).
- `tests/test_redact_pii.py` (new, 140) and `tests/test_reconcile_pii.py` (new, 115).
- `qa/manifests/at780-pii.md` (new, 64), `qa/manifests/at780-harden.md` (new, 79).
- `qa/verdicts/at780-pii.a.md` (90), `at780-pii.b.md` (78), `at780-harden.a.md` (72), `at780-harden.b.md` (125) (new).

Do not touch: `stages/review.py`, `tests/test_review*.py` (RC14), `qa/contracts/*` (checker-owned), `stages/grade.py`.

## 6. Test scope

Builder (exact files, one pytest process, no xdist):
`uv run pytest tests/test_redact_pii.py tests/test_reconcile_pii.py tests/test_reconcile.py tests/test_redact_encoding_coverage.py tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py tests/test_redact_wrap_perf.py tests/test_timing_scale.py -p no:xdist`
(the same eight files the at780-harden checker ran: 341 passed on the old base), then `uv run ruff check src tests scripts` and `uv run autotester doctor`. Note: adapter `uv run pytest` carries `-q` in `addopts`; add no further `-q` (AT-503).
The builder runs no full suite. The checker owns the one full suite (tier L); it was owed since `at780-harden.a.md` line 8.

## 7. Reachable test cases

All already exist in the two test files; the builder only proves they still pass and that the trim changed nothing.
1. Happy path: a step typing `jane.doe@gmail.com` into an Email field, built through `build_judge_prompt` and captured by the recording mock: the prompt carries `<email>` and never the address (`tests/test_reconcile_pii.py`, the exact-prompt tests).
2. A phone such as `+91 98765 43210` (and grouped / dotted / STD forms) becomes `<phone>`.
3. A value typed under a person-name label (Full name, first_name, पिता का नाम) becomes `<name>`; a value under a non-person label (Course name, University name, Bank name) keeps its text.
4. PII in the candidate's title, route and controls and in nested strings is masked.
5. A prompt with no PII is byte-identical to before (RC11): `tests/test_reconcile.py` green and untouched.
6. Seeded secret still replaced or the call refused (RC12), unchanged `assert_no_raw_secrets` path.
7. ReDoS: 200 KB adversarial inputs finish in under `1.0 * timing_scale()` s (`test_mask_pii_is_linear_on_adversarial_input[*]`, 9 cases).
8. Structural: `uv run autotester doctor` exits 0 with `reconcile.py` at 300 lines; `git diff --stat master` shows no change to `stages/review.py`.
9. Ledger: `python -c` over `qa/issues.jsonl` shows every line parses, AT-780 is `open`, AT-830..AT-840 each appear once.
10. Falsification (checker, throwaway copy): delete the `video, other = mask_pii_obj(video), mask_pii_obj(other)` line in `build_judge_prompt`; the exact-prompt tests in `tests/test_reconcile_pii.py` must go red.

## 8. Gate answers

- `qa/gates/commit-before-verdict.md:60`: "Answered: 2026-09-26T22:34:22+05:30 — C — Umesh via AskUserQuestion in the checker session. Official rule: a unit is committed on its own branch (wave/<slug> worktree) before check, and reaches master only by merge after a checker PASS with a matching cycle. This ratifies the current practice."
- `qa/gates/plan-approved.md:13`: "Answered: 2026-09-27T08:43:48Z — plan APPROVED — same answer, same session; scope decisions recorded in docs/plan.md (max parallel; Track C through C3; T-154/T-155 held)"
- `qa/gates/t125-fullsuite-browser-egress.md:821` (governs where the owed full suite may run): "Answered: 2026-10-07 — option A (generalized): drop the native-egress sandbox precondition; local visible browser + full suite on any machine, against any product URL with its supplied credentials; test-suite guards kept (no real creds/.env, no paid calls, no external network in unit tests) — chat 2026-10-07, D-070"
- No gate file exists for AT-780 itself; Umesh's direction on masking is recorded in the AT-780 `resolution` field, not as a gate. Approval to run this unit: `qa/QUEUE.md:20` "approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)".

## 9. UI surface and persona walk

`Persona walk: skip (no UI surface: the diff touches only core/redact.py, stages/reconcile.py, tests/ and qa/ files; checkable with git diff --name-only master, which must list nothing under src/autotester/ui/ and no template or static file)`

## 10. Dependencies and conflicts

- `after: none` (`qa/QUEUE.md:27`).
- One owner per shared file: `stages/reconcile.py` is owned by this row (`QUEUE.md:28`); no other pending row lists `core/redact.py` or the two test files.
- Shared and append-only: `qa/issues.jsonl` (the landing order of `land-t203-hosting`, which "reuses issue ids AT-782..AT-793" per D-080, and other re-lands decides who renumbers; before merging, `grep -c '"AT-83[0-9]\|"AT-840' qa/issues.jsonl` on master must be 0, master's highest AT id today is AT-823). `docs/MAP.md` is regenerated by whichever unit lands last; this one regenerates and commits only a real diff.
- `wave/at780-pii` and `wave/at780-harden` are strict ancestors of `integrate/combined`; they land with it and are deleted by the owner or maker afterwards, not by the builder.
- `wave/at787-bundle-wiring` and `wave/t203-hosting` are other LAND branches; they touch none of this unit's files (see `qa/briefs/_branch-inventory.md`).

## 11. Budget and process rules

- Check budget: tier L, 45 minutes. Fix-cycle cap: not stated in `qa/adapter.json`; use the standard cap (`qa/QUEUE.md:336` calls 2 "the normal cap").
- Builder runs no full suite; scoped files in section 6 only.
- Falsification only in a throwaway copy under the session scratchpad, never in the worktree under check; anchor must match exactly once and the file must be shown changed (C7).
- Kill only PIDs you started. Never `taskkill /IM` or `Stop-Process -Name` (open issue AT-820: the at780-harden builder killed every `python.exe`/`uv.exe` on the host). Give every child process a timeout.
- Edit in place, no new module, no `*_v2`/`*_new` file. No push: the checker pushes on PASS (D-007).
- Use `git -C <dir>` and absolute paths; no `cd X && cmd`.
