# Manifest - crawl-to-flows (AT-887 residual, AT-109)

Status: ready-for-check
Fix cycle: 0
Issues: AT-887, AT-109
Base: origin/master 441224ed, branch wave/crawl-to-flows

## Finding
The core AT-887 fix (crawl paths become DRAFT Flow proposals via `merge_screens_and_flows`, all three doors wired) is already on master (at887-crawl-to-flows, checked-PASS, merged 4f806daa). This unit adds the two residuals the issues still name.

## Changes
- explore_merge.py (265 lines): `not_seen_again` names structural screens an earlier crawl found that this crawl did not reach, in the review note (AT-109). Nothing stored, no Screen rewritten (X13), no Conflict; the DRAFT gate is unchanged.
- expand.py (250 lines): `unreachable_first_targets` + a logged warning in `expand()` when a non-crawl flow's first click names a control no crawled screen shows (AT-887 pre-run warning). A warning, never a gate; review gate untouched.
- tests/test_crawl_to_flows.py: 73-screen crawl -> 72 flows, DRAFT; after approve and proposals, expand yields one case per flow; redesign named in note and nothing rewritten; full re-crawl has nothing stale; unreachable first click warned; no crawl screens -> no warning.

## Verification (per file, -p no:xdist -o addopts=)
test_crawl_to_flows 5 passed; test_explore_merge 16 passed; test_expand 15 passed; test_expand_cli 10 passed; test_expand_redaction 23 passed; test_explore_flows 21 and test_explore_flows_doors 10 passed. ruff clean, autotester doctor clean. No full suite.
