"""Blind-check A: header / recipient injection matrix. Wire-level via a loopback server."""
import email, email.policy, json, sys, socketserver, threading, smtplib
from datetime import UTC, datetime
from autotester.delivery.email import build_mime, SmtpAdapter, TransportError
from autotester.delivery.message import render_message
from autotester.schema.delivery import *

NOW = datetime(2026,10,11,12,0,tzinfo=UTC)
def summ(**o):
    b=dict(project_name="Demo",run_id="run-1",finished_at=NOW,counts=RunCounts(passed=1,failed=0,blocked=0,inconclusive=0),
           coverage_line="Coverage 1 of 1",label=ReportLabel.GREEN,report_url="https://t.test/runs/r1")
    b.update(o); return ReportSummary(**b)

res=[]
def rec(name, outcome): res.append((name,outcome)); print(f"{name:60s} {outcome}")

# recipients
bad = ["a@x.test\r\nBcc: z@y.test","a@x.test\nBcc: z@y.test","a@x.test,b@y.test","a@x.test;b@y.test","a@x.test b@y.test",
       "<a@x.test>","\"a b\"@x.test","a@x.test>","ä@x.test","a@x.tést","a@x.test\n","a@x.test ","a\x00@x.test",
       "a@x.test%0d%0aBcc:z@y.test","a"*65+"@x.test","a@"+"b"*64+".test","a@[127.0.0.1]","a@x.test Bcc:z@y.test",
       "a@@x.test","@x.test","a@x","a@x.test.","(c)a@x.test","a@x.test\r","\ta@x.test","a\@x.test","a@x.test\u0085"]
for a in bad:
    try: Recipient(user_id="u1",address=a); rec("recipient accepted "+repr(a)[:40],"ACCEPTED")
    except ValueError: pass
# very long
try: Recipient(user_id="u1",address="a@"+("b"*60+".")*5+"test"); rec("long 5 labels","accepted(len %d)"%len("a@"+("b"*60+".")*5+"test"))
except ValueError: rec("long 5 labels","refused")
for a in [".a@x.test","a..b@x.test","a.@x.test","a%b@x.test","a+b@x.test","a@-x.test","a@x-.test"]:
    try:
        r=Recipient(user_id="u1",address=a)
        try: m=build_mime(None,r,RenderedMessage(subject="s",body="b")); rec("edge recipient "+a,"accepted; mime ok To="+m["To"])
        except Exception as e: rec("edge recipient "+a,"accepted but build_mime raises "+type(e).__name__)
    except ValueError: rec("edge recipient "+a,"refused")

def check_msg(m, label):
    raw=m.as_bytes(); p=email.message_from_bytes(raw,policy=email.policy.compat32)
    hdr=raw.split(b"\r\n\r\n",1)[0] if b"\r\n\r\n" in raw else raw.split(b"\n\n",1)[0]
    names=[k.lower() for k in p.keys()]
    ok = names.count("to")==1 and names.count("from")==1 and "cc" not in names and "bcc" not in names and names.count("subject")==1
    extra=set(names)-{"from","to","subject","auto-submitted","date","message-id","content-type","content-transfer-encoding","mime-version"}
    rec(label, ("OK" if ok and not extra else "BAD %s extra=%s"%(names,extra)) + f" To={str(p['To'])[:40]} From={str(p['From'])[:70]}")

for nm in ["AutoTester","Evil\r\nBcc: z@y.test","Evil\nBcc: z@y.test",'x" <evil@e.test>',"=?utf-8?b?DQpCY2M6IHpAeS50ZXN0?=","äöü 中文","Bob, <b@e.test>","A Bcc: z@y.test","A\x85Bcc: z@y.test","x"*100,"a\b","(x)", "a;b"]:
    try:
        cfg=SmtpConfig(host="127.0.0.1",port=25,sender_address="reports@x.test",sender_name=nm,tls="none")
    except ValueError: rec("sender_name "+repr(nm)[:30],"refused by schema"); continue
    check_msg(build_mime(cfg,Recipient(user_id="u1",address="to@x.test"),RenderedMessage(subject="s",body="b")),"sender_name "+repr(nm)[:30])

for pn in ["Demo","Demo\r\nBcc: z@y.test","D Bcc: z@y.test","D\x85Bcc","=?utf-8?q?=0D=0ABcc:_z@y.test?=","ä中","x"*190, "A"*199+"é"]:
    try: s=summ(project_name=pn)
    except ValueError: rec("project_name "+repr(pn)[:30],"refused by schema"); continue
    try:
        m=render_message(s); check_msg(build_mime(None,Recipient(user_id="u1",address="to@x.test"),m),"project_name "+repr(pn)[:30]+" subj="+repr(m.subject)[:50])
    except ValueError as e: rec("project_name "+repr(pn)[:30],"build refused (fail-closed) "+str(e)[:50])
# subject direct
for sj in ["ok","bad\r\nBcc: z@y.test","bad\nx"," x","\x85x","a\x0bb","a\x0cb","\x1bx"]:
    try: m=RenderedMessage(subject=sj,body="b")
    except ValueError: rec("subject "+repr(sj),"refused"); continue
    try: check_msg(build_mime(None,Recipient(user_id="u1",address="to@x.test"),m),"subject "+repr(sj))
    except ValueError as e: rec("subject "+repr(sj),"build refused (fail-closed) "+str(e)[:50])
# body smuggling on the wire
class H(socketserver.StreamRequestHandler):
    def handle(self):
        S=self.server.cap; w=lambda s:(self.wfile.write(s.encode()+b"\r\n"),self.wfile.flush())
        w("220 hi"); data=False; buf=[]
        while l:=self.rfile.readline():
            t=l.decode(errors="replace").rstrip("\r\n")
            if data:
                if t==".": data=False; S["msgs"].append(buf); buf=[]; w("250 q")
                else: buf.append(t)
                continue
            S["cmds"].append(t); v=t.split(" ",1)[0].upper()
            if v=="EHLO": self.wfile.write(b"250 x\r\n"); self.wfile.flush()
            elif v=="DATA": data=True; w("354 go")
            elif v=="QUIT": w("221 b"); return
            else: w("250 ok")
srv=socketserver.ThreadingTCPServer(("127.0.0.1",0),H); srv.cap={"cmds":[],"msgs":[]}; srv.daemon_threads=True
threading.Thread(target=srv.serve_forever,daemon=True).start(); port=srv.server_address[1]
from autotester.schema.delivery import SmtpConfig
cfg=SmtpConfig(host="127.0.0.1",port=port,sender_address="reports@x.test",tls="none")
ad=SmtpAdapter(cfg,lambda:None)
body="hello\r\n.\r\nMAIL FROM:<evil@e.test>\r\nRCPT TO:<z@y.test>\r\nDATA\r\n.\nQUIT\n.\r\nx\n.\nRSET\n"
ad.send(Recipient(user_id="u1",address="to@x.test"),RenderedMessage(subject="s",body=body),key="k")
cmds=srv.cap["cmds"]; print("wire commands:",cmds)
rcpts=[c for c in cmds if c.upper().startswith("RCPT")]
rec("wire: exactly one RCPT TO / one MAIL FROM / one DATA", "OK" if len(rcpts)==1 and sum(c.upper().startswith("MAIL") for c in cmds)==1 and cmds.count("DATA")==1 else "BAD")
rec("wire: one DATA body (no smuggled 2nd message)", "OK" if len(srv.cap["msgs"])==1 else "BAD n=%d"%len(srv.cap["msgs"]))
print("\nSUMMARY bad:",[r for r in res if r[1].startswith(("BAD","ACCEPTED"))])
