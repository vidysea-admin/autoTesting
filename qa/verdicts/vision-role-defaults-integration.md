# Independent integration verdict: vision-role-defaults-integration

Verdict: PASS
Status: PASS
Cycle checked: 1
Reviewed SHA: 3c9c3d1f6210b657c5bf70c71dc36f24f241c59a
Base SHA: fbadaf25426059ecd5c7ee753cc662461071e244
Reviewed tree: 0a6ba95e2f59db9c423499e179bb8cbdef7fb72a
Root: C:/Users/product/Desktop/autoTesting
Manifest: qa/manifests/vision-role-defaults-integration.md
Packet SHA256: 34c7795285f53593738b49433b3e8ae2edab3bed7acb40238adb76858ec4e6f3

The independent checker passes this combined integration only. The accepted visual-role/default/migration unit and checked deadline dependency are integrated onto the existing main without reverting account-generation security. The pending-account POST/profile restriction follows TA2; GET remains session-readable. Compatibility repairs update test collaborator targets and fixture preconditions while preserving the intended assertions. Other three backlog items remain outside this verdict.

## Required combined gates — independently authenticated

All commands ran in the clean candidate checkout .work/wt-vision-integration, using retained root .venv CPython3.11.16 and candidate/src import containment. Preflight validated declared installed dependencies and writable temporary parent. PYTEST_ADDOPTS was absent; child-only environment setup avoided dependency synchronization. The actual module/console entrypoint invocations preserve repository configuration and mandatory command scope.

- Full configured pytest: python -m pytest --maxfail=1 with output/temp options only; exit0, no timeout. Actual JUnit contains7544cases:7518passed,12ordinary skips,14expected failures, zero failures/errors. Complete stdout reports80warnings and3585.82s. Actual command wall3601.437s. The successful run completed the entire configured tests surface; no prefix/tail stitching is used as a passing gate.
- Full Ruff: python -m ruff check src tests scripts; exit0,0.250s.
- Doctor: actual autotester.main console entrypoint with doctor argument; exit0,30.281s, final doctor: clean. The diagnostic30second faulthandler dump is retained on stderr; it did not terminate the successful command. Existing citation advisories are not hidden or claimed repaired.

Every stdout/stderr SHA256, immutable candidate/tree identity, clean before/after status, cwd, interpreter, lock/config/conftest hashes and environment fingerprint was independently checked. JUnit counters were parsed directly. All10original working-file hashes remain identical. Evidence: qa/evidence/vision-role-defaults-integration/gates/ and review/finalization/gate-verification.json; archive-index.json records raw artifact hashes and original paths.

## Independent review and bounded evidence reuse

C1-C3/C5/C7/C9/C12 and D-100: prior static review independently established exact23accepted source/test/script blob equality, six-file deadline dependency closure, account-generation preservation and changed-path scope. Subsequent exact-candidate checkpoints rechecked each incremental blob/path and immediate consumer; retained architecture, schema and effective contract clauses governed review. No integration source adaptation was hidden.

The checker independently exercised the actual authorization middleware: pending GET allowed, pending POST403, placed-member POST allowed and anonymous POST401. Changing actual POST/profile policy to SESSION in memory caused the named pending-write assertion to fail; restoring MEMBER passed. No production bytes changed. The full configured suite and retained application tests cover complete request handling; the direct probe is not falsely represented as an end-to-end browser run.

Changed privacy tests require a distinct sanitized image, masking pixels, retained geometry, cleanup and truthful INCONCLUSIVE output. Account-destruction refusals and ordinary destructive-control ordering remain asserted. Deadline tests catch accepted scope-finalization behavior while preserving physical failed-attempt assertions. Profile generation/forged-identity protections remain intact. The final cleanup fixture edits preserve every test-function AST and assertion while targeting actual collaborators; retained PermissionError, directory-left-behind and healthy controls still exercise real fail-closed cleanup. Exact26affected cases passed and output/XML bindings were authenticated.

The rewritten video-retention test has a complete bound proof: named baseline passed, exactly one required source anchor was changed, the named test failed at a PASS video must be pruned, and original bytes were restored. The checker independently reconstructed the mutant hash, parsed attributed red/green XML, and verified all1054source/test/script/config inventory hashes and Git blobs. Later changes touch unrelated fixtures; production, video test, immediate consumers and dependency blobs are unchanged. No redundant browser mutation was run. Actual launched browser executable/version was not independently captured and remains UNKNOWN; package/registry bindings are retained. This bounded proof does not replace final-candidate full-suite browser execution.

Original unit cycle2 PASS and historical mutation proofs retain original identities; they are reused only for unchanged accepted guards. Failed earlier full suites, setup attempts, timeout and harness errors remain failed/incomplete records. No failed command is relabeled PASS. The authoritative successful full gate above supplies final combined certification.

## Accounting and limits

Actual native total tokens, active/wait split and cost remain UNKNOWN; efficiency ratios are UNVERIFIED. All prior checker phases, retries/children, allocation debits and helper refusals remain retained in archived review inputs/checkpoints. The already-committed reserve/unknown-usage helper blocker was not retried identically or represented as admission. Necessary focused continuation/finalization used the explicit finite human authorization relayed by the parent, without changing global policy. Shared integration suites retain separate command accounting; they are not counted as measured maker/checker active time.

This PASS certifies the reviewed combined code/test candidate and required integration gates. It does not certify saved-project migration, live-provider calls, production acceptance, caller-owned fixed-VideoObservation work, or unrelated backlog completion. Maker may close the matching cycle and commit QA-only records with identical reviewed product/test/script blobs. Push remains separately recorded after that closeout commit and exact destination verification.
