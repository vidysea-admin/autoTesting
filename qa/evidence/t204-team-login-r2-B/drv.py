"""Real-server table for AU20 (coordinator B, cycle 2). Throwaway data only."""
import http.client, json, os, shutil, socket, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path("D:/autoTesting/.worktrees/check-t204-r2-b")
PY = str(W / ".venv/Scripts/python.exe")
SCR = Path(__file__).parent
OUT = Path("D:/autoTesting/qa/evidence/t204-team-login-r2-B")
EMAIL, PW = "admin@at.example", "scratch-pass-12345"
LAN = "192.168.1.4"
QA = "https://qa.example.com"
BASE_PORT = 18500


def base_env(rowdir, authdir):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("AUTOTESTER_", "UVICORN_"))}
    env.update(AUTOTESTER_ROOT=str(rowdir), AUTOTESTER_AUTH_DIR=str(authdir),
               PYTHONIOENCODING="utf-8")
    return env


def bootstrap(authdir, rowdir):
    env = base_env(rowdir, authdir)
    r = subprocess.run([str(W / ".venv/Scripts/autotester.exe"), "auth", "bootstrap-admin", "--email", EMAIL,
                        "--password-stdin"], input=PW + "\n", text=True, env=env, cwd=str(SCR),
                       capture_output=True, timeout=180)
    print("bootstrap", r.returncode, r.stdout.strip(), r.stderr.strip()[-300:])


def req(connect, port, method, host, origin=None, body=None):
    try:
        c = http.client.HTTPConnection(connect, port, timeout=30)
        c.putrequest(method, "/auth/login", skip_host=True, skip_accept_encoding=True)
        c.putheader("Host", host)
        if origin:
            c.putheader("Origin", origin)
        data = None
        if body is not None:
            data = urllib.parse.urlencode(body).encode()
            c.putheader("Content-Type", "application/x-www-form-urlencoded")
            c.putheader("Content-Length", str(len(data)))
        c.endheaders(data)
        r = c.getresponse()
        r.read()
        s = r.status
        c.close()
        return s
    except Exception as e:
        return f"ERR {type(e).__name__}"


def probe(connect, port, scheme, host):
    g = req(connect, port, "GET", host)
    p = req(connect, port, "POST", host, origin=f"{scheme}://{host}",
            body={"email": EMAIL, "password": PW})
    return {"scheme": scheme, "host": host, "GET": g, "POST": p, "served": g == 200 and p == 303}


