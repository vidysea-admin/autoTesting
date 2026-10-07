# T-125 full-suite and visible-browser acceptance gate

Recorded: 2026-10-01, root maker/checker continuation.

Question: Authorize separately reviewed containment work in the existing acceptance harness, or retain the full-suite/browser gate while safe fixture verification continues?

Options: (A) approve a reviewed plan for existing-harness containment work; (B) retain the gate. Neither option permits real credentials, provider spend, remote fonts, firewall/system-policy changes, or a blanket localhost/network exception. Any such expansion needs separate explicit approval.

Answer format: `T125 containment plan: approve` or `T125 browser/full-suite gate: retain`.

Blocks: T-125 final acceptance (required full pytest and CT8 visible-browser evidence), checker PASS, release close-out; not safe mocked fixture tests, isolated mutations, or generated-document maintenance.

Evidence: fresh /root/review_t125_recovery read-only review found no validated browser AND native subprocess egress boundary. Existing Job Objects contain ownership/cleanup only; Python socket guards do not contain Chromium/PowerShell; exact-origin browser routes do not establish native background traffic containment. Source references: .work/check-at733-b/contained-ownership-plan.md:1271-1290; headed_report_b.py:748-756; serve_report_b.py:35; src/autotester/browser/session.py:106-116,167.

Status: unanswered. No policy weakening, retry of stopped native diagnostic, or full-suite/browser runtime authorized by this record. Goal remains incomplete.

Answered: 2026-10-05 — Umesh explicitly approved containment-plan work after
the scope explanation. Authorizes independently reviewed existing-harness
containment planning and scoped implementation/verification. Does not authorize
real credentials, provider spend, firewall/system-policy changes, remote fonts
or unrestricted egress. Full-suite/browser execution waits for proven containment.
Current status: answered — containment work authorized; runtime readiness unproven.

Capability investigation after approval: independent /root/codex_tick_marker_plan
ran readonly docker version/info/image ls and explicit dockerDesktopLinuxEngine
version. Both native pipe endpoints missing; exit1 Servernull. Config access also
denied; failed info Images0 is NOT an empty-cache measurement. No daemon start,
pull/build/container or policy change performed. Existing Linux Playwright/Xvfb/
noVNC setup can inform a future plan, but compose ordinary networking and whole
repo mounts are not contained acceptance. Need available daemon, inspectable
offline complete image, credential-free frozen inputs, proven no-egress fixture
boundary and observable headed viewer. Windows-specific proof remains separate.
Current runtime status: BLOCKED-CAPABILITY, not unanswered user approval.

Capability changed — 2026-10-05: sandbox named-pipe version check denied,
but elevated read-only same command returned native0, Linux Docker Engine29.6.1,
Docker Desktop4.81.0. Therefore daemon-unavailable claim is superseded by this
current measurement. Elevated read-only image ls returned native0: cached
postgres/alpine/deepinterview components/kokoro/mongo/speaches, no explicit
AutoTester or Playwright image. No cached complete test-runtime proof yet.
No container/pull/build/start/settings mutation performed. Independent existing
Docker setup containment/preparation plan requested; network preparation and
headed isolated viewer remain unapproved/unproven, no acceptance PASS inferred.

Preparation source audit — 2026-10-05: existing Dockerfile uses official
mcr.microsoft.com/playwright/python:v1.62.0-jammy; apt display dependencies
xvfb/x11vnc/novnc/websockify/curl; unpinned pip install uv; frozen uv sync;
COPY . . and application-only entrypoint. .dockerignore deliberately allows
projects/profiles and also lacks .env/.worktrees/QA-evidence exclusions. Do not
send root as context. No change to dev-mode Docker contracts is implied by a
separate frozen secret-free acceptance context. Candidate uv.lock hash
188681B3A300C36FB485C3979CCB735236E3073443D73015BBB3BACE34C86BA1;
literal HTTP source hosts enumerated: pypi.org/files.pythonhosted.org only;
root editable package is '.'. Redirect delivery/base-image digest/apt sources
still need verification; literal source enumeration is not network proof.
No download, build, context export or Docker source edit performed. Controlled
preparation approval question already asked once, unanswered; retain gate.

Answered: 2026-10-05 — Umesh said "Empty fixture .env aur controlled image
preparation approve." Controlled acceptance-image preparation may download
the reviewed official Playwright image and Ubuntu/PyPI dependencies using a
verified credential-free frozen context. Independent exact preparation plan
and source/digest checks precede execution. No real credentials, product
endpoints, provider calls, system settings, acceptance-container launch or
release/push authority is granted by this approval. Historical unanswered
preparation state above is superseded; runtime containment remains unproven.

Official immutable metadata verified with imagetools inspect and --raw,
both nativeexit0: index017530b316b85f71b3f0989310393a9095253820e77e9ed94aa3b7d7eb5ecd16;
Linux/amd64 child410a6060acd4cfddca8c95231cf39c96fd28af7a94a050f105c0c4b769121adb.
Independent preparation plan approved conditional on digest, dependency-only
context pyproject.toml/uv.lock/.python-version; no product COPY or rootcontext.
Pin uv0.11.27, deny managedPython downloads, require3.11 before dependency
installation; base interpreter compatibility remains unverified. Exact immutable
base pull dispatched under approval; actual handle/result must be recorded
before claiming cached readiness. No acceptance launch/build performed yet.
Owned pull command handle: unified exec session48952. Initial result showed
official fs-layer download in progress, not terminal. Poll this exact handle;
do not relaunch or infer completion from a timeout or manifest file.

Revised preparation plan independently approved: no AT733 harness edits.
After sole pull terminal, mechanical export of only three dependency artifacts
to fresh owned prep-context-UUID; inspect all path components/reparse safety,
credential-material scan without .env/product imports, exact membership and
pre/copy/post source hashes. Full t125-cycle4 identities:
pyproject593084A9B30E8FAEF0B5D2EEE5FC4F9749EA5A0E035F9FF11F2895ED7C127CCA;
lock188681B3A300C36FB485C3979CCB735236E3073443D73015BBB3BACE34C86BA1;
pythonCEBA8FA5C10F40FBED8FEB7EB5238B63DDA568908ACFD874EE413747B29936C8.
Generated stdin recipe: immutableFROM; UV_PYTHON_DOWNLOADS=never; Python3.11
guard BEFORE apt/pip; existing five display packages/cleanup; uv==0.11.27;
COPY only dependency files; frozen no-install-project sync --python3.11.
No product COPY, infra change, app entrypoint or acceptance launch. A base
Python mismatch stops without unapproved interpreter download. Context not
yet exported or built. Latest sole pull poll: last layer0ed686cdabc2 Download
complete, extraction/terminal still pending; session48952 remains live.

Pull session48952 terminal native0 verified: approved Linux/amd64 child digest
410a6060acd4cfddca8c95231cf39c96fd28af7a94a050f105c0c4b769121adb cached.
Image inspect native0: linux/amd64,947618284bytes, matching RepoDigest.
Approved mechanical context exported to existing owned scratch:
D:/autoTesting/.work/check-at733-b/prep-context-9dd2d8ccfb2e, exact3 regular
files, full receipt hashes matched before/copy/after; path-component reparse
checks clear, selected credential-pattern scan clear (not all-secret proof).
No .env, product code, profiles or project state included.
Dependency-only stdin build attempted under approval, nativeexit1 at FIRST
RUN Python guard: actual base Python3.10.12 vs required3.11. No apt/pip/uv
dependency download step executed. No completed prep image/acceptance launch.
Source/context lock hashes retained. This is compatibility BLOCKED, not product
FAIL. Preserve project Python requirement; no implicit interpreter download or
base swap. Independent revised interpreter/source plan requested before retry.

