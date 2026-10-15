# Container supervision exposure review

**Verdict:** HOLD
**Status:** HOLD
**Cycle checked:** 1
**Reviewed SHA:** 326bf0a7ffa5296a81bcbe0bc5a112903bb68787
**Base SHA:** 40299c04cc1c7e9cc247a14cd1a4da89d6f58377

Scope: independent nonroot/exposure/secret-log source review, separate from lifecycle reviewer. Exact candidate was confirmed initially. Current HEAD later became 55563faa6aa886f97d50fe515625a250eefc9c39; source must be rechecked before combining verdicts.

PRE-TEST READINESS: candidate Dockerfile/entrypoint/supervisor/lock hashes match packet and baseline.before.json. restored.before.json and restored-extra.before.json instead bind supervisor f038efbc2d7803f6e831a70715a3733e101a910a5771c7982e39b7a00ef03dd3 versus candidate7223099a177998449eb0baff67f78a4ddc5f12094883a0806f89edd8a06e9b2c. restored-extra also binds entrypoint17d0bed7d27021d3a81ad900e5009aa4db8351e4fe599392573f67c634c9209a versus candidatef5a0611825aeb7d153013f8c19e1718d715f3b0155ffa16cd8e5add04be73bf2. Nonroot mutation receipts include that different supervisor hash. Same-byte restored-green provenance is not established. Explain canonical byte identity and bind the proof, or regenerate narrowly. No tests run because readiness failed; no incompatible receipts reused as proof.

Independent exact diff/current source inspection found no proven new exposure violation: UID/GID10001 follows root-owned source/dependency setup; frozen /opt/venv sits outside source; runtime sync and bytecode writes disabled; build-essential retained. DEPLOY prepares private data volume ownership. VNC commands preserve localhost and5901 viewonly; websockify6080/control and6081/view mapping matches unchanged Caddy permission gates. Prod app bind stays loopback by default. Supervisor diagnostics omit command/environment/OS exception text and uvicorn retains no-access-log. These findings do not establish actual runtime permissions or canary-log safety.

Clauses: C5/C7/C12; HO2/HO3/HO6/HO7/HO12; D1-D3/D6. Pending: Docker/Ubuntu build-host image execution, source immutability, actual UID/volume access, canary logs, viewers and Linux dev mount behavior, sibling lifecycle review and combined integration gates.

Accounting: checker skill loaded. Parent dispatch container-B.json assess exit0 reported; allocation90 active seconds/3000tokens plus sibling90/3000. Maker actual usage unknown. Review actual retrospective active time/tokens/cost unknown; budget debit90seconds/3000tokens retained, ratio unverified. No new phase authorized. No commits/merge/push or maker assets changed. Canonical worktree verdict write was denied by sandbox; this main-root handoff is not canonical and requires parent persistence plus actual machine-parser readback before a canonical verdict claim.

Closure: source blobs independently unchanged versus candidate. Additional finite parent authorization10seconds/500tokens; cumulative allocation190seconds/6500tokens including sibling. Helper assess BOOTSTRAP_REVIEW exit0; ratios remain unverified. Canonical first-field regex readback used because actual repository parser was not located in bounded scope.
