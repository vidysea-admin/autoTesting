# Brief — t206-g10-acceptance: T-206 Group 10 acceptance, end to end on Pathlynks (queue row `t206-g10-acceptance`, plan unit G10)

> **NOT DISPATCHABLE. No contract exists for this unit.** `ls D:/autoTesting/qa/contracts/` has no file for T-206 or "g10-acceptance", and `grep -n "T-206\|g10-acceptance\|G10" qa/contracts/*.md` finds only an unrelated line in `video-learning.md`.
> The acceptance text below comes from `.goal/goal.json`, `docs/plan.md` and `qa/QUEUE.md`, which are not contract criteria (they carry no ids, no verification class and no mutation). A checker has to author `qa/contracts/g10-acceptance.md` first (creation is human-approved under the checker SKILL "Contract maintenance"), and the unit is also blocked on every predecessor being built (section 10).
> Written 2026-10-11 by the readiness pass so the missing pieces are named in one place.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: **L**. Trigger: data writes. The unit builds no code, but its evidence runs execute against production Pathlynks under `ALLOW_WRITES` (`qa/gates/write-policy-tier.md`), send model calls on Pathlynks content, and send real email; the checker's job is to verify those, so the tier follows the actions, not the diff.
Dual check: no. No `security|auth|tenancy|prod-write <path:line>` trigger belongs to this unit: it writes no code, and the guards it exercises (`ui/routes_runs.py:75` approval gate, the Test-button route, the tracker write path) are each dual-checked in their own units.

## 2. Root and base

Root: `D:/autoTesting`. Base: current `master` = `4f8f5da100931ebda1b26836304bfbd38460764b` at the time of writing; it will be far from this when the unit is reachable (every Group 10 unit lands first). Re-read `git -C D:/autoTesting rev-parse master` at dispatch.
Branch: **no code branch**. Evidence only, so the unit lands as `qa/evidence/t206-*` and a manifest. Proposed branch `wave/t206-g10-acceptance` cut from the master tip that contains all predecessors, holding only `qa/evidence/t206-*` and `qa/manifests/t206-g10-acceptance.md`. Reason: D-074 says "Evidence only, no code"; a branch keeps the evidence commit reviewable and mergeable by the checker's PASS commit (D-080 item 1).

## 3. Acceptance criteria

**None exist as contract criteria. The unit is NOT dispatchable.**

What the repo says, verbatim, so the checker can turn it into criteria with ids:

- `.goal/goal.json` T-206 title: "G10 Group 10 acceptance: end to end on Pathlynks (docs/plan.md G10; O8-O15, O6)"; note: "Evidence only, no code (D-074). Depends on units G2-G9; the hosted check waits on T-203 deploy. | Acceptance: end to end on Pathlynks with redacted videos, reviews, bugs, a schedule tick, a Test press, reports on the website and by email for a user who ticked it; review recall against the oracle as numbers; persona walks (dev, admin) in a live browser; Ubuntu run once T-203 deploys."
- `docs/plan.md` G10 row: | G10 | `g10-acceptance` | T-206 (new row) | O8-O15, O6 | none; evidence only | end to end on Pathlynks: redacted videos, reviews, bugs, a schedule tick, a Test press, reports on the website and by email for a user who ticked it; review recall against the oracle as numbers; persona walks in a live browser; Ubuntu run once T-203 deploys | critical | required (dev, admin) | G2-G9; T-203 for the hosted check |
- `qa/QUEUE.md` row `t206-g10-acceptance`: "class: acceptance; criticality: critical ... files: none (evidence only: qa/evidence/t206-*) ... surface: live browser persona walks on Pathlynks: redacted videos, reviews, bugs, a schedule tick, a Test press, reports on the website and by email ... consumes: all Group 10 rows; qa/gates/t203-host-and-dns.md (the hosted and Ubuntu part stays gated); the live Tracker write is NOT part of it (gate open) ... after: t197-pointers-review; t198a-zip-drive-intake; t198b-dev-portal; t199a-bug-loop; t199b-sheet-sync-dryrun; t200-schedule; t201a-report-delivery; t201b-test-button; t203-local-deploy"
- Outcomes it serves: `docs/intent.md` / `docs/features/team-loop/intent.md` O8-O15 and O6 (the two-mode acceptance against a human). The hosted rows already exist in `qa/contracts/hosting.md` (verbatim):

- **HO34 — Team walkthrough (the T-203 done_check, SERVER-GATED).** A team member opens the server URL, signs up, an admin puts them in a
  group, they sign in, onboard a project, run a case from the queue, see the report; restart keeps the data; the Origin/Host guards
  are configured for the server origin; no secret is in the image (HO1). Checker Mode D, persona walks for **dev** and **tester**.
  `serves:` T-203 acceptance, D-072#7.
