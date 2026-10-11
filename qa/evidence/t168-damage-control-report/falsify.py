import re, sys
from pathlib import Path
here = Path(__file__).parent
def edit(k, rel, old, new, count=1):
    p = here / k / rel; t = p.read_text(encoding="utf-8")
    assert t.count(old) == count, (k, old, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8")
SR = "src/autotester/stages/unified_report.py"
RN = "src/autotester/stages/unified_report_render.py"
edit("dc1", SR, "incomplete=not complete)", "incomplete=False)")
edit("dc2", SR, "history=load_history(store), coverage", "history=HistorySection(unavailable='bypass'), coverage")
edit("dc3", RN, '             ("history", "4. Change history", _history(report.history)),\n', '')
edit("dc4a", SR, "return _load_redactor(store).scrub(render_html(build_report(store, run_id)))", "return render_html(build_report(store, run_id))")
edit("dc4b", SR, "    redactor = _load_redactor(store)\n    lines = []", "    redactor = Redactor({})\n    lines = []")
edit("dc4b", SR, "from autotester.schema.crawl import Crawl\n", "from autotester.schema.crawl import Crawl\nfrom autotester.core.redact import Redactor\n")
edit("dc2", SR, "    HistorySection,\n", "    HistorySection,\n", 1)
print("edited")
