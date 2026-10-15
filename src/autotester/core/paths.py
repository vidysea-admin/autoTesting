"""Filesystem layout. The ONLY place project paths are constructed.

Every artifact lives under `projects/<slug>/` as a human-readable file. Nothing
in the system may build these paths by string concatenation elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path

from autotester.core.repo_docs import RepoDocs
from autotester.core.safe_names import SLUG_PATTERN, UnsafeName, safe_name

__all__ = ["ENV_ROOT", "SLUG_PATTERN", "ProjectPaths", "RepoDocs", "repo_root", "team_path",
           "work_dir"]

ENV_ROOT = "AUTOTESTER_ROOT"


def repo_root() -> Path:
    """Repository root; overridable via `AUTOTESTER_ROOT` (used by tests)."""
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[3]


class ProjectPaths:
    """Resolved paths for one project. Construct with a slug, ask for what you need."""

    def __init__(self, slug: str, root: Path | None = None) -> None:
        self.slug = slug
        self.root = root or repo_root()

    @property
    def dir(self) -> Path:
        return self.root / "projects" / self.slug

    @property
    def config(self) -> Path:
        return self.dir / "project.json"

    @property
    def approvals(self) -> Path:
        """Human-granted `RunApproval` rows (D-018). Append-only in practice: an
        approval is never edited, it expires or a new one is granted."""
        return self.dir / "approvals.jsonl"

    @property
    def approval_revocations(self) -> Path:
        """Signed `ApprovalRevocation` rows; sibling of `approvals.jsonl`."""
        return self.dir / "approval_revocations.jsonl"

    @property
    def env_file(self) -> Path:
        """One credential file for the whole repo, at the root (Umesh, 2026-09-03).

        Keys are namespaced per project (`PATHLYNKS_*`) and declared in each
        project's `SecretRef[]`; a project can only resolve the keys it declares.
        """
        return self.root / ".env"

    @property
    def sources_dir(self) -> Path:
        return self.dir / "sources"

    @property
    def sources_index(self) -> Path:
        return self.dir / "sources.jsonl"

    @property
    def flowspec(self) -> Path:
        return self.dir / "flowspec.json"

    @property
    def cases(self) -> Path:
        return self.dir / "cases.jsonl"

    @property
    def case_proposals(self) -> Path:
        """Step-less candidates and their human review, separate from executable cases."""
        return self.dir / "case_proposals.jsonl"

    @property
    def rubrics_dir(self) -> Path:
        return self.dir / "rubrics"

    @property
    def scripts_dir(self) -> Path:
        return self.dir / "scripts"

    @property
    def runs_dir(self) -> Path:
        return self.dir / "runs"

    @property
    def requests(self) -> Path:
        return self.dir / "requests.jsonl"

    @property
    def knowledge(self) -> Path:
        return self.dir / "knowledge.md"

    @property
    def portal_persona(self) -> Path:
        """The durable cross-run product model (T-164). One JSON file per
        project; `knowledge` is its regenerated human-readable view."""
        return self.dir / "portal_persona.json"

    @property
    def user_personas(self) -> Path:
        """T-190: advisory `UserPersona` rows, one per line (id-keyed)."""
        return self.dir / "user_personas.jsonl"

    @property
    def bench_dir(self) -> Path:
        return self.dir / "bench"

    def bench_corpus(self, corpus_id: str) -> Path:
        return self.bench_dir / f"{corpus_id}.json"

    def bench_trial(self, trial_id: str) -> Path:
        return self.bench_dir / f"{trial_id}.trial.json"

    def bench_comparison(self, corpus_id: str) -> Path:
        """The T-136 acceptance-comparison artifact for one corpus."""
        return self.bench_dir / f"{corpus_id}.comparison.json"

    def bench_human_trial(self, corpus_id: str) -> Path:
        """Where the independent human list plugs in (D-089 item 3): a `BenchTrial`
        JSON of kind `human_live`, plus a `human_confirmed` corpus at `bench_corpus`.
        The `.trial.json` suffix is all `list_bench_trials` needs to pick it up."""
        return self.bench_dir / f"{corpus_id}.human.trial.json"

    @property
    def profile_dir(self) -> Path:
        """Persistent browser profile — gitignored, holds the logged-in session."""
        return self.root / "profiles" / self.slug

    def run_dir(self, run_id: str) -> Path:
        """`runs/<run_id>`; the id must be one safe path segment and the result stay under
        `runs_dir` (AT-900: `--run-id ../x` must never write outside runs/)."""
        target = (self.runs_dir / safe_name(run_id)).resolve()
        if not target.is_relative_to(self.runs_dir.resolve()):
            raise UnsafeName(f"unsafe run id {run_id!r}: resolves outside the runs directory")
        return self.runs_dir / run_id

    def pipeline_artifact(self, run_id: str, name: str) -> Path:
        """Run-local stage inputs/progress, never confused with case result JSON."""
        return self.run_dir(run_id) / "pipeline" / f"{safe_name(name)}.json"

    @property
    def flow_plans(self) -> Path:
        """Persisted per-flow validation plans a release run stitches together (T-167, RR6)."""
        return self.dir / "flow_plans.jsonl"

    def run_release_scope(self, run_id: str) -> Path:
        """The release's frozen scope (T-167): written once, before the human confirm."""
        return self.run_dir(run_id) / "scope.json"

    def run_release_record(self, run_id: str) -> Path:
        """The release's durable record + single issues log (T-167); T-168 reads this."""
        return self.run_dir(run_id) / "release.json"

    def bundles_dir(self, run_id: str) -> Path:
        """Where a run's failure bundles live (T-178); each is one directory."""
        return self.run_dir(run_id) / "bundles"

    def run_trace(self, run_id: str) -> Path:
        """The redacted per-run trace (D-041 phase 1, RT1) -- `trace_id`
        equals `run_id`, never re-minted (RT2)."""
        return self.run_dir(run_id) / "trace.jsonl"

    def run_ux_report(self, run_id: str) -> Path:
        """T-190/PU2: the run's advisory UX findings -- beside, never in, a case result."""
        return self.run_dir(run_id) / "ux_report.json"

    # -- Track A: video learning (D-014) ---------------------------------------
    def source_dir(self, source_id: str) -> Path:
        return self.dir / "sources" / source_id

    def source_media(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "media.json"

    def source_transcript(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "transcript.json"

    def source_chunks_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "chunks"

    def source_frames_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "frames"

    def source_observations_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "observations"

    def source_observation(
        self, source_id: str, provider_label: str, prompt_name: str, chunk_index: int
    ) -> Path:
        label = provider_label.replace(":", "_").replace("/", "_")
        name = f"{label}__{prompt_name}__{chunk_index:02d}.json"
        return self.source_observations_dir(source_id) / name

    def source_analysis(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "analysis.json"

    def review_path(self, review_id: str) -> Path:
        return self.dir / "reviews" / f"{review_id}.json"

    def review_work_dir(self, review_id: str) -> Path:
        return self.dir / "reviews" / review_id

    @property
    def issues(self) -> Path:
        return self.dir / "issues.jsonl"

    @property
    def screen_map(self) -> Path:
        return self.dir / "screenmap.json"

    # -- Track B: autonomous explorer (D-015) ----------------------------------
    @property
    def crawls_dir(self) -> Path:
        return self.dir / "crawl"

    @property
    def crawl_summaries_dir(self) -> Path:
        """Tracked, redacted one-file summaries of finished crawls (the full crawl dir is
        gitignored), so a done_check can pass from a clean checkout."""
        return self.dir / "crawl_summaries"

    def crawl_summary(self, crawl_id: str) -> Path:
        return self.crawl_summaries_dir / f"{crawl_id}.json"

    def crawl_dir(self, crawl_id: str) -> Path:
        return self.crawls_dir / crawl_id

    def crawl_shots_dir(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "shots"

    def crawl_nodes(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "nodes.jsonl"

    def crawl_edges(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "edges.jsonl"

    def crawl_issues(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "issues.jsonl"

    def crawl_network(self, crawl_id: str) -> Path:
        """T-170/NA1: first-party NETWORK evidence captured during the crawl."""
        return self.crawl_dir(crawl_id) / "network.jsonl"

    def crawl_frontier(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "frontier.json"

    def crawl_manifest(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "crawl.json"

    def ensure(self) -> None:
        """Create the directories a project needs. Safe to call repeatedly."""
        for path in (self.dir, self.sources_dir, self.rubrics_dir, self.scripts_dir,
                     self.runs_dir, self.profile_dir, self.bench_dir):
            path.mkdir(parents=True, exist_ok=True)


def work_dir(root: Path | None = None) -> Path:
    """Scratch space. Nothing here is committed; nothing outside here is scratch."""
    path = (root or repo_root()) / ".work"
    path.mkdir(parents=True, exist_ok=True)
    return path


def team_path(*parts: str, root: Path | None = None) -> Path:
    """A path under the team data root, `<data root>/.work/team/` (T-205/TF7).

    Every part is checked by `core.safe_names.safe_name`, so a slug, id or encoded slot key
    that could escape the root raises `UnsafeName` before any file is touched. `.work/` is
    ignored by git and by `.dockerignore`, so nothing under it is ever committed or baked in."""
    return (root or repo_root()) / ".work" / "team" / Path(*(safe_name(p) for p in parts))
