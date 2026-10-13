# HUMAN_GATE (PARTIAL) - T-203 server host and DNS

**Opened:** 2026-10-07 (D-071). **Decider:** Umesh. **Status:** OPEN for the real host and DNS; the local-machine part is answered.
**Blocks:** only the hosted check of T-206 (G10 acceptance on Ubuntu). It does not block T-203's build.

Question: which server hosts the AutoTester website, and on which domain? Options: (A) a named Vidysea server + DNS name; (B) this dev machine only.

Umesh (2026-10-10): "krr denge but tu phle sabb run tho krr and for that time iss system mai host krkee use krr".

Answered part: T-203 proceeds as a LOCAL deployment on the dev machine for now. Recorded as D-081 item 4.
STILL OPEN: the real server host and the DNS name. No Answered line for this part. Owed by Umesh.

Answered (local-machine part only): 2026-10-10 - host locally for now - D-081

Umesh (2026-10-12): "ubuntu hoga will provide later abhi tho yhi system mai host kroo" - the real host will be an Ubuntu server, details later; keep hosting on this machine until then. Host name and DNS still OPEN.

Answered 2026-10-13 (chat), see D-090: production host will be Ubuntu, host and DNS later. Now: build and host on this Windows machine (no Docker): launcher script + Windows Scheduled Task (boot start, restart on failure), 127.0.0.1 behind T-204 login by default, LAN exposure one setting (hosting.md HO39-HO46). Ubuntu Docker files untouched; Ubuntu rows (HO10, HO11, HO13, HO34-HO36) deferred. Host name and DNS still OPEN.
