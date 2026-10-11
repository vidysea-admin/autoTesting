import email, email.policy, re, sys
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
from autotester.schema.delivery import *  # noqa: E402,F403

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
S = ReportSummary(project_name="Demo Shop", run_id="run-0001", finished_at=NOW,
                  counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3),
                  coverage_line="Coverage: 12 of 15 screens (80%)", label=ReportLabel.FAILED,
                  report_url="https://tester.example.test/runs/run-0001")
srv = Server(certdir=str(HERE / "certs"))
cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user=None, sender_address="noreply@example.com", tls="none")
deliver_once(DeliveryLog(HERE / "proj4"), dmail.SmtpAdapter(cfg, lambda: "x"),
             Recipient(user_id="u-7f3", address="alice.rcpt@example.com"), render_message(S),
             run_id="run-0001", now=NOW, scrub=lambda t: t)
raw = srv.messages[0]
assert raw.endswith(b"\r\n.\r\n")
em = email.message_from_bytes(raw[:-3], policy=email.policy.default)
tpl = (Path(autotester.__file__).parent / "delivery" / "templates" / "report_email.txt").read_text("utf-8")
exp = Template(tpl).substitute(project="Demo Shop", run_id="run-0001", finished="2026-10-11 12:00 UTC", label="failed",
                               passed=7, failed=2, blocked=1, inconclusive=3, coverage=S.coverage_line, link=S.report_url)
head, _, body = exp.partition("\n\n")
print("subject equal:", str(em["Subject"]) == head.removeprefix("Subject: "))
print("body equals independent fill:", em.get_content().replace("\r\n", "\n") == body.strip() + "\n")
print("header names:", [k for k, _ in em.items()])
print("attachments:", len(list(em.iter_attachments())), "| content types:", [p.get_content_type() for p in em.walk()])
print("raw has boundary/Content-Disposition:", b"boundary" in raw, b"Content-Disposition" in raw)
print("envelope MAIL FROM / RCPT:", [e[1] for e in srv.events if e[0] in ("mailfrom", "rcpt")])
print("RAW (first 700 bytes):\n" + raw[:700].decode())
srv.close()

# the grep-guard bypass: what does the builder's regex see?
rx = r"^\s*(import smtplib|from smtplib)"
for line in ["import smtplib", "from smtplib import SMTP", "import os, smtplib", "import  smtplib", "import ssl, smtplib as s",
             "importlib.import_module('smtplib')", "__import__('smtplib')", "from smtplib\\\n import SMTP"]:
    print(f"guard regex matches {line!r}:", bool(re.search(rx, line, re.M)))
