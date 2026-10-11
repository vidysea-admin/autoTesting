"""Blind wire check, checker B: send path against loopback servers run in this process."""
import contextlib, email, email.policy, io, json, logging, os, shutil, sys, time
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
CERTS = HERE / "certs"
PROJ = HERE / "proj"
shutil.rmtree(PROJ, ignore_errors=True)
PROJ.mkdir()

from miniserver import Server, make_certs  # noqa: E402

make_certs(str(CERTS))
os.environ["SSL_CERT_FILE"] = str(CERTS / "ca.pem")  # trust only my own CA for the 'good' cert

import autotester  # noqa: E402
from autotester.delivery import email as dmail  # noqa: E402
from autotester.delivery.inbox import MAX_ATTEMPTS, DeliveryLog, deliver_once  # noqa: E402
from autotester.delivery.message import render_message  # noqa: E402
from autotester.schema.delivery import (  # noqa: E402
    DeliveryChannel, Recipient, ReportLabel, ReportSummary, RunCounts, SmtpConfig)

PW = "WirePw-canary-7Qx93LmZ"
USER = "wireuser-canary-K4d1"
ADDR = "alice.rcpt@example.com"
UID = "u-7f3"
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
SUMMARY = dict(project_name="Demo Shop", run_id="run-0001", finished_at=NOW,
               counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3),
               coverage_line="Coverage: 12 of 15 screens (80%)", label=ReportLabel.FAILED,
               report_url="https://tester.example.test/runs/run-0001")
print("autotester from:", autotester.__file__)
print("TEST_MARKER:", dmail.TEST_MARKER, "set in env:", dmail.TEST_MARKER in os.environ)

log_lines: list[str] = []
class H(logging.Handler):
    def emit(self, r): log_lines.append(r.getMessage())
logging.getLogger().addHandler(H())
logging.getLogger().setLevel(logging.DEBUG)

rows = []
servers = []


def scrub_id(t): return t


def run_case(name, srv_kw, tls, timeout=15.0, summary=None, sender_name=None, user=USER, max_loop=8,
             scrub=scrub_id):
    srv = Server(certdir=str(CERTS), **srv_kw)
    servers.append(srv)
    cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user=user, sender_address="noreply@example.com",
                     tls=tls, sender_name=sender_name)
    adapter = dmail.SmtpAdapter(cfg, lambda: PW, timeout=timeout)
    log = DeliveryLog(PROJ / name / "log")
    to = Recipient(user_id=UID, address=ADDR)
    msg = render_message(ReportSummary(**(summary or SUMMARY)), scrub)
    out, err = io.StringIO(), io.StringIO()
    raised, recs, t, n0 = None, [], NOW, len(log_lines)
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            for _ in range(max_loop):
                rec = deliver_once(log, adapter, to, msg, run_id="run-0001", now=t, scrub=scrub)
                recs.append(rec)
                if rec is None or rec.status.value != "failed" or rec.next_retry_at is None:
                    break
                t = rec.next_retry_at
    except BaseException as e:  # noqa: BLE001
        raised = f"{type(e).__name__}: {e}"
    el = time.time() - t0
    final = log.latest(f"run-0001__email__{UID}")
    allrecs = log.records_for_key(f"run-0001__email__{UID}")
    row = dict(case=name, raised=raised, records=[(r.attempts, r.status.value, r.error, bool(r.next_retry_at)) for r in allrecs],
               server_messages=len(srv.messages), auth_attempts=len(srv.auth_attempts),
               auth_before_tls=[a[2] for a in srv.auth_attempts], elapsed_s=round(el, 1),
               stdout=len(out.getvalue()), stderr=len(err.getvalue()), logs=len(log_lines) - n0,
               srv_errors=srv.errors, tls_fail=[e for e in srv.events if e[0] == "tls-handshake-failed"],
               rcpts=[e[1] for e in srv.events if e[0] == "rcpt"][:2])
    rows.append(row)
    return srv, row


# ---- part 1: failure modes ------------------------------------------------------------------
srv, r = run_case("accept-plain", {}, "none")
good_msg = srv.messages[0] if srv.messages else b""
run_case("accept-starttls-good", dict(tls="starttls"), "starttls")
run_case("accept-implicit-ssl-good", dict(tls="implicit"), "ssl")
run_case("auth-reject-echo", dict(auth="reject"), "none")
run_case("drop-mid-data", dict(data="drop_mid"), "none")
run_case("drop-after-full-data", dict(data="drop_after_full"), "none")
run_case("rcpt-reject-echo", dict(rcpt="reject"), "none")
run_case("data-554-echo", dict(data="error"), "none")
run_case("silent-no-banner(timeout1s)", dict(silent="no_banner"), "none", timeout=1.0, max_loop=1)
run_case("silent-after-ehlo(timeout1s)", dict(silent="after_ehlo"), "none", timeout=1.0, max_loop=1)
run_case("silent-after-mailfrom(timeout1s)", dict(silent="after_mailfrom"), "none", timeout=1.0, max_loop=1)
run_case("no-starttls-advertised", dict(tls="none", advertise_starttls=False), "starttls")
run_case("starttls-selfsigned", dict(tls="starttls", cert="selfsigned"), "starttls", max_loop=1)
run_case("starttls-wronghost-cert", dict(tls="starttls", cert="wrong"), "starttls", max_loop=1)
run_case("implicit-selfsigned", dict(tls="implicit", cert="selfsigned"), "ssl", max_loop=1)
run_case("implicit-wronghost-cert", dict(tls="implicit", cert="wrong"), "ssl", max_loop=1)

# dribble: per-operation timeout vs total time
class Dribble(Server):
    pass
