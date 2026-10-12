# t177-slice0-browser-seam r1 checker A: probe results (copy: git archive 0a4859a1 on C:, venv on C:)
Probes are in this folder, run with the copy's python (autotester.__file__ inside the copy; doctor clean, ruff clean).

## hostile.py / hostile2.py: verified_cdp_url against a hostile loopback listener named in DevToolsActivePort
- non-http bytes, [], "x", null, 7, ws=list, bad utf8, 50k-digit int, HTTP 500, reset, truncated, empty, accept-never-reply -> CdpEndpointError ("not this browser"); the never-reply case after 2.0 s
- deep nesting 200k ("[" or {"a":) -> RecursionError (NOT CdpEndpointError)
- 300 MB body of spaces -> CdpEndpointError after 3.9 s, peak traced memory 604 MB (body fully buffered)
- 1 byte / 0.5 s forever -> HANG > 20 s, no exception
- 302 to another loopback port with valid JSON -> followed, the probe PASSES (returned the file's port url), target contacted
- 302 loop -> CdpEndpointError; 302 to 192.0.2.1 -> contacted, 2.0 s, CdpEndpointError; 302 to file:// -> refused

## live.py: real headless Chromium, expose_cdp=True, failure after launch
- RecursionError from probe -> raised RecursionError, cdp_url None, port file gone, 0 chromium descendants, close() twice ok
- KeyboardInterrupt / SystemExit(3) from observer.attach -> re-raised unchanged; port closed, file gone, 0 descendants
- context.close() raises during the failure path -> original RuntimeError raised; port closed, file gone, 0 descendants (playwright.stop() in close()'s finally still ran)
- failed start, then start() again on the same object -> works; close() -> port closed
- launch_persistent_context timeout (1 ms) -> TimeoutError, no port file, context None, _playwright still set (pre-existing, no browser), close() ends the driver

## livedrip.py: real browser + port file pointed at a dripping listener
- after 10 s start() had not returned; the REAL Chromium (port 57991) was running and ACCEPTING; 4 chromium descendants.
- When the listener closed: CdpEndpointError after 12.2 s, browser closed, port file gone.

## loop.py: _reaches_past_loopback on this host
- 127.0.0.2 -> loopback-only listener: TimeoutError at 1.0 s (not a refusal); reaches=False
- wildcard 0.0.0.0 accepting listener: reaches=True, 0.00 s
- wildcard 0.0.0.0 listener, backlog full, never accepts: TimeoutError at 1.0 s; reaches=False (hides behind the timeout)
- CLOSED port: both 127.0.0.2 and 127.0.0.1 TimeoutError at 1.0 s (a timeout cannot mean "refused")

## falsify.py: one per repaired item, isolated copy of src/tests/scripts (green / red / restored)
- F1a drop HTTPException: 23 / 1 failed / 23
- F1a drop isinstance guard: 23 / 3 failed / 23
- F1b except BaseException -> ZeroDivisionError: 23 / 1 failed / 23
- _close_quietly -> plain close(): settle file 10 / 1 failed / 10
- F2 OSError branch -> return False: 23 / 2 failed / 23
- Affected tests, clean copy: cdp_live + navigation_secrets + browser + settle + cdp = 118 passed.
