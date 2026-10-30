"""Shared helpers for the crawl-guidance tests (qa/contracts/crawl-guidance.md G1-G12).

Not a test module. Holds the volatile-field normaliser behind the G5 byte-identical baseline and
the fake providers every guidance test uses (no real model, no network, no credential).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from crawl_fake import BASE, make_project, make_session

from autotester.providers.attempts import reserve_attempt
from autotester.providers.base import Provider, ProviderError
from autotester.schema.crawl import CrawlBounds
from autotester.schema.crawl_guidance import GuidanceOptIn, NextActionRanking
from autotester.schema.portal_persona import PersonaProfile, PortalPersona
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages.explore_guidance import Guidance, graft
from autotester.store.project_store import ProjectStore

BASELINE_DIR = Path(__file__).parent / "fixtures" / "crawl_guidance"
ARTIFACTS = ("crawl.json", "nodes.jsonl", "edges.jsonl")
_VOLATILE = [
    (re.compile(r'"(created_at|started_at|finished_at|heartbeat_at)":\s*"[^"]*"'), r'"\1":"T"'),
    (re.compile(r"crawl_[0-9A-Z]{26}"), "crawl_ID"),
    (re.compile(r"appr_[0-9A-Za-z]+"), "appr_ID"),
    (re.compile(r"edge_[0-9a-f]{12}"), "edge_ID"),
]


def normalise(text: str) -> str:
    """The artifact text with every per-run value (clock, ulid, hash of a ulid) fixed."""
    for pattern, replacement in _VOLATILE:
        text = pattern.sub(replacement, text)
    return text


def crawl_artifacts(tmp_path: Path, slug: str = "demo") -> dict[str, str]:
    """name -> normalised text of the one crawl under `tmp_path`'s project."""
    crawl_dir = next((tmp_path / "projects" / slug / "crawl").iterdir())
    return {name: normalise((crawl_dir / name).read_text(encoding="utf-8")) for name in ARTIFACTS}


def baseline(name: str) -> str:
    text = (BASELINE_DIR / f"baseline_{name}").read_text(encoding="utf-8")
    return text.replace(chr(13) + chr(10), chr(10))


def regenerate_baseline(tmp_path: Path) -> None:  # pragma: no cover - run on the pre-change tree
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in crawl_artifacts(tmp_path).items():
        (BASELINE_DIR / f"baseline_{name}").write_text(text, encoding="utf-8", newline="\n")


SECRET = "S3cretPlant-91xyz"
BOUNDS_ON = dict(max_model_calls=50, model_call_timeout_s=20.0, model_total_s=120.0)


class FakeClock:
    """The crawl clock the fakes advance, so model seconds are visible on it (G6)."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def payload_of(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rstrip().rsplit(chr(10) * 2, 1)[1])


def reverse(prompt: str, _nth: int) -> NextActionRanking:
    n = len(payload_of(prompt)["controls"])
    return NextActionRanking(ranked=list(range(n))[::-1], reason="reversed")


def garbage(_prompt: str, _nth: int) -> Any:
    return {"ranked": ["no", None, 99, -4]}


class FakeProvider(Provider):
    """A model that is never called for real: scripted answers, a spy on the guard, the attempt
    budget it was granted, and the crawl-clock seconds it 'took'."""

    id = "fake"

    def __init__(self, answer: Callable[[str, int], Any] = reverse, *, model: str = "fake-1017",
                 takes: float = 0.0, clock: FakeClock | None = None, ready: bool = True,
                 guard_refuses: bool = False) -> None:
        super().__init__(model=model)
        self.answer, self.takes, self.clock = answer, takes, clock
        self.ready, self.guard_refuses = ready, guard_refuses
        self.prompts: list[str] = []
        self.guarded: list[str] = []
        self.granted: list[float] = []
        self._served: str | None = None

    @property
    def served(self) -> str | None:
        return self._served

    def available(self) -> bool:
        return self.ready

    def guard_text(self, text: str) -> None:
        self.guarded.append(text)
        if self.guard_refuses:
            raise ProviderError("prompt withheld")

    def act(self, prompt: str, schema: Any = None, *, prompt_file: str | None = None,
            fed_id: str | None = None) -> Any:
        self._served = None
        self.prompts.append(prompt)
        self.granted.append(reserve_attempt(self.id, "act", 120.0)[1])
        if self.clock is not None:
            self.clock.now += self.takes
        out = self.answer(prompt, len(self.prompts))
        self.record("act", 10, 5)
        self._served = self.options["model"]
        return out

    @property
    def calls(self) -> int:
        return len(self.prompts)


def guided_project(enabled: bool = True) -> Project:
    base = make_project()
    return base.model_copy(update={"crawl_guidance": GuidanceOptIn(enabled=enabled)})


def seed_persona(store: ProjectStore) -> PortalPersona:
    """A persona with a real header, as a persona build leaves it (guidance never creates one)."""
    persona = store.load_portal_persona()
    if persona is None:
        persona = PortalPersona(project="demo", profile=PersonaProfile(name="Demo", base_url=BASE))
        store.save_portal_persona(persona)
    return persona


def commit(rt: Any, *nodes: ScreenNode) -> PortalPersona:
    """What the persona build does with a crawl's nodes at crawl end (D-119): graft, then save."""
    persona = graft(seed_persona(rt.store), list(nodes))
    rt.store.save_portal_persona(persona)
    return persona


def make_rt(tmp_path: Path, *, bounds: CrawlBounds | None = None, clock: FakeClock | None = None,
            project: Project | None = None, persona: bool = False) -> SimpleNamespace:
    """Just enough runtime for `Guidance.order`: bounds, clock, secrets, store, project, nodes.
    `persona=True` seeds a persona with a header; the default is a first crawl with none."""
    project = project or guided_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    if persona:
        seed_persona(store)
    return SimpleNamespace(project=project, session=session, store=store,
                           clock=clock or FakeClock(), started=0.0, nodes={},
                           bounds=bounds or CrawlBounds(**BOUNDS_ON))


def screen(node_id: str = "node_1", template: str = "/home") -> ScreenNode:
    return ScreenNode(id=node_id, crawl_id="c", project="demo", url_template=template,
                      url_example=f"https://app.test{template}?q=1", signature="s", title="Home")


def controls(n: int, prefix: str = "Open") -> list[ElementRef]:
    return [ElementRef(role="button", name=f"{prefix} {i}", selector=f"#b{i}") for i in range(n)]


def guide(provider: FakeProvider, **kw: Any) -> Guidance:
    return Guidance(provider, models=kw.pop("models", ("fake-1017",)), **kw)
