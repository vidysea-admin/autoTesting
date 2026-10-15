# T-145 done_check verdict: live bounded crawl of pathlynks (closer)

Verdict: PASS (dual check: A PASS, B PASS after re-check; qa/verdicts/t145-live-2.A.md, t145-live-2.B.md).

done_check `scripts/check_crawl_approval.py pathlynks`: exit 0.
Output: PASS crawl crawl_01M4XRTHH96QAGSJNP954G826Z (stopped_bound, stop_reason=max_screens, 40 screens, 8 refused) gated by approval appr_a5c000b027dc production=True granted by Umesh; signature verified.

Where it passes: anywhere the repo-root .env key (AUTOTESTER_APPROVAL_KEY) exists, with the signature verified. A clean worktree fails only for the missing gitignored key (production project, signature unverifiable); it passes there when the key is loaded in-process from the main checkout's .env. Approvals are committed (69c6e532).

Coverage is thin: 7 of 40 found screens visited, 9% of controls. The crawl is bounded and met its bounds (130 of 150 actions, 1704 of 1800 s).

Real findings (first party): 502 on /api/pathlynks-quest/island-weightage; 502 on /psychometric/status; 400 on _next/image; console error "Error fetching student recommendations".

Known tooling gap: the done_check picks the newest crawl summary including untracked ones (see the AT issue filed with this close).
