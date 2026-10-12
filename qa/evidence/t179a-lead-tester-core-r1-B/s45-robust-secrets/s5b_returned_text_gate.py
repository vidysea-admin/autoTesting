"""s5b: the text the dispatcher hands back to the model (ToolOutcome.summary), re-checked with the SAME gate
(SecretStore.guard_prompt = core.redact.assert_no_raw_secrets) on that exact string. <python> -I s5b.py <copy> <out.json>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_lib as L  # noqa: E402
L.confirm_copy(sys.argv[1])
from autotester.agents import tools  # noqa: E402
from autotester.schema.enums import Action as A, Outcome, WritePolicy  # noqa: E402
from autotester.schema.run import RawResult  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location("s5", str(Path(__file__).with_name("s5_secrets.py")))
rows = []
for key, secret in L.CANARY.items():
    for lab, text in (("tab_split", "\t".join(secret[i:i+4] for i in range(0, len(secret), 4))),
                      ("newline_split", "\n".join(secret[i:i+4] for i in range(0, len(secret), 4))),
                      ("single_tab", secret[:5] + "\t" + secret[5:]),
                      ("space_split_control", " ".join(secret[i:i+4] for i in range(0, len(secret), 4))),
                      ("zero_width_control", "\u200b".join(secret[i:i+4] for i in range(0, len(secret), 4)))):
        env = L.make_env(WritePolicy.TEST_ACCOUNT, [[L.step(1, A.NAVIGATE, "https://app.test/home")]])
        env.spy.result_factory = lambda case, t=text: RawResult(case_id=case.id, outcome=Outcome.ERRORED, error="saw " + t)
        out = tools.dispatch(env.ctx, "run_case", {"case_id": env.case_ids[0]})
        try:
            env.ctx.secrets.guard_prompt(out.summary); raises = False
        except ValueError:
            raises = True
        stored = [p for p in env.root.rglob("*.json") if p.name.endswith(".json") and "approvals" not in p.name]
        rows.append({"secret": key, "spelling": lab, "dispatch_ok": out.ok, "dispatch_refusal": out.refusal.value if out.refusal else None,
                     "gate_on_returned_summary_raises": raises})
L.dump(sys.argv[2], rows)
for r in rows: print(r)
