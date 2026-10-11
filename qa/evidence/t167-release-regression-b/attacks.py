"""Checker B attack probes (read-only toward product; runs in the throwaway copy)."""
import json, os, sys, tempfile, traceback
from datetime import UTC, datetime
from pathlib import Path

os.environ["AUTOTESTER_APPROVAL_KEY"] = "checker-b-throwaway-key"
REPO = Path(sys.argv[1])
sys.path[:0] = [str(REPO / "tests"), str(REPO / "src")]
import test_regression_trigger as T  # noqa
from run_approval_fixture import grant_live_case_approval
from autotester.core.consent import ApprovalRequired
from autotester.schema.enums import Result
from autotester.schema.release import ReleaseDecision, ReleaseScope
from autotester.stages import release, release_compare
from autotester.stages.release import start_release
from autotester.stages.orchestrate import StageContext, run_or_resume
from autotester.schema.run_state import StageName
import autotester
print("autotester from", autotester.__file__)
P, F = Result.PASS, Result.FAIL


def fresh(**kw):
    return T._store(Path(tempfile.mkdtemp()), **kw)


def out(name, ok, extra=""):
    print(f"{'HELD ' if ok else 'BREACH'} {name} {extra}")


# A1 forged scope: max_actions=1 (narrow approval of 1) but 3 plans -> real cost 3
s = fresh(approve=False, flows=T.ALL)
grant_live_case_approval(s, max_actions=1)
try:
    start_release(T.PROJECT, s, run_id="honest", runners={})
    out("A1a honest narrow approval refused", False)
except ApprovalRequired:
    out("A1a honest narrow approval refused", True)
forged = release.build_scope(T.PROJECT, s, run_id="forged", approval_id=s.list_approvals()[0].id, max_actions=1)
s.paths.run_dir("forged").mkdir(parents=True)
(s.paths.run_release_scope("forged")).write_text(forged.model_dump_json(), "utf-8")
calls = []
try:
    st = start_release(T.PROJECT, s, run_id="forged", runners=T._runners(s, {}, calls))
    done = start_release(T.PROJECT, s, run_id="forged", runners=T._runners(s, T._outcome(f1=P, f2=P, f3=P), calls), decision=T.YES)
    out("A1b forged scope (cost 3 declared 1) vs approval of 1 action", False,
        f"-> reached pause={st.checkpoint(StageName.CONFIRM).status}; after yes calls={calls}")
except ApprovalRequired as e:
    out("A1b forged scope vs approval of 1 action", True, str(e)[:80])

# A2 stale approval on resume: paused then approvals wiped
s = fresh(flows=T.ALL)
r = T._runners(s, T._outcome(f1=P, f2=P, f3=P))
start_release(T.PROJECT, s, run_id="rel", runners=r)
s.paths.approvals.write_text("", "utf-8") if hasattr(s.paths, "approvals") else None
apath = [p for p in s.paths.dir.glob("approvals*")]
print("approval files", apath)
for p in apath:
    p.write_text("", "utf-8")
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A2 resume after approval removed", False)
except ApprovalRequired:
    out("A2 resume after approval removed (frozen scope present)", True)

# A2b expired approval on resume
s = fresh(approve=False, flows=T.ALL)
ap = grant_live_case_approval(s, expires_at="2026-10-11")  # expires after today? today 2026-10-10 -> alive
print("today", datetime.now(UTC).date())

# A3 baseline picker
def runrel(s, rid, outcome, day):
    return T._release(s, rid, outcome, day=day)

s = fresh(flows=T.ALL)
runrel(s, "r1", T._outcome(f1=P, f2=P, f3=P), 1)
runrel(s, "r2", T._outcome(f1=P, f2=P, f3=P), 2)
runrel(s, "r3", T._outcome(f1=P, f2=P, f3=P), 3)
out("A3a latest trusted earlier release is baseline", s.load_release_record("r3").diff.baseline_run_id == "r2",
    "got " + str(s.load_release_record("r3").diff.baseline_run_id))
# later release must never be baseline for an earlier-created run
runrel(s, "r5", T._outcome(f1=P, f2=P, f3=P), 5)
runrel(s, "r4", T._outcome(f1=F, f2=P, f3=P), 4)
d4 = s.load_release_record("r4").diff
out("A3b later (day5) release not baseline of day4 run", d4.baseline_run_id == "r3", f"got {d4.baseline_run_id}")
# unfinished / flagged / failing records are not trusted
rec = s.load_release_record("r3")
for label, upd in [("unfinished", {"finished": False}), ("flagged", {"flagged_bad": True})]:
    out(f"A3c {label} not trusted", not rec.model_copy(update=upd).is_trusted)
