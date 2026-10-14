# t145-live-2: second live bounded crawl of pathlynks (evidence, not a checker verdict)

- Crawl: crawl_01M4XRTHH96QAGSJNP954G826Z, status stopped_bound, stop_reason max_screens (40 of 40). Login case case_cfa40e6b95c2, headed per project config, provider mock.
- Approval: appr_a5c000b027dc (crawl, production true, Umesh, 150 actions / 1800 s, expires 2026-10-21); signature verified.
- Wall time 17:54:40 to 18:23:04 UTC (about 28 min of 1800 s). Actions 130 of 150, denied 8, tool_failures 0, edges 140, issues 17.
- Screens found 40, visited 7 (33 queued unvisited). Control coverage 9% (110 of 1180 exercised) versus the previous crawl 20 found / 4 visited / 6% (35 of 536).
- Frontier left: /career-compare, /help-faq, /settings, /resource-library, /messages, /career-quest, /career-quest/know-yourself, /career-quest/career-selection, /my-matches, /profile, /view-this-assessment-report, plus repeat states of already-visited routes.
- Holes: 1070 total (938 not_visited, 65 error, 47 bound:max_screens, 12 per_node_action_cap, 6 logout never-click, 1 typing disabled, 1 unnamed).
- Findings (first party): 2 x 502 on /api/pathlynks-quest/island-weightage and /psychometric/status; 3 x 400 on _next/image (cs_detail.png); console "Error fetching student recommendations"; 3 overlay-covered control lists (Know Yourself, Career Select, sidebar); 3 lost-screen navigation issues.
- done_check scripts/check_crawl_approval.py pathlynks: PASS (new crawl, appr_a5c000b027dc, signature verified).
- Screenshots, network.jsonl and the crawl dir are not committed. Only the summary JSON is tracked.
