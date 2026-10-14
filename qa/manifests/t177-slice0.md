# Manifest - t177-slice0 (merge verification of t177-slice0-browser-seam)

Full build manifest, criteria mapping, falsifications and residuals: `qa/manifests/t177-slice0-browser-seam.md` (fix cycle 2, code a8f2b9fb). This file records only the verification of the master merge.

Unit: T-177 slice 0 (browser seam, D-086 item 3 port A)
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: required
Fix cycle: 2
Status: superseded
Superseded-by: qa/verdicts/t177-actuator.r2.md (merge a1bab8e8; T-177 done; branch merged)

## Merge 819af45f (master 737fcc9d into the branch) - verified
- No conflict markers in src, tests, scripts, pyproject.toml.
- session.py (281 lines): AT-888 (55816796) did not touch it, it changed video.py and run_case_pipeline.py. `video.py::_restart_session` goes through `start()` (stale port file forgotten, endpoint re-verified); pinned by `tests/test_browser_cdp_restart.py`.
- Per-file runs (`-p no:xdist -p no:cacheprovider -o addopts=`): test_browser_session_cdp 23, test_browser_cdp_probe_hostile 11, test_browser_cdp_restart 1, test_browser_navigation_secrets 68, test_browser_settle 10, test_session_survives_failure 18, test_browser 14 (+1 skip), test_run_case_pipeline 11, test_video_evidence 1 (+1 skip). All pass.
- ruff check src tests scripts: clean.
- doctor: ONE violation was ours, `architecture-too-long` (151 > 150: the D-086-authorized security line made it 151). Fixed by folding the DevTools sentence into the existing item 4 of the security model (no new line, text unchanged). Remaining 6 violations are `ledger-row-missing` for T-154/168/178/197/202/205, from master's goal.json; not ours, not touched.

## Owed to checker (live browser, not run: slot taken)
- tests/test_browser_session_cdp_live.py, tests/test_session_survives_failure_live.py, the video live files.
- Headed Chrome bind of `--remote-debugging-address` (D-086 residual; must pass before headed Pathlynks runs).
- Headed `close()` after a refuse path.
