# AU20 differential fuzz, r2-A (read-only sub-checker, HEAD 27a3a0a9)

Files: harness.py (grid + run), supp.py + linux_probe2.py (Linux re-classification, WSL2 Ubuntu glibc), cases.csv / cases.json (3854 cases, every row),
summary.json, linux_probe.txt, linux_bind.json, compose/ (docker compose config results). Merge note: `cases.N.*` are the Windows first pass,
`supp.N.json` the Linux rerun of 898 cases whose bind classification differed; cases.json = merged.

Per dimension (cases): A bind x port x 29 allow-list shapes 1800 | B-port spelling 100 | B-host spelling 96 | C wildcard spellings 442 | D PUBLIC_ORIGIN 1360 | E list syntax x wildcard 56.
Verdicts: ok-started-served 1243, ok-refused 1058, ok-refused-by-design 877, UNBINDABLE (uvicorn/OS refuses the spelling) 475,
DISAGREE-refused-but-would-serve 117, DISAGREE-started-but-403 8 (+16 "started without PUBLIC_ORIGIN on a real wildcard"), ODDITY accepted-malformed-harmless 60, CRASH 4 (non-AuthConfigError).
Dimension A (concrete/loopback binds, ports, 29 list shapes) and E: zero disagreements. Dimension B/C/D: see report.
