"""Hostile-value wire check, checker B."""
import email, email.policy, email.utils, os, sys
from datetime import UTC, datetime
from pathlib import Path
from string import Template

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from miniserver import Server  # noqa: E402

import autotester  # noqa: E402
from autotester.delivery import email as dmail  # noqa: E402
from autotester.delivery.inbox import DeliveryLog, deliver_once  # noqa: E402
from autotester.delivery.message import render_message  # noqa: E402
from autotester.schema.delivery import (  # noqa: E402
    Recipient, ReportLabel, ReportSummary, RunCounts, SmtpConfig, RenderedMessage)

CERTS = HERE / "certs"
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
BASE = dict(project_name="Demo Shop", run_id="run-0001", finished_at=NOW,
            counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3),
            coverage_line="Coverage: 12 of 15 screens (80%)", label=ReportLabel.FAILED,
            report_url="https://tester.example.test/runs/run-0001")
tpl = (Path(autotester.__file__).parent / "delivery" / "templates" / "report_email.txt").read_text("utf-8")
srv = Server(certdir=str(CERTS))
nsent = 0


def wire_send(summary_kw, rcpt_addr="alice.rcpt@example.com", sender_name=None, tag="x", model_construct=False):
    """Returns (rejected_by, info). Sends over real smtplib to the loopback server."""
    global nsent
    try:
        summ = ReportSummary(**{**BASE, **summary_kw})
        to = Recipient(user_id="u-7f3", address=rcpt_addr)
        cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user=None, sender_address="noreply@example.com",
                         tls="none", sender_name=sender_name)
    except Exception as e:  # noqa: BLE001
        return "schema:" + type(e).__name__, None
    msg = render_message(summ)
    before = len(srv.messages)
    ad = dmail.SmtpAdapter(cfg, lambda: "x")
    log = DeliveryLog(HERE / "proj2" / tag)
    rec = deliver_once(log, ad, to, msg, run_id="run-0001", now=NOW, scrub=lambda t: t)
    if len(srv.messages) == before:
        return "transport:" + str(rec.error), None
    raw = srv.messages[-1]
    em = email.message_from_bytes(raw, policy=email.policy.default)
    info = dict(
        from_=str(em["From"]), to=em.get_all("To"), cc=em.get_all("Cc"), bcc=em.get_all("Bcc"),
        replyto=em.get_all("Reply-To"), subject=str(em["Subject"]), nparts=len(list(em.walk())),
        n_from_addrs=len(email.utils.getaddresses(em.get_all("From") or [])),
        n_to_addrs=len(email.utils.getaddresses(em.get_all("To") or [])),
        nheaders=len(em.items()), rcpt=[e[1] for e in srv.events if e[0] == "rcpt"][-1],
        body=em.get_content())
    return "sent", info


def show(label, res):
    status, info = res
    if info is None:
        print(f"{label:70s} -> {status}")
        return
    print(f"{label:70s} -> {status}; From={info['from_']!r} To={info['to']} Cc={info['cc']} Bcc={info['bcc']} "
          f"ReplyTo={info['replyto']} Subject={info['subject']!r} fromAddrs={info['n_from_addrs']} toAddrs={info['n_to_addrs']} "
          f"parts={info['nparts']} {info['rcpt']}")


print("== baseline ==")
show("normal", wire_send({}, tag="n"))
print("\n== project_name (-> Subject and body) ==")
for i, v in enumerate(["Shop\r\nBcc: x@evil.test", "Shop\nBcc: x@evil.test", "Shop Bcc: x@evil.test",
                       "Shop\u0085Bcc: x@evil.test", "Shop\x0bBcc: x@evil.test", "Shop\x00x",
                       "=?utf-8?b?QmNjOiB4QGV2aWwudGVzdA==?=", "=?utf-8?q?Shop=0D=0ABcc:_x@evil.test?=",
                       "Shop <evil@x.test>", "Shop; Bcc: x@evil.test", "Shop, Bcc: x@evil.test", "Ünï shop ‮",
                       'Shop"quote', "Subject: spoof", "A" * 200, "A" * 201, "$project ${run_id} $$"]):
    show("project_name=" + repr(v)[:55], wire_send({"project_name": v}, tag=f"p{i}"))
