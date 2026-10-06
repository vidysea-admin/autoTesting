# Bounded checker sweep — crawl completion/recovery truth

Bound to `D:/autoTesting`. Source, manifests, credentials and live target were read-only.
Terminal state: FINDINGS: 1 (AT-113 reopened; no duplicate ID).

## Independent evidence

Command: `.venv/Scripts/python.exe qa/evidence/sweep-2026-09-30-crawl-probe.py`.
Initial executable result: `TERMINAL (<CrawlStatus.COMPLETED: 'completed'>, None)`.
This feeds the current real function one ABORTED_ERROR node, completed=True, zero actions,
zero denied and zero edges. The first local run_crawl fixture attempt stopped at SigningKeyMissing;
the probe now uses an ephemeral local dummy approval key, never a credential or .env value.
Re-run completed with exit 0:
`RUN {"status":"completed","stop_reason":"frontier empty","actions":0,"nodes":["aborted_error"],"success":true,"issues":1}`.
The actual stored `crawl_01M3S02YPQRV6S65GEY5TTCCVK` independently read completed,
0 actions, frontier empty, one aborted_error, 7 controls discovered/0 exercised, 0% coverage,
and all seven controls holes with reason error. Actual stored second crawl
`crawl_01M3S0K5CZCKYR4M1J3BPNPHMX`: stopped_bound, wall_clock_s, 44 actions,
four aborted_error nodes, one explored, sixteen queued; 558 discovered/44 exercised, 7%.
The second run is visibly incomplete, so it is evidence for recovery/coverage work rather than
another false-COMPLETED finding.

The original AT-113 title/evidence describes exactly this false completion. Its old checker
verification proved node status and an issue were persisted but did not prove overall crawl
status. `tests/test_explore_node_recovery.py:19` and `:53` still never assert crawl.status.
Reopen AT-113 instead of allocating another ID. T-165 must be reopened against CR5:
“Complete still means the actionable frontier was exhausted” and skipped/unreached controls
remain visible. A popped aborted visit is not exhaustion of its actionable frontier.
The maker owns `.goal/goal.json`; this sweep recommends T-165 pending with AT-113 as reason.

## Proposed existing-file plan (not preimplementation approval)

1. `src/autotester/stages/explore_status.py:147::terminal_status`: keep login-failure/login-wall
   precedence and named bound precedence; when no bound fired and a node is ABORTED_ERROR,
   emit ABORTED with a recovery-failure reason instead of COMPLETED. STOPPED_BOUND is reserved
   for an actual safety/time/action/depth bound, so using it for a navigation recovery failure
   would invent a bound. Do not equate zero actions with failure: a healthy static leaf is valid.
2. `src/autotester/stages/explore.py:151::_bfs`: queue drain must not set frontier_exhausted
   true when a visit aborted with controls unreached. Persist a cause naming the aborted screen;
   continue other queued screens as already designed. A partial graph remains useful, never complete.
   Ensure the caller distinguishes error incompleteness from bound incompleteness.
3. `src/autotester/stages/explore_status.py:195::displayed_status` and `:234::is_success`:
   inspect stored node truth for legacy completed envelopes, through the existing callers/store
   seams. A counter-only Crawl cannot reveal a recovery failure, so do not infer it from issues
   count or zero actions. Preserve legacy artifacts byte-for-byte while all success surfaces become
   truthful. Root must name the exact caller changes after tracing current signatures.
4. `src/autotester/stages/persona_changes.py:118::_judged_exhausted`: reject an aborted/recovery-incomplete
   graph as proof of deletion, even when a caller passes frontier_exhausted=True; report unreached
   prior keys as missing_unjudged. An incomplete crawl must never fabricate missing screens.
   Its current predicate rejects only SKIPPED_UNCHANGED, so abort must be tested independently.
5. Extend existing `tests/test_explore_node_recovery.py` both entry and mid-loop paths; existing
   status/report tests for legacy display/is_success; `tests/test_explore_completeness.py` for
   frontier exhaustion; `tests/test_persona_changes.py` for missing vs missing_unjudged. Prove
   healthy no-action leaf completion, genuine bound+aborted-node precedence, login precedence,
   old completed envelope display correction, and aborted partial crawl classification.
   Falsify each new assertion by reverting only its matching existing seam in a throwaway copy.

## Handshake and next units

at673 currently ends cycle 3 checked-PASS and has matching cycle-3 PASS (`311d322f`, addendum
`ec7c86ce`). Earlier ready-for-check history is superseded. Known detector quoted-field debt is
already ISS-at673-1; a hook's false pending count is not evidence for reopening that unit.

Top 3: (1) AT-113/T-165 completion truth as above; (2) generic authenticated recovery improvement
under existing explore_return.py/return_to replay seams, with its own local authenticated-browser
proof; (3) T-171 permission-surface coverage. Truthful failure alone does not satisfy the requested
end-to-end authenticated crawl or coverage acceptance.

Untouched this bounded sweep: full inbox fold-in, global contract staleness, all commits/bypass
inventory, enforcement wiring execution, whole-goal decomposition, general silent-failure scan,
full suite and live browser. No claim of full coverage or unit PASS.