run_case("dribble(timeout1s)", dict(silent="dribble"), "none", timeout=1.0, max_loop=1)

# unreachable port (connection refused)
import socket
s0 = socket.socket(); s0.bind(("127.0.0.1", 0)); deadport = s0.getsockname()[1]; s0.close()
cfg = SmtpConfig(host="127.0.0.1", port=deadport, user=USER, sender_address="noreply@example.com", tls="none")
log = DeliveryLog(PROJ / "refused" / "log")
rec = deliver_once(log, dmail.SmtpAdapter(cfg, lambda: PW), Recipient(user_id=UID, address=ADDR),
                   render_message(ReportSummary(**SUMMARY)), run_id="run-0001", now=NOW, scrub=scrub_id)
rows.append(dict(case="connection-refused", raised=None, records=[(rec.attempts, rec.status.value, rec.error, bool(rec.next_retry_at))],
                 server_messages=0))

# password unset (live server so the code reaches the login step)
class _NoPw: pass
srv_np = Server(certdir=str(CERTS)); servers.append(srv_np)
cfg_np = SmtpConfig(host="127.0.0.1", port=srv_np.port, user=USER, sender_address="noreply@example.com", tls="none")
log = DeliveryLog(PROJ / "nopw" / "log")
rec = deliver_once(log, dmail.SmtpAdapter(cfg_np, lambda: None), Recipient(user_id=UID, address=ADDR),
                   render_message(ReportSummary(**SUMMARY)), run_id="run-0001", now=NOW, scrub=scrub_id)
rows.append(dict(case="password-unset", raised=None, records=[(rec.attempts, rec.status.value, rec.error, bool(rec.next_retry_at))],
                 server_messages=len(srv_np.messages), auth_attempts=len(srv_np.auth_attempts)))

# cleartext credentials to a non-loopback host are refused by config
env = {"AUTOTESTER_SMTP_HOST": "smtp.example.com", "AUTOTESTER_SMTP_PORT": "25",
       "AUTOTESTER_SMTP_FROM": "noreply@example.com", "AUTOTESTER_SMTP_USER": "u",
       "AUTOTESTER_SMTP_PASSWORD": "p", "AUTOTESTER_SMTP_TLS": "0"}
rows.append(dict(case="config:plain+creds+remote-host", config=repr(dmail.smtp_config_from_env(env))))
env2 = dict(env, AUTOTESTER_SMTP_TLS="")
c2 = dmail.smtp_config_from_env(env2)
rows.append(dict(case="config:unset-TLS-remote", tls=c2.tls if c2 else None))
env3 = dict(env, AUTOTESTER_SMTP_PORT="465", AUTOTESTER_SMTP_TLS="0")
c3 = dmail.smtp_config_from_env(env3)
rows.append(dict(case="config:port465+TLS=0", tls=c3.tls if c3 else None))
# repr/str of adapter and config never show the password or user
cfgx = SmtpConfig(host="127.0.0.1", port=1, user=USER, sender_address="noreply@example.com", tls="none")
ad = dmail.SmtpAdapter(cfgx, lambda: PW)
rows.append(dict(case="repr-leak", leaks=[x for x in (PW, USER) if x in repr(ad) + repr(cfgx) + str(cfgx) + str(ad)]))

for s in servers:
    s.close()

# ---- grep the whole scratch project ---------------------------------------------------------
import base64
needles = {"password": PW.encode(), "user": USER.encode(), "recipient": ADDR.encode(), "rcpt-local": b"alice.rcpt",
           "b64(user+pw)": base64.b64encode(f"\0{USER}\0{PW}".encode()), "b64(pw)": base64.b64encode(PW.encode())}
hits = {k: [] for k in needles}
nfiles = 0
for p in PROJ.rglob("*"):
    if p.is_file():
        nfiles += 1
        data = p.read_bytes()
        for k, nd in needles.items():
            if nd in data:
                hits[k].append(str(p.relative_to(PROJ)))
print("files under scratch project:", nfiles)
print("disk grep hits:", json.dumps(hits))
allout = "\n".join(log_lines)
print("log lines captured (all cases):", len(log_lines), "| contain pw/user/addr:",
      [k for k, nd in needles.items() if nd.decode(errors="ignore") in allout])

for r in rows:
    print(json.dumps(r, default=str))

# ---- part 2 normal bytes --------------------------------------------------------------------
print("\n=== wire bytes for the normal send ===")
em = email.message_from_bytes(good_msg.rstrip(b".\r\n") if False else good_msg, policy=email.policy.default)
print("headers:", [(k, v if k != "Message-ID" else "<id>") for k, v in em.items()])
print("is_multipart:", em.is_multipart(), "content-type:", em.get_content_type(), "parts:", len(list(em.walk())))
print("To count:", len(em.get_all("To") or []), "Cc:", em.get_all("Cc"), "Bcc:", em.get_all("Bcc"))
body_wire = em.get_content()
tpl = (Path(autotester.__file__).parent / "delivery" / "templates" / "report_email.txt").read_text("utf-8")
from string import Template
expected = Template(tpl).substitute(project="Demo Shop", run_id="run-0001", finished="2026-10-11 12:00 UTC",
    label="failed", passed=7, failed=2, blocked=1, inconclusive=3, coverage=SUMMARY["coverage_line"],
    link=SUMMARY["report_url"])
exp_body = expected.partition("\n\n")[2].strip() + "\n"
print("body equals independently-filled template:", body_wire.replace("\r\n", "\n") == exp_body)
print("BODY:\n" + body_wire)
print("envelope:", [r for r in rows if r["case"] == "accept-plain"][0]["rcpts"])