print("\n== coverage_line / body smuggling ==")
for i, v in enumerate([".", "..", "Coverage ok\u0085.", "x\r\n.\r\nMAIL FROM:<a@b.test>", "-- ", "=3D =\n"]):
    st, info = wire_send({"coverage_line": v}, tag=f"c{i}")
    show("coverage_line=" + repr(v)[:50], (st, info))
    if info:
        print("      body lines:", [l for l in info["body"].splitlines() if "Coverage" in l or l.startswith(".") or l == v][:3])
print("\n== sender_name ==")
for i, v in enumerate(["Eve\r\nBcc: x@y.test", "Eve <evil@example.com>", "=?utf-8?b?RXZl?= <e@e.test>",
                       "Eve, Mallory <m@x.test>", 'Eve "the" tester', "Ünï", "A" * 100, "A" * 101, " x"]):
    show("sender_name=" + repr(v)[:50], wire_send({}, sender_name=v, tag=f"s{i}"))
print("\n== report_url ==")
for i, v in enumerate(["javascript:alert(1)", "JaVaScRiPt:alert(1)", "//evil.example/x", "///evil.example/x",
                       "https://user:pw@evil.example/x", "https://evil.example@good.example.test/x",
                       "https://evil.example/x?token=1", "https://evil.example/x#f", "/runs/r1#f", "/runs/r1?t=1",
                       "/runs/run-0001", "https://tester.example.test:8443/runs/r1", "https://x.test:99999/", "http://127.0.0.1/",
                       "ftp://evil.example/x", "data:text/html,<script>", "/\\evil.example", "\\\\evil.example\\x",
                       "https://evil.example/\r\nBcc: x@y.test", "https://é.test/x", "https://good.example.test/runs/r1 evil",
                       "https://good.example.test/a%0d%0aBcc:x", "https://good.example.test/%2e%2e/x", "/", "https://a.b/"]):
    show("report_url=" + repr(v)[:50], wire_send({"report_url": v}, tag=f"u{i}"))
print("\n== recipient address ==")
for i, v in enumerate(["a@x.test,b@y.test", "a@x.test\r\nRCPT TO:<b@y.test>", "a@x.test b@y.test", '"a b"@x.test',
                       "a@x.test>", "<a@x.test>", "a@[127.0.0.1]", "a@x.test\n", "a@x.t€st", "a@x.test;b@y.test",
                       "a+tag@x.test", "Alice <a@x.test>", "a@localhost", "a@x", ".a@x.test", "a..b@x.test", "A@X.TEST", "a@x.test."]):
    show("address=" + repr(v)[:50], wire_send({}, rcpt_addr=v, tag=f"a{i}"))
print("\n== model_construct bypass (defence in depth below the schema) ==")
try:
    bad = Recipient.model_construct(user_id="u-7f3", address="a@x.test\r\nRCPT TO:<b@y.test>")
    cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user=None, sender_address="noreply@example.com", tls="none")
    n0 = len([e for e in srv.events if e[0] == "rcpt"])
    log = DeliveryLog(HERE / "proj2" / "mc")
    rec = deliver_once(log, dmail.SmtpAdapter(cfg, lambda: "x"), bad, render_message(ReportSummary(**BASE)),
                       run_id="run-0001", now=NOW, scrub=lambda t: t)
    print("bad address (CRLF) via model_construct ->", rec.status.value, rec.error,
          "| extra RCPT seen by server:", [e[1] for e in srv.events if e[0] == "rcpt"][n0:])
    bad2 = RenderedMessage.model_construct(subject="Hi\r\nBcc: x@y.test", body="b")
    rec = deliver_once(DeliveryLog(HERE / "proj2" / "mc2"), dmail.SmtpAdapter(cfg, lambda: "x"),
                       Recipient(user_id="u-7f3", address="a@x.test"), bad2, run_id="run-0002", now=NOW, scrub=lambda t: t)
    print("CRLF subject via model_construct ->", rec.status.value, rec.error)
except Exception as e:  # noqa: BLE001
    print("model_construct case raised", type(e).__name__, e)
srv.close()