- **HO35 — Queue rehearsal on the server (SERVER-GATED).** Two projects started together run at once; a second request for the same
  project waits; changing the concurrency setting to 1 on the admin page makes the next start obey it. Evidence: screenshots and the
  queue listing. `serves:` D-072#6.
- **HO36 — Backup and restore drill (T-203 unit 5; SERVER-GATED).** `scripts/backup.sh` produces an encrypted snapshot of the data
  root; restoring it into a scratch directory and starting a second container on it lists the same projects, users and settings and
  opens a report; the snapshot is unreadable without its passphrase. `profiles/` live sessions are excluded unless Umesh says otherwise.
  The script itself passes `shellcheck`-style review and has no secret. `serves:` D-072#7.

Gaps in the repo's own wording that the contract author must settle (not guessed here): what "reports ... by email for a user who ticked it" counts as proof when SES is in sandbox mode (`unknown`); how "review recall against the oracle as numbers" is reported given the contract says numbers, not a pass threshold (`team-video-review.md` "Live acceptance"); and whether the qa/ ordering rule in D-081 item 2 (report first, no human list yet) means recall here is the oracle's 13 rows only, since T-136's independent human list is a separate OPEN gate (`qa/gates/t136-independent-human-list.md`).

## 4. What exists and what is missing

- **Contract: missing.** **Manifest, evidence, verdict: none.** `qa/evidence/t206-*` does not exist.
- **Predecessors, state on 2026-10-11 (nothing is on master):**

| Unit | Task | Where it stands |
|---|---|---|
| G1 `t205-g10-headroom` | T-205 | not built; no branch; `stages/run_launcher.py`, `ui/routers.py`, `store/team_store.py` MISSING |
| G2 `t197-pointers-review` | T-197 | `wave/g2-review-core` head `faa02786`, 20 files, cycle 1 after a cycle-0 CONTINUE-NEEDED, worktree clean, no PASS; conflict in `docs/MAP.md` |
| G3 `t198a-zip-drive-intake` | T-198 | `wave/g3-zip-core` head `ac7df298`, slice 1 (pure core), manifest only, no verdict; conflict in `schema/project.py` |
| G4 `t201a-report-delivery` | T-201 | not built; no branch |
| G5 `t200-schedule` | T-200 | `wave/g5-schedule-core` head `29ce74e8`, pure core slice 1 of 2, manifest `ready-for-check`, no verdict; conflict in `docs/MAP.md` |
| G6 `t199a-bug-loop` | T-199 | `wave/g6-bug-core` head `f8f59265`, TB1-TB6 only, verdict CONTINUE-NEEDED cycle 0 (all MET), TB7 not built; conflicts in `docs/MAP.md`, `schema/project.py` |
| G7 `t201b-test-button` | T-201 | not built (brief `qa/briefs/t201-test-button.md`) |
| G8 `t199b-sheet-sync-dryrun` | T-199 | not built (brief `qa/briefs/t199-bug-loop-dry-run.md`) |
| G9 `t198b-dev-portal` | T-198 | not built; no branch |
| T-203 | local deploy | `wave/t203-hosting` head `66f8b98c`, slice PASS (cycle 1), not landed, conflicts with master in `ui/routes_runs.py`, `docs/MAP.md`; no tick timer and no Settings route on the branch (QUEUE `t203-local-deploy`) |
| T-204 | team login | `wave/t204-auth-fix1` head `886936ab`, cycle 1 ready-for-check after FAIL; not landed |
| T-145 | Pathlynks live crawl and report | QUEUE row first in line; D-081 item 2 says the report is delivered first; state `unknown` here |

- **Goal task:** T-206 `deps: [T-205, T-197, T-198, T-199, T-200, T-201]`, `done_check = uv run python scripts/check_deliverable.py --exists qa/verdicts/t-206-g10-acceptance.md`, status pending. **AT-744** (`qa/issues.jsonl`, `fixed`, 2026-10-07): the pending T-197..T-201 tasks now carry cmd `done_check`s; **it does not cover T-205 or T-206** (its evidence names T-197..T-204 only), but both do carry `--exists` checks today. Same `--exists` weakness as the others: it passes on the existence of the verdict file, not its content. The QUEUE note for T-199 also says that task cannot close while the live-write gate is open, so T-206's `deps` can never all be `done` unless the checker amends T-199's done_check; raise it.
- **Evidence inputs that exist:** the three Navnit videos registered as pathlynks sources `src_e8fcdc4a15ce`, `src_44e2f1f6c64c`, `src_8540cc84081e` (D-067); the oracle `.work/pathlynks-dev-videos-oracle-2026-10-07.md` (13 rows, gitignored); `projects/pathlynks/` (flowspec and crawl are untracked in the working tree).

