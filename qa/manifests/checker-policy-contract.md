# Manifest - checker-policy-contract

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** D-100 proportional independent checker policy (checker-owned contract authoring)
**Branch:** codex/checker-policy-contract
**Base commit:** a8419a82
**Candidate:** immutable commit containing this manifest (resolve branch HEAD; do not review a dirty tree)
**Authorization:** Umesh explicitly requested system-wide checker efficiency; parent approved exact scoped amendments before edits.
**Risk tier:** docs/config structure only in this unit, with safety-policy semantics independently reviewed. No executable config/runtime application changes. Full integrated implementation review remains separate.

## Complete changed files
- docs/DECISIONS.md: D-100 appended only through scripts/append_decision.ps1; prior text unchanged.
- qa/loop.md: effective risk tiers, packet/environment preflight, evidence reuse, independent focused probes, mandatory integration gates and measured efficiency escalation.
- qa/adapter.json: enabled verify.unit_policy distinct from disabled/unconfigured legacy kernel quick lane; exact full commands, allowlist and parallel settings unchanged.
- qa/contracts/core-invariants.md: C7 proportional review and representative checker mutation rerun; maker every-guard/test mutation duty and baseline/application/named-failure proof retained. Append amendment log only elsewhere.
- qa/manifests/checker-policy-contract.md: this handoff.

## Evidence and criteria
- `powershell -NoProfile -File scripts/append_decision.ps1 -EntryFile .work/d100-entry.md -RepoRoot .` (equivalent absolute entry/root used from parent checkout): exit 0, APPENDED D-100.
- Python 3.12.10 stdlib JSON/diff structural checks: exit 0; qa/adapter.json valid; full commands/allowlist/parallel unchanged; enabled unit policy/absent legacy lane; original decisions text prefix intact; only C7+appended log changed; sabotage baseline/application/attribution clauses unchanged. Actual output and source SHA256 map: `.work/policy-validation.json` (local scratch; reviewer must regenerate checks from immutable Git blobs rather than trust paste).
- `git diff --check`: exit 0.
- First raw-byte git-blob/working-checkout decision-prefix probe failed because tracked LF differs from checkout CRLF; normalized text comparison passed. No prior decision prose changed; this limitation is explicit.
- No tests or executable guards added/rewritten; runtime sabotage is inapplicable. Independent reviewer should supply a discriminating policy-consistency probe (e.g. compare adapter full gates and unrelated C7 clauses against base, and reject a deliberately disabled integration gate in an in-memory copy).
- Full pytest/ruff/doctor not run: this doc/config-only unit does not change application behavior. Combined feature integration/release still must satisfy all three exact full gates.

## Binding and environment
- Base a8419a82 includes independent D-099 foundation verdict; inspect `git diff a8419a82..HEAD` for exact complete candidate diff.
- Windows 2025 Server build26100; Python3.12.10; no dependency/runtime/config changes.
- Global checker helper maintained separately by /root/checker_efficiency; this unit documents its preflight/reuse interface. Missing helper is explicit fallback to equivalent checks, not assumed PASS.
- Maker active seconds: unknown; maker tokens: unknown; maker cost: unknown. These are unavailable exact telemetry, never zero; checker ratio unverified, fixed bootstrap scope applies.
- This is not a PASS, deployment approval, integrated-suite result, or production verification. Fresh independent checker verdict required.
