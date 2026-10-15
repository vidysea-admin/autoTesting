# Publication reconciliation: preserved Dockerfile history

Publication assessment: accepted for local application publication
Merge candidate: bf7e07c61ec90d074139691d9511104b2c2bbfff
Original canonical integration PASS: qa/verdicts/vision-role-defaults-integration.md
Original cycle checked: 1
Original reviewed application SHA: 3c9c3d1f6210b657c5bf70c71dc36f24f241c59a
Original QA closeout SHA: eb3afa2c982079c3c0702e099aa7017950ac474e
Preserved remote parent: d381e16949c3c8501b7d38a0e8eb2f28af6459d2
Preserved remote Dockerfile blob: 25687904db962fd0be5501777cccc09a137ff661

The original nonforce push was rejected because remote master contained six Dockerfile-only commits. A normal two-parent merge preserves that remote history and its exact Dockerfile bytes. Relative to the accepted local closeout, Dockerfile is the only product difference. The independent checker verified exact unchanged src/tests/scripts/docs/docker directory trees and pyproject.toml, uv.lock, .env.example and root .gitattributes blobs. All10original user-file SHA256 values remain identical.

Under qa/loop.md D-100's compatible deterministic reuse and explicit narrower-reuse clause, the successful full configured Python3.11 application gate retains its original3c9identity:7518passed,12skipped,14xfailed, zero failures/errors. No full pytest invocation is claimed at the merged candidate, no failed prefix/tail composition is relabeled PASS, and the original canonical PASS/manifest identity remains unchanged.

Fresh exact-bf7 checks replace affected Dockerfile evidence: compatible interpreter/import/dependency/temp preflight passed9.078s; both COMPLETE tests/test_hosting_deploy.py and tests/test_container_supervision.py passed25cases in5.29spytest/12.625scommand; full Ruff src/tests/scripts passed1.953s; actual doctor console entrypoint passed46.078s. Independently parsed XML matches all25baseline node identities from those files, with no failures/errors/skips. Every complete stdout/stderr hash, clean candidate/tree before/after binding and environment fingerprint was authenticated. The retained interpreter/version/dependency versions equal the successful full gate; only the intentionally relocated candidate import/temp paths differ. See verification.json and raw receipts beside this record.

Dockerfile uses managed Python3.12 consistently for installation and frozen synchronization, preserves the locked Playwright tag, root-owned external environment, final UID/GID10001, UV_NO_SYNC and existing entrypoint/port boundaries. chmod a+rX adds read/search access without granting writes. No secret value or application permission change was introduced. Existing Dockerfile secret scan, locked-version coupling and unprivileged/frozen-environment tests pass.

Python3.12 container BUILD/RUNTIME/DEPLOY acceptance remains UNVERIFIED/deferred. No Docker executable was available on PATH, no engine/install/build/deploy was performed, and localPython3.11 success does not certify container runtime. Existing hosting.md BUILD-HOST/SERVER-GATED obligations are not waived or reported complete. Other three backlog tasks remain outside this publication.

Accounting remains honest: prior checker phases, retries, failed push, helper refusals and allocation charges retain their original records; actual total tokens, active/wait split and cost remain UNKNOWN and efficiency UNVERIFIED. Fresh shared checks retain command costs separately. This record adds no test, source, contract or policy change. The following QA-only commit preserves the merge product identity; standing push is nonforce to verified github.com/vidysea-admin/autoTesting origin/master, with final remote SHA recorded separately.
