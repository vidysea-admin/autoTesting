"""Scratch: re-grade RECORDED evidence N times with the real judge (no browser, no production hit)."""
import sys, json, collections
from pathlib import Path
from autotester.core.env import load_repo_env
load_repo_env()
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.run import RawResult
from autotester.stages.grade import grade
from autotester.stages.run_case_pipeline import default_rubric
from autotester.store.project_store import ProjectStore
run_dir, case_id, n = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
store = ProjectStore("pathlynks")
case = store.get_case(case_id)
res = RawResult.model_validate_json((run_dir / f"{case_id}.json").read_text(encoding="utf-8"))
rubric = default_rubric(case, f"rub_{case_id}")
print("criteria:", [c.text for c in rubric.criteria])
judge = LangChainFallbackProvider()
tally = collections.Counter()
for i in range(n):
    v = grade(rubric, res, "regrade", judge, run_dir=run_dir)
    tally[v.result.value] += 1
    print(i, v.result.value, v.scoreboard[:160], "|", (v.note or "")[:120])
print("TALLY", dict(tally))
