"""T-181 AL12: the LIVE agent-vs-pipeline comparison on the seeded local fixture product.

Same product, same two cases, same judge provider: the plain pipeline (`run_and_grade_case`)
vs the guarded agent layer (`run_lead_agent` under `AgentGuardrails`), each in a visible
browser one after the other, scored through `agents/gain.py::measure_gain` -> `stages/bench.py`.
Local fixture only (tests/fixtures/regression_site, broken login seeded into a TEMP COPY); no
external site. Keys are read from the repo-root .env into the process and never printed.

    python scripts/agent_live_comparison.py --env <repo .env> --out qa/evidence/t181-live
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=1_000_000)
    ap.add_argument("--max-usd", type=float, default=10.0)
    ap.add_argument("--usd-per-m", type=float, default=10.0)
    args = ap.parse_args()
    load_dotenv(args.env)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="t181live-"))
    site = root / "site"
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "regression_site"
    shutil.copytree(fixture, site)
    shutil.copy(site / "login.broken.html", site / "login.html")  # seed the bug in the COPY
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        run(f"http://127.0.0.1:{server.server_address[1]}", root, out, args)
    finally:
        server.shutdown()


def run(base: str, root: Path, out: Path, args: argparse.Namespace) -> None:
    from bench_trial import build_cases
    from regression_proof import seat_demo_cases

    from autotester.agents import comparison, gain, lead_agent
    from autotester.agents.context import AgentContext
    from autotester.browser.secrets import SecretStore
    from autotester.browser.session import BrowserSession
    from autotester.core.ids import ulid
    from autotester.core.paths import ProjectPaths
    from autotester.providers.agent_model import agent_chat_model
    from autotester.providers.langchain_fallback import LangChainFallbackProvider
    from autotester.schema.agent_guardrails import AgentGuardrails
    from autotester.schema.approval import RunApproval
    from autotester.schema.bench import BenchCorpus
    from autotester.schema.enums import ApprovalKind, Severity, WritePolicy
    from autotester.schema.lead_loop import AgentRun, TokenBudget
    from autotester.schema.project import Project
    from autotester.stages import bench
    from autotester.stages.run_case_pipeline import default_rubric, run_and_grade_case
    from autotester.store.project_store import ProjectStore

    project = Project(slug="t181live", name="T-181 live fixture", base_url=f"{base}/index.html",
                      allowed_domains=["127.0.0.1"], headed=True,
                      write_policy=WritePolicy.ALLOW_WRITES)
    paths = ProjectPaths(project.slug, root)
    paths.ensure()
    (root / ".env").write_text("", encoding="utf-8")
    store = ProjectStore(project.slug, root)
    store.save_project(project)
    cases = build_cases(project.slug, base)
    for case in cases:
        case.rubric_ref = f"rub_{case.id}"
    cases = seat_demo_cases(store, cases)
    for case in cases:  # one rubric per case, shared by both paths (the judge is the same too)
        store.save_rubric(default_rubric(case, f"rub_{case.id}"))
    store.add_approval(RunApproval(
        project=project.slug, run_kind=ApprovalKind.LIVE_CASE, target=project.base_url,
        scope="T-181 live comparison against the local fixture", max_actions=100,
        wall_clock_s=1800.0, granted_by="umesh", granted_at="2026-10-13",
        expires_at="2099-01-01").sign())
    secrets = SecretStore(project, {})
    login_case = cases[0]
    case_bug_map = {login_case.id: "bug_login_password"}
    corpus = BenchCorpus(
        id="corpus_regression_demo_login", mode="fixture", app="regression-demo",
        build_ref="login.broken.html", material_refs=["tests/fixtures/regression_site/"],
        seeded_bugs=[bench.seeded_bug(
            "bug_login_password", "Login rejects the correct password", "/login.html",
            "Login with correct credentials should succeed but shows an error", Severity.S1)])
    judge_p, judge_a = LangChainFallbackProvider(), LangChainFallbackProvider()
    model_id, model = agent_chat_model()
    guard = AgentGuardrails(
        budget=TokenBudget(max_tokens=args.max_tokens, max_cost_usd=args.max_usd,
                           usd_per_million_tokens=args.usd_per_m))
    pipe_run, agent_run_id = f"run-pipe-{ulid()}", f"run-agent-{ulid()}"

    def new_session(run_id: str, observer: object | None = None) -> BrowserSession:
        return BrowserSession(project, secrets, paths.run_dir(run_id), paths, observer=observer)

    def pipeline() -> list:
        verdicts = []
        with new_session(pipe_run) as session:
            for case in cases:
                _, verdict = run_and_grade_case(case, session, judge_p, pipe_run, store)
                store.save_verdict(pipe_run, verdict)
                verdicts.append(verdict)
                print("pipeline:", case.title, verdict.result.value, flush=True)
        return verdicts

    task = ("You are testing the product at " + project.base_url + ". Two stored cases exist "
            f"({', '.join(c.id for c in cases)}). Run each stored case, grade each executed "
            "case, and report which behave incorrectly. Do not crawl.")
    captured: dict[str, AgentRun] = {}

    def agent(rails: AgentGuardrails) -> tuple[AgentRun, list]:
        ctx = AgentContext(project=project, store=store, secrets=secrets, judge=judge_a,
                           run_id=agent_run_id,
                           open_session=lambda obs: new_session(agent_run_id, obs))
        result = lead_agent.run_lead_agent(ctx, model, task, guardrails=rails)
        captured["run"] = result
        print("agent:", result.stopped, result.reason, result.tool_calls, flush=True)
        # the agent path's total = its own model calls + its judge (grade_case) calls
        total = result.tokens_used + _tokens(judge_a)
        return result.model_copy(update={"tokens_used": total}), store.load_verdicts(agent_run_id)

    cmp = None
    try:
        cmp = gain.measure_gain(corpus, case_bug_map, pipeline, agent, guard,
                                pipeline_tokens=None, out=out / "comparison.json")
    finally:
        _evidence(out, store, [pipe_run, agent_run_id], captured.get("run"), judge_p, judge_a,
                  model_id, guard, args)
    if cmp is not None:
        # re-score with the pipeline's own (judge) token count, known only after the run
        run_ = captured["run"].model_copy(update={"tokens_used": cmp.agent.tokens or 0})
        cmp = comparison.compare(
            corpus, case_bug_map, store.load_verdicts(pipe_run), store.load_verdicts(agent_run_id),
            run_, pipeline_tokens=_tokens(judge_p), pipeline_wall_s=cmp.pipeline.wall_s,
            agent_wall_s=cmp.agent.wall_s, rule=guard.win_rule)
        comparison.write_report(cmp, out / "comparison.json")
        print("VERDICT:", cmp.verdict_line)


def _tokens(provider) -> int:
    return sum(u.input_tokens + u.output_tokens for u in provider.usage)


def _evidence(out, store, run_ids, agent_run, judge_p, judge_a, model_id, guard, args) -> None:
    """Redacted evidence: verdicts (reasons only), token counts, run metadata. No key values."""
    meta = {
        "agent_model_provider": model_id,
        "pipeline_judge_tokens": _tokens(judge_p),
        "agent_judge_tokens": _tokens(judge_a),
        "agent_model_tokens": agent_run.tokens_used if agent_run else None,
        "agent_run": agent_run.model_dump(mode="json") if agent_run else None,
        "guardrails": guard.model_dump(mode="json"),
        "usd_per_million_tokens_configured_estimate": args.usd_per_m,
        "verdicts": {r: [v.model_dump(mode="json") for v in store.load_verdicts(r)]
                     for r in run_ids},
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
