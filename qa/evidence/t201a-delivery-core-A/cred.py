"""Blind-check A: credential + TLS attacks with a hostile fake SMTP server on 127.0.0.1."""
import base64, io, logging, os, pickle, socket, ssl, sys, tempfile, threading, traceback, contextlib
from datetime import UTC, datetime
from pathlib import Path
from autotester.delivery.email import SmtpAdapter, TransportError, smtp_config_from_env, select_transport
from autotester.delivery.inbox import DeliveryLog, deliver_once
from autotester.schema.delivery import *
PW = "Zq9!SECRETpw-ECHOME"
CERTS = Path(os.environ["ATK_CERTS"])
NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)


class Srv:
    def __init__(s, mode, tls=None):
        s.mode, s.tls, s.log, s.auth_seen, s.plain_auth_seen = mode, tls, [], [], False
        s.sock = socket.socket(); s.sock.bind(("127.0.0.1", 0)); s.sock.listen(5)
        s.port = s.sock.getsockname()[1]; s.cert = None
        threading.Thread(target=s.run, daemon=True).start()

    def ctx(s):
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        c.load_cert_chain(CERTS / f"{s.cert}.pem", CERTS / f"{s.cert}.key")
        return c

    def run(s):
        while True:
            try:
                c, _ = s.sock.accept()
            except OSError:
                return
            threading.Thread(target=s.handle, args=(c,), daemon=True).start()

    def handle(s, c):
        try:
            c.settimeout(5)
            if s.tls == "implicit":
                try:
                    c = s.ctx().wrap_socket(c, server_side=True)
                except Exception as e:
                    s.log.append("tls-handshake-failed:" + type(e).__name__); return
            f = c.makefile("rwb", buffering=0)
            w = lambda t: f.write(t.encode() + b"\r\n")
            w("220 hi"); secure = s.tls == "implicit"
            while True:
                l = f.readline()
                if not l:
                    return
                t = l.decode(errors="replace").rstrip("\r\n"); s.log.append(t[:40]); v = t.split(" ", 1)[0].upper()
                if v == "EHLO":
                    if s.mode == "ehlo_echo":
                        w(f"250-hello {PW}\r\n250 AUTH PLAIN")
                    else:
                        caps = ["250-x"]
                        if s.tls == "starttls" and not secure and s.mode != "strip":
                            caps.append("250-STARTTLS")
                        caps.append("250 AUTH PLAIN LOGIN"); w("\r\n".join(caps))
                elif v == "STARTTLS":
                    w("220 go")
                    try:
                        c = s.ctx().wrap_socket(c, server_side=True)
                    except Exception as e:
                        s.log.append("tls-handshake-failed:" + type(e).__name__); return
                    f = c.makefile("rwb", buffering=0); secure = True
                elif v == "AUTH":
                    s.auth_seen.append(secure)
                    if not secure:
                        s.plain_auth_seen = True
                    if s.mode == "auth_echo":
                        w(f"535 5.7.8 Authentication failed for smtp-user pass={PW} {t}")
                    else:
                        w("235 ok")
                elif v == "MAIL":
                    w(f"550 mail rejected {PW}" if s.mode == "mail_echo" else "250 ok")
                elif v == "RCPT":
                    w(f"550 no such user {t} {PW}" if s.mode == "rcpt_echo" else "250 ok")
                elif v == "DATA":
                    if s.mode == "data_echo":
                        w(f"554 data refused {PW}")
                    else:
                        w("354 go")
                        while f.readline().rstrip(b"\r\n") != b".":
                            pass
                        w("250 queued")
                elif v == "QUIT":
                    w("221 bye"); return
                else:
                    w(f"999 weird {PW}" if s.mode == "garbage" else "250 ok")
        except Exception as e:
            s.log.append("srv-exc:" + type(e).__name__)