bad = rec.model_copy(update={"results": {**rec.results, "c-f1": F}})
out("A3d failing result not trusted", not bad.is_trusted)
miss = rec.model_copy(update={"results": {k: v for k, v in rec.results.items() if k != "c-f1"}})
out("A3e missing result (did not run) not trusted", not miss.is_trusted)
# different release compared: regression vs latest good
out("A3f r4 regressed c-f1 vs r3", d4.regressed == ["c-f1"], str(d4.regressed))

# A4 coverage shrink: baseline passes f1,f2,f3; new release FlowSpec drops f2 -> regression of coverage visible?
s = fresh(flows=T.ALL)
runrel(s, "r1", T._outcome(f1=P, f2=P, f3=P), 1)
from autotester.schema.flowspec import Flow, FlowSpec
s.save_flowspec(FlowSpec(project="demo", flows=[Flow(id=f, name=f, entry_screen="home") for f in ("f1", "f3")]))
runrel(s, "r2", T._outcome(f1=P, f3=P), 2)
d = s.load_release_record("r2").diff
print("A4 dropped flow f2 -> diff:", d.regressed, d.fixed, d.new_cases, "|", s.load_release_record("r2").issues)

# A5 corrupt / foreign checkpoint refused
s = fresh(flows=T.ALL)
r = T._runners(s, T._outcome(f1=P, f2=P, f3=P))
start_release(T.PROJECT, s, run_id="rel", runners=r)
cp = s.paths.run_dir("rel") / "checkpoint.json"
raw = cp.read_text("utf-8")
cp.write_text(raw[:-5], "utf-8")
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A5a truncated checkpoint refused", False)
except Exception as e:
    out("A5a truncated checkpoint refused", True, type(e).__name__)
cp.write_text(raw.replace("demo:rel", "demo:other"), "utf-8")
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A5b foreign-thread checkpoint refused", False)
except Exception as e:
    out("A5b foreign-thread checkpoint refused", True, type(e).__name__)
cp.write_text(raw, "utf-8")

# A6 semantic tamper: scope.json widened after the pause (more flows/plans) -> must be refused
s = fresh(flows=T.ALL)
r = T._runners(s, T._outcome(f1=P, f2=P, f3=P))
start_release(T.PROJECT, s, run_id="rel", runners=r)
sp = s.paths.run_release_scope("rel")
sc = json.loads(sp.read_text("utf-8"))
sc["max_actions"] = 1
sp.write_text(json.dumps(sc), "utf-8")
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A6 scope.json edited after pause refused", False)
except Exception as e:
    out("A6 scope.json edited after pause refused", True, type(e).__name__ + ": " + str(e)[:70])

# A7 decision on a fresh run / decision replay after finish
s = fresh(flows=T.ALL)
r = T._runners(s, T._outcome(f1=P, f2=P, f3=P))
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A7a decision on a fresh run refused", False)
except Exception as e:
    out("A7a decision on a fresh run refused", True, type(e).__name__)
print("   scope.json left after A7a:", s.paths.run_release_scope("rel").exists())
start_release(T.PROJECT, s, run_id="rel", runners=r)
start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
try:
    start_release(T.PROJECT, s, run_id="rel", runners=r, decision=T.YES)
    out("A7b replay decision after finish refused", False)
except Exception as e:
    out("A7b replay decision after finish refused", True, type(e).__name__)

# A8 run_or_resume with no release_scope against a release run id
s = fresh(flows=T.ALL)
r = T._runners(s, T._outcome(f1=P, f2=P, f3=P))
start_release(T.PROJECT, s, run_id="rel", runners=r)
try:
    run_or_resume(T.PROJECT, StageContext(store=s, run_id="rel", runners=r))
    out("A8 non-release ctx cannot drive a release run (bypass CONFIRM)", False)
except Exception as e:
    out("A8 non-release ctx cannot drive a release run", True, type(e).__name__)

# A9 path traversal run id
s = fresh(flows=T.ALL)
try:
    start_release(T.PROJECT, s, run_id="../escaped", runners={})
    print("A9 run_id '../escaped' accepted; escaped dir:", (s.paths.runs_dir.parent / "escaped").exists())
except Exception as e:
    print("A9", type(e).__name__, str(e)[:80])
