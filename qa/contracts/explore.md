# Contract — EXPLORE stage (the bounded BFS crawl)

**Covers:** goal tasks T-140 (B1 observation primitives), T-141 (B2 identity + crawl schema),
T-142 (B4 safety layer), T-143 (B3 the crawl stage itself).
**Owner:** /checker. **Criticality:** HIGH — this is the only code in the repo that decides on
its own what to click, and it does so in a real, usually logged-in browser against a production
product. Every other stage replays what a human authored.
**Depends on:** `core-invariants.md` (all), `browser-and-secrets.md` (B5-B9),
`execute.md` **E5 — explicitly preserved, never amended by this contract** (see X1).
**Authorized by:** D-015 (the stage and its file layout) and D-016 (the safety matrix).

## Purpose

Discover a product's screens without being told they exist: open `base_url`, enumerate the
interactive controls, click the safe ones, fingerprint wherever that lands, and repeat
breadth-first until a bound stops it — producing a screen graph on disk plus the problems noticed
on the way.

`execute.md` E5 says `run_case` "performs exactly the actions in `case.steps` — it never invents
an extra click, submit, or navigation." A crawler is by definition the invention of clicks. Rather
than weaken E5, D-015 puts the invention in one place, under this contract, with brakes. **E5
remains the rule for `run_case`; this contract is the single, bounded exception, and it is an
exception about *clicking*, never about *typing* (X10).**

The prior attempt at this failed five specific ways — URL-only identity (every SPA state
invisible), an LLM-text stop condition that never fired, `beforeunload` dialog traps, analytics
noise reported as product bugs, and "coverage" that only meant the script ran. X3, X12, X8, X9
and the B5 coverage work exist against exactly those.

## Criteria

