# Verdict - ephemeral-storage-warning (Mode A, head b58c8ec2, branch fix/ephemeral-storage-warning)
Verdict: FAIL
Cycle checked: 0
Head tested: b58c8ec2 (one commit on master e74664f8). Independent checker; no contract edited; main checkout untouched.

## Blocking findings (2, both introduced by this branch)
1. `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` is RED because of this diff.
   Command: `uv run pytest tests/test_storage_warning.py tests/test_container_entrypoint_behaviour.py tests/test_env_loading.py tests/test_hosting_config.py tests/test_hosting_deploy.py tests/test_hosting_gaps.py`
   Output: `1 failed, 88 passed, 1 skipped`; `AssertionError: undocumented env keys: ['AUTOTESTER_EPHEMERAL_OK']` (tests/test_hosting_deploy.py:70).
   Cause: `src/autotester/core/env.py` (EPHEMERAL_OK_ENV) introduces a key read by the code; `.env.example` has no `AUTOTESTER_EPHEMERAL_OK=` line (the test scans `src/**/*.py` for `AUTOTESTER_[A-Z_]+` against `.env.example`, e.g. `.env.example:93` documents AUTOTESTER_HOSTED). `git grep EPHEMERAL_OK master -- .env.example src` is empty, so the test was green on master. The manifest's own verification list never ran tests/test_hosting_deploy.py.
   Fix: add a commented/empty `AUTOTESTER_EPHEMERAL_OK=` line with a one-line explanation to `.env.example` (no secret-looking value; test_env_example_holds_no_secret_looking_value must stay green).
2. `uv run autotester doctor` reports 2 violations, not the 1 pre-existing one the manifest claims. The second is new: `decision-citation-dangling: qa/manifests/ephemeral-storage-warning.md:29 cites the decision id 110 (written D, hyphen, 110), which has no matching entry in docs/DECISIONS.md`. (The other, qa/verdicts/6c-1028-signup.md:4, is the pre-existing one and is ignored per brief.)
   Fix: reword manifest line 29 so it does not cite the bare id (D, hyphen, 110) (say "the signup verdict's dangling decision citation").
   Also: this verdict spells that id out for the same reason.

## Per criterion (everything else holds)
1. Same-device hosted root -> banner. PASS. `env.storage_warning` (src/autotester/core/env.py, after `dollar_warning`) returns the exact sentence "Storage is not persistent: accounts and projects are lost on every deploy. Mount a volume at <root>."; `ui/admin_view.py::storage_banner` gated on `auth.loopback.hosted()`, rendered at top of `users_body` and `groups_body` (the only two callers: ui/routes_admin.py:46, 97, 109, 163; there is no bare /admin route). Probe: same-device with root-listed-as-fuse, tmpfs, ramfs, not-in-mounts all return the sentence; banner text is `html.escape`d (probe: injected `<b>` rendered as `&lt;b&gt;`).
2. Mounted root -> no banner. PASS. Probe with the real function: `gcsfuse <root> fuse.gcsfuse` -> None; `gcsfuse <parent> fuse` (ancestor volume) -> None; octal-escaped mount point (`\040`) decoded -> None. Shell function under real bash with fake stat: `/data fuse.gcsfuse` quiet, `/data/sub` under that mount quiet, `/data/` trailing slash quiet, sibling `/data2` mount does NOT count for `/data` (warns), `tmpfs /data` warns.
3. Non-hosted -> no banner. PASS. tests/test_storage_warning.py::test_no_banner_when_not_hosted green; `storage_banner` short-circuits on `hosted()` before the detector runs.
4. `AUTOTESTER_EPHEMERAL_OK=1` silences both. PASS. Python: `" 1 "` -> None, banner dropped end to end (test_opt_out_env_drops_banner_end_to_end); `"true"` does not silence (strictly "1", as documented). Shell: probe 11 (opt-out with ephemeral tmpfs and same device) prints nothing and returns 0.
5. Never stops start or a page render. PASS. Python probes (uv run python scratchpad probe): missing /proc/mounts, empty file, binary garbage, NUL in root path, mounts path being a directory, no `/` entry, garbled short lines, nonexistent deep root, `_device` raising PermissionError (test_device_error_never_raises), an internal helper (`_mount_entries`) raising RuntimeError -> every case returns a value or None, none raise; `users_body`/`groups_body` render fine afterwards. The try/except wraps repo_root, read, parse, device and compare; only the f-string tail is outside and cannot fail. Shell: docker/entrypoint.sh has `set -euo pipefail` at line 3; I extracted the function verbatim and ran it under `set -euo pipefail` as `warn_if_ephemeral || true` for 14 cases (no mounts file, mounts a directory, nonexistent root, unset/empty AUTOTESTER_ROOT, root `/`, relative root, trailing slash, stat reporting same device while listed as fuse, etc.): every case printed `survived rc=0`. Function has no `exit` (test_entrypoint_syntax_and_function_never_exits), `bash -n` passes, file is LF in index (`git ls-files --eol`: i/lf, attr eol=lf).
6. Entrypoint warning line. PASS. Emits exactly one stderr line `WARNING: storage is not persistent: AUTOTESTER_ROOT=<root> is on the container's own filesystem; ...` when root device == `/` device or no non-tmpfs/ramfs mount line holds the root or an ancestor. Placed after the AUTOTESTER_ROOT setup and before the supervisor exec (docker/entrypoint.sh diff hunk @@ -35). Probes 7, 9, 10, 13, 14 warn; 5, 6, 8 stay quiet. Minor, not blocking: a mount point containing a space is not octal-decoded in the awk path, so it can only produce a false warning, never a failure.
7. docker/DEPLOY.md paragraph. PASS. One "Persistent storage" paragraph added in the Cloud Run section (diff +2 lines) naming the warning, the banner and the opt-out.

## Secrets / env echo
No env value other than the data-root path (which the criterion text itself requires: "Mount a volume at <root>") is echoed; no .env read by this check or by me. PASS.

## Other commands
- `uv run ruff check src tests scripts`: All checks passed.
- Design rules: core/env.py 229 lines, ui/admin_view.py 136, tests 174 (all under 300); functions under 50 lines.
- Not exercised (no Linux container available, Windows host): a real Cloud Run gen2 mount. Residual risk accepted by the maker stands: confirm on first deploy that the volume appears in /proc/mounts as fuse/nfs and not tmpfs.

## Next step for the maker
Fix the two blocking findings above (a 2-line change), re-run tests/test_hosting_deploy.py and `uv run autotester doctor`, bump `Fix cycle: 1`, re-request check. Manifest Status stays ready-for-check (not flipped).
