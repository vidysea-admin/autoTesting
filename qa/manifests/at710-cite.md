# Manifest: at710-cite (docs-lane citation repair for AT-710 / AT-718 / AT-740)

Status: merged-no-check (docs-lane) -- pending maker read-through
Policy-Version: proportional-verification/2026-10-19.17
Base: 7424e6ec, branch wave/at710-cite. Authorized by Umesh 2026-10-22 ("fix kar do").

## Step 1 -- which entries really authorize ALLOW_WRITES

- **D-053 (docs/DECISIONS.md:1360) authorizes it.** Deciding sentence (What, :1362): "`ALLOW_WRITES` is the authorized
  write-policy CEILING on every target including production (Umesh, `qa/gates/write-policy-tier.md`, commit 88ab7638)."
  It adds that no project is flipped by the entry itself.
- **D-018 (:238) does NOT itself contain the write-policy authority.** Its text covers RunApproval consent gates, the
  T-145 done_check and the adapter allowlist. D-053 (:1371) attributes the phrase "ALLOW_WRITES is Umesh's switch" to
  D-018, but that phrase is actually in **D-016 (:226)**: "ALLOW_WRITES is Umesh's switch". D-018 therefore stays only
  as the pre-existing "see also" link in pathlynks-user-account-first.md; it was not newly cited as authority.
- D-068 (:2021) is related (provisioned credentials are the run approval) but not a write-tier authority; not added.
- D-056 (:1569) = at673 round-cap waiver; D-057 (:1621) = Umesh's three answers (AT-710 new module, CT6 order-only,
  T-167 deps). Neither mentions write policy. D-058 (:1667) supersedes D-057 and carries the AT-740 note.
- Decision: D-053 is the correct entry, so the task is not BLOCKED.

## Step 2 -- hits for `git grep -E "D-05[67]"`

State found: the seven citations had already been re-pointed to the placeholder
`WP-DECISION (NOT YET WRITTEN; number assigned when written ...)` (AT-740 note in D-058), so the live write-policy
authority citations were the WP-DECISION placeholders in two gate files. No gate file still cites D-056/D-057 as
write-policy authority. All other hits:

| Files | Hits | Class | Reason |
|---|---|---|---|
| qa/gates/at654-d029-dev-only-vs-production-pathlynks.md :16, :26, :71 | 3 placeholder cites | (a) FIX | placeholder stood in for the write-policy authority; replaced by D-053 |
| qa/gates/pathlynks-user-account-first.md :39, :43, :46, :75 | 4 placeholder cites | (a) FIX | same; replaced by D-053 |
| same two files, CITATION CORRECTED banner (:4-8) | 2 (D-056, D-057) | (c) historical | AT-718/AT-740 incident narrative, states the ids were spent elsewhere; correct as history |
| qa/gates/write-policy-tier.md :103-111 | 4 | (c) historical | AT-718 note recording the wrong citation and the placeholder; left untouched |
| qa/gates/at673-cycle2-scope.md, qa/manifests/at673-sessionstart-unclosed-detector.md | 3 + 7 | (b) | cite the real D-056 round-cap waiver |
| qa/gates/new-module-authorization.md, t125-ct6-..., t168-new-modules.md, qa/contracts/catalog.md, qa/briefs/*, qa/manifests/at710-decision-citation-resolver.md | ~30 | (b) | cite the real D-057 (new module / CT6 / three answers) |
| qa/contracts/living-ledger.md (18), qa/QUEUE.md (6), qa/triage/*, qa/briefs/t196-*, qa/.last-tick, qa/.last-sweep, qa/evidence/** | many | (c) | checker-owned contract / dated queue snapshots / logs describing the incident; out of editable scope or historical |
| qa/feedback-inbox.md (202) | 202 | (c) | verbatim feedback log, not edited |
| docs/DECISIONS.md, qa/verdicts/**, qa/issues.jsonl | many | never-edit | immutable |
| src/autotester/ledger/citations.py, tests/test_citations.py, tests/test_mc_sessionstart_unclosed.py, qa/hooks/mc-sessionstart.ps1 | 1 + 11 + 1 + 1 | never-edit (.py/.ps1) | oracle fixtures / code |

## Step 3 -- replacements made (7 occurrences, 2 files)

- at654 :16 `(D-053, WP-DECISION ...)` -> `(D-053)`
- at654 :26 table cell `..., WP-DECISION ...` -> `..., D-053`
- at654 :71 Links: removed the placeholder (D-053 already listed)
- user-account-first :39 `(WP-DECISION ...)` -> `(D-053)`
- user-account-first :43 `WP-DECISION ... authorizes` -> `D-053 authorizes`
- user-account-first :46 `report WP-DECISION ... refuses` -> `report D-053 refuses`
- user-account-first :75 Links: removed the placeholder (D-053 and D-018 already listed)

## Residual items for the maker (not changed, outside the brief)

- The CITATION CORRECTED banners and the write-policy-tier.md note still say the write-policy entry "is to be written"
  / is "a forward reference". D-053 now stands as that entry, so those sentences are stale narrative. Not edited
  (historical record, brief says add nothing else); flag for a follow-up wording pass if wanted.
- pathlynks-user-account-first.md:43 still says project.json is `read_only`; projects/pathlynks/project.json is now
  `allow_writes`. Unrelated to citations; untouched.
- D-053 (:1371) misattributes "Umesh's switch" to D-018 (it is D-016). Immutable log; only a new entry could correct it.
- AT-710/AT-718/AT-740 rows in qa/issues.jsonl are checker-owned; closing them is not done here.