### X1 — E5 stays intact; this is the only stage that invents an action
`stages/explore.py` is the sole module permitted to originate a click or navigation the human did
not author. `run_case` is unchanged in behaviour and its contract is unamended. The explorer calls
`run_case` for exactly one thing: the human-authored login bootstrap case.
**Verify:** `execute.py` and `execute.md` are absent from the unit's diff; `grep -n run_case
src/autotester/stages/explore.py` shows one call site, inside `_bootstrap_login`.

### X2 — Every browser touch goes through `browser/`
No `playwright` import and no `.page.` access anywhere in `src/autotester/` outside `browser/`.
The explorer composes `BrowserSession` methods; it never reaches past them.
**Verify:** `tests/test_actuator_chokepoint.py`, and the grep above returning nothing.

### X3 — Screen identity is structural
A `ScreenNode` id is a pure function of `(templated URL path, structural signature of the visible
non-row interactive elements)` — never URL alone, never a model's free-text description. Two list
pages differing only in row data are ONE screen; two states at one URL offering different controls
are TWO. The same page always yields the same id, whenever it is visited. One recorded
exception (2026-10-29): pressing a button/switch named collapse/expand/toggle/show/hide + sidebar /
side nav / navigation menu at an unchanged `url_template` is recorded SAME_SCREEN, not a new node
(`screen_identity.same_screen`); ids and `structural_signature` are unchanged.
**Verify:** `/students/1/` and `/students/2/` collapse to a single `/students/{id}` node, and the
same-URL filter toggle produces a second `/` node — both against a real browser.

### X4 — Bounds fire, and name themselves
`max_screens`, `max_actions`, `wall_clock_s` and `max_depth` each actually end the crawl, and the
one that fired is named in `Crawl.stop_reason`. Bounds are checked before every node and before
every action, so a bound cannot be overshot by a whole node. A crawl always terminates and always
records why.
**Verify:** one test per bound, wall-clock driven by an injected clock rather than real sleeping.

### X5 — `write_policy` is enforced — the D-016 matrix
The first runtime enforcement of `Project.write_policy`, as an INNER guard inside Umesh's outer
boundary (the test account's own permissions):

| policy | destructive-name deny-list | form submits | typing |
|---|---|---|---|
| `READ_ONLY` | ON | never clicked | never |
| `TEST_ACCOUNT` | ON | allowed | allowed (X10-b only: synthetic values, gated run) |
| `ALLOW_WRITES` | OFF | allowed | allowed (X10-b only: synthetic values, gated run) |

**Verify:** against a real browser, a Delete-labelled control is never clicked under `READ_ONLY`
and IS clicked under `ALLOW_WRITES` — the same fixture, both directions. The typing column is
X10-b's, not D-016's original: it widens only under the four X10-b conditions and is otherwise
"never", exactly as the base row read before the amendment.

### X6 — Session-ending controls are never clicked, at any policy
Logout/sign-out is refused under every `write_policy`, including `ALLOW_WRITES`, and the refusal
is checked against the module-level baseline, not against an overridable policy field — no
configuration can narrow it, only widen it (AT-092). An unnamed non-link control is skipped and
counted, never clicked blind (D-004: a rule decides only where it is certain).

**Known and accepted limitation (D-016, not a defect to re-raise):** the deny-list matches on a
control's *name*. A destructive control the list does not name IS clicked — verified live: a
button relabelled "Obliterate" was clicked and reached the delete sentinel. D-016 accepts this
deliberately, because the real boundary is what the test account is permitted to do. Widening the
pattern set is maintenance, not a contract violation.

**Known OPEN gap against this criterion:** `AT-093` — `Log-Out`, `LOG_OUT`, `Log.Out` and
`Sign-Out` are NOT denied, because the never-click patterns tolerate only `\s`/`\w` between the
two words. Re-verified live at T-143. X6 is therefore **not** clean today for
punctuation-separated labels; this must close before the explorer is pointed at a real product
(T-145).

### X7 — The host is re-checked after EVERY action
Not only on `goto`. A click that navigates off-domain is caught by re-checking
`session.current_url()` after the action completes — the case plain destination-checking on
navigation never saw. A refusal produces an `OFF_DOMAIN_REFUSED` edge plus a `NAVIGATION` issue,
and then recovery (back → the node's own URL → `base_url`), never a silent continue. No node is
ever created from an off-domain page.

### X8 — Dialog circuit breaker
Every JS dialog is recorded. `beforeunload` is accepted; every other dialog is dismissed. More
than `dialog_repeat_limit` dialogs on one node aborts that node — and the crawl continues with the
rest of the frontier rather than hanging. The prior attempt was permanently trapped here.

### X9 — Third-party noise is not a product issue
A failed request becomes a `CrawlIssue` only when the host is first-party. Declared analytics and
tracker hosts are dropped entirely; any other third party is tallied as noise and never reported
as a bug. A first-party 404 IS an issue.

### X10 — Nothing is typed, except synthetic values under X10-b
**X10 (base, unchanged in force everywhere else):** the explorer never calls `fill`,
`select_option`, or `upload`. It does not invent form data, ever. The only typing that happens on
a crawl is the human-authored login case executed through `run_case`. This is the hard half of
X1's exception: the explorer may invent a *click*, never a *value*.
**Verify:** `grep -n 'fill\|select_option\|upload' src/autotester/stages/explore*.py` returns
nothing outside `explore_typing.py` and the FILL/SELECT handling named below.

**X10-b (the D-029 exception, narrow and four-conditioned):** the typing pre-pass
`stages/explore_typing.py::type_form` may additionally type into post-login form fields ONLY
when ALL FOUR hold, each alone being a refusal:
1. **policy** — the run's `SafetyPolicy.write_policy` is `TEST_ACCOUNT` or `ALLOW_WRITES` AND
   `SafetyPolicy.synthetic_typing` is explicitly `True` for that run (`typing_allowed` is the
   one boolean; default OFF keeps X10 exactly as it was for every existing caller);
2. **synthetic values only** — every value comes from `stages/synthetic_values.py`, a fixed,
   deterministic, non-PII generator keyed on the field's own name/selector (no provider, no
   clock, no randomness — X12's determinism extends to what is typed);
3. **non-production target** — the run's `RunApproval` names a dev-environment target
   (`production: false`), per the live-crawl gate answer (Pathlynks dev, 2026-09-21);
4. **non-destructive** — password-named fields are never typed (`typing_target_allowed`), an
   upload is never performed, and the standing never-click (X6) and deny-list (X5) guards are
   unchanged: typing widens nothing else.

Typed actions are first-class crawl actions: each records an edge (`FILL`/`SELECT`,
`SAME_SCREEN` or `NAVIGATED`) and counts toward `max_actions` and the per-node cap (X4 binds
typing exactly as it binds clicks). The click loop still runs after the pre-pass, so a filled
form's submit is exercised under the same X5 matrix as before. The verify grep's exception is
exactly `explore_typing.py` — no other module may import or re-implement the typing behaviour
(one concept, one place).

### X11 — Artifacts are incremental, human-readable, and survive a crash
Nodes, edges and issues are JSONL and the crawl envelope and frontier are JSON, under
`projects/<slug>/crawl/<crawl_id>/`. They are written *as the crawl proceeds*, not assembled at
the end, so a crawl killed partway leaves a graph that still loads (C6). A node's final status
must reach disk — `add_node` is idempotent, so a status transition requires `update_node`;
without it a fully explored graph records every node as `queued` forever.

**Scope of the crash guarantee (honest limit):** append-only writes never rewrite an earlier line
and whole-file writes are atomic (tmp + `os.replace`), so a kill *between* writes is safe and
provably leaves a loadable partial graph. A kill *during* a single line's append is NOT covered:
`read_jsonl` raises on a malformed row rather than skipping it, so a torn final line would make
the file unloadable. Claim only what the ordering supports.

### X12 — The crawl is DOM-driven and deterministic; a model may ORDER controls, never choose or perform one
**Default (guidance off, the shipped default): `run_crawl` takes no provider at all.** No stop
condition, no action choice, and no safety decision depends on model output — a crawl completes
with `provider=None`, byte-identical to the pre-D-118 crawl. **Amended 2026-10-29 (D-118):** when
and only when per-project guidance is switched on (`qa/contracts/crawl-guidance.md`, G1-G12), an
injected `providers.base.Provider` may be handed ONE screen's code-built, numbered candidate
controls and return a RANKING of them. The model never adds a control, never performs one, never
names a selector, URL, value or stop, and never overrides a refusal: the deny-list, destructive-last
(D-040), `link_is_safe`, `allowed_domains`, the signed `RunApproval` check, every `CrawlBounds`
bound, the X7 host re-check and the X10/X10-b typing gate run unchanged on every control the model
ordered. Any model failure leaves the code's own order in force (G4). Screen identity (X3) stays
structural and never reads a model answer. A model's other permitted role is unchanged: *naming* an
already-discovered screen for human readability. **Still rejected, not revived:** vision-guided
action choice (images) — D-015 rejected it and D-118 keeps it rejected; the model sees redacted
text only (G3). This is what keeps the crawl reproducible and its failures debuggable, and why the
whole stage, guidance included, can be proven without a credential or an API key (a fake `Provider`).
**Falsifiable:** with guidance off, `run_crawl` is called with no provider and `nodes.jsonl` /
`edges.jsonl` for the fixture site are byte-identical to the pre-amendment baseline; with a fake
provider returning garbage, the crawl's node set, refused/denied set and stop reason equal the
guidance-off run's (G1/G4).

### X13 — A crawl may propose screens, never approve them
`stages/explore_merge.py::merge_screens` **never rewrites an existing `Screen`** — a human-named
or human-reviewed screen survives a merge byte-identically. When the merge adds anything, the
spec's `Review` is reset to `DRAFT` and `version` is bumped, so a `FlowSpec` can never carry
`approved` over screens no human has seen. When it adds nothing the spec is returned untouched:
re-merging the same crawl produces no version bump, no second review reset and no duplicate
conflict, and the persisted `flowspec.json` is byte-identical.
**Verify (both directions, and the gate must be load-bearing):** set a spec to `APPROVED`, merge a
crawl with one new screen, confirm `DRAFT`; merge the same crawl twice and diff the persisted file
byte-for-byte; **and sabotage the `Review(...)` reset — at least one test must fail.** A reset no
test defends is a decorative human gate.

### X14 — A disagreement between SOURCES is kept, never resolved
When a crawled screen claims a `url_pattern` an already-known screen claims under a different
name, **both screens survive** and a `Conflict` records both claims with both `source_ref`s. The
merge never picks a winner and never overwrites: silently resolving is how a product map stops
matching the product. The same conflict is not recorded twice on a re-merge.

**Deliberate exception, judged and UPHELD by the checker (2026-09-08), and WIDENED from "the same
crawl" to "both claims are structural" (2026-09-08, at103-conflict-scope):** two screens that both
carry a *structural* identity and share a `url_pattern` are **not** a conflict, however many crawls
found them. X3 requires two states at one URL
offering different controls to be TWO screens; a single source correctly modelling an SPA is not
two sources disagreeing, and raising a `Conflict` there would file a false one on every SPA in
every product. Verified live on the fixture site: 7 screens across 6 url patterns, 0 conflicts.
A `Conflict` means *sources disagree*, not *patterns collide* — this criterion pins that meaning.

Only a claim with **no** structural identity — a human's or an ingested video's screen, which
asserts a URL and nothing more — can be contradicted by a crawl. **AT-103 is CLOSED by this
scoping** (`_is_structural` / `disagreement`, `stages/explore_merge.py`).

**One residual of the current rule, tracked rather than written out of it** (not a violation of
this criterion as written; a ledger issue to be closed by a later unit):
**AT-109** — the price of scoping on identity: a **genuine product change** (a later crawl finding
a structurally different screen at a pattern an earlier crawl claimed) is now silently two screens
and files no `Conflict`, so the stale screen is kept forever with nothing marking it stale. That
trade is deliberate — at this layer a product change and an SPA re-crawl are the same shape, and
the alternative fires a false conflict on every SPA state on every re-crawl — and it costs no data
(both screens survive, `Review` still resets to DRAFT). The remedy is a *different* mechanism,
last-seen/staleness on `Screen`, not a re-narrowing of the exemption.

**AT-102 CLOSED** (unit `at102-merge-rediscovery-dedup`, commit `c29d322`, verified by /checker
2026-09-11) — a non-structural screen re-discovered at a known `url_pattern` under the SAME name
now merges instead of duplicating (`_is_rediscovery`, `stages/explore_merge.py`); see the
amendment log entry below.

### X15 — `Screen.url_pattern` is a host-less path, not the node's browsing template
`ScreenNode.url_template` carries a host (it is a browsing identity); `Screen.url_pattern` is a
path pattern, because that is what `stages/coverage.py` and `stages/ingest.py` compare against.
`screen_from` therefore derives it as `url_template(node.url_example, keep_host=False)` and never
copies `node.url_template`. Copying the template verbatim would make every coverage diff miss.
**Verify:** every merged `url_pattern` starts with `/`, and `/students/1` and `/students/2`
collapse to one `/students/{id}` screen.

### X16 — The crawl report shows what was REFUSED and why it STOPPED
A bounded crawl reported as only what it found reads as full coverage of the product. Both the
crawl page and the workbook therefore give `Crawl.stop_reason` equal billing with the headline
counts, and both list **every** `DENIED_POLICY` / `SKIPPED_UNNAMED` / `OFF_DOMAIN_REFUSED` edge
with its `reason` and the control it names. Third-party noise counted under X9 is recorded in the
workbook's own `Noise` sheet — "we ignored it" stays auditable — and never appears as a
`CrawlIssue`. The workbook is
`Summary / Screens / Edges / Denied & Skipped / Issues / Tool failures / Noise`.
**Known gap, tracked not waived: AT-105** — the noise counts reach the workbook only; the crawl
page does not surface them.

**A failure of the CRAWLER is not a finding about the PRODUCT.** When the tool itself cannot record
something — a screenshot it could not take — it files an `IssueKind.EVIDENCE` issue rather than
inflating the product's issue list, which is X9's principle applied one step closer to home
(AT-114, upheld by /checker 2026-09-08). **The separation must hold in the NUMBERS, not only in
the enum:** `Crawl.tool_failures` counts EVIDENCE issues apart from `Crawl.issues`, and every
surface a human reads keeps them apart — the workbook's `Issues found (in the product)` /
`Tool failures (the crawler's own)` summary rows and its own `Tool failures` sheet, the crawls
table's own column, and the crawl page's own stat and card. They are counted apart and reported,
never dropped: each one is a hole in the evidence the rest of the report is built on, so the same
"we did not report it stays auditable" rule that governs `Noise` governs them.
**AT-120 CLOSED** (unit `at120-evidence-not-product-issues`, commit `bc29b34`, verified by
/checker 2026-09-08 — the same probe that measured `issues = 5` at `6e98487` now measures
`issues = 1, tool_failures = 4`). **X16 is clean for tool failures.**
**The two residual display gaps are now CLOSED too** (unit `at121-at122-crawl-count-surfaces`,
commit `6c653fd`, verified by /checker 2026-09-08): **AT-121** — the crawls table rendered a known
zero with the `—` it uses for unknown; the row now reads `<td>0</td><td>0</td>` for the two count
cells while `stop_reason` and `started_at` keep the `—` for genuine unknowns, and no numeric field
anywhere in `src/` still renders through the sentinel. **AT-122** — the `autotester crawl` CLI
one-liner (extracted as `cli_crawl.echo_crawl_summary` so it is testable) now carries
`{tool_failures} tool failures`, so a headless or CI run, whose entire report is that one line, is
told about holes in its own evidence. **The counted-apart rule now holds on every surface a human
reads: the CLI line, the crawls table, the crawl-page stat, the workbook summary and its own sheet,
and `crawl.json`.** New residuals, tracked not waived, neither a violation as written: **AT-123**
(the CLI line is the one surface that does not guard `stop_reason`, printing `None`; unreachable
through `explore_cmd` today) and **AT-124** (a crawl artifact written before `tool_failures` existed
loads with the default `0` and is displayed as a measured zero — the same property `issues` and
`denied` have always had; the remedy is a schema change, not a display change).

### X17 — A crawl started from the product UI logs in exactly as the CLI can
A crawl that cannot pass the login wall maps one screen of a product and calls it the product. The
CLI's `--login-case` (`cli_crawl.py:59`, passed at `:89`) is today the only door past it; the UI
Explore route (`ui/routes_crawls.py:226-227`) calls `run_crawl` with no `login_case`, and
`Project` has no field naming one, so **no crawl started from the UI can ever reach a post-login
screen** (AT-457). This criterion requires:

- **(a) One declared source.** A project names its login case in exactly one place on disk (a
  `Project` field or one equivalent declaration — not a UI-only default, not a second copy per
  entry point). The CLI flag may override it for one run; it may not be a second, drifting default.
- **(b) The UI uses it.** When a login case is declared, the UI Explore route passes that case to
  `run_crawl`, and the persisted `crawl.json` carries `login_case_id` equal to the declared case
  id. When none is declared, the crawl form says so on the page *before* the crawl starts — never
  silently runs an anonymous crawl as if it were the whole product.
- **(c) Nothing else widens.** Consent (`require_consent`), `write_policy` (X5), session-ending
  refusals (X6) and X10 (nothing typed except the human-authored login case through `run_case`) are
  unchanged. This criterion routes an existing, already-consented login through a second door; it
  does not authorize a new outward action, and it does not relax `READ_ONLY`'s form-submit denial
  for anything after login (that is D-016's per-project `TEST_ACCOUNT` choice, a human decision).

**Verify (load-bearing, both directions):** against a real browser on a fixture site whose content
sits behind a login form, a crawl POSTed through the UI route with a declared login case reaches at
least one screen whose `url_template` is not the login page's, and `crawl.json.login_case_id` is set;
the same POST with the `login_case=` argument removed in a scratch copy must fail that test. A crawl
with no declared case renders the "no login case declared" notice on the form. Checker Mode D drives
the Explore form itself.

### X18 — A crawl that never gets past the login wall never reads as COMPLETED
`_terminal_status` (`stages/explore.py:200-211`) returns `COMPLETED` whenever the frontier empties
and at least one action was performed. AT-242's `BLOCKED_NO_ACTIONS` covers only `actions_used ==
0`; a login page with one clickable link ("Forgot password", a footer link) that is followed and
leads back returns `COMPLETED` while the product behind the wall was never seen (AT-458). On disk,
all three crawls of `saucedemo` and `checkerdemo` read `status=completed` with 1 screen, 0 actions
and 3 denied (they predate AT-242's `2bb3270`, and are still displayed as `completed`).

- **(a)** With a declared login case, a reached node counts as *"still the login screen"* when its
  `url_template` equals the login case's own template AND EITHER its `signature` equals the
  signature OBSERVED on the login page before the case typed, OR — when that comparison cannot
  decide, because the signature moved (a sticky wrong-password banner, AT-467) or was never
  observed at all (AT-474) — every FILL step target of the login case is present as an element's
  `selector` on that node. A node missing at least one FILL-target selector is never caught by the
  fallback; signature-only comparison stays in force for it (AT-462's single-page-app dashboard
  control). A crawl that reaches no screen other than what counts as the login screen ends
  `LOGIN_FAILED` (or a named equivalent), never `COMPLETED`.

  When the login page's signature could not be observed, `stop_reason` carries an appended
  qualifier naming why (`-- login not judged: could not observe the login page (<Type>: <msg>)`)
  and an `IssueKind.EVIDENCE` `CrawlIssue` is filed (so `tool_failures` counts it) — deliberately
  even when the crawl otherwise resolves conclusively that every reached node is NOT the login
  screen via a plain `url_template` mismatch alone, which needs no signature at all. This is an
  intentional, checker-accepted trade (2026-09-17): never let a precheck failure go unmentioned, at
  the cost of an occasional qualifier appended to an otherwise-clean `COMPLETED`. Pinned live by
  `test_a_login_page_that_cannot_be_observed_is_not_an_unqualified_success`. This qualifier and the
  bound suffix below are mutually exclusive: both are computed in `terminal_status`, but the
  `LOGIN_FAILED`-via-fallback and `LOGIN_WALL` branches return before the qualifier's check is
  reached, so the two never combine in one `stop_reason` (verified by reading `terminal_status`'s
  control flow, not merely asserted).

  **ISS-x18a-1 CLOSED as filed** by /checker at unit `at480-489-wall-bound-and-fill-fallback`
  (cycle 1, commit `44d2547`, verdict `qa/verdicts/at480-489-wall-bound-and-fill-fallback.md`). The
  fallback now ALSO requires the login case's own submit control — the selector of its last CLICK
  step (`login_submit_selector`) — to be present on the node, alongside every FILL target; a case
  with no CLICK step never fires the fallback at all. This closes the case the issue was filed
  against (a node exposing every FILL-target selector alone, with no submit control, is never
  misclassified — verified live:
  `test_a_dashboard_with_a_matching_field_but_no_sign_in_button_is_not_login_failed` reads
  `COMPLETED`, and the checker's own falsifying edit — dropping the submit-selector clause,
  restoring the pre-AT-489 body — reproduces the original `LOGIN_FAILED` misclassification in an
  isolated copy). **Narrower residual, disclosed rather than assumed away:** a screen that
  coincidentally reuses BOTH every FILL-target selector AND the login form's own submit-control
  selector is still classified `LOGIN_FAILED` by design
  (`test_a_screen_with_the_submit_control_and_every_fill_target_is_still_login_failed` pins this
  as a control, not a defect) — the fallback is no longer distinguishable from a real repeated
  login screen by selector alone once both coincide, and D-004 (a rule decides only where certain)
  favours the narrower false-failure over reopening the AT-467 gap. This residual is structurally
  smaller than what ISS-x18a-1 named (it now needs a coincidental match on the submit control too,
  not fields alone) and is accepted, not tracked as a new open issue.
- **(b)** With no declared login case, a crawl whose every reached screen carries a form submit that
  was refused under policy and which has **no `NAVIGATED` edge to a screen offering a different
  structural signature from the seed** ends in a distinct non-success status naming the wall in
  `stop_reason`, **regardless of `actions_used`**.
- **(c)** That status reaches every surface X16 lists (crawl page, crawls table, CLI line, workbook
  Summary, `crawl.json`) with non-success tone — `_STOP_TONE` must not colour it positive.
- **(d)** A legacy `crawl.json` whose persisted status is `completed` but whose counts are
  `actions == 0 and denied > 0` is not displayed as a success (the AT-124 legacy-artifact shape, for
  status rather than counts).
- **(e)** A crawl bound (`max_screens`/`max_actions`/`wall_clock_s`) firing WHILE the crawl is also
  stuck at (a)'s login wall or (b)'s wall never silences X4: the fired bound is still named in
  `stop_reason` via an appended clause `-- the <bound> bound fired before every control was tried`,
  and the wall sentence's "no link led anywhere else" claim is dropped in that case — a bound can
  leave controls genuinely untried, and the sentence must not claim otherwise. A crawl whose
  frontier genuinely emptied (no bound fired) keeps today's sentence byte-for-byte; the two never
  combine, because `stop_reason` at the point `terminal_status` is called is always either
  `"frontier empty"` (`completed=True`, no suffix) or one of the three bound names
  (`completed=False`), never an unrelated value — `explore.py`'s only caller sets `completed`
  from `rt.stop_reason == "frontier empty"` and passes that same string through, so a "spurious
  suffix on a naturally-completed wall" is not reachable through the shipped call path (verified
  by checker inspection of `explore.py:298-300`, the single production call site, and live-browser
  reproduction: `qa/evidence/browser-at480-489-wall-bound-and-fill-fallback-2026-09-17-checker/report.json`).
  **Known structural gap, tracked not waived:** `max_screens` cannot itself be the bound named on a
  `LOGIN_WALL` crawl — `_enqueue` (`stages/explore_node.py:104-115`) only declines a new node once
  `screens_found` has ALREADY reached the cap from an earlier enqueue in the same crawl step, so the
  node whose own discovery pushed the count to the cap (and any node still queued behind it) is left
  `queued`, never visited, and therefore never carries its own `DENIED_POLICY` edge; `is_login_wall`
  requires every discovered node to be walled, so it returns `False` the instant `max_screens` is the
  bound that fires. Such a crawl correctly reads `STOPPED_BOUND`/`max_screens` instead, which is
  already X4-honest on its own — not a false claim, the honest boundary of this mechanism. Pinned
  live by `test_max_screens_on_a_would_be_wall_correctly_stays_a_plain_bound`.

**Verify:** a fixture login page with one followable same-domain link, crawled with no login case →
status ≠ `completed` with `actions_used ≥ 1`; sabotage `_terminal_status` back to the pre-X18 body in a
scratch copy → that test fails. The three on-disk legacy crawls render non-success on the crawls
table (Mode D). **(e)'s bound suffix:** one test per bound (`max_actions`, `wall_clock_s`) on a
walled page names the bound and drops the untried-links claim; a control pins the unbounded wall
sentence unchanged; `max_screens`'s structural non-co-occurrence is pinned live, not sabotaged (Mode
D, checker-driven, confirms the same behaviour against a real browser and a real UI page render, not
only the pure-function tests).

## No-fire list (do not raise these as findings)

- Filling forms with synthetic data, and vision-guided action choice — both rejected by D-015/X10.
  *(Updated 2026-09-21: synthetic typing is now BUILT as X10-b under D-029's four conditions —
  raising "synthetic form data" as a finding is wrong only when the run lacks one of the four
  X10-b conditions; the D-015 vision-guided-action-choice rejection is unchanged.)*
- Resuming an interrupted crawl, parallel tabs, and CI triggers — not built, not claimed.
- `EvidenceKind.TRACE`.
- Auto-generating cases from crawl screens — that is `expand.py`, after human review.
- Auth bypass or 2FA automation; a wildcard for `allowed_domains`.
- Crawl → FlowSpec merge, coverage from observed screens, and the crawl report (Excel + UI page) —
  that is B5/T-144, explicitly out of T-143's scope.
- The name-based deny-list being incomplete *in principle* (X6's accepted limitation, D-016). A
  specific missing pattern class is a normal issue; the design choice is settled.
- The 8s settle default in `session.settle` being different from the crawl's 2500ms — deliberate
  and documented: a graded case performs a handful of actions, a crawl performs hundreds.
- Auto-generating cases from crawled screens (that is `expand.py`, after human review); naming
  screens with a model (`prompts/explore_name_screen_v1.md` is designed for and deliberately NOT
  built — X12 keeps the crawl provider-free); background/async crawling from the UI (synchronous,
  the same trade-off `routes_runs.py` already makes); resuming an interrupted crawl; merging
  crawl-discovered *flows* (only screens are merged); editing a merged screen from the crawl page.

## Amendment log (append-only; git history is the version)

- 2026-09-07 · init · contract created at T-143 by /checker, from the criteria the maker filed in
  `qa/feedback-inbox.md` (2026-09-07) — the maker never writes a contract. Changes made to the
  maker's proposed X1-X11 while authoring: **added X12** (DOM-driven/deterministic; a model may
  name a screen but never choose an action), which the maker's list omitted although D-015
  authorizes "explore.md X1-X12" and rejects vision-guided crawling by name — restoring the count
  the decision names; **tightened X6** with the live-verified "Obliterate" limitation (accepted
  per D-016) and with AT-093 recorded as an OPEN gap rather than letting the criterion read clean;
  **tightened X11** to state the exact scope of the crash guarantee, since `read_jsonl` raises on
  a torn row and the append-only ordering only supports the between-writes claim; added the
  settle-ms and deny-list-in-principle rows to the no-fire list so neither is re-litigated.
  `execute.md` E5 is untouched and stays the rule for `run_case`.

- 2026-09-08 · routine · **X13-X16 added** at T-144 (Track B5) by /checker, from the criteria the
  maker filed in `qa/feedback-inbox.md` (2026-09-08). Authorized by D-015, whose
  `Changes-authorized` names `qa/contracts/explore.md` and `coverage.md V1 after B5`. Adds
  criteria, softens none; X1-X12 are byte-unchanged and were re-verified in the same check
  (`scripts/explore_proof.py` 10/10; `run_case` still one call site in `_bootstrap_login`; no
  `playwright` import or `.page.` access outside `browser/`; `grep fill|select_option|upload`
  over every module this unit added returns nothing). Changes made to the maker's proposed
  wording while authoring: **X13 gained a mandatory sabotage clause** — the DRAFT reset must be
  defended by a test that fails when the reset is removed, because a human gate no test defends is
  decorative (executed: `status=ReviewStatus.DRAFT` → `status=spec.review.status` fails
  `test_new_screens_are_added_and_review_resets_to_draft`); **X14's exception was judged on its
  merits and UPHELD**, and re-stated as *sources disagree, not patterns collide*, with the two
  residuals of the current implementation (AT-102 same-name silent duplicate, AT-103 cross-crawl
  false conflict) recorded in the criterion rather than left implicit; **X16 was tightened** to say
  where noise is auditable and to record AT-105 (the crawl page omits it) as a tracked gap rather
  than letting the criterion read clean. The maker's offered no-fire list is folded in above.

- 2026-09-08 · routine · **X14's exception re-scoped** from "the same crawl" to "both claims carry
  a structural identity", by /checker at unit `at103-conflict-scope` (commit `ef881b9`, verdict
  `qa/verdicts/at103-conflict-scope.md`). This is what X14's own AT-103 residual paragraph
  prescribed on 2026-09-07 — *"the exemption is right; its scope is one crawl rather than one
  source"* — so it records a change the criterion asked for rather than softening one to pass an
  artifact. Verified by the checker against the pre-fix module (`git show a195fbf:…`) run beside
  HEAD: the same SPA pair merged as crawl 1 then crawl 2 gives `conflicts=1` before and
  `conflicts=0` after, `screens=2` both sides. X14's core is unchanged and re-proven by sabotage —
  suppressing conflicts wholesale (`_is_structural → return True`) fails three tests, including
  `test_a_human_authored_claim_is_still_contradicted_by_a_crawl`. **AT-103 removed from the
  residual list (closed); AT-109 added** — the cost of the new scope, stated inside the criterion
  rather than left implicit. No criterion is removed or weakened; X1-X13, X15, X16 are
  byte-unchanged.

- 2026-09-08 · routine · **X16 tightened** by /checker at unit `at108-at114-swallowed-causes`
  (commit `6e98487`, verdict `qa/verdicts/at108-at114-swallowed-causes.md`). Records the new
  `IssueKind.EVIDENCE` member and the rule it exists for — a failure of the crawler is not a
  finding about the product — after ruling on the design call the maker put to the checker. The
  ruling: an **additive** enum member that weakens no criterion, reverses no goal direction and
  enables no outward-facing action is a routine amendment under D-015 (which already authorizes
  this stage, its file layout and this contract), not a new DECISIONS entry; the alternative
  (filing screenshot failures as `NAVIGATION`) was rejected on the same grounds X9 rejects calling
  third-party noise a product bug, and the maker's second test fails under that lazy fix — verified
  by the checker's own sabotage run. `capture()` staying non-fatal was also upheld: AT-114's defect
  is the SILENCE, not the survival, and killing a crawl over a missing screenshot trades X11's
  crash-survivable partial graph for no graph at all. **AT-120 added as an OPEN gap** — the
  separation is real in the enum and absent in every count and report a human reads — stated inside
  the criterion rather than left implicit. No criterion is removed or weakened; X1-X15 are
  byte-unchanged.

- 2026-09-08 · routine · **X16's AT-120 gap CLOSED and the criterion restated** by /checker at unit
  `at120-evidence-not-product-issues` (commit `bc29b34`, verdict
  `qa/verdicts/at120-evidence-not-product-issues.md`). The gap this checker opened one unit earlier
  is closed on its own re-executed probe, not on the maker's transcript: the fixture crawl whose
  every screenshot fails reported `crawl.issues = 5` with kinds `{evidence: 4, navigation: 1}` at
  `6e98487` and now reports `issues = 1, tool_failures = 4`, with the workbook's `Issues` sheet
  carrying the one product row and the new `Tool failures` sheet carrying the four. The criterion
  is **tightened, not softened**: it now names the counter, the two summary rows, the sheet, the
  column, the stat and the card, so the next kind-blind regression fails the contract and not only
  a test. The workbook sheet list is amended to add `Tool failures` between `Issues` and `Noise` —
  a legitimate contract change the unit earns, and the pinned exact ordered list in
  `tests/test_crawl_report.py::SHEETS` was checked to still be an `==` on the full list rather than
  a subset. Two residual display gaps (AT-121, AT-122) recorded inside the criterion rather than
  left implicit. Authorized by D-015. No criterion is removed or weakened; X1-X15 are byte-unchanged.

- 2026-09-08 · routine · **X16's AT-121 and AT-122 residual gaps CLOSED** by /checker at unit
  `at121-at122-crawl-count-surfaces` (commit `6c653fd`, verdict
  `qa/verdicts/at121-at122-crawl-count-surfaces.md`). Both gaps were opened by this checker one
  unit earlier and are closed on its own executed evidence, not on the maker's diff: the real
  `cli_crawl.echo_crawl_summary` was called and its captured stdout read (`… 1 issues, 4 tool
  failures`, carried at 0, 4 and 123456), and `/projects/demo/crawls` was rendered through
  `TestClient` (`<td>0</td><td>0</td>` for the two count cells, one `—` left, on `started_at`).
  Both sabotages reproduce in a `git archive` scratch copy with `PYTHONPATH` pinned — sabotage 7
  character-for-character as the manifest transcript claims (the AT-117 concern, checked
  deliberately) and sabotage 8 as `assert 1 == 2`; restore → 8 passed. Every remaining `or '—'` in
  `src/` was swept and all sit on optional string fields. The criterion is **tightened, not
  softened** — it now states that the counted-apart rule holds on every surface a human reads, and
  the two NEW residuals it earns (AT-123 the unguarded `stop_reason` on the CLI line, AT-124 the
  legacy artifact's default-0) are recorded inside it rather than left implicit. Authorized by
  D-015. No criterion is removed or weakened; X1-X15 are byte-unchanged.

- 2026-09-11 · routine · /checker (t135-coverage-merge-expand unit, cycle 1) · **naming correction
  only, no criterion touched**: X12's prose named the helper `_disagreement`; T-135 promoted it to
  the public `disagreement` (and renamed its `crawl_id` parameter to `source_id`) so the video
  merge seam and the crawl merge seam share one rule instead of growing two. Verified identical in
  behaviour before recording it here — the diff is the two identifiers and nothing else, the
  function body is byte-unchanged, the full suite is green, and the crawl merge was driven live in
  a browser (the path that calls it) with the same result. Softens nothing; a contract that names a
  symbol which no longer exists is a contract nobody can check.

- 2026-09-11 · routine · /checker (at102-merge-rediscovery-dedup unit, cycle 1) · **X14's AT-102
  residual CLOSED**. A new `_is_rediscovery(clash, incoming)` helper in `stages/explore_merge.py`
  catches the case `disagreement()` deliberately leaves alone — clash non-structural, same name,
  same `url_pattern` — and `merge_screens` now skips the add instead of appending a second,
  identically-named `Screen` row. Verified by this checker in an isolated `git archive HEAD`
  extract with its own `uv sync` venv (`autotester.__file__` resolved inside the extract):
  mutating `_is_rediscovery` to `return False` reproduces the exact original defect shape
  (`assert 2 == 1` in `test_a_same_named_rediscovery_merges_instead_of_duplicating`) while the
  other 14 tests in `tests/test_explore_merge.py` stay green, and the full suite (`uv run pytest`)
  is green on the live tree. The three dispatch paths — SPA (add, no conflict), genuine conflict
  (add + Conflict), re-discovery (skip) — were checked exhaustive by hand over all
  clash-exists × clash-structural × same-name combinations: a structural clash always takes the
  SPA path regardless of name (X3 requires two structurally distinct states at one URL to be two
  screens, so a name collision between them is not evidence of duplication), so no combination
  falls through uncaught. No criterion is removed or weakened; X1-X13, X15, X16 are byte-unchanged.

- 2026-09-16 · routine · /checker (Mode B sweep #6 of 2026-09-16) · **X17 and X18 added**, folding
  Umesh's 2026-09-16T22:25+05:30 `qa/feedback-inbox.md` entry verbatim: *"abhi tho hmara testing flow
  login k baad hi ruk jata hi … puura product map hona chiaye na aend to end testing . each possible
  route"*. Authorized by D-015 (this stage and this contract). Each maker claim was re-derived from
  code and crawl.json counts only, not read: `routes_crawls.py:226-227` calls `run_crawl` without
  `login_case` (TRUE); `Project` declares no login case at all (NEW — the maker's evidence did not
  name this, and it means X17 needs a declaration, not only a kwarg); `explore_safety.py:88-89`
  denies every form submit under `READ_ONLY` (TRUE); defaults 30 / 200 / 600 s in `schema/crawl.py:59-61`
  and both entry points (TRUE); every on-disk crawl stopped at or before login — saucedemo 1/0/3
  completed, checkerdemo ×2 1/0/3 completed, pathlynks `login_failed` 0 screens (TRUE). **One claim
  corrected:** "a crawl that ends on the login page reports COMPLETED" is true of those three
  artifacts only because they predate AT-242 (`2bb3270`, 2026-09-09T08:17Z; crawls 03:51Z/05:44Z);
  today's code would label them `blocked_no_actions`. The live residual is narrower and real — any
  performed action on the wall page restores `COMPLETED` — and X18 is written against that, plus
  the legacy display. Adds criteria, softens none; X1-X16 byte-unchanged. **Deliberately NOT folded:**
  relaxing `READ_ONLY`'s form-submit denial after login, or raising the default bounds — the first
  weakens a D-016 safety invariant (CRITICAL, human), the second is a per-crawl choice that V7's
  coverage number makes visible instead of hiding. Issues: AT-457, AT-458.

- 2026-09-17 · routine · **X18(a) tightened** by /checker at unit `x18a-login-both-directions`
  (cycle 1), folding the maker's proposed wording with two corrections, both from checker-run
  evidence, neither weakening the AT-467/AT-474 fixes. The mechanism itself (structural-signature
  match OR every FILL-target selector present as the fallback) is adopted as proposed and verified
  independently: three falsifying single-hunk edits to `src/autotester/stages/explore_status.py`
  were reproduced by the checker in an isolated `git archive e70bb2c` extract (each restored
  byte-identical before the next), each firing the exact assertion the manifest claimed, plus the
  maker's own live-browser regression
  (`test_a_wrong_password_with_a_sticky_error_banner_is_still_login_failed`) re-read as evidence.
  **(i)** The proposal's closing sentence — "a genuinely different screen that merely shares the
  login's url is never caught by this fallback" — is FALSE as a blanket claim: the checker built a
  node sharing the login's `url_template`, carrying a different signature and different content,
  but with a coincidentally-matching `#email` FILL-target selector, and the unmodified
  `_still_login` classified it `LOGIN_FAILED`. The blanket sentence is dropped from the criterion;
  the narrower, TRUE claim (a node missing at least one FILL target is never caught) is kept, and
  the coincidental-match risk is recorded above as a new Known OPEN gap (**ISS-x18a-1**) rather
  than assumed away. **(ii)** The not-judged qualifier's own conservatism — firing even when a
  plain `url_template` mismatch alone already resolves a node as not-the-login-screen, needing no
  signature — is now stated explicitly in the criterion rather than left to the manifest's prose,
  because it is contract-relevant behaviour pinned by an existing test
  (`test_a_login_page_that_cannot_be_observed_is_not_an_unqualified_success`) and the checker
  accepted it as a deliberate trade, not a defect, on the reasoning already in that test's own
  docstring. **AT-474 CLOSED** — independently re-verified: the qualifier fires, an
  `IssueKind.EVIDENCE` `CrawlIssue` is filed, and `tool_failures` counts it. **AT-467 was never a
  formal `qa/issues.jsonl` row** — referenced in `qa/verdicts/at458-crawl-stuck-at-login-never-
  completed.md` and `qa/QUEUE.md` but never appended to the ledger itself (a ledger-hygiene gap
  already tracked as AT-475); the underlying defect it named — a sticky wrong-password banner
  reading `COMPLETED` — is independently verified fixed here regardless. **Live-browser (Mode D)
  verification**, against the checker's own real headless Chromium driving the actual product UI
  (not the maker's screenshots, not `curl`): a crawl started from the Crawls page with a
  wrong-password login case reads `login_failed` with `badge-blocked` (warning) tone on both the
  crawl page and the crawls table row; the same flow with a correct password reads `completed`
  with `badge-pass` (positive) tone. Zero console errors either way. Evidence:
  `qa/evidence/browser-x18a-login-both-directions-2026-09-17-checker/report.json`. No criterion is
  removed or weakened; X1-X17 are byte-unchanged. Verdict:
  `qa/verdicts/x18a-login-both-directions.md`.

- 2026-09-17 · routine · **X18(a) gains its ISS-x18a-1 closure and X18 gains new point (e)**, by
  /checker at unit `at480-489-wall-bound-and-fill-fallback` (cycle 1, commit `44d2547`, verdict
  `qa/verdicts/at480-489-wall-bound-and-fill-fallback.md`), adopting the maker's proposed wording
  with one addition. The maker's mechanism is adopted as proposed and independently re-verified: all
  4 capability-coverage rows (bound-named-on-a-walled-crawl, bound-honest wall sentence, the
  submit-control requirement, and the AT-467 sticky-banner control) were reproduced by the checker
  in an isolated `git archive HEAD` extract — each single-hunk falsifying edit restored
  byte-identical before the next, each firing the exact assertion the manifest claimed. **Addition
  beyond the proposal:** the ISS-x18a-1 closure is adopted as "closed **as filed**", not closed
  outright — the checker traced `terminal_status`'s control flow and confirms a narrower residual
  survives (a screen coincidentally matching every FILL target AND the submit control is still
  `LOGIN_FAILED`), which the manifest's own new control test already pins as intentional; this
  amendment states that residual explicitly rather than letting "CLOSED" read as "no residual",
  consistent with how every earlier X18/X14/X16 closure in this log has stated its own residual.
  **Live-browser (Mode D) verification**, against the checker's own headless Chromium driving the
  real UI app (not the maker's screenshots, not `curl`, and not `tests/fixtures/login_site` — that
  fixture has no extra links and cannot produce a bound firing mid-wall without also losing the
  visited node's own `DENIED_POLICY` edge, so the checker authored a small local-only fixture: one
  denied form submit plus three same-page self-links, served on `127.0.0.1`): a crawl with no
  declared login case, started from the Crawls page with `max_actions=2` against a 3-self-link
  walled page, reads `login_wall` with `badge-blocked` (warning) tone on both the crawl-status pill
  and the stop-reason pill (confirmed from the element's own `outerHTML`, not a page-wide substring
  match — a `badge-pass` span elsewhere on the page is the visited node's own unrelated
  "explored" marker), names `max_actions` in `stop_reason`, and drops the "no link led anywhere
  else" claim, on both the crawl page and the crawls table. Zero console errors. Evidence:
  `qa/evidence/browser-at480-489-wall-bound-and-fill-fallback-2026-09-17-checker/report.json`. The
  `max_screens`/`LOGIN_WALL` non-co-occurrence claim in "Known limits" was independently re-derived
  from `_enqueue`'s and `_bfs`'s code (not merely read) and confirmed accurate — a stronger claim
  than the manifest's own prose reasoning, since it also covers every node left queued behind the
  cap-reaching one, not only the cap-reaching node itself. **Hunt on the edited test helper**
  (`_root_login_case()` gained a CLICK step): reproduced live in the isolated copy — reverting the
  CLICK-step addition alone (test file only) reddens exactly one existing test,
  `test_a_sticky_wrong_password_banner_is_still_login_failed` (the AT-467 control), and leaves the
  other 15 tests in the file green — confirming the edit was a necessary tightening (the banner
  fixture already carried `#go` before this unit; the case needed a CLICK step to name it as the
  submit selector) and not a vacuous-guard workaround; no pre-existing AT-462/AT-467/partial-fill
  test was weakened. No criterion is removed or weakened; X1-X17 and X18(b)/(c)/(d)'s existing text
  are byte-unchanged aside from the additions named above.
- 2026-09-21 · CRITICAL amendment · **X10 amended to X10-b (synthetic typing under four
  conditions) and X5's typing column widened accordingly**, by the maker acting under D-029's
  explicit `Changes-authorized` ("qa/contracts/explore.md — X10 + X5 amendment only, by the
  checker" — this unit is the amendment itself; /checker verifies the implementation against
  the amended criterion in cycle 1). Authorization chain: `qa/gates/post-login-forms.md`
  answered **(b)** by Umesh in chat 2026-09-21 (verbatim: *"what is actually login form and
  details like apni best intelligence se system ko fill krr lena chahiye like auto tester kya
  krta hai, they cases and cases various different combinations ki like usse hota kya hai and
  next time kis aur ways se kr ke dekhta hai"*) + `qa/gates/live-crawl-target.md` answered
  **(b) Pathlynks** the same day → D-029 appended via `scripts/append_decision.ps1`, whose
  `Changes-authorized` names exactly this amendment. What changed: X10's absolute typing ban
  gains the X10-b exception (four conditions — widening policy + explicit per-run
  `synthetic_typing` switch, synthetic deterministic values only from
  `stages/synthetic_values.py`, non-production `RunApproval` target, non-destructive
  [password fields never typed, uploads never performed, X6/X5 guards unchanged]); X5's
  typing column reads "allowed (X10-b only)" under TEST_ACCOUNT/ALLOW_WRITES; the no-fire
  row's first bullet is updated to name the built exception; X12 is unchanged (the fill
  CHOICE is DOM-driven, no provider anywhere in the pre-pass). What did NOT change: X1-X9,
  X11-X18 are byte-unchanged; `run_case` (E5) is untouched — the login case remains the only
  `run_case` site and the pre-pass composes `session.fill`/`session.select_option`
  directly, the same actuator boundary every other stage composes. **Load-bearing by
  construction:** `tests/test_explore_typing.py` pins each violation as its own refusal
  (READ_ONLY no, flag-off no, password-field no, determinism, bounds-bind-typing,
  deny-list-still-ON-under-TEST_ACCOUNT) plus a REAL-browser proof
  (`test_a_real_browser_types_and_submits_the_filled_form`: a genuine headless Chromium
  fills the fixture's displayname and the submit carries the synthetic value in the
  resulting GET url). Existing typing-off behaviour verified unchanged: test_explore.py +
  test_explore_safety.py + test_explore_live.py + test_crawl_coverage.py all green, and the
  default `SafetyPolicy()` keeps `synthetic_typing=False` so every pre-amendment caller and
  test is unaffected. First live use: Pathlynks stage-2 form-exploration crawl (after the
  READ_ONLY map crawl), under its own RunApproval citing both gate answers.
- 2026-10-29 · CRITICAL amendment · **X12 amended (rewritten in place) under D-118 (Approved-by
  Umesh, chat 2026-10-29; D-117 item 1 gave the go-ahead, D-118 the design and the models).** What
  changed: X12 no longer says "a model never chooses an action" absolutely. With per-project
  guidance ON, an injected `Provider` may ORDER the code-built candidate controls of one screen; it
  may not add, perform or bypass anything, and every safety/approval/bound clause runs on every
  ordered control. The guidance-off default keeps X12's original text and verify exactly. What did
  NOT change: D-015's rejection of vision-guided crawling (images) stands; X3 identity, X5-X10-b
  safety and typing, X7 host re-check, X11 bounds, X13/X14 merge discipline, and the `D-018`
  approval check are byte-unchanged. The new behaviour is judged by `qa/contracts/crawl-guidance.md`
  (G1-G12); X12 here is only the carve-out. The no-fire entry "naming screens with a model ...
  `explore_name_screen_v1` deliberately NOT built" is unchanged (guidance orders controls; it does
  not name screens). Not yet built: Units 1-5 of D-118 follow; this amendment alone authorizes none
  of them to PASS without their own checker verdict.

- 2026-10-29 · routine · /checker (unit `crawl-record-gaps`, cycle 0) · **X3 and X12 clarified**
  (no criterion removed): X12's "completes with `provider=mock`" restated as `provider=None` (the
  maker's change to `Crawl.provider`, issue gap (d)); X3 gains the one named layout-toggle exception
  the same unit shipped (gap (a)), recorded so the contract and `screen_identity.py` agree. X3's
  verify case (same-URL filter toggle = second node) still passes: `tests/test_explore_traversal.py`.
