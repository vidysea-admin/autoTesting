# t136-route-b checker real-data run (copy only; main tree untouched)
Copy root: scratchpad chk-t136-route-b/real (project.json, cases.jsonl, run-01M58F744J7R3CB99CMH9S7FQ3, 13 crawl dirs: issues/nodes/crawl.json only, corpus pathlynks-acceptance.json mode unknown).
Command 1: uv run python scripts/bench_from_run.py pathlynks --run run-01M58F744J7R3CB99CMH9S7FQ3 --crawl all --root <copy> -> saved trial (14 findings, duration_s=44.827), exit 0.
Command 2: uv run python scripts/check_acceptance_comparison.py pathlynks --root <copy> -> exit 0; recall/detection "unavailable (no human list)", fp_rate 1 (unadjudicated), human unavailable.
Raw issue rows in the 13 crawls: console 139, network 36, navigation 31, overlay 20, dialog 1 (all first_party=true, no EVIDENCE rows). Findings: 14, none from navigation/overlay/dialog; none from a warning line.
All evidence refs per finding resolve against the real projects/pathlynks tree (0 missing): crawl/<id>/issues.jsonl and crawl/<id>/shots/<png>.
Observation (low, AT-1346): 6 of the 14 are console "Failed to load resource ... status of N ()" or CSP report-only lines; the console text carries no URL, so first-party is unknowable (drain() marks every console line first_party=true) and the same fault is also counted by its network row.