Independent revised direction approved, download authority still pending:
retain immutable Playwright base, install exact CPython3.11.15 Linux x86_64 GNU
from Astral python-build-standalone release20260623. Reviewer read official
uv0.11.27 download-metadata.json, keycpython-3.11.15-linux-x86_64-gnu:
artifactcpython-3.11.15+20260623-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz;
SHA2560604cd029b142dc223e131f17f5941c0c8d2d5074997c8178b515b19eea2a6c2.
This is upstream metadata attribution, not local artifact-hash proof. Exact
GitHub release path and observed release-asset redirect require authority and
verification before transfer; no arbitrary GitHub source allowance. Root asked
one additional exact-artifact download question, unanswered. No new interpreter
download/build retry executed. Require actual archive hash/exact installed
version, disable later Python downloads, frozen sync explicit3.11.15, retain
existing three source/context hashes. Do not infer uv checksum enforcement from
metadata alone. Preparation still does not authorize acceptance launch.

Answered: 2026-10-05 — Umesh explicitly selected "Exact CPython 3.11.15
preparation download approve". Only the specified Astral release artifact and
verified release-asset redirect are added to preparation sources; enforce the
recorded SHA256. No other interpreter download, product/credential/provider
access or acceptance launch authority is inferred.

Actual approved archive preparation completed, nativeexit0: root independently
read official uv0.11.27 metadata; exact GitHub URL returned302 to HTTPS
release-assets.githubusercontent.com without userinfo. Guarded GET returned200
without another redirect; signed delivery query withheld. Downloaded30889133bytes
to owned python-artifact-8b896f0020 using create-new, SHA256 independently matched
0604cd029b142dc223e131f17f5941c0c8d2d5074997c8178b515b19eea2a6c2.
Mechanical export to prep-context-9dd2d8ccfb2e rehashed identically; revised
membership exactly4 files (original3 metadata plus interpreter archive).
Read-only stdlib archive probe native0:4992 unique members,3944 regular files,
1048 symlinks; expected python/ root, no absolute/traversal member paths,
no special types, lexical link targets stay in root, no member has a link
ancestor. This probe is not extraction/runtime proof. Exact extraction recipe
review remains underway; image rebuild and acceptance launch not performed.

Independent preparation reviewer /root/codex_tick_marker_plan approved exact
manual extraction snippet and dependency-only recipe. Revalidated archive
layout independently:4992members/3944regular/1048symlink,82587700data bytes,
261 implied directories, no indirect links. No extractall/hardlinks/ownership
restoration; validate before writes, exclusive newly owned /opt/cpython,
regulars before symlinks. Root encoded exact reviewed snippet, decoded and
compared bytes; SHA2562794AA74B65F63E6DADCCC41897E92ECE1A13EE7319793E33A2B5EF0BC7CCBAC.
Four context hashes rechecked before actual approved stdin build.
Owned build unifiedexec session96746: extraction DONE and exact installed
Python3.11.15 assertion DONE; Ubuntu dependency preparation currently running.
Poll same handle; do not infer finished image from intermediate progress.
No product code/tests/credentials copied, no acceptance-container launch.

Build session96746 terminal nativeexit0: exact3.11.15 assertion passed;
uv0.11.27 verified; frozen no-install-project sync installed79locked packages
including Playwright1.62.0. Final export/unpack completed, image inspect native0:
autotester-t125-prep:9dd2d8ccfb2e immutable local ID
sha256:e2dca6c5dd32e9c2a2c1ce2f3935363fd85eaa25625ce02b081b963d5ad0711f,
linux/amd64,1175369314bytes, UV_PYTHON_DOWNLOADS=never retained.
This completes dependency preparation only, not browser/runtime containment,
feature acceptance, Windows suite equivalence, checker PASS, commit or push.
Runtime plan review identified466-path source/test inventory as insufficient
for full adapter: scripts/docs/qa/config and isolated Git metadata need explicit
safe export identities. Linux skips Windows-specific coverage; retain separate
Windows checks. No acceptance runtime has been launched.

Runtime direction reviewed by /root/codex_tick_marker_plan: immutable image,
networknone/readonly/capdropALL/no-new-privileges/nonroot, no published ports,
only enumerated credential-free export and owned scratch, bounded host-loopback
viewer over fixed dockerexec bridge; exact bridge/entrypoint/input closure
implementation review still required. One combined isolated-runtime approval
question asked asynchronously; not yet answered. No duplicate question needed.
Host headroom read-only elevated Get-CimInstance Win32_OperatingSystem exit0:
TotalVisibleMemorySize24866680KiB, FreePhysicalMemory625236KiB (~611MiB).
Do not launch proposed3GiB workload under this measurement. Read-only docker
stats native0 showed9unrelated containers; none stopped/changed. Insufficient
current host headroom is resource evidence, not product FAIL or task closure.

Exact next implementation plan approved by /root/codex_tick_marker_plan:
existing scratch job_launcher_b.py::main (currentlyline920) gets dedicated
--docker-probe dispatch before WindowsAPI initialization; same-file fixed
command/inspect/controller helpers only. No source export, app entrypoint,
console wrapper or viewer relay in capabilityprobe patch. Preserve all Windows
modes and unchanged runner/headed-helper/oracle bytes. Before-edit launcher
SHA256C6FCDF81EF7ABBE5B249CAD9371A9EA73A35F49CA5994091102D60B8055AE14E;
runnerB9C1F21FA48CE652FA69412D2909A654562CF2B6983C55CEDDDCB4EEE33A9B1D;
headed6A8EC22FE03552DE87DBD90157B4890A8E81A778D478AA2A14B0C2CB80AAFE36.
Fixed image/config,180s active/15s cleanup, exact recorded-container-only
cleanup, no mounts/ports/source. Probe proves native namespace/no-egress,
registered loopback fixture and headed Chromium capability, NOT observable
viewer/CT8. Read-only AST/fake-subprocess failure/cleanup controls and independent
implementation review precede runtime. No launcher patch or runtime executed yet.

Subsequent BUILDING progress: approved pure command builder and inspect validator
added in-place to existing job_launcher_b.py (originalline920 boundary); no
Docker dispatch/controller or inline native/browser probe exists yet, so mode
cannot execute. Root AST-isolated controls run with python -I -S -B -c:
RED missing-seam assertion native1, then GREEN commands4 + metadata-mutants18
refused + restoredpositive1 native0; no module top-level import, Docker/network
or child process invoked. Initial GREEN fixture omitted IpcMode and its label
mutation split a dotted key; those setup errors received no falsification credit,
fixture corrected without weakening validator. Touched helper lint0; entire old
scratch launcher ruff exits1 with existing out-of-scope findings (not cleanclaim).
run_acceptance/headed-helper full hashes remain unchanged. Remaining controller,
strict-environment/entrypoint closure, fake-failure cleanup tests and independent
implementation review pending. No product PASS/goalclose/runtime/commit/push.

Next BUILDING turn: root closed reviewer-found Config.Env/Entrypoint/Cmd/
WorkingDir, ownership-ID syntax and host-mount/device-cgroup/sysctl gaps.
Updated purecontrols native0:25unsafe metadata mutations refused, fixed
exec/image/reconciliation argv checks passed; no Docker call. Fixed Docker
executable is observed C:/Program Files/Docker/Docker/resources/bin/docker.exe,
not caller PATH lookup. Additive fixedpayload/controller/main plan approved;
worker /root/docker_probe_controller_build owns those seams only, reviewer
/root/codex_tick_marker_plan read-only. Controls/final review still in progress.
Root removed only the new helperblock/flag/mode-term/dispatch in-memory and
reconstructed original launcher LF SHA256C6FCDF81EF7ABBE5B249CAD9371A9EA73A35F49CA5994091102D60B8055AE14E:
legacy Windows code byte identity confirmed, not merely assumed from diff.
Other runner/headed hashes unchanged. Fresh headroom measurement563392KiB;
runtime prerequisite chosen4GiB (fixed3GiB cap+1GiBmargin), not met.
No runtime grant answer received or flags enabled; no launch performed.

