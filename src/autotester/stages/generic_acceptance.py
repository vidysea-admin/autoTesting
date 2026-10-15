"""GENERIC ACCEPTANCE: one harness that drives a product through BOTH entry modes (T-169).

One job: onboard a project through the app's own `/onboard` form (no CLI), let the
orchestrator pick INGEST (teaching sources) or DISCOVER (URL + credentials only), walk the
reviewed-truth gates through the UI routes, press Run, then hand the finished run to the
existing `bench_from_run` + `acceptance_comparison` -- nothing is scored here (bench.md K3,
D-089/D-090: with no human list, recall stays "unavailable").

The harness is slug-driven: `ModeSpec.onboard=False` reuses an already-onboarded project, so
the same check runs on a real target (Pathlynks) once T-145 produces data. Everything that
touches a model or a browser is a seam on `ModeSeams`, so this module imports neither.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from autotester.browser.secrets import SecretStore
from autotester.core.ids import ulid
from autotester.providers.base import Provider
from autotester.schema.acceptance import AcceptanceComparison
from autotester.schema.crawl import Crawl
from autotester.schema.enums import SourceKind
from autotester.schema.run_state import RunState, StageName
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.acceptance_comparison import build_comparison, completeness_problems
from autotester.stages.bench_from_run import bench_from_run
from autotester.stages.orchestrate import StageContext, choose_mode, run_or_resume
from autotester.stages.orchestrate_runners import (
    make_discover_runner,
    make_ingest_runner,
    make_model_runner,
)
from autotester.store.project_store import ProjectStore

Mode = Literal["teaching", "url_only"]
EXPECTED_ENTRY = {"teaching": StageName.INGEST, "url_only": StageName.DISCOVER}
EXPECTED_MODE = {"teaching": "learn", "url_only": "explore"}


@dataclass
class ModeSpec:
    """What the user types into the onboarding form -- and nothing else."""

    mode: Mode
    slug: str
    name: str
    base_url: str
    allowed_domains: list[str]
    credentials: list[tuple[str, str, str]] = field(default_factory=list)
    """(key, value, domains) rows -- the test account; keys live in the project's namespace."""
    evals: str = ""
    use_cases: str = ""
    sources: list[tuple[str, str, str]] = field(default_factory=list)
    """(kind, path-or-text, label) rows -- video / doc / text teaching material."""
    onboard: bool = True
    """False = the project already exists (a real target); skip the form."""

    def form(self) -> dict[str, Any]:
        """The `/onboard` POST body, exactly as the browser form would send it."""
        data: dict[str, Any] = {
            "slug": self.slug, "name": self.name, "base_url": self.base_url,
            "allowed_domains": ", ".join(self.allowed_domains),
            "evals": self.evals, "conditions": "", "use_cases": self.use_cases,
            "credential_key": [c[0] for c in self.credentials],
            "credential_value": [c[1] for c in self.credentials],
            "credential_domains": [c[2] for c in self.credentials],
            "credential_description": ["test account" for _ in self.credentials],
        }
        data.update({"source_kind": [s[0] for s in self.sources],
                     "source_value": [s[1] for s in self.sources],
                     "source_label": [s[2] for s in self.sources]})
        return data


@dataclass
class ModeSeams:
    """The only model/browser contact points; a real target supplies real ones."""

    ingest_provider: Provider | None = None
    crawl_fn: Callable[[], tuple[Crawl, list[ScreenNode]]] | None = None
    before_run: Callable[[ProjectStore], None] | None = None
    """Grant the signed live-case approval a UI run needs (AT-570)."""
    case_bug_map: dict[str, str] = field(default_factory=dict)


@dataclass
class ModeResult:
    mode: Mode
    run_state: RunState
    run_id: str
    comparison: AcceptanceComparison
    problems: list[str]


def _check(response: Any, step: str, ok: tuple[int, ...] = (200, 303)) -> None:
    if response.status_code not in ok:
        raise AssertionError(f"{step}: HTTP {response.status_code}: {response.text[:200]}")


def enter_pipeline(store: ProjectStore, spec: ModeSpec, seams: ModeSeams) -> RunState:
    """Run the orchestrator once: it chooses INGEST or DISCOVER from the stored sources,
    then MODEL, and stops at the review gate (EXPAND has no runner by design)."""
    project = store.load_project()
    assert project is not None, f"project {spec.slug!r} is not onboarded"
    if choose_mode(store.list_sources())[0] != EXPECTED_MODE[spec.mode]:
        raise ValueError("acceptance mode differs from stored teaching inputs; "
                         "use an isolated baseline")
    runners: dict[StageName, Any] = {StageName.MODEL: make_model_runner()}
    teaching = next((s for s in store.list_sources() if s.kind is SourceKind.VIDEO), None)
    if spec.mode == "teaching":
        if teaching is None or seams.ingest_provider is None:
            raise ValueError("teaching mode needs a video source with a path and a provider")
        runners[StageName.INGEST] = make_ingest_runner(
            teaching, spec.slug, seams.ingest_provider)
    else:
        if seams.crawl_fn is None:
            raise ValueError("url_only mode needs a crawl_fn")
        runners[StageName.DISCOVER] = make_discover_runner(project, seams.crawl_fn)
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    ctx = StageContext(store=store, run_id=f"orch-{ulid()}", runners=runners, secrets=secrets)
    return run_or_resume(project, ctx)


def _press_run(client: Any, store: ProjectStore) -> str:
    before = {p.name for p in store.paths.runs_dir.iterdir()} if store.paths.runs_dir.exists() \
        else set()
    _check(client.post(f"/projects/{store.paths.slug}/run", follow_redirects=False), "run")
    made = [p.name for p in store.paths.runs_dir.iterdir()
            if p.name not in before and store.load_run(p.name) is not None]
    if len(made) != 1:
        raise AssertionError(f"expected exactly one new UI run, found {made}")
    return made[0]


def _review_proposals_in_ui(client: Any, store: ProjectStore, slug: str, by: str) -> None:
    """GA5: stage, then bulk-approve every proposal through the proposal-review page's routes."""
    base = f"/projects/{slug}/proposals"
    _check(client.get(base), "proposals page")
    _check(client.post(f"{base}/stage", follow_redirects=False), "stage proposals")
    ids = [p.id for p in store.list_case_proposals()]
    if not ids:
        raise AssertionError("no case proposals were staged for review")
    _check(client.post(f"{base}/review", data={"by": by, "decision": "approve",
                                                "proposal_id": ids},
                       follow_redirects=False), "approve proposals")


def run_mode(client: Any, store: ProjectStore, spec: ModeSpec, seams: ModeSeams,
             *, approver: str = "acceptance-reviewer") -> ModeResult:
    """Onboard -> orchestrate -> approve -> generate -> run -> score, through the app."""
    slug = spec.slug
    if spec.onboard:
        _check(client.post("/onboard", data=spec.form(), follow_redirects=False), "onboard")
    state = enter_pipeline(store, spec, seams)
    _check(client.post(f"/projects/{slug}/flowspec/approve",
                       data={"by": approver, "note": "generic acceptance"},
                       follow_redirects=False), "flowspec approve")
    _review_proposals_in_ui(client, store, slug, approver)
    _check(client.post(f"/projects/{slug}/cases/generate", follow_redirects=False), "generate")
    if seams.before_run is not None:
        seams.before_run(store)
    run_id = _press_run(client, store)
    bench_from_run(store, slug, run_id, seams.case_bug_map)
    comparison = build_comparison(store, slug)
    return ModeResult(spec.mode, state, run_id, comparison, completeness_problems(comparison))

