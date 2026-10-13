# Verdict - t196-citation, checker B (blind, cycle 1)

Cycle checked: 1
Bound to: detached worktree at origin/wave/t196-citation = 3616517575b72098fb929fd8719e0fe196165b7a. Date 2026-10-12. Mode: ADVISORY per D-087 item 3. Tier L, second blind check.

VERDICT: PASS (with findings F1-F3; none blocks the advisory merge)

## Gate
- Full suite `uv run pytest -o addopts=`: 5632 passed, 5 failed, 7 skipped, 14 xfailed. All 5 failures are the known Windows symlink noise (test_discover symlink_escape, 2 in test_report_export, test_ui_crawls[symlink], test_ui_video_route_traversal). No citation, doctor, schema or ledger test failed.
- ruff check src tests: clean (a root-level `ruff check .` scans the nested .worktrees and is not meaningful).
- `uv run autotester doctor` on the branch: exit 0, "doctor: clean"; warnings only: coverage 2317, declaration 372, known-disputed 2 (K1, K2 listed, non-blocking).

## Temp-merge onto current origin/master (18626438)
Merge is conflict-free. Ruff clean. Citation tests + test_doctor: 145 passed, 1 failed: `test_the_real_tree_has_no_dangling_citation`. Cause: checker A's committed verdict `qa/verdicts/t196-citation.r1.a.md:11` cites a fictitious a fictitious decision id as a probe example, which L9 flags dangling. `autotester doctor` on the merge is therefore RED (1 blocking violation, exit 1). This is a defect of A's verdict text, not of the branch (L9 already existed on master; master itself is red from that line). Required before/at merge: reword that line without a literal fake id. My own verdict avoids literal fake ids for this reason.

## Criteria (as adjusted by D-087 item 3)
- Dangling blocks: probe prose a fictitious id in qa/manifests: blocking `decision-citation-dangling`; also with a canonical claim to a nonexistent id: blocking. Met.
- Wrong subject blocks, WHEN the occurrence has a review row: claim D-001 quoting D-002's What, claim quoting only Why, and reviewed-as-ordinary-reference: all blocking `subject-mismatch`. Correct claim: clean. Met, but see F1.
- Coverage / declaration are advisory: unreviewed citations, prose authorization without canonical claim: only warnings, exit 0. Met.
- Code block / blockquote: NOT excluded (brief has no exclusion); a fenced or quoted nonexistent id still blocks as dangling. Consistent with the brief ("examples never provide a whole-file exemption").
- File scope: covered = qa/gates/*.md, qa/contracts/*.md, qa/manifests/*.md, qa/verdicts/*.md, docs/*.md. Ignored (probed): qa/manifests/x.txt, qa/manifests/sub/n.md, docs/sub/q.md, qa/notes.md, README.md. Matches the five globs.
- Sealed record: unchanged unit clean and counted under `sealed`; appending a line to a sealed manifest drops the seal and every occurrence reverts to coverage violations (advisory). Changing the cited D-001 What after the seal does NOT invalidate the seal (correct per brief: seal hashes the unit, "covered, not classified clean"). A sealed unit containing a wrong claim and a dangling id still reports the dangling id as blocking (a seal covers only the coverage obligation). Met.
- Data migration / idempotency: the new modules (citations, seals, review_block, advisory) contain no write_text, write_bytes or open(); they only read. No migration or seal-writing code exists, so nothing can corrupt ledger rows or be non-idempotent. The migration of current claims and the real-tree inventory/seal rows are checker-owned and remain open (explains the 2317 + 372 advisory findings), as D-087 allows.
- Mutation (temp-merge tree, restored after): (a) force `_scan` to skip dangling -> 8 tests in test_citations fail (red for the right reason). (b) add `decision-citation-dangling` to NON_BLOCKING -> NO new test fails (see F2).
- K1/K2 listed known-disputed, non-blocking (doctor output shows 2).

## Findings
- F1 (substantive, advisory-mode gap): `_judge` skips any occurrence with no review row. An unreviewed canonical claim quoting the wrong entry produces only `decision-citation-coverage` (advisory) and NO subject-mismatch; probe: wrong claim unreviewed -> blocking = []. Wrong-subject blocking therefore applies only to rows already in the inventory. D-087 says wrong-subject "remain blocking if the unit already treats them so", and the unit does so only for reviewed rows, so this meets D-087 literally, but the AT-718 scenario (a fresh wrong claim) is not caught until coverage is reviewed. Recommend: judge canonical claims even without a review row, before any promotion decision, or state the limit in the manifest.
- F2 (test gap): `tests/test_citation_advisory.py::test_a_wrong_subject_or_dangling_citation_fails_doctor` parametrizes only subject-mismatch and subject-unavailable; the name claims "dangling" but no test pins that `decision-citation-dangling` blocks through `blocking()`/the CLI. Mutation (b) survives.
- F3 (advisory scope not pinned): `ADVISORY_CITATION == {coverage, declaration}` is pinned by no test (grep of tests: zero references to ADVISORY_CITATION or NON_BLOCKING). No criterion strictly requires a pin, but D-087's split is exactly this list, so a one-line equality test is cheap and recommended. Today the list is correct: dangling, subject-mismatch, subject-unavailable are not in it.

## Ruling: dual-check conflict
Brief line 12 ("Dual check: no", policy .9, needs a real security|auth|tenancy|prod-write trigger, none here) governs over L10's last paragraph, which was written under policy .3 and is stale. The checker-owned L10 line should be amended at close-out. This second blind check was run anyway at the orchestrator's request; it is harmless and not required for closure.