Worker implemented fixed inline payload/controller/main dispatch; still BUILDING.
Root independently AST-compiled launcher and embedded payload;4preflight controls
(each missing grant and low-memory fake) refused before token/files/Docker/native
API calls, native0. Scoped security reviewer found two concrete controller
blockers in inspected b0bf8804 state: malformed create stdout assigned before
ID validation prevents valid name-based cleanup; optimization strips assert-only
runtime/review/RAM gates. Worker instructed localcandidate-beforeassign and
explicit optimization/grant refusals, with final-hash fakefailure controls.
No implementation-ready approval inferred. Runtime/user grant and RAM gates
remain independently unsatisfied; no real container launched.

Worker final freeze: launcherSHA256a3dc495094ba980211c6f9bc8e52590ad1bd0a80217c87f92dd9641d761c1545;
fixedpayloadSHA256f912a569e3442b4be5ad38a3533ee0000e91e86ed5a5309c940b71f198683fe3.
Worker /root/docker_probe_controller_build reports36offline fake-Popen controls
native0 with unchanged frozenbytes, including malformedcreate/timeout reconcile,
ownership ambiguity, wrongimage/platform/environment, unsafe/failedinspect,
start/exec/scoreboard failures, deadline/overflow/drain/close/wait failures,
stop-kill-remove/readback/receipt failures; no physical runtime/evidencefiles.
Root independently reran AST/payload compile and4grant/headroom refusals native0
on same frozenhash; separately ran actual python -I -S -B -O AST-only controller
control native0, explicitly refused before environment/memory/files/Docker.
Reviewer-found malformedID assignment and optimized assert-only gates repaired.
Fresh read-only security implementation review requested on this exact freeze;
helper build is not feature readiness/PASS. Runtime flags remain unenabled.

Next turn reconciliation found idle reviewer had not restarted from send_message;
root explicitly dispatched followup_task (no background-review claim inferred).
Actual final read-only review then APPROVED scoped implementation readiness at
a3dc495094ba980211c6f9bc8e52590ad1bd0a80217c87f92dd9641d761c1545:
both concrete blockers corrected,180s active/15s cleanup retained, no further
high-confidence blocker against probe-only plan. Not native capability evidence.
Runtime question remains unanswered; flags unenabled and no launch occurred.

Input-closure review confirmed original466source/test bytes must include authorized
untracked candidate files: tracked source/test counts171/289 versus frozen174/292.
Preliminary broader readonly hash inventory1729files had digest
B32A824627411AE337EA13183BD8780DA0F7D3C716F78E76499CFE8D29212810,
but included unnecessary QA evidence and omitted other required config surfaces;
do not use it as final export/acceptance identity. Narrower approved membership
is being rederived from originalfreeze + explicit tracked selectors/literal inputs.
Only .env.example template examined:10assignment values all empty,38lines,
SHA2563C0609BA64562813CE4A6571B8DB1BB3499F6C23D15CA1D651F678D5B84B5774;
no real .env/project/profile/credential files read/exported. Input-closure work
is read-only; no source export or Git metadata copy performed.

Planned input inventory now1219explicit paths: original466freeze + tracked
approved selectors from git ls-files -z + existing untracked candidate manifest.
All original466SHA256 values matched current candidate bytes; literal containment,
regular-file and all ancestor reparse checks passed. Final sorted path/NUL/hash/
NUL/byte-size row digestDD39FDB7EC5999ED2EE6CEB2C38FABF31373A863C9A19634D74C9C9E6CC8B572.
Breakdown includes174src/292tests/14scripts/13docs/705QA/5goal, explicitly named
root/docker/hook inputs. Earlier1218digestB1C19080509728B9914C2D18017D6C417FEC1EBB91EA44065FA90827C55E218F
is superseded after adding candidate manifest and repairing T171 goal reference.
Both canonical/candidate71done-check Python literal references now exist;
reference-only correction and before/after JSON audit recorded in feedback-inbox.
This proves current planned membership/hashes, not all-secret screening, physical
export, Git reconstruction, console-entrypoint readiness, full-suite execution,
viewer observation or product acceptance. No real .env/profiles/projects/.git
in selected membership; runtime question remains unanswered and flags disabled.

Console-entrypoint seam resolved at plan/static-evidence level, not runtime:
scoped reviewer approved generated packaging shim in newly owned runtime
/work/bin/autotester pointing only to existing autotester:main. No uv_build
wheel/download/image mutation/product module needed. Root stdlib tomllib/AST
probe native0 verified exact pyproject script mapping and __init__ forwarding
to autotester.cli.main, without importing product or writing a shim.
Use literal adapter commands with fixed PATH/PYTHONPATH/VIRTUAL_ENV/
UV_PROJECT_ENVIRONMENT, UV_NO_SYNC=1/UV_OFFLINE=1/UV_PYTHON_DOWNLOADS=never;
bind shim hash and imported candidate path. Physical creation/execution remains
behind the existing unanswered runtime approval and fresh4GiBheadroom check.
Separate root in-memory tracker oracle native0: currentGREEN, old T171 missing
filename mutant detected exactly, original dictionary restoredGREEN; no pytest
or new product acceptance inferred. No Docker/export/install/runtime performed.

Continuation platform-seam audit: /root/docker_probe_controller_build identified
an actual Windows-only acceptance boundary, independently located by root with
rg: headed_report_b.py::main line871 asserts os.name == "nt"; snapshot_api
line178 and bind_served_identity line444 use native Windows ownership/snapshot
controls, and line936 requires evidence mode windows-lock. Therefore the frozen
Linux dependency image cannot execute this unchanged main or prove equivalent
Windows acceptance. Existing portable assertion seams are check_receipts537,
classify_download_handoffs544, rendered_cases621 and portable_cases678. Next
implementation requires a reviewed Linux-specific containment/served-identity
branch in the existing helper while retaining these assertions and the separate
Windows coverage requirement; do not remove the platform assertion alone or
fabricate windows-lock evidence. No helper edits or acceptance launch performed.
Active .3 tick --policy-check returned targets=2 drift=0. Fresh Get-CimInstance
Win32_OperatingSystem was denied by sandbox, so current headroom is unknown,
not inferred from older measurements. Runtime approval remains unanswered.

Goal-alignment correction after independent /root/codex_tick_marker_plan review:
do NOT implement the proposed AT733 report/download harness port for T125.
That historical harness does not establish catalog CT1-CT9; its technical
portable-seam approval is not authorization to call it T125 acceptance.
Retain generic dependency/input preparation and capability probe only. The
actual existing T125 seams are tests/test_ui_catalog.py::store/_auth_flow,
GET /projects/demo/catalog, src/autotester/ui/routes_catalog.py and existing
test_catalog/test_catalog_packs tests. A contained headed catalog walk must
reuse their credential-free fixture semantics and contract-derived row
assertions, not report/export or windows-lock evidence. No AT733 helper changed.
Fresh elevated read-only Get-CimInstance Win32_OperatingSystem returned
FreePhysicalMemory=668820KiB, TotalVisibleMemorySize=24866680KiB: roughly653MiB
free, below fixed4GiB prerequisite. No unrelated process stopped; runtime
approval unanswered and no acceptance launched. Full suite and separate
Windows-specific coverage remain unproven; no task status/PASS changed.

