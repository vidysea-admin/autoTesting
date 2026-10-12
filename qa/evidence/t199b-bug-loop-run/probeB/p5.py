from h import *
from autotester.core.redact import mask_pii
banner("5a planted secrets/PII with a Redactor declaring only DEMO_PASSWORD (and API key declared)")
APIKEY="sk-ant-api03-AbCdEf0123456789xyz"
R=Redactor({"DEMO_PASSWORD":SECRET,"API":APIKEY})
sc=R.scrub
planted={"declared pw":f"x {SECRET}","declared apikey":f"k {APIKEY}",
 "undeclared sk-ant":"k sk-ant-api03-ZZZZZZZZZZZZZZZZZZZ","bearer":"Authorization: Bearer abcDEF123456.tok","jwt":"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
 "password pair":"password=Sup3rS3cret!","email":"mail bob@example.com now","phone":"call +91 98765 43210","aws":"AKIAIOSFODNN7EXAMPLE",
 "url token":"https://app.example.com/x?token=abc123SECRET&u=1","placeholder":"{{SECRET:KEY}}"}
for k,v in planted.items():
    out=sc(v); surv = out==v
    pii=mask_pii(out)
    print(f"  {k:18} scrub-> {out[:60]!r}  survives_scrub={surv}  mask_pii_would_change={pii!=out}")
banner("5b planted in bug fields through plan (title, screen, assignee, severity n/a, criterion?)")
sh=FakeSheet(HEADER)
cols=SheetColumns(sheet_id="s",tab="t",columns={"bug_key":"Key","title":"Title","severity":"Severity","status":"Status","assignee":"Assignee"})
bug_=B(1,title=f"pw {SECRET} k {APIKEY} bob@example.com",assignee=f"as {SECRET}",screen=f"scr {SECRET}")
p=plan_sync([bug_],sh.read("s","t"),cols,SyncMemory(),sc)
text=render_plan(p); blob=p.model_dump_json()+text
print("  declared secrets in plan/render/hash-input:", SECRET in blob, APIKEY in blob, "email in plan:", "bob@example.com" in blob)
write_confirmed_plan(sh,[bug_],cols,SyncMemory(),sc,conf(p)); print("  in fake calls/rows:",SECRET in repr(sh.calls)+repr(sh.rows))
print("  title cell:", sh.rows[0][2])
# screen is not mapped here: use mapping with screen
cols2=SheetColumns(sheet_id="s",tab="t",columns={"bug_key":"Key","title":"Title","screen":"Notes (human)","assignee":"Assignee"})
sh=FakeSheet(HEADER); p=plan_sync([bug_],sh.read("s","t"),cols2,SyncMemory(),sc); print("  screen cell:",[c.after for c in p.rows[0].changes if c.column=="Notes (human)"])
banner("5c sheet-side values are shown unscrubbed (before / sheet_has)")
leak=f"typed by human with {SECRET}"
sh=FakeSheet(HEADER,[["",B(1).bug_key,leak,"S2","open",""]]); mem=SyncMemory()
p=plan_sync([B(1,title="other")],sh.read("s","t"),COLS,mem,sc)
blob=p.model_dump_json()+render_plan(p); print("  sheet-side secret in plan/render:", SECRET in blob)
sh=FakeSheet(HEADER,[["",B(1).bug_key,"old","S2","open",f"assigned {SECRET}"]]); mem.written[B(1).bug_key]={"Title":"old","Assignee":f"assigned {SECRET}"}
p=plan_sync([B(1,title="new")],sh.read("s","t"),COLS,mem,sc); print("  'before' secret in plan:",SECRET in p.model_dump_json()+render_plan(p))
banner("5d scrub returning weird: scrub that is identity / raises / scrub applied to key?")
p=plan_sync([bug_],FakeSheet(HEADER).read("s","t"),cols,SyncMemory(),lambda t:t); print("  identity scrub: plan accepted, secret in plan:", SECRET in p.model_dump_json(), "(scrub is a caller-supplied callable; no enforcement)")
banner("5e formula guard")
P0=[("=",'=SUM(1)'),("+",'+1'),("-","-5"),("@","@x"),("TAB","\tx=1"),("CR","\rx"),("LF","\nx"),("fullwidth =","＝SUM(1)"),("fullwidth +","＋1"),("fullwidth -","－5"),("fullwidth @","＠x"),
 ("space then =",' =1+1'),("zwsp then =","\u200b=1"),("BOM then =","\ufeff=1"),("already apostrophe","'=x"),("neg number","-5"),("date-ish","-1"),("pipe","a|b"),("newline inside","a\nb"),("tab inside","a\tb")]
for lab,v in P0:
    try:
        b_=B(1,title=v)
    except Exception as e: print(f"  {lab:20} bug model refuses ({type(e).__name__})"); continue
    p=plan_sync([b_],FakeSheet(HEADER).read("s","t"),COLS,SyncMemory(),sc)
    t=[c.after for c in p.rows[0].changes if c.column=="Title"][0]
    print(f"  {lab:20} {v!r:16} -> {t!r}  guarded={t!=v}")
banner("5f idempotence: planning twice / double apply; and apostrophe leading")
b_=B(1,title="'=x"); p=plan_sync([b_],FakeSheet(HEADER).read("s","t"),COLS,SyncMemory(),sc); print("  '=x ->",[c.after for c in p.rows[0].changes if c.column=="Title"])
banner("5g second-sync empty with formula-looking titles, and -5")
for v in ["=HYPERLINK(\"http://e\",\"x\")","-5","-1","+44 20 7946","@mention","\tx"]:
    try: bb=B(1,title=v)
    except Exception as e: print("  refused",repr(v)); continue
    sh=FakeSheet(HEADER); mem=SyncMemory(); p=plan_sync([bb],sh.read("s","t"),COLS,mem,sc); write_confirmed_plan(sh,[bb],COLS,mem,sc,conf(p))
    p2=plan_sync([bb],sh.read("s","t"),COLS,mem,sc); print(f"  {v!r:36} cell={sh.rows[0][2]!r} second plan empty={p2.rows==[]}")
banner("5h REAL-SHEET model: Sheets (USER_ENTERED) strips the leading ' on read-back")
class Strip(FakeSheet):
    def read(s,a,b):
        st=super().read(a,b); st.rows=[[c[1:] if c.startswith("'") else c for c in r] for r in st.rows]; return st
for v in ["=HYPERLINK(\"http://e\",\"x\")","-5"]:
    bb=B(1,title=v); sh=Strip(HEADER); mem=SyncMemory(); p=plan_sync([bb],sh.read("s","t"),COLS,mem,sc); write_confirmed_plan(sh,[bb],COLS,mem,sc,conf(p))
    p2=plan_sync([bb],sh.read("s","t"),COLS,mem,sc); print(f"  {v!r}: second plan rows={[(r.action,[ (c.column,c.sheet_has,c.we_last_wrote) for c in r.conflicts]) for r in p2.rows]}")
banner("5i bug_key cell guard + status/severity/assignee guarded?")
print("  _safe applied to all mapped fields via want dict (stages/sheet_plan.py:70-71) incl. bug_key")
