# t145-prod-project

**Status:** ready-for-check
**Fix cycle:** 1
**Branch:** wave/t145-prod-project
**Serves:** T-145 prerequisite; D-087 item 1 (each environment its own project); D-088 item 3 (pathlynks.vidysea.com is production, project.json corrected by a builder unit)

## Changes
- `projects/pathlynks/project.json`: description now PRODUCTION; `allowed_domains` = `["pathlynks.vidysea.com"]` (was `vidysea.com`, a suffix match); secrets reduced to `PATHLYNKS_USER_EMAIL` / `PATHLYNKS_USER_PASSWORD` (host `pathlynks.vidysea.com`); `write_policy` read_only.
- `projects/pathlynks-prepod/project.json` (new): `PATHLYNKS_COUNSELLOR_EMAIL` / `_PASSWORD` moved here; `allowed_domains` = `["dev-new.vidysea.com"]`; base_url `https://dev-new.vidysea.com/login`; read_only; no login case yet. Slug follows D-087's "pathlynks-prepod" and the goal note that dev-new is PREPOD.

## Domain evidence
Only host in `projects/pathlynks/{cases,knowledge,approvals}` is `https://pathlynks.vidysea.com` (login case_cfa40e6b95c2 navigates, fills and submits on `/signin` on that host, no redirect to another auth host recorded). dev-new.vidysea.com appears only in the old project.json.

## Verification
- Both files load through `ProjectStore.load_project()` (Project schema).
- `uv run autotester doctor`: clean.
- `scripts/check_crawl_approval.py pathlynks`: exit 1 "no finished crawl" (expected, no crawl yet).
- No approval minted (needs AT-651 merged; appr_ce61e4420ac9 / production:false rows must not be used).

## Approve command (maker runs after AT-651 merge; D-081 item 3 standing approval, D-088 item 4)
```
uv run autotester approve pathlynks --kind crawl --target https://pathlynks.vidysea.com/signin --scope "Bounded READ_ONLY BFS map crawl of Pathlynks PRODUCTION, user-role test account via declared login case; no form submits, nothing typed except login case, logout never clicked, deny-list on" --granted-by Umesh --expires <YYYY-MM-DD> --max-actions 150 --max-probes 1 --wall-clock 600 --production
```
(bounds 20 screens / 150 actions / 600 s per live-crawl-target.md answer; set `--expires` to run day + 1.)
