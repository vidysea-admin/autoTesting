# Behavioral proof selection — cycle 1

Source/test candidate: `8d793363a2d0d3098ce4172eec8cf096036855c6`.
Production bytes remain the checked-INIT `b6722b61` bytes; two approved safety tests were added.
The prior INIT and its 20-mutation **draft** specification remain intact. The final specification
is produced by `probe-riskgroups.py` under `risk-proofs/`, with 13 behavioral mutation groups.
All 13 selected groups are now executed with attributable GREEN/RED/restored receipts; the
selection itself grants no PASS. `readiness.json` re-derives the maker's provenance chains before
dispatch to the fresh unit checker.

| Selected risk | Named defenders / distinct claim |
|---|---|
| source configuration frozen | stale/config |
| teaching input bytes frozen | stale/input |
| output ownership / no overwrite | existing, redirected, overlap; partial-write refuses reuse |
| source-project path containment | stale/source-escape |
| declared build identity required | stale/empty-build; positive receipt explicitly unverified |
| input containment / secret-file exclusion | escape, absolute, env; real resolved junction/symlink alias |
| owner input approval reference required | inputs/unapproved |
| explicit input-type allowlist | inputs/historical-json |
| rich input presence | inputs/no-doc |
| credential KEY existence and domain scope | unknown, duplicate, unscoped, foreign-domain, empty |
| allowed credential-free target URL | url-credentials |
| URL-only source isolation | positive end-to-end script test |
| historical project clone forbidden | positive end-to-end script test |

Each named rejection variant still gets its own attributable failed node ID. The output-ownership
mutation disables the equivalent output-ownership checks plus exclusive mkdir as one bounded-span
edit, and runs all four named defenders. It permits both new writes beneath the source project and
reuse/overwrite of an existing or partial output; no variant is dropped. The input-containment
mutation runs all four path/secret variants against the same canonical resolved-path guard.

Five redundant positive-test mutations from the draft are **not executed**: `same-target`,
`scoped-refs-only`, `provider-config`, `no-env-copy`, `input-provenance`. The shared 22-case GREEN
still directly asserts URL/build/config identity, exact selected scoped references, provider copy,
no `.env` in outputs, input-byte/provenance preservation and unchanged historical source bytes.
The positive test is independently discriminated by mode leakage and historical clone mutations;
the latter introduces historical config/truth/cases/runs/crawl/approval and `.env` contamination.
Dedicated scope and approved-input/path guards independently discriminate the credential and input
boundaries. This consolidates equivalent positive evidence; it does not waive those assertions.

Existing checked `acceptance-isolation` evidence proves the driver's polluted truth/case and mode
refusals, not this preparer's creation behavior. It is complementary context only and is not used
to waive a new preparer guard. No extra selection reviewer is dispatched; the fresh unit checker
must judge this mapping and can require narrower additional probes for a concrete uncovered risk.

The real alias test must create and resolve an actual temporary junction/symlink. Failure to create
one is an explicit environment gap, never a skip/PASS. Injected partial filesystem failure preserves
source bytes and leaves a visible incomplete destination with no success receipt; reusing it must
refuse without changing it. Automatic cleanup and atomic all-or-nothing publication are **not**
implemented or claimed. No cleanup redesign, browser/model/target contact or approval minting.