Catalog-specific coverage reconciliation (read-only, no runtime): CT6 integration
already has the real trigger seam routes_runs.py::_execute_with_trace and
trigger_run, with existing test_ui_runs_serial_entry_order.py::
test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases (line150)
and persisted all-three-tier zero-count assertions at182-183. Include that
existing integration test in affected scope; helper-only tiers_to_run tests
do not substitute for CT6 dispatch/never-skip/report proof.
CT8 reserved reasons NO_GROUND_TRUTH/NO_LIVE_ENDPOINT have readable labels
in routes_catalog.py but no current production-stage emission. Independent
review permits schema-valid injected build_catalog fixtures through the actual
route renderer to test labels/actions/escaping/row counts, explicitly marked
renderer-only; those cannot claim production stage blocking. Real project/
FlowSpec route fixtures remain required for the four reachable reasons.
No contract edited or weakened; no mock renderer substitute, test execution,
fresh acceptance verdict or helper modification. Additive fixed catalog-payload
generator plan is under independent preimplementation review, not dispatched.

Generator-only preparation implemented after independent plan approval in
existing job_launcher_b.py::_docker_catalog_script; no dispatch/runtime added.
Root independently AST-extracted only the no-argument generator, evaluated it
in an otherwise empty namespace and compiled its returned string without
executing it. Initial launcherSHA256
8f6c196d11e575d2b883e00cfa4e3ac33b824d9956ed7127255573ff784d1c18;
payloadSHA256dde37332bba365af00a6451646db5c1848f9f3c0b45204d83ea4c502666417eb,
248lines. Product imports0/payloadexecution0. This is not runtime acceptance.
Scoped safety reviewer found self-authorizing input manifest, post-allocation
manifest/aggregate limits and unbounded callback receipts; bounded DOM/per-row
evidence also missing. Worker repairing only additive generator, retaining
legacy paths and generic probe. This initial freeze is NOT execution-ready;
no feature readiness, checker PASS, source export, Docker launch or browser.

Catalog-generator repair freeze: launcherSHA256
ba3892bf88c4d1339fe144aad1b50f7b3af69c27984676922d8c96a0bac12b81;
payloadSHA256dc2187201784d671cc2ee9fb95a82910d6d4b7c844100c4f20c8057d70669f81.
Root reran exact saved read-only inventory command terminal0:1219members,
466original hashes matched, DD39FDB7EC5999ED2EE6CEB2C38FABF31373A863C9A19634D74C9C9E6CC8B572
unchanged. Payload pins exact ordered rows (path/NUL/uppercaseSHA/NUL/decimal
size joined LF), not guessed Linux sorting. Root independently AST generator
evaluation/compile passed with payloadexecution0; removing only additive
function/adjacent blank lines reconstructs exact original A3DC launcherhash.
Independent scoped re-review /root/codex_tick_marker_plan approved inert
preparation at this freeze: prior identity/read-size/event-buffer issues closed;
bounded browser rows/DOM and evidence recorded. This is NOT runtime readiness
or feature PASS. Fixed payload has no dispatch. Controller/source immutability,
visible viewer, remaining catalog criteria/falsification/fullsuite and Windows
coverage still unproven. Runtime approval unanswered; no acceptance launched.

Approved existing-file CT8 test-strengthening implemented in candidate
tests/test_ui_catalog.py::
test_reserved_blocked_reasons_render_label_action_and_escape_in_actual_route.
Two parametrized injected renderer fixtures cover reserved NO_GROUND_TRUTH
and NO_LIVE_ENDPOINT through actual TestClient route/build_catalog dependency.
Assertions bind actual case-class table, exact15class rows/tiers/applicability,
target row label/action/escaping and14runnable/15total; provenance explicitly
renderer-only. No stage logic/contracts/skip/threshold changed. Root stdlib AST
syntax compile passed;190filelines/36functionlines; no test execution or PASS.
IMPORTANT: this authorized test edit invalidates the earlier466source/test
freeze and DD39 inventory/payload pin for any future acceptance. Do not bypass
the mismatch or execute old generator against changed candidate. Re-freeze
with attributable original-to-new test hash/change scope before dispatch.

Read-only reconciliation after authorized renderer-test edit terminal0:
same1219members;465original source/test hashes unchanged and one explicitly
authorized delta tests/test_ui_catalog.py AB5EC3B84E66FEAB02AA3DB9641280C6236DACBA9285609D70B04F931F26E89F
to7BFDD0EA8BFE252961DBB2A757F7C787402425C7C137CAC09FA9A95D55F4C80C.
Root AST reverse-change reconstructed exact original test hash, compile passed,
190filelines/36functionlines; tests not executed. The inventory command's legacy
ORIGINAL_FROZEN_MATCHES=466 label means466rows checked; exactunchanged count465.
New ordered identity05B123541AF3FBBA37D90ECE6263DF130B6325C3A1A8353C454583D57DC91082.
Old freeze XML/DD39 retained unchanged as history. Scoped reviewer approved
exactpin replacement only, relying on root reconciliation (no independentrerun).
Root applied single digest change: launcherSHA256
c728c56bf1f5a06f717411deae73d9dd00269c1fc9229c38e480528b85f11937;
payloadSHA256b05537e77077aa13e6099b1864cc34a3efb768072b2279ca503c29d2b5530ec1.
Reverse onlypin recovers previous ba3892 launcher exact; inertgenerator/compile
passed payloadexecution0. No source export/runtime/acceptance/PASS implied.

Root independently ran actual selected-inventory identity negative controls,
not synthetic manifests: same1219members/465unchanged/1authorizedtestdelta,
05B123 baselineGREEN; isolated in-memory path/hash/order/count substitutions
each changed the pinned digest and were REJECTED; original rowsequence restored
GREEN. Exact PowerShell command terminal0; no physical source mutation/export,
product import/test/payload/browser/Docker execution. This proves the inventory
identity algorithm/control behavior, not payload/runtime validation or feature
falsification. Next scoped read-only controller plan dispatched to existing
worker; no execution controller or live viewer claimed implemented.

Integrated controller design review held implementation pending exact privileged
ack identity/sequence/evidence, nonce transport and maintained bridge protocol.
Worker refinement uses locked websockets16.1.1 (root confirmed uv.lock2092-2093),
fixed root ack program/stdin and screenshot-bound ordered acknowledgements.
Root inspected actual CUA IAB documentation/capability inventory without opening
a tab or navigating: screenshot API returns Uint8Array; browser capabilities
only visibility/viewport. No documented private request/header or cookie-setting
API exists in this surface. Read-only DOM evaluate is not an auth-write escape.
Therefore proposed private header/cookie bootstrap is BLOCKED-CAPABILITY as
specified; do not implement an unauthenticated or hidden-evaluation workaround.
Ordinary reviewed auth UI would require explicit design revision, not assumption.
Fresh elevated readonly RAM returned FreePhysicalMemory2246496KiB (~2.14GiB),
still below4GiB. No runtime approval answer received, container/browser acceptance
not launched; screenshot bytes are documented capability, not live viewer proof.

Scoped reviewer confirmed ordinary password-form cookie bootstrap is technically
possible but CUA fill would put its ephemeral value in the tool-call transcript,
violating the currently proposed no-transcript-token requirement. No hidden
evaluation/unauthenticated bootstrap/URL-token fallback authorized.
Human choice requested: manual direct localviewer entry without chat/tool value,
or narrow explicit authorization for short-lived LOCAL viewer token in CUA
provisioning transcript only, still excluded from URLs/logs/evidence. No real
Pathlynks/provider credential involved; no token generated or submitted yet.
Runtime approval and4GiBheadroom remain separately required. No feature PASS.

