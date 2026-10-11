# Verdict — t155-ai-report

Date: 2026-10-11 · Cycle checked: 0 · Checked sha: a4308b35 (product b1ac3e40, base 9c9a91f3) · single coordinator
Policy-Version: proportional-verification/2026-10-10.9 · Bound to D:/autoTesting, worktree `.worktrees/t155-ai-report`

## Plan
Tier M held (new shared report stage + one-hunk helper move). No UI surface, no live portal, no data artifact. Checks: re-run
the affected tests (builder pre-check lines are under 30 s, so not reused), ruff, doctor, step 4c diff read in full, one
falsification per criterion in throwaway copies, an adversarial probe of every text field that reaches a cell. Quick lane: off
(`lane.enabled` not set), `lane=normal`. Dual-check trigger scan of the diff: `core/redact.py` and `schema/` are untouched,
so `Dual check: no` is right.

VERDICT: PASS
SCOREBOARD: 6/6 criteria met (AI9-AI14), 3/3 touched invariants hold (C3 one place, C5 secrets, C7 presents-not-judges)
TIER: M (multi-file behaviour: new shared report stage `stages/ai_report.py`, helper moved into `core/excel.py:16-21`; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 7/7 reproduced (AI9-AI14 plus the AI14 autosize row), each green before and red after on an assertion in its own copy (`qa/evidence/t155-ai-report/falsification.md`)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages, src/autotester/core, tests, docs/MAP.md; no UI surface)
ISSUES-WRITTEN: AT-925, AT-926, AT-927
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## What I ran
- `uv run pytest -p no:xdist tests/test_ai_report.py tests/test_crawl_report.py` -> 29 passed. `uv run ruff check src tests scripts` -> clean. `uv run autotester doctor` -> clean.
- Step 4c: 6 files, nothing removed that a criterion did not ask for. `clean_cell` moved with the identical regex `[\x00-\x08\x0b\x0c\x0e-\x1f]`; `grep _ILLEGAL|def clean_cell` over `src/` finds one copy (`core/excel.py:16,19`), `crawl_report.py` imports it as `_clean`.
- Probe (`ai_report.py:203-219`): a synthetic secret planted in verdict criterion_id/reason/fix_hint/note/grader_provider, capture endpoint, refusal target+reason, run endpoint+approval id. Plain, with newline+tab+non-ASCII+RTL mark, and 40,000 chars: the secret is in no cell (0 hits in 24 builds); the long string is cut to 32,767 by the library. A secret split by a control character (`sk-live-1234\x01567890...`) is rejoined by `clean_cell`, caught by `assert_clean`, and the whole report is WITHHELD (fail closed, nothing written). A cell starting `=` (`=cmd|' /C calc'!A0`) is written as a live formula cell (`data_type == 'f'`) in 8 fields; `+...` and `@...` stay text. See AT-925.

## Rulings (the six asked)
1. `Dual check: no` is right. The diff only calls `Redactor.scrub` and `assert_clean`; `core/redact.py` and `schema/` are unchanged. No `dual-trigger` line is needed. No tier raise.
2. `clean_cell` move: behaviour identical (same regex, same non-string passthrough), one concept in one place, `test_crawl_report.py` 6 passed.
3. Behaviour: blocked reads BLOCKED with the reason value and `unblock_action` (`BlockedReason` has no other human text, so the action is the human part); empty tiers show 0; failure strings are verbatim (newline and double space survive; only control characters 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f are stripped, which AI11 does not forbid); two refusal lines give two rows and no probe text; `grep Verdict\(` on the stage returns nothing; the tests patch socket and `Provider.judge` to raise. Probe output above.
4. Real use vs fixtures (criterion text quoted):
   - AI9 "reads one project's stored Track C evidence ... every tier has a section and shows its runnable count, including 0 ... no stored AI results produces a workbook whose summary says so": MET for real use on the tier sections, the zero counts and the no-results statement (today's real state). The populated static/behavioural rows are fixtures only: nothing writes `ai/behavioural/<id>/capture.json` or `verdict.json`.
   - AI10 "renders status BLOCKED, the reason text and its unblock_action": MET for real use; `ai_catalog.match` already produces the entries. The caller must pass them (no CLI/UI caller exists; contract open choice 2 allows that).
   - AI11 "Each judged row shows, verbatim ... every Failure.criterion_id, reason and fix_hint ... Verdict.note ... grader_provider": FIXTURES ONLY. A judged row needs a stored `verdict.json` and no unit writes one (T-153's judge returns in memory), so a real project has no judged row. AT-927.
   - AI12 "constructs no Verdict, calls no model provider, opens no network connection": MET for real use.
   - AI13 "each line of refusals.jsonl appears as a row ... missing or empty log shows 'no refused attempts recorded'": MET for real use. `stages/adversarial.py:121` appends `ProbeRefusal` lines to that path and `:191` writes `run.json`, both the shapes the reader parses. Stored runs read NOT JUDGED (no adversarial judge exists), which is honest.
   - AI14 "Every cell passes Redactor.scrub ... autosize_columns ... shared helper": MET for real use.
5. `mutant-cap-raise`: not needed as written. The floor is 1 falsification per criterion (6); the cap of 3 applies to mutants beyond it, so the builder's 10 is 1 over the cap of 9, and the line lacks the required `file:line`. Both are process wording, no FAIL. I ran the floor (6) plus the AI14 autosize row (7 copies), no extra mutants.
6. New module `stages/ai_report.py` (234 lines, under the 300 cap): reason sound (`report_export.py` is at 300/300, AI12 names `stages/ai_report*.py`, and it is a distinct concept from the crawl report). `qa/gates/new-module-authorization.md` is answered for AT-710 only and says per-case; its scope note leaves AT-697-type cases to a new answer. Owner acknowledgement is missing: a finding for the owner, not a FAIL ground.
D-014 round cap, seam "stored-evidence layout and workbook shape of stages/ai_report.py": this is PASS 1 of 2 (non-security seam; no earlier verdict names ai_report).

EXPLANATION: All six criteria hold on real behaviour and on the falsifications. The caveats are about use, not correctness: nothing yet writes the behavioural inputs, so AI9/AI11 populated rows exist only in fixtures, and cells beginning `=` become formulas (shared exporter pattern, not a criterion). slow: falsification copies and secret probe, about 5 min of 9.
Metrics: start=2026-10-11T00:27Z end=2026-10-11T00:36Z wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=540 mutants=0 defects_unit=0 defects_6c=0
