# AU20 sub-check (r1-B, head 6ea9b688) -- read-only, in-process, no server

Script: `qa/evidence/t204-team-login-r1-B/au20_probe.py`
Run: `D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe D:/autoTesting/qa/evidence/t204-team-login-r1-B/au20_probe.py`
(imports `autotester` from the worktree src; sets sys.argv + os.environ, calls `check_startup()`.)

## Verdict
- Concrete-bind logic is mostly right but has two real defects (D1 port, D2 junk values) and smaller ones (D3, D4).
- Wildcard bind: the second clause of AU20 cannot be met literally, so it is a HUMAN_GATE-REQUEST.
- AU20 should not be PASS until D1/D2 are repaired or the owner narrows the sentence.

## How the hosted server is launched (docker/)
- `docker/entrypoint.sh`: `exec uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port 8000 --no-access-log` (wildcard bind, port 8000).
- `docker/compose.prod.yml`: publishes `127.0.0.1:8000` (or `AUTOTESTER_BIND=0.0.0.0` interim); optional Caddy (`--profile https`) with `reverse_proxy autotester:8000`.
- DEPLOY.md documents `AUTOTESTER_ALLOWED_HOSTS=<domain-or-ip>` and `AUTOTESTER_ALLOWED_ORIGINS=https://<domain>` (interim http: `http://<ip>:8000`). `.env.example` lines 49-50 and 73 document the keys.
- `check_startup()` runs only in the `ui/app.py:59` lifespan. It is skipped by `TestClient(app)` without a context manager, by `--lifespan off`, and (with no `--host` in argv) a programmatic `uvicorn.run(host=...)` is judged as 127.0.0.1.

## 1. Matrix (HOSTED=1; 20 bind strings x {--host V, --host=V} x {no port, --port 8443, --port=8443} x 8 allow-list configs)
Configs: H=host, H=host:PORT, O=http://host:PORT, O=https://host (no port), H=other, H=host:9999, H=host:8000, none set.
`--host V` and `--host=V` gave identical outcomes in every row (0 differences); `--port N` and `--port=N` identical.

| bind | outcome (ok unless stated) | my AU20 expectation | agree |
|---|---|---|---|
| 10.0.0.5, 2001:db8::5, app.example.com, App.Example.COM | ok only when bind (bare or with the effective port) is listed as host or origin netloc; RAISE for other, :9999, none | same (bind lower-cased) | yes |
| 127.0.0.1, localhost, ::1, 127.0.0.2, ::ffff:127.0.0.1 | ok in every config except "none set" | loopback always allowed (AU19) | yes |
| 0.0.0.0, ::, '' , '*' | ok in every config except "none set" | wildcard: only "at least one set" | yes (see 3) |
| app.example.com. (trailing dot) | RAISE in all configs, even H=app.example.com | judgment: same DNS name | NO, fail-closed |
| ::ffff:10.0.0.5 | RAISE unless the literal `[::ffff:10.0.0.5]` is listed | accept when 10.0.0.5 listed | NO, fail-closed |
| 0 (short form of 0.0.0.0) | treated as a hostname | wildcard | NO, fail-closed |
| 127.1, 0x7f.1 (loopback short forms) | treated as hostnames | loopback | NO, fail-closed |
| ::0, ::ffff:0.0.0.0 (wildcard equivalents) | RAISE in all configs | wildcard | NO, fail-closed |
| [::1] (bracketed text, uvicorn cannot bind it) | RAISE, message shows `[[::1]]` | n/a | n/a |

All disagreements are fail-closed. No unsafe false negative on the bind-spelling axis.

Env / argv shape:

| input | outcome | expectation | agree |
|---|---|---|---|
| UVICORN_HOST=10.0.0.5, H=10.0.0.5 / H=other | ok / RAISE | same | yes |
| UVICORN_HOST=10.0.0.5 plus argv `--host 127.0.0.1`, H=other | ok (argv wins) | argv wins | yes |
| no --host, H=other | ok (default 127.0.0.1) | same | yes |
| `--uds /tmp/s.sock`, H=other | ok | no TCP origin | yes |
| `--host` as last arg without value | ok (ignored) | uvicorn errors anyway | yes |
| shipped argv (`--host 0.0.0.0 --port 8000`), H+O / only H / only O / interim IP+http origin | ok | ok | yes |
| shipped argv, neither set | RAISE | RAISE | yes |
| shipped argv, H=other.example.com | ok | own origin unknowable | see 3 |
| shipped argv, H=`*`, O=`*`, H=`,`, H=`  ,  `, O=`/` | ok | should RAISE (nothing usable) | NO (D2) |

## 2. Unsafe false negatives and false positives
- **D1 (MEDIUM). A bare host satisfies the check at a non-default port, but no client Host header can match.**
  - `--host 10.0.0.5 --port 8443` with `AUTOTESTER_ALLOWED_HOSTS=10.0.0.5` (or `ALLOWED_ORIGINS=https://10.0.0.5`): startup ok.
  - A client sends `Host: 10.0.0.5:8443`; `_host_allowed("10.0.0.5:8443")` with that env is False (whole-string match, port included, AU19). Every request is 403.
  - Cause: `config.py` `_check_own_origin` does `_host_allowed(name) or _host_allowed(f"{name}:{port}")`. The first operand accepts a bare entry for any port. With no `--port` the same holds (Host `10.0.0.5:8000` is not matched by bare `10.0.0.5`).
  - Startup should have raised. Fail-closed at runtime, silent at startup: the exact mistake AU20 exists to catch.
  - Consistent repair: only the port-qualified form (or an origin netloc with that port) satisfies the check.
