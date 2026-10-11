# Checkpoint (coordinator B) - t177-slice0-browser-seam

Cycle checked: 0
Status: CONTINUE-NEEDED (verdict qa/verdicts/t177-slice0-browser-seam.b.md), Resume: 1 of 2 used
Head: 3495ee61fa5604beebc01e4354ec8f3e3d935425 (code d2d463a9), base master 808cdf7f
Worktrees (left in place): D:/autoTesting/.worktrees/check-t177s0-b (head, uv-synced), D:/autoTesting/.worktrees/check-t177s0-b-master (baseline, PYTHONPATH use)
Policy-Version: proportional-verification/2026-10-10.9
Environment: Windows 11 10.0.26300, bundled Chromium 151 (headed) and chrome-headless-shell (headless), local pages, no .env read, no network beyond loopback.

## Evidence identity (qa/evidence/t177-slice0-browser-seam-B/)
| Check | Result | File |
|---|---|---|
| Bind table, headless+headed, expose off/on | clean, loopback only | bind-table-raw.txt, SUMMARY.txt |
| Stale / replant / concurrent / refuse / wildbind | stale refused, concurrency OK, refuse clean (headless); replant adopted (note N3) | scenarios-headless.txt, scenarios-headed.txt |
| Hostile schemes via real goto, head vs master | head 19/19 refused, master executes | bad-scheme-real-goto.txt |
| Regression head vs master (headless) | identical incl. tab2 gap on both | regression-head-vs-master.txt |
| Falsifications B5, B6, AF3, B9 | green/red/restored | falsifications.txt |
| In-tree pytest 83 passed, ruff, doctor | clean | unit-and-live-tests.txt |
| Headed close hang probe | head and master both hang | headed-close-hang-probe.txt |
| Killed-browser attempt | not verifiable (zombie, close blocks) | kill-scenario-headless.txt |

## Remaining (for the resume)
1. Killed-browser teardown: port closed, cdp_url None, port file gone after the browser process dies (needs a machine where a killed process actually exits).
2. Headed refuse / forced-wildcard / start-raises-midway teardown.
3. Headed regression (settle, recorded case, video, first-tab mask, tab2 gap on both).
Blocker for 2-3: headed BrowserSession.close() does not return here, on master as well.

No pytest was ever run through `--project`; the only pytest runs are the in-tree `uv --directory` ones above, so nothing was redone. B wrote no issue rows, merged nothing, closed no task, pushed nothing.
