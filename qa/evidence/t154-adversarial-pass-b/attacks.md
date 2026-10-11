# t154-adversarial-pass coordinator B: attack and falsification log

Throwaway copy of 575a7c3f, fixture transport, throwaway test signing key. Scripts (scratchpad check-t154-b/scripts: attacks.py, fals.py, fals2.py) are not committed.

## Attacks (counting transport)
"Held" = zero sends, exactly one refusals.jsonl line, no run dir, no probe text or secret in the log.

Held: no approval; expired (date, datetime, unparseable); crawl row (same target, max_probes 99); read row; other project; sibling subdomain; target with a port; production=True against a production=False row; row flipped to production in the file (id dropped); max_probes -1 / 0 / 3-vs-4; approval wall_clock 0, and 10 vs run 11; 51 probes with max_probes 1e9; 60 probes via 4x duplicate set names; hosts evilvidysea.com, x.vidysea.com.evil.com, userinfo@evil.com, evil.com/vidysea.com, [::1], file://, "chat", "" (all AdversarialBlocked); approval tampered (max_probes 999 with id kept, id dropped, id and signature dropped); no signing key; secret in endpoint, in a probe_sets name, in probe text raw and base64.

Not refusals by design: wall_clock_s -1 / nan / inf raise ValueError before the gate (no log row, 0 sends). wall_clock_s=0 with a 0-wall row passes the gate and sends 0.

Mid-run: virtual clock where each send advances 100 s, wall 120 s, 4 planned -> 2 sent, unsent 2, cap_hit True. The latch is checked before every send, so 0 extra sends after it; a send already in flight has no timeout of its own.

Output: a reply echoing the secret raw is stored as [REDACTED]; echoing it base64 withholds the whole record (CaptureWithheld) and writes nothing.

Observations: an approval is not consumed (3 passes on one max_probes=4 row sent 12). probe_sets=["../outside"] loads a .md from outside prompts/probes and sends it (operator-supplied name only).

## Falsifications (own copy per mutant; named test green before, red after by assertion)
- AD1: kind=CRAWL (crawl param, DID NOT RAISE); refusal also creates a run dir (7 failed).
- AD2: probes=min(planned,3).
- AD3: ProbeRun.production=False (red on run.production).
- AD4: drop the empty-set block.
- AD5: add a `passed` field to ProbeRun.
- AD6: `> ceiling` -> `> ceiling+1`.
- AD7: requested_probes=0; refusal line never appended.
- Output scrub of the response removed (red).

## Survivors (test gaps; the code is correct in each case)
- `wall_clock_s=0.0` in the require_approval call (no test refuses on a wall-clock shortfall).
- `>` -> `>=` at the ceiling (exactly 50 untested).
- Refusal log `target=` and `reason=` unscrubbed (no test puts a secret in the endpoint or a probe_sets name).
- `>=` -> `>` on the wall-clock check.