- **D2 (MEDIUM). "At least one is set" is a raw non-empty test, not "at least one usable entry".** (Pre-existing line in `check_startup`, not in the repair diff.)
  - `AUTOTESTER_ALLOWED_HOSTS=*`, `=,`, `="  ,  "`, `AUTOTESTER_ALLOWED_ORIGINS=*` or `=/` on the wildcard bind (the shipped container): startup ok.
  - `helpers._listed` drops `*` and empty items (AU18/AU19: `*` is ignored), so the effective list is empty: `_host_allowed("app.example.com")` is False and only loopback works.
  - Same with H=other.example.com: starts ok, the real public Host is refused.
  - Fail-closed at runtime, but AU20 says startup raises.
- **D3 (LOW). argv/env fidelity versus uvicorn.**
  - (a) `_option` takes the FIRST occurrence; uvicorn/click take the LAST. `--host 127.0.0.1 --host 10.0.0.5` with H=other: startup ok while uvicorn binds 10.0.0.5 (false negative, contrived). `--port 1111 --port 8443` is judged on 1111; `--port 8443 --port 1111` is judged on 8443.
  - (b) `UVICORN_PORT` (honoured by uvicorn) is never read. `UVICORN_PORT=9000`, bind 10.0.0.5, H=10.0.0.5:8000: ok (real origin :9000 unlisted). `UVICORN_PORT=9000`, H=10.0.0.5:9000: RAISE (false positive). `PORT` is not read by uvicorn either, so ignoring it is right.
  - (c) `--port abc` is judged as origin `10.0.0.5:abc`.
- **D4 (LOW, false positive).** Concrete private-LAN bind behind a separate proxy: `--host 10.0.0.5`, H=app.example.com, O=https://app.example.com: RAISE ("own origin 10.0.0.5:8000 is not allowed"). Legitimate shape; workaround `H=app.example.com,10.0.0.5:8000` works. Not the shipped shape. The message names the fix.
- No false positive for the shipped configuration: wildcard bind with H and/or O set is ok; the interim IP http config is ok; nothing set raises with the existing message.

## 3. Wildcard bind ruling: HUMAN_GATE-REQUEST (not NOT-MET on this alone)
- Contract sentence: "at least one of ... must be set, AND the server's own origin must be an allowed one".
  - Clause 1 is MET for wildcard (modulo D2).
  - Clause 2 has no defined meaning for `0.0.0.0` / `::`. The process cannot know its public name, and neither AU20 nor HO9 defines a key for it. The builder comment is accurate for the shipped container: the public name belongs to the proxy.
- What protects a hosted wildcard deployment today:
  - AU19, enforced by `_OriginGuard` on every request of any method: a Host that is not loopback, an ALLOWED_ORIGINS netloc, or an exact ALLOWED_HOSTS entry gets an empty 403.
  - AU18 Origin guard on every unsafe method, and the AU1 login gate.
  - `cookie_secure` is Secure when hosted.
  - A wrong or junk list therefore fails closed (users locked out), never open. The residual risk of not enforcing clause 2 on a wildcard is operational (a server that starts but refuses its own public name), not a confidentiality hole.
- The owner must decide ONE of:
  1. Accept the narrower reading: own origin is verified only when the bind names one address. Amend AU20 to say so. A wildcard needs only a non-empty USABLE list (after the D2 fix). Cheapest, no new key.
  2. Strengthen within existing keys: on a wildcard bind require at least one non-loopback entry in `AUTOTESTER_ALLOWED_HOSTS` or an `AUTOTESTER_ALLOWED_ORIGINS` netloc, so `*`, `,` and loopback-only are refused.
  3. Add an explicit public-origin key (e.g. `AUTOTESTER_PUBLIC_ORIGIN`, documented in `.env.example` per HO9) that must itself be an allowed origin; hosted with it unset raises. Strictest, changes DEPLOY.md and compose.
- Recommendation: 1 plus the D2 repair, because the container cannot know its public name and 3 changes the deployment contract. Owner's call.

## 4. Port semantics
- Default port `8000` when `--port` is absent (matches uvicorn). `_option("--port") or "8000"` handles `--port N` and `--port=N`. Repeated `--port` uses the first (D3a).
- `_host_allowed` compares the Host string whole.
  - Listed `host:8000` satisfies a bind with no `--port`.
  - Listed `host:8443` does not satisfy default 8000 (RAISE).
  - Listed bare `host` is accepted by the check at ANY port but does not admit the `host:port` Host header (D1).
  - `ALLOWED_ORIGINS` is reduced to netloc, so `https://host` behaves as a bare host.
- The check ignores `UVICORN_PORT` and `uvicorn.run` kwargs (D3b).
- IPv6: bracketed `[2001:db8::5]:8443` works; unbracketed `2001:db8::5` raises (Host headers are bracketed, correct); non-canonical bind text `2001:DB8:0::5` must be listed exactly as `[2001:db8:0::5]` (fail-closed).

## Reproduction
- D1: with `AUTOTESTER_HOSTED=1 AUTOTESTER_ALLOWED_HOSTS=10.0.0.5 AUTOTESTER_FIRST_ADMIN_EMAIL=a@b.invalid`, `sys.argv=['uvicorn','x:app','--host','10.0.0.5','--port','8443']`, `check_startup()` returns normally, then `_host_allowed('10.0.0.5:8443')` is False. Output: `startup ok; Host 10.0.0.5:8443 allowed = False`.
- D2: same env with `--host 0.0.0.0 --port 8000` and `AUTOTESTER_ALLOWED_HOSTS='*'`: startup ok; `_host_allowed('app.example.com')` is False.
- Both are also in the "RUNTIME CROSS-CHECK" block of `au20_probe.py` output.