Independent reviewer approved ONE integrated preparation implementation in
existing job_launcher_b.py against completed specification: ordinary local
password POST/HttpOnlySameSiteStrictcookie; exact authenticated viewer HTTP18766
and WS18767; installed websockets16.1.1 framing/limits; fixed rootack/stdin
identity+sequence+actualcapture binding; owned immutable upload/UIDrefusal proof;
shared180soperation/15scleanup; zero create before all runtime/review/lane/login
choice/privatecredential/unoptimized/RAM/identity gates. Worker dispatched
implementation with20minbudget; preserve existing probe/legacy bytes, no native
runtime/newfiles/sourceexport/auth provision. Final safety implementation review
and offline failurecontrols required before activation. This authorizes code
preparation only, not a provisioning choice/runtime/visual evidence/PASS.

Continuation checkpoint: native agent inventory confirmed the same
docker_probe_controller_build worker RUNNING; no restart dispatched. Root
compiled a live preparation snapshot using stdlib AST only: launcher and all
five catalog/ack/verify/asset/bridge embedded programs compiled successfully
(command exit0). Embedded payload execution0, product imports0, container
launch0. This is syntax evidence only, not a completed freeze or acceptance.
The10second mailbox observation timed out without a terminal notification;
retain the same worker handle and await complete controls/final identity.

Bounded draft checkpoint: worker reported ten AST-isolated zero-create gate
controls passing, native runtime0; root has not independently rerun those ten
controls. Integrated upload/auth/transport/cleanup failure controls remain
unexecuted, so the implementation is NOT ready-for-check or activation.
Root independently compiled launcher plus five embedded programs at SHA256
5bdb68cd6da83ea2a0f4728505a154d0959a5afede46dc8d0c7a53e2c5d9895d
(terminal0, embedded execution0). Successful-login HTTP cookie nonce is now
separate from root-ack identity. Root requested worker stop at a concrete
partial checkpoint with reproducible control commands and remaining scope;
no acceptance checker or runtime dispatched.

Worker terminal partial checkpoint at5bdb68: edits stopped, BUILDING remains.
Catalog payload42a2966d1b939d5c199e27ad590043f995b57dd370b71c0f4d0b662500580cee.
Earlier ten-control command was not retained, so that report is NOT independently
reproducible evidence. Active minutes could not be reconstructed; worker treated
20minute budget exhausted. Remaining: image/input/upload/secret-content controls,
auth/header/expiry/rotation controls, ack replay/order controls, bridge
overflow/EOF/backpressure controls, cleanup failure controls and exact baseline
preservation. Root dispatched two bounded read-only preparation tasks in parallel:
reconstruct reproducible AST-only zero-create controls, and exact in-memory
legacy/probe preservation measurement. Neither is feature checking or activation.

Root independently reran reconstructed stdlib AST-isolated controller gates:
six missing grant/mode/password/hash cases plus optimized/non-Windows/low-RAM/
memory-query failure,10/10 rejected before runtime imports (terminal0).
Fake memory calls occurred only in the last two cases; actual native/create/
network/browser/product calls0; launcher5bdb68 unchanged. This establishes only
early prerequisite refusal, not later image/upload/auth/ack/transport/cleanup.
Exact command and output are retained in this turn's terminal tool record.
Scoped provenance agent independently reversed all catalog additions in memory:
exact A3DC495094BA980211C6F9BC8E52590AD1BD0A80217C87F92DD9641D761C1545
pre-catalog baseline recovered, proving legacy/probe bytes unchanged. C728
generator-specific reverse remains UNPROVEN without retained prior body bytes.
No feature verdict/runtime/commit/push implied.

Root ran seven AST-extracted actual container bridge forward() controls with
fake streams/socket only: positive record, cleanEOF, truncatedheader, zerolength,
oversize record, truncatedbody and aggregate overflow. All7 reached expected
send/error/close assertions (terminal0); aggregate rejected after64 permitted
1MiB records. No real thread/socket/network/native/payload process; file unchanged.
This covers one pipe direction only, not host bridge cancellation/backpressure,
WebSocket framing implementation or cleanup acceptance. Input/upload and
auth/ack preparation controls dispatched independently in parallel, read-only.

Actual AST authentication controls found duplicate Host/Origin/Cookie accepted
because headers.get selects the first value (frozen5bdb68 lines1913-1917);
POST length/type admissions have the same ambiguity. Scoped independent plan
approved in-place get_all cardinality repair: singleton Host allviewerrequests,
singleton Origin POST/WS (GET may retain absentOrigin), singleton Cookie when
auth applies, singleton POST length/type and reject any Transfer-Encoding before
bodyread. Login does not require an auth cookie. Both read-only agents terminal
before sole-owner worker dispatched repair with10minbudget. Runtime stays0.
Input agent's synthetic actual-prefix/tail controls rejected identity/count/
path/order/hash/size, corruption/owner/mode/symlink and successful forbidden
mutations; NOT authoritative1219positive or actual OS/upload proof. Root did not
independently rerun those controls; exact command/output in agent message.

Header repair frozen EF2F3195744371FDFFB294385E7954BB7B50783CE962CBE0B18649E3AD2372D9.
Worker reported actual auth/GET/POST duplicate/missing/TE/loginrotation controls
terminal0, no runtime. Root independently accepted valid authenticated request
and rejected12 duplicate Host/Origin/Cookie variants. Initial root harness
omitted SimpleCookie and failed baseline; supplying that real stdlib dependency
restored baseline/control success, terminal0. Not a product regression.
Root also ran6 actual cleanup-branch fakeCLI controls: successful owned removal,
remove/absence failures, changedID(no removal), proven nevercreated absence,
timeoutunknown refusal. All expected branches reached, terminal0; native0.
Ack agent executed actual payload with fake FS: ready+1..5 sixwrites and14
rejections with zerowrites. Ack payload7725835283273d13e606c468dd6e8cd8481020a31d59844b286aa95c888ac941
unchanged. Control-character evidence IDs satisfy existing length-only grammar;
no added printable grammar assumed. Real capture binding remains unproven.
Full baseline preservation after header repair still requires remeasurement.

EF2F preservation remeasurement completed by provenance agent: in-memory removal
of catalog additions/parser dispatch recovered exactA3DC pre-catalog baseline,
terminal0,writes0. Root reran authoritative inventory:1219members,465unchanged,
one approved test delta7BFDD0..., ordered digest05B123... confirmed. In-memory
JSON from those actual rows passed the actual controller manifest prefix
(AUTHORITATIVE_1219_PREFIX_POSITIVE_OK, terminal0); no physical manifest/export.
CLI agent executed9 actual-function fake dependency cases: EOF0 and exit7
returned explicitly, overflow/writer/deadline/cancellation/backpressure/cleanup
failure rejected. Not actual scheduling/blocking pipe or asyncWS evidence.
Remaining include caller exit-code handling, asyncWS cancellation/backpressure,
secret-content rejection, native ownership/upload and final scoped safetyreview.
No acceptance runtime/featurePASS/taskclosure/commit/push.

Root actual require_cli AST controls accepted status0 and rejected1/7/-9 without
raw stderr leakage (terminal0, fakeCLIonly). Read-only secret routing found
existing scanner real_values reads real.env, prohibited in this scope; known-value
redaction without supplied secrets cannot prove absence. No scanner imported or
realcredential read. Heuristic approved-source-byte screening remains to design,
with exact fixture exceptions and declared blindspots, not an absence guarantee.
Async bridge agent's actual-code fake controls found connection.close failure
skips process cleanup/active reset, and text/oversize rejection adds no stateerror.
Root requested scoped independent in-place repair-plan approval before edits.
No native runtime or feature verdict.