## 5. Files the builder will touch

No source file. Evidence only:

| Path | New / existing | Lines now | What |
|---|---|---|---|
| `qa/evidence/t206-*` (directory and files) | new | - | Screenshots, run ids, report links, outbox message, schedule slot records, recall numbers, persona-walk captures. Nothing here may hold a credential or student data. |
| `qa/manifests/t206-g10-acceptance.md` | new | - | The evidence manifest, `Status: ready-for-check`. |
| `projects/pathlynks/**` | existing, runtime | - | Written by the runs themselves (projects data root). Not hand-edited. |

Not touched: everything under `src/`, `tests/`, `qa/contracts/`, `qa/gates/`, `docs/DECISIONS.md`, `.goal/goal.json`.

## 6. Test scope

No pytest node. The verification is the checker's evidence commands, which cannot be named until a contract exists. Provisional, to be fixed by that contract: `uv run autotester doctor` and `uv run ruff check src tests scripts` on the integrated head (nothing new to lint), and the existing `scripts/check_deliverable.py --exists` done_check. `unknown` beyond that.

## 7. Reachable test cases

Scenarios the acceptance would exercise (from the goal note and plan row), happy path first. The split between what this machine can show and what must wait for the real host is in section 8.

1. Local, happy: a Developer signs in to the local server (T-204), uploads or links a redacted Navnit video, gets one source (T-198), runs `ingest run --pointers` and receives the summary and the 4-5 row confirm-list (T-197); recall is computed against the oracle's 13 rows and **reported as a number**, not a pass threshold.
2. Local: a Pathlynks run (T-145's report-first run, then a Test press) fails a case; the failure becomes one tracked bug; a re-test updates it; two consecutive evidenced passes close it (T-199a).
3. Local: the tracker binding shows its mapping preview and exact cells on a fake sheet; **no live write** (T-199b, D-081 item 7).
4. Local: a schedule tick enqueues once (T-200) on the local queue; a second tick for the same slot does not; a project with no credentials records `blocked_no_credentials` with zero requests at the transport.
5. Local: a Developer presses Test; the run is attributed to them; the report appears on the website and in "My reports"; with "Email me run reports" ticked exactly one message appears in the outbox (or one real message if the SES values are in `.env` and the checker allows it); with it unticked, none.
6. Local: an Admin walks the admin screens, access requests and a permission-denied path (persona walks dev and admin).
7. Gated: the Ubuntu server run, HTTPS, proxy, reboot supervision, backup drill and a team member opening the server URL (section 8).

## 8. Gate answers

- `qa/gates/t203-host-and-dns.md` (verbatim): "**Status:** OPEN for the real host and DNS; the local-machine part is answered." / "**Blocks:** only the hosted check of T-206 (G10 acceptance on Ubuntu). It does not block T-203's build." / "Umesh (2026-10-10): "krr denge but tu phle sabb run tho krr and for that time iss system mai host krkee use krr"." / "STILL OPEN: the real server host and the DNS name. No Answered line for this part. Owed by Umesh." / "Answered (local-machine part only): 2026-10-10 - host locally for now - D-081"
- D-081 item 4 (verbatim): "**T-203 host and DNS: later; host on this machine for now.** Umesh: "krr denge but tu phle sabb run tho krr and for that time iss system mai host krkee use krr". T-203 proceeds as a local deployment on the dev machine. The server host and DNS remain an open human input and gate only the hosted check of T-206."
- D-081 item 7 (verbatim): "**Pathlynks Tracker sheet: no live write now.** Umesh: "vo in future hogaa abhi nhi". T-199 builds and proves a dry run only; the first live write stays a HUMAN_GATE." `qa/gates/t199-first-live-write.md`: Status OPEN, no `Answered:` line. The live Tracker write is excluded from T-206 (QUEUE row).
- `qa/gates/d081-pathlynks-report-first.md` (verbatim): "Answered: 2026-10-10 - A (Pathlynks report first) - D-081"
- `qa/gates/d081-run-approvals.md` (verbatim): "Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081" (scope: T-145 and T-154 per-run rows; each run still writes its own signed row).
- `qa/gates/email-sender-credentials.md` (verbatim): "Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081"
- `qa/gates/drive-identity.md` (verbatim): "Answered: 2026-10-10 - A (existing gws CLI login) - D-081"
- `qa/gates/plan-approved-g10.md` (verbatim): "Approved -- Umesh, 2026-10-07 (chat), recorded as D-074." Its assumption: "Review needs a per-project, per-provider approval before a video goes to a model."
- `qa/gates/t136-independent-human-list.md`: Status OPEN, no `Answered:` line; it blocks T-136 / T-169, not T-206, but the recall number in scenario 1 is oracle-based only.
- `qa/gates/write-policy-tier.md`: "**`ALLOW_WRITES`, on every target, production included.**" (Answered by Umesh, 2026-09-27.)

## 9. UI surface and persona walk

UI surface: yes (every Group 10 screen is exercised end to end).
Persona walk: required (dev, admin). User types from `docs/features/team-loop/intent.md`: admin, subadmin, dev, tester; the plan G10 row and the goal note name **dev** and **admin**. Judged by the checker in a live browser (Mode D) against the local server; the hosted persona walks (HO34: dev and tester) wait for the real host.

## 10. Dependencies and conflicts

Must land first: every unit in the table in section 4 (QUEUE `after:` list: `t197-pointers-review; t198a-zip-drive-intake; t198b-dev-portal; t199a-bug-loop; t199b-sheet-sync-dryrun; t200-schedule; t201a-report-delivery; t201b-test-button; t203-local-deploy`), plus `t205-g10-headroom`, `t204-team-login`, `land-t203-hosting`, and a Pathlynks run to test against (`t145-pathlynks-live-report`).
Shared files: none (the unit writes no source file). Its only shared surface is `projects/pathlynks/` at runtime: the T-145 crawl, the T-154 adversarial pass and this unit all run against the same Pathlynks project, so the **runs must be serialised** and each run mints its own signed `RunApproval` (D-081 item 3). Owner of that serialisation: the coordinating maker, one orchestrator at a time (D-080 item 2).

| Shared surface | Used by | Owner |
|---|---|---|
| `projects/pathlynks/` data root (runs, flowspec, bugs, schedule records) | t145, t154, t199, t200, t201, t206 | one run at a time; the coordinating maker |
| local server port and the single run slot | t203-local-deploy, t206, any checker Mode D | whoever started the server; kill only own PIDs |
| `docs/MAP.md` | n/a (no source change) | n/a |

## 11. Budget and process rules

Check budget: **45 min** (Tier L) for the checker's verification of the evidence. The wall time of the live runs themselves is separate and `unknown` (T-145's bounded crawl and each Pathlynks run are bounded by their own `RunApproval`).
- Edit in place. Name the exact file and function before changing existing code. No `*_v2.py` / `*_new.py`, no second copy of a function (CLAUDE.md design rules). A regression is reverted to the last good git state, never stacked with a new fix.
- Design rules (enforced by `uv run autotester doctor`): file <= 300 lines, function <= 50 lines, module docstring states one job, every domain shape is a Pydantic model in `schema/` with `extra="forbid"`, prompts are files, all model calls go through `providers.base.Provider`.
- Credentials: values live only in the gitignored repo-root `.env`; code and tests name keys as `SecretRef`, never values. No secret in a log, plan, page, outbox file or error string (`Redactor.scrub`).
- The builder runs NO full suite (`uv run pytest` bare). It runs only the test files named in section 6, `uv run ruff check` on the files it changed, and `uv run autotester doctor`. No CLI `-q` on pytest (AT-503). The one full suite is run once, by the checker, at the integration head (G6 verdict, `wave/g6-bug-core:qa/verdicts/g6-bug-core.md`, "Full-suite status").
- Falsification (mutation) only in a throwaway copy outside the repo (for example `git archive` into the scratchpad, unique directory name per unit). Never perturb the bound worktree.
- Kill only PIDs the builder itself started (record each PID when launching; no `taskkill /IM`, no kill by port or by name). Other agents run servers and browsers in parallel on this machine.
- No `cd X && cmd`; use `git -C <dir>`, absolute paths or the tool's working directory.
- Never edit `qa/contracts/`, `docs/DECISIONS.md`, `qa/gates/`, `.claude/hooks/*`, `qa/hooks/*`, `.claude/settings.json`. Contract questions go verbatim to `qa/feedback-inbox.md`. Only `/checker` can PASS; the maker ends at `Status: ready-for-check` with `Fix cycle: N` in `qa/manifests/<slug>.md`.
- Commit before asking for a verdict (`qa/gates/commit-before-verdict.md`); `docs/MAP.md` is regenerated with `uv run autotester map` as the last step, not hand-edited (it conflicts across sibling branches, so regenerate at merge).
- No git push by the builder; the checker pushes `origin master` on PASS (CLAUDE.md "Push on PASS", D-007).
- Extra for this unit: every live run is bounded by its signed `RunApproval` (D-081 item 3); real email only from the AutoTester-prefixed `.env` keys, never printed; no redacted-video bytes leave the machine except to the already-approved model provider; no live Tracker write; no student data or credential in `qa/evidence/t206-*`; the checker, not the builder, grades every claim (`/outcome-grader` or `/checker`, never self-attested).
