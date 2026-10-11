import socketserver, threading, email, email.policy
from datetime import UTC, datetime
from autotester.delivery.email import SmtpAdapter
from autotester.delivery.message import render_message
from autotester.schema.delivery import *

class H(socketserver.StreamRequestHandler):
    def handle(self):
        S = self.server.cap; w = lambda s: (self.wfile.write(s.encode() + b"\r\n"), self.wfile.flush())
        w("220 hi"); data = False; buf = []
        while l := self.rfile.readline():
            t = l.rstrip(b"\r\n")
            if data:
                if t == b".": data = False; S["msg"] = b"\r\n".join(buf); w("250 q")
                else: buf.append(t)
                continue
            v = t.split(b" ", 1)[0].upper()
            S["cmds"].append(t.decode(errors="replace"))
            if v == b"EHLO": self.wfile.write(b"250 x\r\n"); self.wfile.flush()
            elif v == b"DATA": data = True; w("354 go")
            elif v == b"QUIT": w("221 b"); return
            else: w("250 ok")

srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.cap = {"cmds": []}; srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
cfg = SmtpConfig(host="127.0.0.1", port=srv.server_address[1], sender_address="rep@x.test", sender_name="Tëst 中", tls="none")
ad = SmtpAdapter(cfg, lambda: None)
s = ReportSummary(project_name="Café 中文 Shop", run_id="run-1", finished_at=datetime(2026, 10, 11, tzinfo=UTC),
                  counts=RunCounts(passed=1, failed=0, blocked=0, inconclusive=0), coverage_line="Coverage: 3 of 4 ✓",
                  label=ReportLabel.GREEN, report_url="https://t.test/runs/r1")
ad.send(Recipient(user_id="u1", address="to@x.test"), render_message(s), key="k")
raw = srv.cap["msg"]; print("wire is 7-bit clean:", all(b < 128 for b in raw))
p = email.message_from_bytes(raw, policy=email.policy.default)
print("subject:", p["Subject"]); print("from:", p["From"]); print("body:", p.get_content())
print("commands:", srv.cap["cmds"])