def run_case(name, mode, tls_server=None, tls="none", password=PW, cert=None, ssl_cert_file=None):
    srv = Srv(mode, tls_server); srv.cert = cert
    td = Path(tempfile.mkdtemp(prefix="atk-")); out = io.StringIO(); err = io.StringIO()
    hs = io.StringIO(); h = logging.StreamHandler(hs); root = logging.getLogger(); root.addHandler(h)
    old = root.level; root.setLevel(1)
    if ssl_cert_file:
        os.environ["SSL_CERT_FILE"] = str(ssl_cert_file)
    else:
        os.environ.pop("SSL_CERT_FILE", None)
    env = {"AUTOTESTER_SMTP_HOST": "127.0.0.1", "AUTOTESTER_SMTP_PORT": str(srv.port),
           "AUTOTESTER_SMTP_FROM": "rep@x.test", "AUTOTESTER_SMTP_USER": "smtp-user",
           "AUTOTESTER_SMTP_PASSWORD": password}
    if tls == "none":
        env["AUTOTESTER_SMTP_TLS"] = "0"
    ad = select_transport(env, td / "outbox")
    log = DeliveryLog(td / "log"); to = Recipient(user_id="u1", address="to@x.test")
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rec = deliver_once(log, ad, to, RenderedMessage(subject="s", body="b"), run_id="run-1", now=NOW, scrub=lambda s: s)
    root.removeHandler(h); root.setLevel(old)
    blob = [p.read_text(errors="replace") for p in td.rglob("*") if p.is_file()]
    cfg = getattr(ad, "_config", None)
    texts = {"files": "\n".join(blob), "stdout": out.getvalue(), "stderr": err.getvalue(), "logging": hs.getvalue(),
             "repr(adapter)": repr(ad) + str(ad), "record": rec.model_dump_json() if rec else "",
             "cfg": (repr(cfg) + (cfg.model_dump_json() if cfg else ""))}
    try:
        pickle.dumps(ad); pk = "pickle SUCCEEDED"
    except Exception as e:
        pk = "pickle refused: " + type(e).__name__
    b64 = base64.b64encode(("\0smtp-user\0" + password).encode()).decode()
    leaks = [k for k, v in texts.items() if password in v or b64 in v]
    try:
        ad.send(to, RenderedMessage(subject="s", body="b"), key="k2"); direct = "send ok"; chain = ""
    except TransportError as e:
        chain = []; x = e
        while x is not None:
            chain.append(f"{type(x).__name__}:{x!s:.70}"); x = x.__cause__ or x.__context__
        chain = " <- ".join(chain)
        tb = "".join(traceback.format_exception(e))
        if password in tb:
            leaks.append("traceback.format_exception")
        direct = f"TransportError({str(e)!r}) suppress_ctx={e.__suppress_context__}"
        chain = ("PW REACHABLE via __context__: " if password in chain else "ctx chain clean: ") + chain
    except Exception as e:
        direct = "other " + type(e).__name__; chain = ""
    print(f"[{name}] status={rec.status.value if rec else None} err={rec.error if rec else None!r} "
          f"AUTH_secure={srv.auth_seen} plainAUTH={srv.plain_auth_seen} leaks={leaks} {pk}\n    direct: {direct} | {chain}",
          flush=True)
    srv.sock.close(); return srv, leaks, rec


allleaks = []
for m in ["auth_echo", "ehlo_echo", "mail_echo", "rcpt_echo", "data_echo", "garbage"]:
    s, l, r = run_case("plain-loopback " + m, m); allleaks += l
s, l, r = run_case("unicode password echo", "auth_echo", password="päss中" + PW); allleaks += l
print("=== TLS ===")
s, l, r = run_case("starttls required, server strips STARTTLS", "strip", "starttls", tls="starttls"); print("   AUTH seen:", s.auth_seen, "server saw:", s.log)
s, l, r = run_case("starttls, untrusted CA", "ok", "starttls", tls="starttls", cert="good"); print("   AUTH seen:", s.auth_seen, s.log[-3:])
s, l, r = run_case("starttls, wrong hostname (CA trusted)", "ok", "starttls", tls="starttls", cert="wrong", ssl_cert_file=CERTS / "ca.pem"); print("   AUTH seen:", s.auth_seen, s.log[-3:])
s, l, r = run_case("starttls, GOOD cert, CA trusted (positive control)", "ok", "starttls", tls="starttls", cert="good", ssl_cert_file=CERTS / "ca.pem"); print("   AUTH seen:", s.auth_seen)


def implicit(name, cert, ca):
    srv = Srv("ok", "implicit"); srv.cert = cert
    if ca:
        os.environ["SSL_CERT_FILE"] = str(ca)
    else:
        os.environ.pop("SSL_CERT_FILE", None)
    cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user="smtp-user", sender_address="rep@x.test", tls="ssl")
    ad = SmtpAdapter(cfg, lambda: PW)
    try:
        ad.send(Recipient(user_id="u1", address="to@x.test"), RenderedMessage(subject="s", body="b"), key="k"); res = "SENT"
    except TransportError as e:
        res = "refused: " + str(e)
    print(f"[implicit ssl {name}] {res} AUTH_seen={srv.auth_seen}"); srv.sock.close()


implicit("untrusted CA", "good", None); implicit("wrong hostname", "wrong", CERTS / "ca.pem")
implicit("good cert trusted CA (positive control)", "good", CERTS / "ca.pem")
for host in ["smtp.example.test", "10.0.0.5", "127.0.0.2", "LOCALHOST", "localhost", "::1", "127.0.0.1"]:
    try:
        SmtpConfig(host=host, port=25, user="u", sender_address="a@x.test", tls="none"); r = "allowed"
    except ValueError:
        r = "refused"
    print(f"plain+credentials host={host}: {r}")
base = {"AUTOTESTER_SMTP_HOST": "smtp.example.test", "AUTOTESTER_SMTP_FROM": "a@x.test"}
for extra in [{"AUTOTESTER_SMTP_PORT": "587", "AUTOTESTER_SMTP_USER": "u", "AUTOTESTER_SMTP_TLS": "0"},
              {"AUTOTESTER_SMTP_PORT": "25", "AUTOTESTER_SMTP_TLS": "none"},
              {"AUTOTESTER_SMTP_PORT": "465", "AUTOTESTER_SMTP_TLS": "0", "AUTOTESTER_SMTP_USER": "u"},
              {"AUTOTESTER_SMTP_PORT": "587", "AUTOTESTER_SMTP_USER": "u", "AUTOTESTER_SMTP_TLS": "weird"},
              {"AUTOTESTER_SMTP_PORT": "587", "AUTOTESTER_SMTP_USER": "u"}]:
    c = smtp_config_from_env({**base, **extra})
    print("env", {k[len('AUTOTESTER_SMTP_'):]: v for k, v in extra.items()}, "->", None if c is None else (c.tls, c.user))
print("\nALL LEAKS:", allleaks)
