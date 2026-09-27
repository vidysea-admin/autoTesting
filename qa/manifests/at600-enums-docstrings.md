# Manifest — at600-enums-docstrings

**Unit:** AT-600 — t182 reflowed 3 unrelated docstrings in `schema/enums.py` to stay under the
300-line cap and lost content: `Outcome.ASSERTION_FAILED` dropped "the grader still owns the
verdict" (a C7 statement) and `IssueKind.EVIDENCE` dropped "for third-party noise".
**Contract:** `docs/ARCHITECTURE.md` (schema rules: closed vocabularies live in `schema/enums.py`)
· `qa/contracts/core-invariants.md`
**Goal task:** none (issue-driven)
**Executor:** claude-sonnet-subagent
**Date:** 2026-09-26
**Fix cycle:** 1 of max 3
**Persona walk:** skip (docstring restore/refactor, no product behavior change)
**Issues addressed:** AT-600 (low)

## What changed

- Found the t182 merge commit (`b7506f0` — "fix(execute): enact VIEWPORT_MOBILE/LOCALE_I18N or
  report not-run (AT-581, D-045 E6)") and diffed `src/autotester/schema/enums.py` against its
  parent `7913387` to recover the exact pre-reflow wording of all three docstrings
  (`Outcome.ASSERTION_FAILED`, `IssueKind.OVERLAY`, `IssueKind.EVIDENCE`).
- `src/autotester/schema/enums.py:118-120` — `Outcome.ASSERTION_FAILED`'s docstring restored to
  its pre-t182 wording verbatim (3 lines, "An OBSERVATION, not a grade — the grader still owns
  the verdict.").
- `src/autotester/schema/issue_kind.py` (new) — `IssueKind` moved here in full, both docstrings
  (`OVERLAY`, `EVIDENCE`) restored to their pre-t182 wording verbatim. This is the split that
  keeps `enums.py` under the 300-line cap after the docstring restoration, per the issue's
  suggestion ("Split enums.py (e.g. IssueKind into its own module)").
- `src/autotester/schema/enums.py:7` — `from autotester.schema.issue_kind import IssueKind  #
  noqa: F401 -- re-exported (AT-600)` added so `enums.py` stays the single public import surface:
  every existing `from autotester.schema.enums import IssueKind` (11 call sites across
  `schema/crawl.py`, `stages/crawl_report.py`, `stages/explore_node.py`,
  `stages/explore_typing.py`, `stages/portal_persona.py`, `ui/routes_crawls.py`, and 5 test
  files) still resolves unchanged. `IssueKind` is now defined in exactly one place
  (`schema/issue_kind.py`) — no duplicate definition.
- `docs/MAP.md` — regenerated via `uv run autotester map` (doctor's `stale-generated` check
  required it) to add the new module row and the `IssueKind` entry now pointing at
  `schema/issue_kind.py`.
- No other docstring in the file was touched or reflowed.
- `enums.py` line count: 300 → 285 (well under the cap, even after the ASSERTION_FAILED
  restoration added 1 line and the new re-export import added 2 lines).

## Verbatim-restore proof (diff against the pre-t182 commit 7913387)

```
$ git diff 7913387 -- src/autotester/schema/enums.py
@@ -4,6 +4,8 @@ from __future__ import annotations

 from enum import StrEnum

+from autotester.schema.issue_kind import IssueKind  # noqa: F401 -- re-exported (AT-600)
+

 class SourceKind(StrEnum):
     VIDEO = "video"
@@ -120,6 +122,9 @@ class Outcome(StrEnum):
     step's expected state) deterministically did not hold at settle time.
     An OBSERVATION, not a grade — the grader still owns the verdict."""

+    NOT_RUN = "not_run"
+    """D-045/AT-581/E6: condition not enacted; case did not run -- must never be judged PASS."""
+

 class Result(StrEnum):
     """The grader's verdict. Only the grader writes this."""
@@ -264,26 +269,6 @@ class EdgeOutcome(StrEnum):
     ERRORED = "errored"


-class IssueKind(StrEnum):
-    """What kind of problem a crawl-detected `CrawlIssue` is."""
-
-    CONSOLE = "console"
-    NETWORK = "network"
-    NAVIGATION = "navigation"
-    DIALOG = "dialog"
-    OVERLAY = "overlay"
-    """A screen whose controls were covered by an in-page overlay (AT-227).
-    A PRODUCT observation, not a tool failure: the screen really was
-    uninteractable in the state the crawl met it, and saying so is the
-    difference between a blocked crawl and a crawl that looks complete."""
-
-    EVIDENCE = "evidence"
-    """The crawler itself failed to record something (AT-114). Kept distinct
-    from the four kinds above because those describe the PRODUCT under test and
-    this describes the tool: filing a tool failure as a product bug is exactly
-    the dishonesty X9 forbids for third-party noise."""
-
-
 class CrawlStatus(StrEnum):
     RUNNING = "running"
     COMPLETED = "completed"
```

Every remaining hunk is either the legitimate `NOT_RUN` addition from the later, unrelated
`b7506f0` commit (untouched by this fix) or the `IssueKind` class body moving out wholesale —
its docstring text is byte-for-byte identical, not reflowed again. Confirmed programmatically:

```
$ python3 - <<'EOF'
pre = open('enums_pre_t182.tmp', encoding='utf-8').read()          # git show 7913387:...enums.py
i = pre.index('class IssueKind'); j = pre.index('class CrawlStatus')
pre_block = pre[i:j].rstrip()
cur = open('src/autotester/schema/issue_kind.py', encoding='utf-8').read()
cur_block = cur[cur.index('class IssueKind'):].rstrip()
print("MATCH" if pre_block == cur_block else "DIFF")
EOF
MATCH
```

The same byte-for-byte check was run for the `ASSERTION_FAILED` block (pre-t182 slice vs. the
restored slice in the live `enums.py`) — `MATCH`.

## How to verify (commands + expected)

- `uv run pytest <every test importing schema.enums, plus tests/test_schema*>` (117 files,
  grepped via `grep -rln "schema\.enums\|schema import enums\|import enums" tests`) → all pass
- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → `doctor: clean`

## Actual outputs (from maker's own run)

```
$ uv run pytest <117 files importing schema.enums / test_schema*>
1130 passed, 4 skipped, 15 warnings in 561.18s (0:09:21)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
root-clutter: test_list.txt -- scratch and evidence belong in .work/, not the repo root
stale-generated: docs/MAP.md -- generated sections differ; run `autotester map`
2 violation(s)
```
(`test_list.txt` was a throwaway scratch file used to build the pytest command line and was
deleted before commit — not part of the diff. `docs/MAP.md` was regenerated with `autotester
map` per the instruction; re-running doctor afterward:)

```
$ uv run autotester doctor
doctor: clean
```

The 4 skips are pre-existing (unrelated to this change — none of the skipped tests touch
`schema/enums.py` or `schema/issue_kind.py`).

## Capability coverage (each claim -> its isolating falsification)

| capability | check | falsifying edit | expected result if broken |
|---|---|---|---|
| `IssueKind` still importable from `schema.enums` after the split (re-export intact) | any of the 11 call sites' import lines, e.g. `tests/test_store_crawl.py::test_...` | delete the `from autotester.schema.issue_kind import IssueKind` re-export line in `enums.py` | every one of those imports raises `ImportError: cannot import name 'IssueKind' from 'autotester.schema.enums'` — collection-time failure across ~8 modules and 5+ test files, not a silent pass |
| `IssueKind` is defined in exactly one place (no duplicate definition after the split) | manual grep: `grep -rn "^class IssueKind" src/` | (not edited — verified by inspection) | grep returns exactly one hit (`schema/issue_kind.py`); a second `class IssueKind` anywhere would be the "one concept, two places" bug this split exists to avoid |
| the restored `ASSERTION_FAILED` docstring is the exact pre-t182 text, not a paraphrase | byte-for-byte diff of the pre-t182 slice vs. the live slice (script above) | any character change to the docstring | script prints `DIFF` instead of `MATCH` |
| the restored `IssueKind.OVERLAY`/`EVIDENCE` docstrings are the exact pre-t182 text | byte-for-byte diff of the pre-t182 `class IssueKind` block vs. `issue_kind.py`'s block | any character change | script prints `DIFF` instead of `MATCH` |
| `enums.py` stays under the 300-line cap | `uv run autotester doctor` (file-length rule) | revert the `IssueKind` split while keeping the docstring restorations | doctor reports a `file-too-long` (or equivalent) violation on `schema/enums.py` |

I did not additionally sabotage-and-revert the running test suite for this unit (a pure
docstring/import-surface change, no branching logic to falsify) — the import-resolution and
duplicate-definition risks above are the only two behaviors this refactor could plausibly break,
and both are covered by the table above plus the actual full-suite pytest run (1130 passed).

## Known limits (disclosed, not claimed)

- The `# noqa: F401` on the re-export import is necessary because `ruff` would otherwise flag
  `IssueKind` as an unused import in `enums.py` — it is intentionally unused there; its only job
  is to be re-exported. `ruff check` passed clean with the noqa in place.
- No other docstring in `enums.py` (or anywhere else) was inspected for similar t182-era reflow
  damage beyond the two clauses AT-600 names; if other issues exist they are out of this unit's
  scope.

## Live browser: not UI-touching

This unit is a pure schema/docstring/module-layout change with zero behavioral or UI surface —
no page, route, or rendered output reads `IssueKind`'s or `Outcome.ASSERTION_FAILED`'s docstring
text or module location. No live browser evidence applies.

## Status: checked-PASS (cycle 1, qa/verdicts/at600-enums-docstrings.md 3228a6b)
