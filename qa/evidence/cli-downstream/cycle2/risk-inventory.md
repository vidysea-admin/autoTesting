# Approved minimal risk inventory

Parent approved the 15-to-11 selection on 2026-10-15. The ledger and bound command receipts
record which selected mutations actually ran and their red/restored outcomes.
Final source is 030560cf033782f50fb54c5c034b4f0fb3e0bb93; shared 21-node GREEN is sealed
in shared-green.json and its raw log. This is maker evidence, not an independent verdict.
The numbers below identify the original 15-entry draft, not execution counts.

| Keep | Independent behavioral risk | Why a separate probe matters |
|---|---|---|
| 1 | Replacing exact MODEL input with canonical truth | Different source content can generate different cases despite a valid review status. |
| 3 | Canonical result consumers lose pre-grade observations | store.load_results must serve actual execution before any grading call; the checkpoint copy alone does not satisfy that filestore API. |
| 4 | A browser is constructed before approval | Constructor/session/target side effects must remain zero on refusal. |
| 5 | Concurrent canonical edits change actions | Only frozen case steps may reach the target in this run. |
| 7 | Browser interruption repeats possible writes | Target-side uncertainty cannot be repaired by resetting a same-run budget. |
| 8 | Mutated frozen input silently changes lineage | A persisted snapshot is validated by exact content, separately from ordinary canonical edits. |
| 10 | MODEL launders an existing human block | Captured pre-MODEL authority must survive a changed current review object. |
| 11 | GRADE interruption repeats model spend | Browser checkpoint reuse alone does not prevent another judgment call. |
| 12 | EXPAND interruption repeats model spend | Generation precedes an output artifact and needs its own admission boundary. |
| 14 | One unsafe generated Case contaminates storage | Validate the entire generated set before storing even its first safe member. |
| 15 | Unsafe RawResult is stored before batch validation | The execution result has an independent write site, so the case-set guard cannot protect it. |

Reuse final bound GREEN and source/consumer evidence instead of extra mutations:

- Draft2: current canonical NEEDS_EDIT has a direct refusal/zero-generator-spend test;
  draft10 is the representative extended human-authority mutation.
- Draft6: the frozen snapshot test verifies both executed URL and actual HTML metadata;
  existing HTML/XLSX consumers retain backward compatibility. Draft5 represents the more
  consequential action-lineage mutation without claiming a report mutation was run.
- Draft9: the profile wipe implementation is unchanged and merely extracted. The new test
  observes an actual stale marker removed in the isolated profile while the normal marker
  survives; the existing UI profile test runs unchanged. No mutation of this old helper needed.
- Draft13: refusal before model admission then successful retry is directly exercised;
  source confirms the callback follows existing review/prompt/secret gates. Draft12 represents
  the uncertain-spend risk. No extra syntactic callback-reordering mutant claimed.

This reduces the proposed mutation count from 15 to 11 without omitting any final GREEN
test. It does not claim full artifact privacy, full physical accounting, or a completed CLI hook.