def run_row(idx, row):
    rid = row["id"]
    port = BASE_PORT + idx
    rowdir = SCR / "data" / rid
    authdir = rowdir / "auth"
    shutil.rmtree(rowdir, ignore_errors=True)
    rowdir.mkdir(parents=True)
    shutil.copytree(SCR / "auth_template", authdir)
    env = base_env(rowdir, authdir)
    sub = lambda s: s.replace("{P}", str(port)).replace("{LAN}", LAN)
    if row["hosted"]:
        env.update(AUTOTESTER_HOSTED="1", AUTOTESTER_COOKIE_SECURE="0",
                   AUTOTESTER_FIRST_ADMIN_EMAIL="boss@at.example")
    for k, v in row["env"].items():
        env[k] = sub(v)
    args = [sub(a) for a in row["args"]]
    connect = sub(row["connect"])
    probes = []
    for item in row["probes"]:
        scheme, name = item[0], sub(item[1])
        p = item[2] if len(item) > 2 else port
        default = 80 if scheme == "http" else 443
        host = f"[{name}]" if ":" in name and not name.startswith("[") else name
        if p != default:
            host = f"{host}:{p}"
        probes.append((scheme, host))
    errlog = rowdir / "server.err"
    with open(errlog, "wb") as ef:
        proc = subprocess.Popen([PY, "-m", "uvicorn", "autotester.ui.app:app", *args],
                                env=env, cwd=str(rowdir), stdout=ef, stderr=subprocess.STDOUT)
    rec = {"id": rid, "cmd": "uvicorn autotester.ui.app:app " + " ".join(args),
           "env": {k: v for k, v in env.items()
                   if k.startswith(("AUTOTESTER_HOSTED", "AUTOTESTER_ALLOWED", "AUTOTESTER_PUBLIC",
                                    "AUTOTESTER_AUTH_DIS", "UVICORN_"))},
           "pid": proc.pid, "expect": row["expect"], "note": row["note"]}
    t0 = time.time()
    state = None
    while time.time() - t0 < 150:
        if proc.poll() is not None:
            state = "raised"
            break
        try:
            socket.create_connection((connect, port), timeout=1).close()
            state = "started"
            break
        except OSError:
            time.sleep(0.5)
    rec["startup"] = state or "timeout"
    if state == "raised":
        txt = errlog.read_text(errors="replace")
        rec["exit"] = proc.returncode
        msg = [ln for ln in txt.splitlines() if "AuthConfigError" in ln]
        rec["message"] = (msg[-1] if msg else (txt.strip().splitlines() or [""])[-1])[:400]
        r = subprocess.run([PY, str(SCR / "guard_eval.py")],
                           input=json.dumps({"probes": probes, "args": args}), text=True,
                           env=env, cwd=str(rowdir), capture_output=True, timeout=300)
        try:
            gw = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            gw = f"ERR {r.stdout[-200:]} {r.stderr[-300:]}"
        rec["guard_would_serve"] = gw
        rec["agree"] = (isinstance(gw, list) and not any(p["served"] for p in gw)) if probes else None
    elif state == "started":
        time.sleep(1)
        rec["probes"] = [probe(connect, port, s, h) for s, h in probes]
        rec["foreign_host_403"] = req(connect, port, "GET", "evil.example") == 403
        rec["agree"] = any(p["served"] for p in rec["probes"]) if probes else None
        rec["all_probes_served"] = all(p["served"] for p in rec["probes"]) if probes else None
    else:
        rec["agree"] = False
    if proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    try:
        proc.wait(timeout=20)
    except Exception:
        pass
    print(rid, rec["startup"], rec.get("agree"), flush=True)
    return rec


rows = []


def add(id, args, env=None, probes=None, expect=None, hosted=True, connect="127.0.0.1", note=""):
    rows.append(dict(id=id, args=args, env=env or {}, probes=probes or [], expect=expect,
                     hosted=hosted, connect=connect, note=note))


def both(name):
    return [("http", name), ("https", name)]


