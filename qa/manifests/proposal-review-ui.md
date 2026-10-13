# Manifest — proposal-review-ui

**Contract:** qa/contracts/failure-bundle.md (FB5 — human pruning of proposed cases before any
provider spend); qa/contracts/auth.md (AU14 central policy table)
**Goal task:** none assigned (gap reported by the T-169 maker: no UI route to review proposals)
**Status:** ready-for-check
**Fix cycle:** 1

## Why this unit

Proposals could only be approved through the CLI (`autotester expand --approve/--prune`), so the
"no CLI" acceptance path had to approve through a code seam.

## What changed

- `src/autotester/ui/routes_proposals.py` (new) — `GET /projects/{slug}/proposals` (list: kind,
  title, flow + entry screen, why proposed, status/reviewer), `POST .../proposals/stage`,
  `POST .../proposals/review` (single via per-row button, bulk via ticked rows; approve or prune;
  signed by a required name). Both POSTs call `stages.expand.stage_and_review`, the function the
  CLI calls; the page reads `ProjectStore.list_case_proposals`. A bulk request with any absent or
  stale id is refused (404) before anything is written. Pruning HAPPY keeps it pending (schema rule).
- `src/autotester/auth/policy.py` — three rows: GET `/proposals` = `project.view`;
  POST `/proposals/stage` and `/proposals/review` = `project.edit` (same key as the FlowSpec
  approve gate; no new permission key proposed).
- `src/autotester/ui/routers.py` — registers the router.
- `tests/test_ui_auth_policy_table.py` — additive rows. `tests/test_proposal_review_ui.py` (new).

## Not done, on purpose

Title/steps editing: the CLI has none (proposals are content-addressed; a changed title is a new
proposal needing fresh review), so the UI has none either.

## Verification

See the commit's test run: new tests, `test_ui_auth_policy_table.py`, `test_routers_list.py`,
ruff on touched files, `autotester doctor`. One local browser smoke walk was not run.
