from autotester.core.paths import RepoDocs
from autotester.schema.enums import CaseClass
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.explore_flows import flows_from_crawl
from autotester.stages.expand import build_expand_prompt, guard_expand_prompt
r = ScreenNode(crawl_id="c", project="p", url_template="x.test/land", url_example="https://x.test/land?token=eyJhbGciOiJIUzI1NiJ9.SESSIONSECRET&email=a@b.com", signature="r", name="Land")
f = flows_from_crawl([r], [], crawl_id="c")[0]
pr = guard_expand_prompt(build_expand_prompt(f, CaseClass.NEGATIVE if hasattr(CaseClass,"NEGATIVE") else list(CaseClass)[1], RepoDocs()), None)
print("token reaches prompt text:", "SESSIONSECRET" in pr, "| email masked:", "a@b.com" not in pr)