Root read-only four-rule heuristic source screen over approved1219members
completed terminal0: privatekeyblocks/GitHubtoken/AWSaccessID/credentialURL.
Binary-unexamined0; five finding rows, allcredentialURL in two tests and three
historical QA files (six matches total). Only path/rule/count and userinfo-redacted
context reported. Context indicates regression fixtures/history, not a clearance
or an approved exception; exact-hash/rule/occurrence classification remains.
No real.env/credentialstore read, physical export, source mutation or runtime.
This limited rule set does NOT cover arbitrary secrets/password assignments.

Scoped bridge cleanup repair frozen7F79EC06AD94FC90E1F3367DB03BB4D02751E39C71C5A8CA9D84A7AE98448DA8:
worker actualAST11fake controls terminal0; typed close/stdin/kill/wait errors
sticky, active reset independent; text/oversize sticky before1003. Worker exact
in-memory reverse recovered EF2F; root has not independently rerun these11.
Remaining .01 operational timeout floors and unbounded cancellationgather
identified, independent scoped repairplan approved then soleownerworker
dispatched10minbudget. No runtime/deadline reset or featurePASS.
Read-only credentialURL classification recorded exact path/hash/rule/occurrence
and offsets for all6matches:2 recognized synthetic pairs,4 unclassified. No
blanket exemption/clearance; no matched values printed or candidate bytes altered.

Independent context classification resolved all6 credentialURL matches as
specific regression fixtures/history. Any future exception must bind exact
filehash/rule/rawbyteoffset, not wholefile/directory: issues395c7b... offsets
566740/567899; at298verdictf64835...9607; t011verdict635d68...3898;
migrate-test729cf1...9786; secrets-testbe21c0...11262. Root earlier offsets were
UTF16character indices; reviewer explicitly computed rawbyte offsets. No
exception installed, secret absence guarantee or runtime clearance implied.
Deadline repair draftD4D0E359ABAEA90AC851F4587AB758DA0358FD1498AF3683C6C0CAE32B97F7C3
root syntaxcompile terminal0, execution0. Worker actualASTfake controls report
expiry stops nextI/O and stalledgather/cancellation records stickyerrors with
cleanup; real cancellation-resistant wait_for/gather termination UNPROVEN.
Worker requested terminal scopedcheckpoint, no silent expansion/runtime.

Root independently remeasured D4D0 launcher catalog reverse: exactA3DC legacy/
probe baseline recovered, terminal0,writes0. Scoped review inspected local
CPython3.11 asyncio: wait_for waits for cancellation completion; real hardbound
cannot be inferred from fake timeoutcontrols. Need bounded asyncio.wait task
ownership plus enclosing server/eventloop shutdown; pendingtasks prevent success.
Current asyncio.run shutdown remains unresolved, runtime NOT eligible.
In parallel worker drafting source-screen in existing source-read loop before
create/export, exact fixture tuples supplied, no implementation authorized yet.

Source-screen plan returned exact existing loop anchor1870 and six URL tuples;
strictUTF8/controlbytes/provider-token/secretassignment baseline feasibility
UNMEASURED. Root dispatched bounded read-only actual1219 feasibility measurement,
no implementation or realcredential reads. In parallel integrated asyncownership
plan review dispatched covering bridge explicittasks+boundedwait, explicitserver
shutdown and privateeventloop replacing asyncio.run, with pendingtask failure
and verified ownedthread termination. ExistingD4D0 unchanged. No partial plan
treated as runtime clearance; actual containment remains in preparation.

Integrated asyncownership plan APPROVED with explicit owner-thread task/server/
transport/loop operations, locked loop lifecycle publication, librarytask snapshot,
boundedwait without unboundedcancelawait, pendingtask/processfailure prevents
success, verified threadjoin and independent exactcontainercleanup. Root
dispatched separate solewriter catalog_async_shutdown_build20minbudget to
existing nested functions only; source-screen worker remains readonly candidate
measurement. No newfiles/functions/runtime. Worker cited existing lines
1796/2017-2140/2193/2229 before editing. Canonical backlog reread still24pending.

Live asyncwriter draft landed private ownerloop/sharedcleanupclock; worker
reports no wait_for/gather in catalogcontroller, offline controls stillpending.
Root independently compiled current live launcher AST terminal0, execution0.
This is BUILDING snapshot only, not freeze/review/runtime. Same source-screen
worker confirmedlive; observationtimeouts did not cause restart. Both original
budget slices retained, boundedcheckpoint requested for source measurement.

Asyncworker syntheticcontrol session22303 ran>10s, exact owned session interrupted
exit1/nooutput; failed/inconclusive notPASS. Worker investigating actuallogic vs
testharness shutdown, same20minbudget. Root live snapshotde37240... ASTcompile
terminal0 and catalogcontroller asyncio.run/wait_for/gather callcount0, but that
static property is not runtime termination evidence. Sourceworker live53601
reported MEMBERS1219; previous stalled pipeline96398 explicitlycancelledexit1,
noevidenceclaim. Root cannotpoll53601(unknown session scope), askedowner inspect
samehandle withoutrestart; terminal state not inferred from pollingfailure.

Source measurement SAME53601 terminal0:1219members13,532,130bytes,05B123exact,
authorizedtest7BFD; strictUTF8failures0,NUL0. Proposed rules found47matches:
6classifiedURL,38secretassignments,1providertoken,2unsupportedcontrols;41new
classification obligations, no blanketexception/screenimplementation/export.
Exact boundedcommand/29reportrows retained sourceagent tool0b02aa/9afe80.
Asyncwriter terminal PARTIAL checkpointFC0657E7F0F3B70FF82D0F1ADA384701C984EEFAD193AD86A57241ACB528CEF3.
Root final ASTsyntax+exactA3DC legacy/probe reverse passed terminal0,writes0.
Behavioral owner/shutdown/initrace/librarytask/processclosure controls missing;
inconclusive test sessions stopped, cannotattribute interpreter stalls toproduct.

Root independent candidate strictUTF8/NUL measurement terminal0:1219PASS,
13,532,130bytes,05B123identity and authorized7BFDtest reconfirmed. This does
not clear other secret/controlbyte findings. Two readonly10minscopes dispatched:
actualASTfake asyncownershipbehavior and exact41finding contextclassification.
Asyncworker reports6ownerloop+4outercleanup controls terminal0 againstFC0657,
allfakes/noasyncimport/native; actualbridge/serverbehavior coverage stillmissing.
No featureverdict or runtimeeligibility implied.
Draft notready/runtimeeligible; finalimplementationreview stillnotdispatched.

Async scoped implementationreview found aggregate servicejoins could consume
the entire shared15scleanup and starve containerremoval. Independent repairplan
approved viewer3s/hostCLI2s aggregate subcaps under sameclock, no positivefloor;
solelauncherwriter implementing controls. Sourceproposalworker appended below,
reproduction41tuples39candidates2unresolved terminal0; independent exactexception
review dispatched, no exceptions installed/runtime clearance.

## Source-screen exception proposal: exact 41 additional occurrences

PROPOSAL ONLY: 39 CANDIDATE occurrences (35 synthetic-fixture, 4 historical
documentation) and 2 UNRESOLVED control bytes. No exception approved/installed.
No blanket test/file exemption. Each row below binds one exact path, complete
SHA256, rule, and raw-byte offset. Context is supporting provenance, not proof
of secret absence. Historical context cue alone needs independent confirmation.
The earlier 6 credential-URL exceptions are separate, not repeated here.

