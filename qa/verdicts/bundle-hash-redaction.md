# Verdict - bundle-hash-redaction

**Verdict:** PASS
**Cycle checked:** 0
**Checked commit:** 111fd23e (base e74664f8), branch fix/bundle-hash-redaction
**Checker:** fresh /checker, did not write the code. Diff read in full: `git diff e74664f8..111fd23e` (3 files, +152/-1).

## Criteria
1. **Short secret inside a computed sha256 no longer breaks the bundle. PASS.**
   `src/autotester/stages/failure_bundle.py:87-103` `_dump_manifest` blanks well-formed digests, scrubs/gates the rest via `_dump`, restores digests; call site `:221`. Test `test_short_secret_inside_a_computed_hash_does_not_break_the_bundle` asserts `load_bundle` returns, every screenshot sha equals the real hash, and no `[REDACTED]` in manifest.json.
   Revert test: `git checkout e74664f8 -- src/autotester/stages/failure_bundle.py` then `uv run pytest tests/test_failure_bundle_hash_redaction.py -o addopts=` gave `1 failed, 2 passed` (the criterion-1 test red); fix restored (`git status` clean).
2. **Free-text fields still scrubbed and gated. PASS.** `test_free_text_manifest_field_is_still_masked` (secret in `run_id` becomes `[REDACTED]:APP_PASSWORD`, absent from the file, bundle loads) passes. Own probe: secret in `files[].name` and `run_id` masked; a 64-hex secret placed in `run_id` masked while the real digest is kept.
3. **Tampered sha256 still refused. PASS.** `load_bundle` check unchanged (`failure_bundle.py:249`, `_sha256(target) != f.sha256`); `test_a_tampered_hash_is_still_refused` passes.
4. **Only well-formed 64-hex exempt. PASS.** `_SHA256_RE = [0-9a-f]{64}` with `fullmatch` (`:84`, `:98`). Own probes: a malformed value containing a secret (short/odd length) is masked; uppercase 64-hex-style value containing a secret is masked.
5. **Other parts unchanged. PASS.** `_dump` untouched in the diff (only `import re`, the new regex/function, one call-site change). Probe: `_dump_manifest` output is byte-identical to `_dump` when no digest is well-formed, and when digests exist but no secret overlaps.

## Adversarial
- Can a secret be smuggled through the exempt field? The only producer of `BundleFile.sha256` is `_sha256(dest)` at `failure_bundle.py:163-164` (`hashlib.sha256(bytes).hexdigest()`); no caller-supplied text reaches it. A secret could survive there only if it equalled the SHA-256 of a bundle file, which is not attacker-reachable. Probe A confirmed that a manifest hand-built with digest == a 64-hex secret keeps it (by design; unreachable through `build_failure_bundle`). Non-blocking note: the restored digests are not re-gated by `assert_clean`; acceptable for the reason above.
- Residual from the manifest (bundle_id like `fb_<hex>` could still be altered by a very short secret; `load_bundle` does not compare it to the directory name) is accurate and out of scope; not blocking.

## Commands run (worktree D:/autoTesting/.claude/worktrees/bundle-hash, one pytest at a time, `-o addopts=`)
- Targeted + every test importing failure_bundle (`test_failure_bundle_hash_redaction`, `test_run_failure_artifacts`, `test_goal_contract_registration`, `test_failure_bundle_escape`, `test_failure_bundle`, `test_failing_step_bundle`, `test_at1384_mask_limit_wiring`): `53 passed`.
- Importers via report_export (`test_report_export`, `_reason`, `_secrets`, `test_video_report_export`): `31 passed`.
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: 1 violation, `decision-citation-dangling: qa/verdicts/6c-1028-signup.md:4 cites D-110` (expected: D-110/D-111 live only in the main checkout's uncommitted DECISIONS.md). Nothing from failure_bundle.py (300-line / 50-line / duplicate rules clean).
- Full `uv run pytest` not run (machine low on memory, per instruction); change is confined to one stage file whose importers were covered above.

## Non-blocking
None requiring a fix cycle.
