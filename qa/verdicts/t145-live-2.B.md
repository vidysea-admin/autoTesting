# Checker B verdict: T-145 live crawl 2 (adversarial)

Overall: FAIL on committed state (fixable by committing approvals.jsonl); substance PASS.

1. Binding of crawl to approval: PASS. Summary records approval_id, production flags and bounds; script requires the id to be in approvals.jsonl, matches project/kind/target, bounds, expiry at crawl start, human grant, and fails a production project without the key.
2. Approval signature: PASS in the main checkout. appr_a5c000b027dc is crawl, production true, granted_by Umesh, signature verified with the .env key (key not printed).
   BUT FAIL at committed master (b26712ca): the row exists only as an UNCOMMITTED change to projects/pathlynks/approvals.jsonl (+2 lines). In a clean worktree the done_check prints "FAIL ... approval appr_a5c000b027dc is not in approvals.jsonl". Commit the approvals rows or the evidence is unreproducible.
3. Numbers: PASS. actions 130 <= 150; wall 17:54:40 to 18:23:04 = 1704 s <= 1800; visited 7 <= found 40; screens 40 = max_screens bound.
4. Credentials/PII: PASS. Summary JSON holds only ids, counters and bounds; no secrets, cookies, tokens or emails.
5. Acceptance wording: PASS with caveat. Crawl is bounded and stopped on max_screens; only 7 of 40 screens visited and 9% control coverage, so thin; not a defect of the done_check.
Also note: an older untracked summary (crawl_01M4WWYW...) sits in the main tree; the script picks the newest, so ordering is OK, but keep it untracked or ensure it sorts older.

Re-check after 69c6e532 (closer, 2026-10-15): done_check exit 0 in a clean worktree at master with the approval key loaded in-process from the main checkout's .env (never printed): PASS crawl_01M4XRTHH96QAGSJNP954G826Z, approval appr_a5c000b027dc, production=True, granted by Umesh, signature verified. Blocker resolved, PASS.