Read-only measurement terminal0 reproduced 1219 members, 13,532,130 bytes,
inventory 05B123541AF3FBBA37D90ECE6263DF130B6325C3A1A8353C454583D57DC91082;
authorized tests/test_ui_catalog.py hash
7BFDD0EA8BFE252961DBB2A757F7C787402425C7C137CAC09FA9A95D55F4C80C.
Affected files' hashes/offsets rechecked during classification; this appendix
does not claim another complete membership measurement. Strict UTF8 failures0,
NUL0, assignment38/provider1/control2 additional occurrences; credentialURL6
already classified. No real.env reads, matched-value output, source mutation,
physical export, provider calls or acceptance/runtime.

| Path | SHA256 | Rule | Raw-byte offset | Proposal / safe provenance |
|---|---|---|---:|---|
| qa/issues.jsonl | 395C7BE5A55E0364F702A03EFB0F9EF5B63EC7610887D0162386C19EF3505EC5 | secret-assignment | 749115 | CANDIDATE historical QA record; local test/fake/fixture context |
| qa/manifests/t055-langchain-fallback.md | 6A4F3C0C4DB9FCE9E4EA0C837CA4A700DA6781B9431186DDDE4006A41AAF3041 | secret-assignment | 4077 | CANDIDATE historical maker record; local test/fake/fixture context |
| qa/verdicts/t045-db-assert.md | 9004F2AADA3ADA19A6C86B3EEA4403E66E4D4DAE035707229FC8EC0A9E31298B | secret-assignment | 3859 | CANDIDATE historical checker record; local test/fake/fixture context |
| qa/verdicts/t172-run-trace.md | DAEA8F979FD974BD2AE02140561844D0421549E86E75251AFB5DF13EA959BCE8 | secret-assignment | 6550 | CANDIDATE historical checker record; local test/fake/fixture context |
| tests/fixtures/inventory_site/inventory.json | BC0B8A6BF5112F0EC93DA68363D019CBCBFC13F6BFF20D932D2E02E8CD528BA8 | secret-assignment | 726 | CANDIDATE local inventory fixture consumed by test_crawl_inventory_live.py serve_dir |
| tests/test_browser_settle.py | 23F892FD56F70119EC7101687399A2E251D011EA79D1CAD520BA0C6774DDDB63 | secret-assignment | 564 | CANDIDATE PASSWORD constant consumed by make_store fixture |
| tests/test_browser_unreadable.py | BCFA84CD92E7FBFEBEA7AB832B14B0DFEF4D3E19D3011B2259B9E633469D9CA7 | secret-assignment | 1290 | CANDIDATE SECRET constant consumed by password masking tests |
| tests/test_browser_visual_order.py | 4ED64ADC965DCB509A04859BFBE2BC7ABAD943F541A1263DEB290EE715DAEA28 | secret-assignment | 1116 | CANDIDATE SECRET constant consumed by rendered-secret detection tests |
| tests/test_browser.py | C04190508E5DD587A4DA5FD831F9A4F7956EDD6B4B56A67B7B3897B1BED2467C | secret-assignment | 714 | CANDIDATE PASSWORD constant used by make_store and fake-page fill/redaction tests |
| tests/test_core.py | 5CA8888AC3FC04B4B1CBAC68FE8A0D99DA0A275BACB46C487D41EA91B06D35B9 | secret-assignment | 628 | CANDIDATE direct literals in redactor masking/nested-structure tests |
| tests/test_core.py | 5CA8888AC3FC04B4B1CBAC68FE8A0D99DA0A275BACB46C487D41EA91B06D35B9 | secret-assignment | 1174 | CANDIDATE direct literals in redactor masking/nested-structure tests |
| tests/test_db.py | 0E59F2CBA17D0CBF4A75A0BB5BED6C73C0E1611EF84E87925E2FC06987BC0984 | secret-assignment | 513 | CANDIDATE SECRET constant consumed by test_assert_document_evidence_is_redacted |
| tests/test_explore_login_spa_live.py | 813E62F4923A660227229103A482467D2C1165C58FFCA9997D1D3BF3ED476E5A | secret-assignment | 3684 | CANDIDATE explicit correct/wrong-password local SPA test literals |
| tests/test_explore_login_spa_live.py | 813E62F4923A660227229103A482467D2C1165C58FFCA9997D1D3BF3ED476E5A | secret-assignment | 4120 | CANDIDATE explicit correct/wrong-password local SPA test literals |
| tests/test_explore_login_spa_live.py | 813E62F4923A660227229103A482467D2C1165C58FFCA9997D1D3BF3ED476E5A | secret-assignment | 4811 | CANDIDATE explicit correct/wrong-password local SPA test literals |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 1457 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 1758 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 2284 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 2571 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 2861 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 3509 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 3959 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_config.py | F9A9F44580971FE4FA1DABB463B8554A9134B4C0E198863E19A5DC1E0CAB3067 | secret-assignment | 4383 | CANDIDATE literals in configuration media/thinking/temperature tests |
| tests/test_gemini_schema.py | 060231C63B1C896B72E45C4FB7A809D0CB0D20C777FFE98DAED574110B1B76C4 | secret-assignment | 7897 | CANDIDATE provider schema test literal and _fake_gemini_call helper |
| tests/test_gemini_schema.py | 060231C63B1C896B72E45C4FB7A809D0CB0D20C777FFE98DAED574110B1B76C4 | secret-assignment | 9486 | CANDIDATE provider schema test literal and _fake_gemini_call helper |
| tests/test_onboard_pathlynks.py | 4826FDCA166BAAB46E5FFAC76BF19298D94299F1B67BCEEC6F5CDB9287B3A3F2 | secret-assignment | 739 | CANDIDATE PASSWORD constant used by seed_project_and_env and FakePage tests |
| tests/test_portal_persona.py | 69EB405BB5C60DF746979C01D16E64A16E40DC0830473110B396975E57B8D38D | secret-assignment | 5154 | CANDIDATE test_pp5_a_secret_token_never_reaches_the_persona_or_page literal |
| tests/test_providers.py | B0F561C84888E16F16118830065A3EC2FA2692A163F6E21C1F552CF2EA2DDBEF | secret-assignment | 775 | CANDIDATE API-key presence and missing-schema test literals |
| tests/test_providers.py | B0F561C84888E16F16118830065A3EC2FA2692A163F6E21C1F552CF2EA2DDBEF | secret-assignment | 1202 | CANDIDATE API-key presence and missing-schema test literals |
| tests/test_providers.py | B0F561C84888E16F16118830065A3EC2FA2692A163F6E21C1F552CF2EA2DDBEF | secret-assignment | 1691 | CANDIDATE API-key presence and missing-schema test literals |
| tests/test_providers.py | B0F561C84888E16F16118830065A3EC2FA2692A163F6E21C1F552CF2EA2DDBEF | secret-assignment | 2263 | CANDIDATE API-key presence and missing-schema test literals |
| tests/test_run_trace.py | 1F6692F91F2CAE9FB917889022681203896283344D2E3CEE23B45EFFEB9EB8E0 | secret-assignment | 8409 | CANDIDATE test_redactor_assert_clean_raises_on_a_surviving_secret literal |
| tests/test_secrets.py | BE21C06FA610E35E291F68FF7373482B9B59B4FE06F7C81E5D4BE506DD80A585 | secret-assignment | 556 | CANDIDATE PASSWORD constant used by fake store guard/resolve/redaction tests |
| tests/test_source_adapters_drive.py | AB7890EA316D2CC14409CBCD5E8F1123B939A891B6505D2EFB62D84F788DFFFA | secret-assignment | 5792 | CANDIDATE test_drive_credential_never_reaches_stored_sources literal |
| tests/test_ui_credential_exemption_scope.py | 741588D4CDD174FFB53F33074CB60EDF9E0CCEA3EB569C8C5FEB566B9562D104 | secret-assignment | 2828 | CANDIDATE split-credential exemption-boundary test literal |
| tests/test_ui_project_intake.py | 9632413E4D2736037BDA801A34A8C9106B4A136FC7A951DE285E741F8E122BFF | secret-assignment | 1554 | CANDIDATE intake/env-reference and credential-smuggling test literals |
| tests/test_ui_project_intake.py | 9632413E4D2736037BDA801A34A8C9106B4A136FC7A951DE285E741F8E122BFF | secret-assignment | 5233 | CANDIDATE intake/env-reference and credential-smuggling test literals |
| tests/test_ui_project_intake.py | 9632413E4D2736037BDA801A34A8C9106B4A136FC7A951DE285E741F8E122BFF | secret-assignment | 5845 | CANDIDATE intake/env-reference and credential-smuggling test literals |
| tests/test_portal_persona.py | 69EB405BB5C60DF746979C01D16E64A16E40DC0830473110B396975E57B8D38D | provider-token | 5163 | CANDIDATE same PP5 redaction fixture provider-format literal |
| qa/gates/at673-sessionstart-unclosed-detector.md | 0EA2555F37357A2B9B47C8EE5F6F405B03E69C09953FEE4B469AF34AF08430AD | unsupported-control | 9508 | UNRESOLVED historical QA backspace byte 8 |
| qa/gates/at673-sessionstart-unclosed-detector.md | 0EA2555F37357A2B9B47C8EE5F6F405B03E69C09953FEE4B469AF34AF08430AD | unsupported-control | 13203 | UNRESOLVED historical QA bell byte 7 |

