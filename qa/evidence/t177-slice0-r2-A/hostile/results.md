| case | direct wall min/med/max s | return | client bytes read (max) | listener sent (max) | accepts | public wall min/med/max s | public result | leftover thr/sock/netstat |
|---|---|---|---|---|---|---|---|---|
| 01 header trickle 1B/0.1s | 2.06/2.11/2.11 | False | 37 | 38 | [(1, 1, 1, 1)] | 2.05/2.09/2.11 | CdpEndpointError | none |
| 02 body trickle CL=60000 1B/0.1s | 2.02/2.08/2.09 | False | 189 | 190 | [(1, 1, 1, 1)] | 2.08/2.09/2.14 | CdpEndpointError | none |
| 03a chunked trickle 1B/0.1s | 2.00/2.02/2.05 | False | 104 | 104 | [(1, 1, 1, 1)] | 2.09/2.09/2.11 | CdpEndpointError | none |
| 03b chunked endless tiny chunks fast | 0.31/0.38/0.42 | False | 399189 | 756085 | [(1, 1, 1, 1)] | 0.33/0.36/0.39 | CdpEndpointError | none |
| 03c chunk-size ext endless fast | 0.00/0.02/0.05 | False | 65617 | 82001 | [(1, 1, 1, 1)] | 0.02/0.03/0.11 | CdpEndpointError | none |
| 04 no-CL Connection:close endless fast | 0.00/0.01/0.01 | False | 65607 | 73900 | [(1, 1, 1, 1)] | 0.02/0.05/0.08 | CdpEndpointError | none |
| 05a padded 65536 declared CL | 0.01/0.03/0.09 | True | 65610 | 65610 | [(1, 1, 1, 2)] | 1.03/1.03/1.06 | returned | none |
| 05b padded 65537 declared CL | 0.00/0.03/0.06 | False | 8192 | 65611 | [(1, 1, 1, 1)] | 0.03/0.03/0.06 | CdpEndpointError | none |
| 05c padded 65536 undeclared (close) | 0.31/0.31/0.31 | True | 65606 | 65606 | [(1, 1, 1, 2)] | 1.33/1.34/1.36 | returned | none |
| 05d padded 65537 undeclared (close) | 0.00/0.01/0.01 | False | 65607 | 65607 | [(1, 1, 1, 1)] | 0.03/0.05/0.08 | CdpEndpointError | none |
| 05e padded 65536 chunked | 0.01/0.05/0.09 | True | 65629 | 65629 | [(1, 1, 1, 2)] | 1.03/1.03/1.08 | returned | none |
| 05f padded 65537 chunked | 0.00/0.03/0.05 | False | 65623 | 65630 | [(1, 1, 1, 1)] | 0.02/0.02/0.03 | CdpEndpointError | none |
| 06 accepts, never answers | 2.02/2.02/2.02 | False | 0 | 0 | [(1, 1, 1, 1)] | 2.03/2.03/2.08 | CdpEndpointError | none |
| 07a never-accept (backlog filled) | 2.00/2.02/2.02 | False | 0 | 0 | [(0, 0, 1, 1)] | 2.02/2.03/2.03 | CdpEndpointError | none |
| 07b unrouted CDP_HOST 192.0.2.1 | 2.00/2.01/2.02 | False | 0 | 0 | [(0, 0, 1, 1)] | 2.02/2.02/2.03 | CdpEndpointError | none |
| 08a mid-body close, valid JSON prefix (CL 1000) | 0.02/0.03/0.05 | True | 175 | 175 | [(1, 1, 1, 2)] | 1.05/1.05/1.05 | returned | none |
| 08b mid-body close, partial JSON | 0.00/0.01/0.02 | False | 103 | 103 | [(1, 1, 1, 1)] | 0.01/0.05/0.09 | CdpEndpointError | none |
| 08c closed after headers only | 0.02/0.02/0.02 | False | 72 | 72 | [(1, 1, 1, 1)] | 0.02/0.02/0.03 | CdpEndpointError | none |
| 09a 100 Continue forever fast | 2.00/2.01/2.02 | False | 11051008 | 11350000 | [(1, 1, 1, 1)] | 2.03/2.06/2.09 | CdpEndpointError | none |
| 09b 103 once then 200 good | 0.00/0.03/0.06 | False | 214 | 214 | [(1, 1, 1, 1)] | 0.02/0.05/0.08 | CdpEndpointError | none |
| 09c 100 Continue trickled | 2.02/2.05/2.09 | False | 475 | 500 | [(1, 1, 1, 1)] | 2.08/2.12/2.16 | CdpEndpointError | none |
| 09d 100 once then 200 good (control) | 0.01/0.02/0.02 | True | 199 | 199 | [(1, 1, 1, 2)] | 1.03/1.04/1.05 | returned | none |
| 10a 301 -> other loopback port (good id) | 0.01/0.02/0.02 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.03/0.04/0.05 | CdpEndpointError | none |
| 10b 301 -> http://localhost:<aux> | 0.03/0.05/0.06 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.02/0.02/0.03 | CdpEndpointError | none |
| 10c 301 -> http://example.invalid/ | 0.00/0.01/0.01 | False | 87 | 87 | [(1, 1, 1, 1)] | 0.01/0.02/0.02 | CdpEndpointError | none |
| 10a 302 -> other loopback port (good id) | 0.00/0.00/0.00 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.02/0.02/0.03 | CdpEndpointError | none |
| 10b 302 -> http://localhost:<aux> | 0.02/0.03/0.05 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.03/0.09/0.16 | CdpEndpointError | none |
| 10c 302 -> http://example.invalid/ | 0.00/0.01/0.01 | False | 87 | 87 | [(1, 1, 1, 1)] | 0.05/0.06/0.06 | CdpEndpointError | none |
| 10a 307 -> other loopback port (good id) | 0.00/0.03/0.06 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.01/0.02/0.02 | CdpEndpointError | none |
| 10b 307 -> http://localhost:<aux> | 0.00/0.01/0.01 | False | 84 | 84 | [(1, 1, 1, 1)] | 0.03/0.03/0.03 | CdpEndpointError | none |
| 10c 307 -> http://example.invalid/ | 0.02/0.02/0.02 | False | 87 | 87 | [(1, 1, 1, 1)] | 0.03/0.04/0.05 | CdpEndpointError | none |
| 11a deep [ x30000 | 0.00/0.02/0.05 | False | 30074 | 30074 | [(1, 1, 1, 1)] | 0.03/0.03/0.03 | CdpEndpointError | none |
| 11b deep {"a": x30000 | 0.00/0.01/0.02 | False | 8192 | 150075 | [(1, 1, 1, 1)] | 0.01/0.02/0.03 | CdpEndpointError | none |
| 11c deep [ exactly cap | 0.00/0.00/0.00 | False | 65610 | 65610 | [(1, 1, 1, 1)] | 0.05/0.06/0.08 | CdpEndpointError | none |
| 11d deep {"a": exactly cap | 0.02/0.02/0.03 | False | 65610 | 65610 | [(1, 1, 1, 1)] | 0.03/0.06/0.09 | CdpEndpointError | none |
| 11e 60000-digit number in good obj | 0.00/0.03/0.06 | False | 60180 | 60180 | [(1, 1, 1, 1)] | 0.03/0.03/0.03 | CdpEndpointError | none |
| 11f invalid UTF-8 inside good obj | 0.00/0.01/0.01 | False | 183 | 183 | [(1, 1, 1, 1)] | 0.01/0.05/0.08 | CdpEndpointError | none |
| 11g dup key right then wrong | 0.00/0.00/0.00 | False | 249 | 249 | [(1, 1, 1, 1)] | 0.03/0.09/0.14 | CdpEndpointError | none |
| 11h dup key wrong then right | 0.00/0.02/0.05 | True | 249 | 249 | [(1, 1, 1, 2)] | 1.05/1.14/1.24 | returned | none |
| 11i UTF-8 BOM prefix + good | 0.02/0.02/0.03 | True | 177 | 177 | [(1, 1, 1, 2)] | 1.03/1.04/1.05 | returned | none |
| 11j id field = list | 0.00/0.01/0.01 | False | 176 | 176 | [(1, 1, 1, 1)] | 0.02/0.02/0.02 | CdpEndpointError | none |
| 11k id field = dict | 0.00/0.01/0.01 | False | 181 | 181 | [(1, 1, 1, 1)] | 0.09/0.09/0.09 | CdpEndpointError | none |
| 11l id field = int | 0.00/0.01/0.02 | False | 98 | 98 | [(1, 1, 1, 1)] | 0.03/0.04/0.05 | CdpEndpointError | none |
| 11m id field = null | 0.00/0.03/0.06 | False | 101 | 101 | [(1, 1, 1, 1)] | 0.03/0.05/0.06 | CdpEndpointError | none |
| 11n id field = str w/ right path as suffix of longer str | 0.00/0.02/0.03 | True | 177 | 177 | [(1, 1, 1, 2)] | 1.01/1.02/1.03 | returned | none |
| 11o id field = right path + trailing junk | 0.01/0.03/0.05 | False | 175 | 175 | [(1, 1, 1, 1)] | 0.02/0.06/0.09 | CdpEndpointError | none |
| 11p top-level array containing good obj | 0.00/0.01/0.02 | False | 176 | 176 | [(1, 1, 1, 1)] | 0.03/0.05/0.06 | CdpEndpointError | none |
| 11q control: good identity | 0.01/0.02/0.03 | True | 174 | 174 | [(1, 1, 1, 2)] | 1.03/1.03/1.03 | returned | none |
| 11r control: good identity chunked | 0.00/0.00/0.00 | True | 192 | 192 | [(1, 1, 1, 2)] | 1.03/1.04/1.05 | returned | none |
| 12a 150 headers | 0.00/0.01/0.02 | False | 1714 | 1714 | [(1, 1, 1, 1)] | 0.01/0.05/0.08 | CdpEndpointError | none |
| 12b 99 headers (control, should pass) | 0.02/0.02/0.02 | False | 1154 | 1154 | [(1, 1, 1, 1)] | 0.05/0.08/0.11 | CdpEndpointError | none |
| 12c one 70000-byte header line | 0.01/0.02/0.03 | False | 70181 | 70181 | [(1, 1, 1, 1)] | 0.01/0.02/0.02 | CdpEndpointError | none |
| 13a non-HTTP reply | 0.00/0.00/0.00 | False | 20 | 20 | [(1, 1, 1, 1)] | 0.01/0.02/0.03 | CdpEndpointError | none |
| 13b empty reply (close) | 0.00/0.01/0.02 | False | 0 | 0 | [(1, 1, 1, 1)] | 0.03/0.06/0.09 | CdpEndpointError | none |
| 13c HTTP/0.9-style bare body | 0.31/0.32/0.33 | False | 102 | 102 | [(1, 1, 1, 1)] | 0.33/0.38/0.42 | CdpEndpointError | none |
| 13d 200 headers, no CL, no body, stays open | 2.02/2.04/2.06 | False | 51 | 51 | [(1, 1, 1, 1)] | 2.03/2.03/2.03 | CdpEndpointError | none |

MAX direct wall 2.110s; MAX public wall 2.156s

notes: [('07a never-accept (backlog filled)', 'fill=40 extra-connect-hangs=connect probe: TimeoutError after 0.70s'), ('07b unrouted CDP_HOST 192.0.2.1', 'CDP_HOST patched to 192.0.2.1 (RFC5737)')]

## Other measurements (see JSON files alongside)
- session.json: BrowserSession.start() with fake launch: cases 01/02/04/09a/11a/11b -> CdpEndpointError, context closed, port file removed, endpoint refuses; control good id starts (wall 1.03 s: `_reaches_past_loopback` timeout). Walls 2.05-2.13 s for hanging cases.
- ki.json: KeyboardInterrupt/SystemExit propagate from read1 / SocketIO.readinto / request / getresponse; Timer.cancel() and HTTPConnection.close() ran each time; no Timer thread left.
- race_fast.json: 2000 fast good replies -> 2000 True, 0 exceptions, 0 leftover threads at end (346 iterations showed the cancelled Timer thread for a few ms after return; amp_T.json: max time-to-gone 32 ms over 1500 iterations).
- race_near_a/b/c.json (2 s deadline, reply at 1.99-2.01 s): see files; amp_*.json: deadline patched to 0.2 s, 1800 boundary iterations: 195 True-full, 0 True-TRUNCATED.
- extra.json: header region is not byte-capped (97 x 65000 B headers + valid body accepted True, 6.3 MB read); interim `100 Continue` stream consumed 237 MB in 2 s (time-bounded only).
- rec.py: json.loads of 65536 '[' -> RecursionError at default limit; with sys.setrecursionlimit >= ~20000 the process hard-crashes (0xC00000FD) on Windows. src/ never raises the limit (grep empty).
