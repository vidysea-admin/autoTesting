# t145-live: Pathlynks live crawl + first-cases chain (evidence, not a checker verdict)

- Crawl: crawl_01M4T9SNAAWD7EKA6TSY448S53, status stopped_bound, stop_reason max_screens.
- Screens found 20 (4 visited, 16 queued unvisited), edges 41, actions 36 of 150, denied 2, issues 9, tool_failures 0.
- Wall time: 09:34:33 to 09:43:04 UTC (about 8.5 min of 600 s). Control coverage 6% (35 of 536).
- Approval: appr_9251602cdf24 (crawl, production true, Umesh, 150 actions / 600 s, expires 2026-10-20). A second row appr_f372fbba1f25 (non-production, account-derived, expired 09:44) was minted by the earlier attempt.
- done_check scripts/check_crawl_approval.py: PASS.
- Findings (all first party): 2 overlay-covered controls lists, 4 lost-screen navigation errors (back/URL landed elsewhere), 1 console 400, 1 network 400 on _next/image, 1 console "Error fetching student recommendations".
- Crawl provider: mock (no model calls). The crawl was kept, not re-run.
- T-136 chain: run_id run-01M4THHQ6369QK96NP7J46R7QE, 3 login cases (worst, edge, best) all PASS, graded by gemini. Ollama/DeepSeek are not wired into the repo chain (no OLLAMA_BASE_URL; providers lists gemini, langchain-fallback, mock), so Gemini served.
- bench_from_run: 0 findings, duration 84.1 s. Comparison: INCOMPLETE (no human list, no ground-truth bugs, FP rate unavailable).
- Errors: none beyond the above. Screenshots are gitignored and not committed; network.jsonl not committed.