Exact bounded heuristic patterns used (byte regex, NOT arbitrary-secret proof):

```python
patterns = {
 'private-key': rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
 'github-token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',
 'aws-access-key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'provider-token': rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{35}|xox[baprs]-[A-Za-z0-9-]{20,})',
 'credential-url-userinfo': rb'https?://[^\s/"\x27<>]+:[^\s/@"\x27<>]+@',
 'secret-assignment': rb'(?im)(?:["\x27]?\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)["\x27]?)\s*[:=]\s*(["\x27])([^\r\n"\x27]{1,256})\1',
}
```

Assignment-only placeholder policy: strip surrounding whitespace, lowercase,
then allow exactly empty, placeholder, example, example-key, test, test-key,
dummy, dummy-key, changeme, your-api-key, redacted; also exact case-sensitive
`{{SECRET:[A-Z][A-Z0-9_]*}}` byte pattern. No entropy guessing.
Strict decode UTF8 without replacement; reject NUL and controls 1..8,11,12,14..31.
A new ambiguous match fails closed. File16MiB/aggregate256MiB bounds retained.
These are the measured proposal rules, not installed product rules.

Reproduce the exact 41 tuple/hash/match controls without executing candidate
code (PowerShell, stdlib Python; reads only this appendix and named candidate
files; no values emitted). This verifies listed occurrences, not a new whole
1219 inventory or provenance approval:

```powershell
@'
import hashlib,re,json
from pathlib import Path
gate=Path(r'D:\autoTesting\qa\gates\t125-fullsuite-browser-egress.md').read_text(encoding='utf-8')
section=gate.split('## Source-screen exception proposal: exact 41 additional occurrences',1)[1]
table=section.split('Exact bounded heuristic patterns used',1)[0]
rules={
'secret-assignment':rb'(?im)(?:["\x27]?\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)["\x27]?)\s*[:=]\s*(["\x27])([^\r\n"\x27]{1,256})\1',
'provider-token':rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{35}|xox[baprs]-[A-Za-z0-9-]{20,})',
'unsupported-control':rb'[\x01-\x08\x0b\x0c\x0e-\x1f]'}
root=Path(r'D:\autoTesting\.worktrees\t125-cycle4')
count=0; candidates=0; unresolved=0; cache={}
for line in table.splitlines():
 if not line.startswith('| '):continue
 cells=[part.strip() for part in line.split('|')[1:-1]]
 if len(cells)!=5 or not re.fullmatch('[A-F0-9]{64}',cells[1]):continue
 path,sha,rule,offset,reason=cells; offset=int(offset)
 if path not in cache:
  raw=(root/path).read_bytes();assert len(raw)<=16777216
  raw.decode('utf-8','strict');cache[path]=raw
 raw=cache[path];assert hashlib.sha256(raw).hexdigest().upper()==sha
 assert re.compile(rules[rule]).match(raw,offset)
 if reason.startswith('CANDIDATE'):candidates+=1
 elif reason.startswith('UNRESOLVED'):unresolved+=1
 else:raise AssertionError('proposal status')
 print(json.dumps({'path':path,'sha256':sha,'rule':rule,'raw_offset':offset,'proposal':reason}))
 count+=1
assert (count,candidates,unresolved)==(41,39,2)
print('EXACT_TUPLES',count,'CANDIDATES',candidates,'UNRESOLVED',unresolved,'values_printed=0')
'@ | & 'D:\autoTesting\.venv\Scripts\python.exe' -I -B -
```

This evidence proposal does not authorize exceptions, source changes, container
creation, source export, live viewer use, provider/product traffic or PASS.

Independent exception review approved exact35testfixture+dbassert3859=36 new
tuples only; issues749115/t0554077/t1726550 and2controlbytes UNRESOLVED.
Provenance trace dispatched for3historical assignments without realcredential
reads/valueoutput. Solewriter sourceguard implementation dispatched afterasync
writerterminalF4B0, reviewedrules+36new+6priorURLexceptions only, failclosed at
unresolved/newmatches; actualbaseline expectedBLOCK notforcedgreen.
Async sharedbudget4fakeclock controls terminal0, containerremaining15/12/13/10s,
successguardrejects unresolvedfailures. RootF4B0syntaxcompile terminal0. Worker
exactinverse recoveredFC0657; nativepoll/kill hardbounds unproven; noactivation.

Sourceguard terminalB62C9C7F909CC40357A7BAE195999C34AE3A723ADEDD4666C20DCD954BA07782:
44exact reviewedexceptions installed(38new+6URL), actualASTcontrols terminal0,
baseline correctlyblocks t0554077 and at6739508/13203. No sourcebyte mutation.
Worker exactinverse recoveredF4B0; root draftsyntaxcompile terminal0.
Final scopedpreparation review dispatched sourceguard+sharedbudgetrepair,
NOT featureacceptance/runtimeclearance. Independent dependencyreview found
twofileexclusion compatiblecatalogsmoke but reducesdoctor/citation/history
coverage; humanaskedonce scoped1217smoke repin, originals/fulltreeobligations
retained. No approvalresponse/exclusion/newpin/export/runtime yet.

Final scopedpreparationreview APPROVE B62C9C... exact38new+6URL exceptions,
unresolvedexceptions0; sharedcleanupbudget defect repaired. NOT execution or
featurePASS. Root independently actualscreen3checks terminal0: approvedportal
fixtureaccepted, t055 and at673 expectedBLOCK; native/export/runtime0.
Read-only proposed1217 inventory digest95C6BD3FCD142136B5E086A8A10A350E0ABB06CB5EAD7F6CCDC20A03F19DA2E0
computed terminal0 afteractual1219 reconciliation; proposalonly no activepin
change/manifest/export. Still requires human reducedscopechoice, runtimeapproval,
viewerprovisioningchoice, fresh4GiB and boundreview/input/lane grants. Existing
original1219pin05B123 remainsunchanged; complete-tree doctor/fullsuite separate.

Answered: 2026-10-07 — option A (generalized): drop the native-egress sandbox precondition; local visible browser + full suite on any machine, against any product URL with its supplied credentials; test-suite guards kept (no real creds/.env, no paid calls, no external network in unit tests) — chat 2026-10-07, D-070