H = ["--host", "{LAN}", "--port", "{P}"]
LN = "{LAN}"
add("c01-lan-hosts-bare-custom-port", H, {"AUTOTESTER_ALLOWED_HOSTS": "{LAN}"}, both(LN), "raise", connect=LN)
add("c02-lan-origin-https-bare-custom-port", H, {"AUTOTESTER_ALLOWED_ORIGINS": "https://{LAN}"}, both(LN), "raise", connect=LN)
add("c03-lan-hosts-with-port-no-origin", H, {"AUTOTESTER_ALLOWED_HOSTS": "{LAN}:{P}"}, both(LN), "raise", connect=LN)
add("c04-lan-origin-http-port", H, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c05-lan-origin-https-port", H, {"AUTOTESTER_ALLOWED_ORIGINS": "https://{LAN}:{P}"}, both(LN), "start-any-scheme", connect=LN, note="scheme question")
add("c06-lan-hosts-and-origin", H, {"AUTOTESTER_ALLOWED_HOSTS": "{LAN}:{P}", "AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c07-lan-wrong-port-in-origin", H, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:1"}, both(LN), "raise", connect=LN)
add("c08-lan-other-host-listed", H, {"AUTOTESTER_ALLOWED_HOSTS": "at.example", "AUTOTESTER_ALLOWED_ORIGINS": "https://at.example"}, both(LN), "raise", connect=LN)
add("c09-lan-eq-form", ["--host={LAN}", "--port={P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c10-lan-eq-form-bare-origin", ["--host={LAN}", "--port={P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}"}, both(LN), "raise", connect=LN)
add("c11-lan-uvicorn-port-env", ["--host", "{LAN}"], {"UVICORN_PORT": "{P}", "AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c12-lan-uvicorn-port-env-origin-8000", ["--host", "{LAN}"], {"UVICORN_PORT": "{P}", "AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:8000"}, both(LN), "raise", connect=LN)
add("c13-lan-argv-port-beats-env", H, {"UVICORN_PORT": "9", "AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c14-lan-repeated-host-last-wins", ["--host", "10.9.9.9", "--host", "{LAN}", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c15-lan-repeated-port-last-wins", ["--host", "{LAN}", "--port", "1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c16-lan-repeated-port-same", ["--host", "{LAN}", "--port", "{P}", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c17-second-lan-addr", ["--host", "172.22.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://172.22.0.1:{P}"}, both("172.22.0.1"), "start", connect="172.22.0.1")
add("c18-lan-hosts-star-only", H, {"AUTOTESTER_ALLOWED_HOSTS": "*"}, both(LN), "raise", connect=LN)
add("c19-lan-lists-comma-blank", H, {"AUTOTESTER_ALLOWED_ORIGINS": ",", "AUTOTESTER_ALLOWED_HOSTS": " "}, both(LN), "raise", connect=LN)
add("c20-lan-star-plus-real-entry", H, {"AUTOTESTER_ALLOWED_ORIGINS": "*,http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("c21-lan-origin-caps-slash", H, {"AUTOTESTER_ALLOWED_ORIGINS": "HTTP://{LAN}:{P}/"}, both(LN), "start", connect=LN)
add("c22-lan-origins-space-separated", H, {"AUTOTESTER_ALLOWED_ORIGINS": "https://x.example http://{LAN}:{P}"}, both(LN), "start", connect=LN)
add("l01-127.0.0.1-foreign-list", ["--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("127.0.0.1"), "start")
add("l02-127.0.0.2-foreign-list", ["--host", "127.0.0.2", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("127.0.0.2"), "raise", connect="127.0.0.2")
add("l03-127.0.0.2-origin-listed", ["--host", "127.0.0.2", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://127.0.0.2:{P}"}, both("127.0.0.2"), "start", connect="127.0.0.2")
add("l04-localhost-foreign-list", ["--host", "localhost", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("localhost"), "start")
add("l05-localhost-port-env", ["--host", "localhost"], {"UVICORN_PORT": "{P}", "AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("localhost"), "start")
add("l06-localhost-eq-form", ["--host=localhost", "--port={P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "https://at.example"}, both("localhost"), "start")
add("l07-ipv6-loopback", ["--host", "::1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("::1"), "start", connect="::1")
add("l08-loopback-star-only-list", ["--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "*"}, both("127.0.0.1"), "raise")
add("l09-loopback-no-list", ["--host", "127.0.0.1", "--port", "{P}"], {}, both("127.0.0.1"), "raise")
add("l10-loopback-uppercase-LOCALHOST", ["--host", "LOCALHOST", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("localhost"), "start")
add("l11-repeated-wild-then-loop", ["--host", "0.0.0.0", "--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, both("127.0.0.1"), "start")
Wd = ["--host", "0.0.0.0", "--port", "{P}"]
LO = {"AUTOTESTER_ALLOWED_HOSTS": "qa.example.com", "AUTOTESTER_ALLOWED_ORIGINS": QA}
pub = [("https", "qa.example.com", 443)]
add("w01-wild4-missing-public", Wd, dict(LO), pub, "raise")
add("w02-wild4-public-right", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start")
add("w03-wild6-public-right", ["--host", "::", "--port", "{P}"], {**LO, "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start", connect="::1")
add("w04-wild6-missing-public", ["--host", "::", "--port", "{P}"], dict(LO), pub, "raise", connect="::1")
add("w05-wild4-public-bare-host", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "qa.example.com"}, pub, "raise")
add("w06-wild4-public-ftp", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "ftp://qa.example.com"}, pub, "raise")
add("w07-wild4-public-path", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": QA + "/app"}, pub, "raise")
add("w08-wild4-public-bad-port", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": QA + ":abc"}, pub, "raise")
add("w09-wild4-public-no-host", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "https://"}, pub, "raise")
add("w10-wild4-public-userinfo", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "https://me@qa.example.com"}, pub, "raise")
add("w11-wild4-public-star", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "*"}, pub, "raise")
add("w12-wild4-public-blank", Wd, {**LO, "AUTOTESTER_PUBLIC_ORIGIN": "   "}, pub, "raise")
add("w13-wild4-public-wrong-host", Wd, {"AUTOTESTER_ALLOWED_HOSTS": "other.example.com", "AUTOTESTER_ALLOWED_ORIGINS": "https://other.example.com", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w14-wild4-public-wrong-port", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "https://qa.example.com:8443", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w15-wild4-public-wrong-scheme", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "http://qa.example.com", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w16-wild4-public-hosts-only", Wd, {"AUTOTESTER_ALLOWED_HOSTS": "qa.example.com", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w17-wild4-public-origins-only", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": QA, "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start")
add("w18-wild4-public-explicit-443", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": QA, "AUTOTESTER_PUBLIC_ORIGIN": QA + ":443"}, pub, "start")
add("w19-wild4-public-caps-slash", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": QA, "AUTOTESTER_PUBLIC_ORIGIN": "HTTPS://QA.Example.com/"}, pub, "start")
add("w20-wild4-public-lan-http", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}", "AUTOTESTER_PUBLIC_ORIGIN": "http://{LAN}:{P}"}, [("http", LN)], "start", connect=LN)
add("w21-wild4-public-lan-nonlisted-port", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}", "AUTOTESTER_PUBLIC_ORIGIN": "http://{LAN}:1"}, [("http", LN)], "raise", connect=LN)
add("w22-wild4-public-loopback", Wd, {"AUTOTESTER_ALLOWED_HOSTS": "at.example", "AUTOTESTER_PUBLIC_ORIGIN": "http://localhost:{P}"}, [("http", "localhost")], "start")
add("w23-wild4-eq-form-missing", ["--host=0.0.0.0", "--port={P}"], dict(LO), pub, "raise")
add("w24-wild4-eq-form-public", ["--host=0.0.0.0", "--port={P}"], {**LO, "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start")
add("w25-loop-then-wild-repeated", ["--host", "127.0.0.1", "--host", "0.0.0.0", "--port", "{P}"], dict(LO), pub, "raise")
add("w26-env-UVICORN_HOST-wild-missing", ["--port", "{P}"], {**LO, "UVICORN_HOST": "0.0.0.0"}, pub, "raise")
add("w27-env-UVICORN_HOST-wild-public", ["--port", "{P}"], {**LO, "UVICORN_HOST": "0.0.0.0", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start")
add("w28-wild4-star-list-public-ok", Wd, {"AUTOTESTER_ALLOWED_HOSTS": "*", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w29-wild4-comma-list-public-ok", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": ",", "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w30-wild4-blank-list", Wd, {"AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "raise")
add("w31-wild4-star-plus-entry", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "*," + QA, "AUTOTESTER_PUBLIC_ORIGIN": QA}, pub, "start")
add("w32-odd-wildcard-host-0", ["--host", "0", "--port", "{P}"], dict(LO), pub, "raise", note="uvicorn binds '0' as every IPv4 address; the code sees a concrete host '0'")
add("w33-odd-wildcard-host-0-listed", ["--host", "0", "--port", "{P}"], {"AUTOTESTER_ALLOWED_ORIGINS": "http://0:{P}"}, [("http", "0")], "?", note="operator lists '0'; the real server binds every address and no public origin is required")
add("w34-odd-wildcard-ipv6-long", ["--host", "0:0:0:0:0:0:0:0", "--port", "{P}"], dict(LO), pub, "raise", connect="::1", note="long-form wildcard")
add("p01-lan-public-admitted", H, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P} " + QA, "AUTOTESTER_PUBLIC_ORIGIN": QA}, [("http", LN), ("https", "qa.example.com", 443)], "start", connect=LN)
add("p02-lan-public-not-admitted", H, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}", "AUTOTESTER_PUBLIC_ORIGIN": QA}, [("http", LN), ("https", "qa.example.com", 443)], "raise", connect=LN)
add("p03-lan-public-malformed", H, {"AUTOTESTER_ALLOWED_ORIGINS": "http://{LAN}:{P}", "AUTOTESTER_PUBLIC_ORIGIN": "qa.example.com"}, [("http", LN)], "raise", connect=LN)
add("p04-loop-public-not-admitted", ["--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example", "AUTOTESTER_PUBLIC_ORIGIN": QA}, [("http", "127.0.0.1"), ("https", "qa.example.com", 443)], "raise")
add("p05-loop-no-public", ["--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_ALLOWED_HOSTS": "at.example"}, [("http", "127.0.0.1")], "start")
add("n01-not-hosted-wild", Wd, {}, [("http", "127.0.0.1")], "start", hosted=False)
add("n02-not-hosted-loop", ["--host", "127.0.0.1", "--port", "{P}"], {}, [("http", "127.0.0.1")], "start", hosted=False)
add("n03-hosted-auth-disabled", ["--host", "127.0.0.1", "--port", "{P}"], {"AUTOTESTER_AUTH_DISABLED": "1", "AUTOTESTER_ALLOWED_HOSTS": "at.example"}, [("http", "127.0.0.1")], "raise")

add("w35-compose-default-localhost-wrong-lists", Wd, {"AUTOTESTER_ALLOWED_HOSTS": "wrong.example", "AUTOTESTER_ALLOWED_ORIGINS": "http://wrong.example:{P}", "AUTOTESTER_PUBLIC_ORIGIN": "https://localhost"}, [("http", LN)], "raise", connect=LN, note="what compose.prod.yml passes when neither AUTOTESTER_PUBLIC_ORIGIN nor AUTOTESTER_DOMAIN is set; the lists do not name the server")
add("w36-compose-default-localhost-no-lists-naming-server", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "https://other.example", "AUTOTESTER_PUBLIC_ORIGIN": "https://localhost"}, [("http", LN)], "raise", connect=LN, note="same, origin list names another host")
add("w37-loopback-public-http-localhost-explicit", Wd, {"AUTOTESTER_ALLOWED_ORIGINS": "https://other.example", "AUTOTESTER_PUBLIC_ORIGIN": "http://localhost:{P}"}, [("http", LN)], "raise", connect=LN, note="operator sets a loopback public origin on a wildcard bind; real users arrive by LAN")

if __name__ == "__main__":
    sel = sys.argv[1:]
    if not (SCR / "auth_template").exists():
        rd = SCR / "data" / "_boot"
        shutil.rmtree(rd, ignore_errors=True)
        rd.mkdir(parents=True)
        bootstrap(SCR / "auth_template", rd)
    todo = [(i, r) for i, r in enumerate(rows) if not sel or any(s in r["id"] for s in sel)]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda t: run_row(*t), todo))
    OUT.mkdir(parents=True, exist_ok=True)
    name = "real-server-table.json" if not sel else "real-server-table-" + "-".join(sel) + ".json"
    (OUT / name).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("DONE", len(res))
